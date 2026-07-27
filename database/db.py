import sqlite3
import re
from typing import Any


class Database:
    def __init__(self, db_name: str = "products.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

        self.create_table()
        self.ensure_source_column()
        self.ensure_last_seen_column()
        self.create_price_history_table()
        self.backfill_current_prices()

    def create_table(self) -> None:
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT,
                category TEXT,

                price TEXT,
                mrp TEXT,
                discount TEXT,

                rating TEXT,
                ratings_reviews TEXT,

                image TEXT,
                url TEXT UNIQUE,

                source TEXT
            )
            """
        )

        self.conn.commit()

    def ensure_last_seen_column(self) -> None:
        self.cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in self.cursor.fetchall()]

        if "last_seen_at" not in columns:
            self.cursor.execute(
                "ALTER TABLE products ADD COLUMN last_seen_at TEXT"
            )
            self.conn.commit()

    def create_price_history_table(self) -> None:
        self.cursor.execute(
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
        self.cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_price_history_lookup
            ON price_history(product_url, source, observed_on)
            """
        )
        self.conn.commit()

    @staticmethod
    def parse_price(value: Any) -> int | None:
        if value is None:
            return None

        match = re.search(r"\d+(?:\.\d+)?", str(value).replace(",", ""))

        if not match:
            return None

        price = int(float(match.group(0)))
        return price if price > 0 else None

    def backfill_current_prices(self) -> None:
        self.cursor.execute(
            """
            SELECT url, source, price
            FROM products
            WHERE url IS NOT NULL
              AND source IS NOT NULL
              AND price IS NOT NULL
            """
        )

        for url, source, raw_price in self.cursor.fetchall():
            price = self.parse_price(raw_price)

            if not price:
                continue

            self.cursor.execute(
                """
                INSERT OR IGNORE INTO price_history (
                    product_url,
                    source,
                    price,
                    observed_on,
                    observed_at
                )
                VALUES (?, ?, ?, DATE('now', 'localtime'), DATETIME('now', 'localtime'))
                """,
                (url, source, price),
            )

        self.conn.commit()

    def ensure_source_column(self) -> None:
        """Add source column safely for older databases."""

        self.cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in self.cursor.fetchall()]

        if "source" not in columns:
            self.cursor.execute(
                "ALTER TABLE products ADD COLUMN source TEXT"
            )
            self.conn.commit()

    def insert_product(self, product: dict[str, Any]) -> bool:
        try:
            url = product.get("url")

            if not url:
                return False

            self.cursor.execute(
                "SELECT 1 FROM products WHERE url = ?",
                (url,),
            )
            is_new = self.cursor.fetchone() is None

            self.cursor.execute(
                """
                INSERT INTO products (
                    name,
                    category,
                    price,
                    mrp,
                    discount,
                    rating,
                    ratings_reviews,
                    image,
                    url,
                    source,
                    last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATETIME('now', 'localtime'))
                ON CONFLICT(url) DO UPDATE SET
                    name = excluded.name,
                    category = excluded.category,
                    price = excluded.price,
                    mrp = excluded.mrp,
                    discount = excluded.discount,
                    rating = excluded.rating,
                    ratings_reviews = excluded.ratings_reviews,
                    image = excluded.image,
                    source = excluded.source,
                    last_seen_at = DATETIME('now', 'localtime')
                """,
                (
                    product.get("name"),
                    product.get("category"),
                    product.get("price"),
                    product.get("mrp"),
                    product.get("discount"),
                    product.get("rating"),
                    product.get("ratings_reviews"),
                    product.get("image"),
                    url,
                    product.get("source"),
                ),
            )

            price = self.parse_price(product.get("price"))

            if price:
                self.cursor.execute(
                    """
                    INSERT INTO price_history (
                        product_url,
                        source,
                        price,
                        observed_on,
                        observed_at
                    )
                    VALUES (?, ?, ?, DATE('now', 'localtime'), DATETIME('now', 'localtime'))
                    ON CONFLICT(product_url, source, observed_on)
                    DO UPDATE SET
                        price = excluded.price,
                        observed_at = excluded.observed_at
                    """,
                    (
                        url,
                        product.get("source") or "unknown",
                        price,
                    ),
                )

            self.conn.commit()

            return is_new

        except sqlite3.Error as error:
            print(f"Database insert error: {error}")
            return False

    def close(self) -> None:
        self.conn.close()
