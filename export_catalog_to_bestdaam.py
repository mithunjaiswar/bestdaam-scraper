import csv
from datetime import datetime
import json
import os
import re
import shutil
import sqlite3
from urllib.parse import urlparse


DB_PATH = "products.db"
COMPARISON_CSV = "output/comparison.csv"
SITE_DIR = os.path.expanduser(
    os.environ.get("BESTDAAM_SITE_DIR", "~/Desktop/bestdaam-price")
)
OUTPUT_JSON = os.path.join(SITE_DIR, "data", "products.json")

MAX_PRODUCTS_PER_CATEGORY = 100
PRODUCT_LIMITS_BY_CATEGORY = {
    "stationery": 200,
}


CATEGORY_LABELS = {
    "mobiles": "Mobile",
    "iphone": "iPhone",
    "laptops": "Laptop",
    "headphones": "Headphones",
    "earbuds": "Earbuds",
    "wired_earphones": "Wired Earphones",
    "mens_clothing": "Men's Clothing",
    "smartwatches": "Smartwatch",
    "televisions": "Television",
    "speakers": "Speaker",
    "tablets": "Tablet",
    "cameras": "Camera",
    "stationery": "Stationery",
    "requested_products": "Requested Products",
}


CATEGORY_EMOJIS = {
    "mobiles": "📱",
    "iphone": "📱",
    "laptops": "💻",
    "headphones": "🎧",
    "earbuds": "🎧",
    "wired_earphones": "🎧",
    "mens_clothing": "👕",
    "smartwatches": "⌚",
    "televisions": "📺",
    "speakers": "🔊",
    "tablets": "📱",
    "cameras": "📷",
    "stationery": "✏️",
    "requested_products": "🛍️",
}


def clean_text(value):
    if value is None:
        return ""

    value = str(value).strip()
    value = value.replace("...", "")
    value = value.replace("…", "")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_price(value):
    if value is None:
        return None

    value = str(value)
    value = value.replace("₹", "")
    value = value.replace(",", "")
    value = value.strip()

    match = re.search(r"\d+(?:\.\d+)?", value)

    if not match:
        return None

    return int(float(match.group(0)))


