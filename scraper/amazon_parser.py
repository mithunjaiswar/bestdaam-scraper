from urllib.parse import urljoin

from playwright.async_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)


AMAZON_BASE_URL = "https://www.amazon.in"


async def safe_text(locator: Locator) -> str:
    try:
        if await locator.count() == 0:
            return ""

        text = await locator.first.inner_text(timeout=2000)
        return text.strip()

    except PlaywrightTimeoutError:
        return ""

    except Exception:
        return ""


async def safe_attr(
    locator: Locator,
    attribute: str,
) -> str:
    try:
        if await locator.count() == 0:
            return ""

        value = await locator.first.get_attribute(
            attribute,
            timeout=2000,
        )

        return value.strip() if value else ""

    except PlaywrightTimeoutError:
        return ""

    except Exception:
        return ""


async def first_text(
    card: Locator,
    selectors: list[str],
) -> str:
    for selector in selectors:
        value = await safe_text(
            card.locator(selector)
        )

        if value:
            return value

    return ""


async def first_attr(
    card: Locator,
    selectors: list[str],
    attribute: str,
) -> str:
    for selector in selectors:
        value = await safe_attr(
            card.locator(selector),
            attribute,
        )

        if value:
            return value

    return ""


async def parse_products(page: Page) -> list[dict]:
    product_cards = page.locator(
        'div[data-component-type="s-search-result"]'
    )

    product_count = await product_cards.count()

    print(f"Products Found: {product_count}")

    products: list[dict] = []
    skipped_count = 0

    for index in range(product_count):
        card = product_cards.nth(index)

        # Amazon image alt usually contains the full title.
        name = await first_attr(
            card,
            [
                "img.s-image",
                "img",
            ],
            "alt",
        )

        if not name:
            name = await first_text(
                card,
                [
                    "h2",
                    "h2 a",
                    ".a-size-medium.a-color-base.a-text-normal",
                    ".a-size-base-plus.a-color-base.a-text-normal",
                    "a.a-link-normal.s-line-clamp-2",
                ],
            )

        product_url = await first_attr(
            card,
            [
                "h2 a",
                "a.a-link-normal.s-line-clamp-2",
                "a.a-link-normal.s-no-outline",
                "a.a-link-normal.a-text-normal",
                "a[href*='/dp/']",
                "a[href*='/gp/']",
            ],
            "href",
        )

        if product_url:
            product_url = urljoin(
                AMAZON_BASE_URL,
                product_url,
            )

        price_whole = await first_text(
            card,
            [
                ".a-price-whole",
                "span.a-offscreen",
            ],
        )

        price_fraction = await safe_text(
            card.locator(".a-price-fraction")
        )

        price = ""

        if price_whole:
            cleaned_whole = (
                price_whole
                .replace("₹", "")
                .replace(",", "")
                .replace(".", "")
                .strip()
            )

            if price_fraction:
                price = f"{cleaned_whole}.{price_fraction}"
            else:
                price = cleaned_whole

        mrp = await first_text(
            card,
            [
                ".a-price.a-text-price span.a-offscreen",
                ".a-price.a-text-price span",
            ],
        )

        rating = await first_text(
            card,
            [
                ".a-icon-alt",
                "span[aria-label*='stars']",
            ],
        )

        ratings_reviews = await first_text(
            card,
            [
                "span.a-size-base.s-underline-text",
                "a[href*='customerReviews'] span",
            ],
        )

        image = await first_attr(
            card,
            [
                "img.s-image",
                "img",
            ],
            "src",
        )

        if not name or not product_url:
            skipped_count += 1

            if skipped_count <= 3:
                print(
                    f"Skipped card {index + 1}: "
                    f"name={name!r}, "
                    f"url={product_url!r}"
                )

            continue

        if len(products) < 5:
            print(
                f"Amazon product "
                f"{len(products) + 1}: {name}"
            )

        products.append(
            {
                "name": name,
                "price": price,
                "mrp": mrp,
                "discount": "",
                "rating": rating,
                "ratings_reviews": ratings_reviews,
                "image": image,
                "url": product_url,
            }
        )

    print(f"Successfully Parsed: {len(products)}")
    print(f"Skipped Products   : {skipped_count}")

    return products