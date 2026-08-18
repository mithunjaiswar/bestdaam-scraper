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

    succeeded = []
    failed = []

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

        try:
            products = scrape_top_products(
                page=page,
                base_url=base_url,
                category=query,
                limit=category_limit,
            )
        except Exception as error:
            failed.append((name, str(error)))
            print(
                f"Category '{name}' temporarily failed: {error}. "
                "Last verified catalog data will be preserved."
            )

            if selected_category:
                raise

            continue

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
        succeeded.append(name)

    if not succeeded:
        raise RuntimeError(
            "All requested categories failed; refusing to publish an "
            "unverified catalog refresh."
        )

    print(
        f"\nCategory refresh summary: {len(succeeded)} succeeded, "
        f"{len(failed)} failed."
    )

    for name, error in failed:
        print(f"- Preserved previous data for {name}: {error}")
