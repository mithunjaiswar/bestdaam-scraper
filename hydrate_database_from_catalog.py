import json
import os
import sqlite3


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

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_url TEXT NOT NULL,
            source TEXT NOT NULL,
            price INTEGER NOT NULL,
            observed_on TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            UNIQUE(product_url, source, observed_on)
        )
        """
    )

    inserted = 0

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

        for point in product.get("priceHistory", []):
            date = str(point.get("date", "")).strip()
            price = point.get("price")

            if not date or not isinstance(price, (int, float)) or price <= 0:
                continue

            cursor.execute(
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
            inserted += cursor.rowcount

    connection.commit()
    connection.close()
    print(f"Historical price rows restored: {inserted}")


if __name__ == "__main__":
    main()
