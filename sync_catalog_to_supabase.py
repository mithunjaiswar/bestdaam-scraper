import json
import os
from pathlib import Path

import requests


SITE_DIR = Path(
    os.path.expanduser(
        os.environ.get("BESTDAAM_SITE_DIR", "~/Desktop/bestdaam-price")
    )
)
PRODUCTS_JSON = SITE_DIR / "data" / "products.json"


def request_headers():
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    # Legacy service-role JWTs need the Authorization header. Supabase's
    # modern sb_secret_* keys authenticate through the apikey header only.
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def post_rows(table, rows, batch_size=200):
    base = os.environ["SUPABASE_URL"].rstrip("/")
    headers = request_headers()

    for start in range(0, len(rows), batch_size):
        response = requests.post(
            f"{base}/rest/v1/{table}",
            headers=headers,
            json=rows[start : start + batch_size],
            timeout=90,
        )
        response.raise_for_status()


def main():
    products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
    product_rows = []
    history_rows = []

    for product in products:
        product_rows.append(
            {
                "id": product["id"],
                "name": product["name"],
                "raw_name": product.get("rawName"),
                "category": product.get("category") or "Other",
                "category_key": product.get("categoryKey"),
                "emoji": product.get("emoji"),
                "image_url": product.get("image"),
                "rating": float(product["rating"]) if product.get("rating") else None,
                "ratings_reviews": product.get("ratings_reviews"),
                "last_updated": product.get("lastUpdated") or None,
                "catalog_data": product,
            }
        )

        flipkart = next(
            (
                entry
                for entry in product.get("prices", [])
                if str(entry.get("store", "")).lower() == "flipkart"
            ),
            None,
        )

        if not flipkart:
            continue

        for point in product.get("priceHistory", []):
            if point.get("date") and point.get("price"):
                history_rows.append(
                    {
                        "product_id": product["id"],
                        "store": "Flipkart",
                        "observed_on": point["date"],
                        "price": int(point["price"]),
                        "source_url": flipkart.get("url"),
                    }
                )

    post_rows("products", product_rows)
    post_rows("price_history", history_rows)
    print(
        f"Supabase synced: {len(product_rows)} products, "
        f"{len(history_rows)} price rows"
    )


if __name__ == "__main__":
    main()
