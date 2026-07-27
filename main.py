import argparse

from database.db import Database
from scraper.browser import SyncBrowserManager
from scraper.category_runner import run_all_categories


FLIPKART_BASE_URL = "https://www.flipkart.com"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Flipkart category scraper"
    )
    parser.add_argument(
        "--category",
        help="Sirf ek category key scrape kare, jaise wired_earphones",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    browser_manager = SyncBrowserManager()
    database = Database("products.db")

    try:
        page = browser_manager.start()

        run_all_categories(
            page=page,
            base_url=FLIPKART_BASE_URL,
            db=database,
            limit=100,
            selected_category=args.category,
        )

        print("\n" + "=" * 60)
        print("All Flipkart categories completed successfully.")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\nScraping stopped by user.")

    except Exception as error:
        print(f"\nFlipkart scraper error: {error}")
        raise

    finally:
        database.close()
        browser_manager.close()


if __name__ == "__main__":
    main()
