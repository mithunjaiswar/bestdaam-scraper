from playwright.sync_api import TimeoutError


def safe_text(locator):
    try:
        if locator.count() > 0:
            return locator.first.inner_text(timeout=2000).strip()
    except:
        pass
    return ""


def safe_attr(locator, attr):
    try:
        if locator.count() > 0:
            value = locator.first.get_attribute(attr)
            if value:
                return value.strip()
    except:
        pass
    return ""


def parse_products(page):

    products = []

    cards = page.locator("div[data-id]")

    total = cards.count()

    print(f"Products Found: {total}")

    for i in range(total):

        card = cards.nth(i)

        try:

            # --------------------------
            # Product Name (Universal)
            # --------------------------

            name = ""

            name_selectors = [
                ".RG5Slk",      # Mobiles
                ".wjcEIp",      # Electronics
                ".KzDlHZ",      # New Flipkart Layout
                ".syl9yP",      # Fashion
                "a[title]",
                "img[alt]"
            ]

            for selector in name_selectors:

                name = safe_text(card.locator(selector))

                if name:
                    break

            if not name:
                name = safe_attr(card.locator("img"), "alt")

            if not name:
                continue

            # --------------------------
            # Price
            # --------------------------

            price = ""

            price_selectors = [
                ".Nx9bqj",
                ".hZ3P6w",
                "div._30jeq3"
            ]

            for selector in price_selectors:

                price = safe_text(card.locator(selector))

                if price:
                    break

            # --------------------------
            # MRP
            # --------------------------

            mrp = safe_text(card.locator(".kRYCnD"))

            # --------------------------
            # Discount
            # --------------------------

            discount = safe_text(card.locator(".HQe8jr span"))

            # --------------------------
            # Rating
            # --------------------------

            rating = safe_text(card.locator(".MKiFS6"))

            # --------------------------
            # Ratings & Reviews
            # --------------------------

            ratings_reviews = safe_text(card.locator(".PvbNMB"))

            # --------------------------
            # Image
            # --------------------------

            image = ""

            image_selectors = [
                "img.UCc1lI",
                "img.DByuf4",
                "img"
            ]

            for selector in image_selectors:

                image = safe_attr(card.locator(selector), "src")

                if image:
                    break

            # --------------------------
            # Product URL
            # --------------------------

            link = safe_attr(card.locator("a"), "href")

            if link and not link.startswith("http"):
                link = "https://www.flipkart.com" + link

            # --------------------------
            # Save Product
            # --------------------------

            products.append({
                "name": name,
                "price": price,
                "mrp": mrp,
                "discount": discount,
                "rating": rating,
                "ratings_reviews": ratings_reviews,
                "image": image,
                "url": link
            })

        except Exception as e:
            print(f"Skipped Card {i+1}: {e}")

    return products