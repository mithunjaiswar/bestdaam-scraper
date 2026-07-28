import json

from scraper.category_filters import product_belongs_to_category
from scraper.exporter import save_to_csv
from scraper.paginator import scrape_top_products


def run_all_categories(
    page,
    base_url,
    db,
    limit=100,
    selected_category=None,
):

    with open("categories.json", "r", encoding="utf-8") as file:
        categories = json.load(file)

    if selected_category:
        categories = [
            category
            for category in categories
            if category["name"] == selected_category
        ]

        if not categories:
            raise ValueError(
                f"Category '{selected_category}' categories.json me nahi mili."
            )

    for category in categories:

        name = category["name"]
        query = category["query"]
        category_limit = int(
            category.get(
                "scrapeLimit",
                category.get("limit", limit),
            )
        )

        print("\n" + "=" * 60)
        print(f"Starting Category : {name}")
        print("=" * 60)

        products = scrape_top_products(
            page=page,
            base_url=base_url,
            category=query,
            limit=category_limit,
        )

        products = [
            product
            for product in products
            if product_belongs_to_category(product, name)
        ]

        saved_count = 0

        for product in products:

            product["category"] = name
            product["source"] = "flipkart"

            db.insert_product(product)
            saved_count += 1

        filename = f"output/{name}.csv"

        save_to_csv(products, filename)

        print(f"Scraped products : {len(products)}")
        print(f"Database handled : {saved_count}")
        print(f"CSV saved        : {filename}")
