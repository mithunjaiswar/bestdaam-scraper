import re
import os
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from scraper.parser import parse_products


def product_name_key(product):
    name = str(product.get("name", "")).lower()
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


def load_results_page(page, url, attempts=None):
    is_ci = os.environ.get("CI", "").lower() == "true"
    attempts = attempts or (2 if is_ci else 3)
    navigation_timeout = 25000 if is_ci else 45000
    selector_timeout = 10000 if is_ci else 20000

    for attempt in range(1, attempts + 1):
        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=navigation_timeout,
            )
            page.wait_for_selector("div[data-id]", timeout=selector_timeout)
            page.wait_for_timeout(1500)
            return
        except (PlaywrightTimeoutError, PlaywrightError) as error:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except PlaywrightError:
                pass

            try:
                if page.locator("div[data-id]").count() > 0:
                    print("Page slow tha, lekin products load ho gaye.")
                    return
            except PlaywrightError:
                pass

            if attempt == attempts:
                raise

            wait_seconds = attempt * 5
            print(
                f"Page load issue ({type(error).__name__}). "
                f"Retry {attempt}/{attempts} "
                f"{wait_seconds} seconds baad..."
            )
            time.sleep(wait_seconds)


def scrape_top_products(page, base_url, category="mobiles", limit=100):
    seen_urls = set()
    seen_names = set()
    all_products = []
    page_no = 1

    while len(all_products) < limit:
        print(f"\n========== PAGE {page_no} ==========")
        url = f"{base_url}/search?q={category}&page={page_no}"
        print(url)
        load_results_page(page, url)
        products = parse_products(page)

        if not products:
            print("No more products found.")
            break

        for product in products:
            url = product.get("url")
            name_key = product_name_key(product)

            if not url or not name_key:
                continue

            if url in seen_urls or name_key in seen_names:
                continue

            seen_urls.add(url)
            seen_names.add(name_key)
            all_products.append(product)

        print(f"Unique Products: {len(all_products)}")

        if len(products) < 24:
            break

        page_no += 1

    return all_products[:limit]
