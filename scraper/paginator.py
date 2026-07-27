import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from scraper.parser import parse_products


def load_results_page(page, url, attempts=3):
    for attempt in range(1, attempts + 1):
        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=45000,
            )
            page.wait_for_selector("div[data-id]", timeout=20000)
            page.wait_for_timeout(1500)
            return
        except PlaywrightTimeoutError:
            if page.locator("div[data-id]").count() > 0:
                print("Page slow tha, lekin products load ho gaye.")
                return

            if attempt == attempts:
                raise

            wait_seconds = attempt * 5
            print(
                f"Page load timeout. Retry {attempt}/{attempts} "
                f"{wait_seconds} seconds baad..."
            )
            time.sleep(wait_seconds)


def scrape_top_products(page, base_url, category="mobiles", limit=100):
    seen = set()
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
            if product["url"] not in seen:
                seen.add(product["url"])
                all_products.append(product)

        print(f"Unique Products: {len(all_products)}")

        if len(products) < 24:
            break

        page_no += 1

    return all_products[:limit]
