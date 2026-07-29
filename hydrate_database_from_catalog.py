import json
import os

from database.db import Database


SITE_DIR = os.path.expanduser(
    os.environ.get("BESTDAAM_SITE_DIR", "~/Desktop/bestdaam-price")
)
PRODUCTS_JSON = os.path.join(SITE_DIR, "data", "products.json")
DB_PATH = "products.db"


def main():
    if not os.path.exists(PRODUCTS_JSON):
        raise FileNotFoundError(PRODUCTS_JSON)

    with open(PRODUCTS_JSON, "r", encoding="utf-8") as file:
        products = json.load(file)

    database = Database(DB_PATH)
    restored_products = 0
    restored_history = 0

    for product in products:
        flipkart = next(
            (
                entry
                for entry in product.get("prices", [])
                if str(entry.get("store", "")).lower() == "flipkart"
            ),
            None,
        )

        if not flipkart or not flipkart.get("url"):
            continue

        database.insert_product(
            {
                "name": product.get("rawName") or product.get("name"),
                "category": product.get("categoryKey"),
                "price": flipkart.get("price"),
                "mrp": "",
                "discount": "",
                "rating": product.get("rating"),
                "ratings_reviews": product.get("ratings_reviews"),
                "image": product.get("image"),
                "url": flipkart.get("url"),
                "source": "flipkart",
            }
        )
        restored_products += 1

        for point in product.get("priceHistory", []):
            date = str(point.get("date", "")).strip()
            price = point.get("price")

            if not date or not isinstance(price, (int, float)) or price <= 0:
                continue

            database.cursor.execute(
                """
                INSERT OR IGNORE INTO price_history (
                    product_url, source, price, observed_on, observed_at
                )
                VALUES (?, 'flipkart', ?, ?, ?)
                """,
                (
                    flipkart["url"],
                    int(price),
                    date,
                    f"{date} 00:00:00",
                ),
            )
            restored_history += database.cursor.rowcount

    database.conn.commit()
    database.close()
    print(f"Catalog products restored : {restored_products}")
    print(f"Historical price rows restored: {restored_history}")


if __name__ == "__main__":
    main()