def slugify(value):
    value = str(value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")

    return value


def normalize_key(value):
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def normalize_url(value):
    value = clean_text(value)

    if not value:
        return ""

    parsed = urlparse(value)
    hostname = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/").lower()

    if hostname and path:
        return f"{hostname}{path}"

    return value.split("?")[0].split("#")[0].rstrip("/").lower()


def load_existing_affiliate_urls():
    affiliate_urls = {}

    if not os.path.exists(OUTPUT_JSON):
        return affiliate_urls

    try:
        with open(OUTPUT_JSON, "r", encoding="utf-8") as file:
            products = json.load(file)
    except (OSError, json.JSONDecodeError):
        return affiliate_urls

    for product in products:
        for price_entry in product.get("prices", []):
            original_url = normalize_url(price_entry.get("url"))
            affiliate_url = clean_text(price_entry.get("affiliateUrl"))

            if original_url and affiliate_url:
                affiliate_urls[original_url] = affiliate_url

    return affiliate_urls


def load_existing_affiliate_urls_by_product():
    affiliate_urls = {}

    if not os.path.exists(OUTPUT_JSON):
        return affiliate_urls

    try:
        with open(OUTPUT_JSON, "r", encoding="utf-8") as file:
            products = json.load(file)
    except (OSError, json.JSONDecodeError):
        return affiliate_urls

    for product in products:
        category_key = clean_text(product.get("categoryKey")).lower()
        product_names = {
            normalize_key(product.get("rawName")),
            normalize_key(product.get("name")),
        }
        product_names.discard("")

        if not category_key or not product_names:
            continue

        for price_entry in product.get("prices", []):
            if clean_text(price_entry.get("store")).lower() != "flipkart":
                continue

            affiliate_url = clean_text(price_entry.get("affiliateUrl"))

            if affiliate_url:
                for product_name in product_names:
                    affiliate_urls[(category_key, product_name)] = (
                        affiliate_url
                    )

    return affiliate_urls


def load_existing_amazon_entries():
    entries = {}

    if not os.path.exists(OUTPUT_JSON):
        return entries

    try:
        with open(OUTPUT_JSON, "r", encoding="utf-8") as file:
            products = json.load(file)
    except (OSError, json.JSONDecodeError):
        return entries

    for product in products:
        key = normalize_key(product.get("rawName") or product.get("name"))

        for price_entry in product.get("prices", []):
            if clean_text(price_entry.get("store")).lower() != "amazon":
                continue

            price = clean_price(price_entry.get("price"))
            url = clean_text(price_entry.get("url"))

            if key and price and url:
                entries[key] = {
                    "store": "Amazon",
                    "price": price,
                    "url": url,
                }

    return entries


def smart_title(value):
    text = clean_text(value).title()

    replacements = {
        "Dji": "DJI",
        "Osmo": "Osmo",
        "Iphone": "iPhone",
        "Samsung": "Samsung",
        "Asus": "ASUS",
        "Hp": "HP",
        "Dell": "Dell",
        "Msi": "MSI",
        "Amd": "AMD",
        "Intel": "Intel",
        "Ryzen": "Ryzen",
        "Geforce": "GeForce",
        "Rtx": "RTX",
        "Gtx": "GTX",
        "Ssd": "SSD",
        "Emmc": "EMMC",
        "Ram": "RAM",
        "Gb": "GB",
        "Tb": "TB",
        "Usb": "USB",
        "Wifi": "WiFi",
        "Hd": "HD",
        "Full Hd": "Full HD",
        "Ultra Hd": "Ultra HD",
        "Uhd": "UHD",
        "Led": "LED",
        "Qled": "QLED",
        "Oled": "OLED",
        "Tv": "TV",
        "Cm": "cm",
        "Mm": "mm",
        "Db": "dB",
    }

    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    text = re.sub(r"iPhone\s+(\d+)E\b", r"iPhone \1e", text)

    return text


def limit_words(text, max_words=12):
    words = clean_text(text).split()

    if len(words) <= max_words:
        return clean_text(text)

    return " ".join(words[:max_words])


def extract_bracket_specs(name):
    match = re.search(r"\((.*?)\)", name)

    if not match:
        return ""

    specs = match.group(1)

    ram = ""
    storage = ""

    ram_match = re.search(r"(\d+\s*GB)\s*/", specs, flags=re.I)
    storage_match = re.search(r"(\d+\s*(?:GB|TB)\s*SSD|\d+\s*(?:GB|TB)\s*EMMC)", specs, flags=re.I)

    if ram_match:
        ram = ram_match.group(1).replace(" ", "")

    if storage_match:
        storage = re.sub(r"\s+", " ", storage_match.group(1)).upper()

    if ram and storage:
        return f"{ram} / {storage}"

    if ram:
        return ram

    if storage:
        return storage

    return ""


def clean_laptop_name(name):
    raw = clean_text(name)

    # Keep laptop model part before detailed specs.
    base = raw.split(" - ")[0].strip()

    # Remove marketing text.
    base = re.sub(r"\bwith Office.*", "", base, flags=re.I).strip()
    base = re.sub(r"\bwith MSO.*", "", base, flags=re.I).strip()
    base = re.sub(r"\bwith Backlit.*", "", base, flags=re.I).strip()
    base = re.sub(r"\bwith 1 Yr.*", "", base, flags=re.I).strip()

    specs = extract_bracket_specs(raw)

    base = limit_words(base, 11)
    display = smart_title(base)

    if specs:
        display = f"{display} ({specs})"

    return display


def clean_camera_name(name):
    raw = clean_text(name)

    lower = raw.lower()

    if "osmo pocket 3 creator combo" in lower:
        return "DJI Osmo Pocket 3 Creator Combo"

    if "osmo nano standard combo" in lower:
        storage_match = re.search(r"\((\d+\s*GB)\)", raw, flags=re.I)
        storage = f" ({storage_match.group(1).replace(' ', '')})" if storage_match else ""
        return f"DJI Osmo Nano Standard Combo{storage}"

    if "canon eos r50" in lower:
        return "Canon EOS R50 Mirrorless Camera"

    if "sports and action" in lower:
        base = re.split(r"sports and action", raw, flags=re.I)[0].strip()
        return smart_title(limit_words(base, 9))

    if "mirrorless camera" in lower:
        base = re.split(r"mirrorless camera", raw, flags=re.I)[0].strip()
        return smart_title(f"{limit_words(base, 8)} Mirrorless Camera")

    if "dslr camera" in lower:
        base = re.split(r"dslr camera", raw, flags=re.I)[0].strip()
        return smart_title(f"{limit_words(base, 8)} DSLR Camera")

    return smart_title(limit_words(raw, 10))


def clean_mobile_name(name, category_key):
    raw = clean_text(name)

    # Flipkart phones usually look like: Name (Color, Storage)
    if "(" in raw:
        base = raw.split("(")[0].strip()
        inside = re.search(r"\((.*?)\)", raw)

        if inside:
            parts = [p.strip() for p in inside.group(1).split(",")]
            storage = ""

            for part in parts:
                if re.search(r"\d+\s*GB|\d+\s*TB", part, flags=re.I):
                    storage = part.replace(" ", "")

            if storage:
                return smart_title(f"{base} ({storage})")

        return smart_title(base)

    if category_key == "iphone":
        storage_match = re.search(r"\b(\d+\s*(?:GB|TB))\b", raw, flags=re.I)
        storage = storage_match.group(1).replace(" ", "") if storage_match else ""

        base = limit_words(raw, 5)
        display = smart_title(base)

        if storage and storage not in display:
            display = f"{display} ({storage})"

        return display

    return smart_title(limit_words(raw, 8))


def clean_tv_name(name):
    raw = clean_text(name)

    # Keep size + resolution + smart TV info.
    size = ""
    resolution = ""

    cm_match = re.search(r"(\d+\s*cm)", raw, flags=re.I)
    inch_match = re.search(r"(\d+\s*inch)", raw, flags=re.I)

    if cm_match and inch_match:
        size = f"{cm_match.group(1)} ({inch_match.group(1)})"
    elif inch_match:
        size = inch_match.group(1)
    elif cm_match:
        size = cm_match.group(1)

    if re.search(r"full\s*hd", raw, flags=re.I):
        resolution = "Full HD"
    elif re.search(r"hd\s*ready", raw, flags=re.I):
        resolution = "HD Ready"
    elif re.search(r"4k|ultra\s*hd|uhd", raw, flags=re.I):
        resolution = "4K Ultra HD"

    brand = raw.split()[0] if raw.split() else ""

    parts = [brand]

    if size:
        parts.append(size)

    if resolution:
        parts.append(resolution)

    parts.append("Smart TV")

    return smart_title(" ".join(parts))


def clean_general_name(name):
    raw = clean_text(name)

    raw = re.split(r"\s+-\s+", raw)[0]
    raw = re.split(r"\s+\|\s+", raw)[0]
    raw = re.split(r"\bwith\b", raw, flags=re.I)[0]
    raw = re.split(r"\bfor\b", raw, flags=re.I)[0]

    return smart_title(limit_words(raw, 10))


def clean_product_name(name, category_key):
    if category_key == "laptops":
        return clean_laptop_name(name)

    if category_key == "cameras":
        return clean_camera_name(name)

    if category_key in ["mobiles", "iphone"]:
        return clean_mobile_name(name, category_key)

    if category_key == "televisions":
        return clean_tv_name(name)

    return clean_general_name(name)


def load_amazon_matches():
    matches = {}

    if not os.path.exists(COMPARISON_CSV):
        print(f"Comparison file not found: {COMPARISON_CSV}")
        print("Amazon matched price skip hoga.")
        return matches

    with open(COMPARISON_CSV, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            flipkart_product = clean_text(row.get("flipkart_product"))
            amazon_product = clean_text(row.get("amazon_product"))
            amazon_price = clean_price(row.get("amazon_price"))
            amazon_url = clean_text(row.get("amazon_url"))

            if not flipkart_product or not amazon_price or not amazon_url:
                continue

            key = normalize_key(flipkart_product)

            matches[key] = {
                "store": "Amazon",
                "price": amazon_price,
                "url": amazon_url,
                "matched_product": amazon_product,
            }

    return matches


def load_flipkart_products():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            name,
            category,
            price,
            image,
            url,
            rating,
            ratings_reviews,
            last_seen_at
        FROM products
        WHERE LOWER(source) = 'flipkart'
        ORDER BY category, id
        """
    )

    rows = cursor.fetchall()
    connection.close()

    return rows


def deduplicate_flipkart_rows(rows):
    best_rows = {}
    key_order = []

    for row in rows:
        category_key = clean_text(row["category"]).lower()
        display_name = clean_product_name(row["name"], category_key)
        product_key = (category_key, normalize_key(display_name))
        price = clean_price(row["price"])

        if not product_key[1] or not price:
            continue

        if product_key not in best_rows:
            best_rows[product_key] = row
            key_order.append(product_key)
            continue

        existing_row = best_rows[product_key]
        observed_at = clean_text(row["last_seen_at"])
        existing_observed_at = clean_text(existing_row["last_seen_at"])

        if observed_at > existing_observed_at:
            best_rows[product_key] = row
            continue

        existing_price = clean_price(existing_row["price"])

        if (
            observed_at == existing_observed_at
            and (not existing_price or price < existing_price)
        ):
            best_rows[product_key] = row

    return [best_rows[key] for key in key_order]


def load_flipkart_price_history():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            product_url,
            observed_on,
            price
        FROM price_history
        WHERE LOWER(source) = 'flipkart'
          AND observed_on >= DATE('now', '-89 day', 'localtime')
        ORDER BY product_url, observed_on
        """
    )

    history_by_url = {}

    for row in cursor.fetchall():
        history_by_url.setdefault(row["product_url"], []).append(
            {
                "date": row["observed_on"],
                "price": row["price"],
            }
        )

    connection.close()
    return history_by_url


def make_unique_id(base_id, used_ids):
    if base_id not in used_ids:
        used_ids.add(base_id)
        return base_id

    counter = 2

    while True:
        new_id = f"{base_id}-{counter}"

        if new_id not in used_ids:
            used_ids.add(new_id)
            return new_id

        counter += 1


def build_product(
    row,
    amazon_matches,
    existing_affiliate_urls,
    existing_affiliate_urls_by_product,
    existing_amazon_entries,
    price_history_by_url,
    used_amazon_urls,
    used_ids,
):
    raw_name = clean_text(row["name"])
    category_key = clean_text(row["category"]).lower()
    flipkart_price = clean_price(row["price"])
    flipkart_url = clean_text(row["url"])
    image = clean_text(row["image"])

    if not raw_name or not flipkart_price or not flipkart_url:
        return None

    display_name = clean_product_name(raw_name, category_key)

    category = CATEGORY_LABELS.get(category_key, "Electronics")
    emoji = CATEGORY_EMOJIS.get(category_key, "🛍️")

    base_id = slugify(f"{category_key}-{display_name}")
    product_id = make_unique_id(base_id, used_ids)

    flipkart_entry = {
        "store": "Flipkart",
        "price": flipkart_price,
        "url": flipkart_url,
    }

    existing_affiliate_url = existing_affiliate_urls.get(
        normalize_url(flipkart_url)
    )

    if not existing_affiliate_url:
        existing_affiliate_url = existing_affiliate_urls_by_product.get(
            (category_key, normalize_key(raw_name))
        )

    if not existing_affiliate_url:
        existing_affiliate_url = existing_affiliate_urls_by_product.get(
            (category_key, normalize_key(display_name))
        )

    if existing_affiliate_url:
        flipkart_entry["affiliateUrl"] = existing_affiliate_url

    prices = [flipkart_entry]

    amazon_match = amazon_matches.get(normalize_key(raw_name))

    if not amazon_match:
        amazon_match = existing_amazon_entries.get(normalize_key(raw_name))

    if (
        amazon_match
        and amazon_match["url"] not in used_amazon_urls
    ):
        prices.append(
            {
                "store": "Amazon",
                "price": amazon_match["price"],
                "url": amazon_match["url"],
            }
        )
        used_amazon_urls.add(amazon_match["url"])

    price_history = price_history_by_url.get(flipkart_url, [])

    return {
        "id": product_id,
        "name": display_name,
        "rawName": raw_name,
        "category": category,
        "categoryKey": category_key,
        "emoji": emoji,
        "image": image,
        "rating": clean_text(row["rating"]),
        "ratings_reviews": clean_text(row["ratings_reviews"]),
        "priceHistory": price_history,
        "lastUpdated": (
            price_history[-1]["date"]
            if price_history
            else ""
        ),
        "prices": prices,
    }


def main():
    amazon_matches = load_amazon_matches()
    flipkart_rows = deduplicate_flipkart_rows(load_flipkart_products())
    price_history_by_url = load_flipkart_price_history()
    existing_affiliate_urls = load_existing_affiliate_urls()
    existing_affiliate_urls_by_product = (
        load_existing_affiliate_urls_by_product()
    )
    existing_amazon_entries = load_existing_amazon_entries()

    products = []
    used_ids = set()
    used_amazon_urls = set()
    category_counts = {}

    for row in flipkart_rows:
        category_key = clean_text(row["category"]).lower()

        current_count = category_counts.get(category_key, 0)
        category_limit = PRODUCT_LIMITS_BY_CATEGORY.get(
            category_key,
            MAX_PRODUCTS_PER_CATEGORY,
        )

        if current_count >= category_limit:
            continue

        product = build_product(
            row=row,
            amazon_matches=amazon_matches,
            existing_affiliate_urls=existing_affiliate_urls,
            existing_affiliate_urls_by_product=(
                existing_affiliate_urls_by_product
            ),
            existing_amazon_entries=existing_amazon_entries,
            price_history_by_url=price_history_by_url,
            used_amazon_urls=used_amazon_urls,
            used_ids=used_ids,
        )

        if not product:
            continue

        products.append(product)
        category_counts[category_key] = current_count + 1

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    os.makedirs("output", exist_ok=True)

    if os.path.exists(OUTPUT_JSON):
        backup_path = os.path.join(
            "output",
            "products_before_export_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        shutil.copy2(OUTPUT_JSON, backup_path)
        print(f"Backup saved             : {backup_path}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(products, file, ensure_ascii=False, indent=2)

    print("=" * 80)
    print(f"Products exported       : {len(products)}")
    print(f"Amazon matched products : {len(amazon_matches)}")
    print(f"Saved to                : {OUTPUT_JSON}")
    print("=" * 80)

    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count}")

    print("=" * 80)

    two_store_count = 0

    for product in products:
        if len(product["prices"]) > 1:
            two_store_count += 1

    print(f"Products with 2 stores  : {two_store_count}")
    print(f"Products with 1 store   : {len(products) - two_store_count}")
    print("=" * 80)


if __name__ == "__main__":
    main()
