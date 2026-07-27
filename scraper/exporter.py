import csv
import os


def save_to_csv(products, filename="output/products.csv"):

    if not products:
        print("No Products Found")
        return

    os.makedirs("output", exist_ok=True)

    # Automatically detect all columns from product dictionary
    fieldnames = list(products[0].keys())

    with open(filename, "w", newline="", encoding="utf-8-sig") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(products)

    print(f"\n✅ Saved {len(products)} products to {filename}")