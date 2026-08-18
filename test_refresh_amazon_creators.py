import unittest

from refresh_amazon_creators import extract_asin, refresh_catalog


class AmazonCreatorsRefreshTests(unittest.TestCase):
    def test_extracts_supported_amazon_urls(self):
        self.assertEqual(
            extract_asin("https://www.amazon.in/dp/B0CF5QFH77?tag=example-21"),
            "B0CF5QFH77",
        )
        self.assertEqual(
            extract_asin("https://www.amazon.in/gp/product/B0CF5QFH77/"),
            "B0CF5QFH77",
        )
        self.assertIsNone(extract_asin("https://www.amazon.in/s?k=earbuds"))

    def test_updates_only_matching_existing_amazon_offer(self):
        products = [
            {
                "prices": [
                    {
                        "store": "Amazon",
                        "price": 1999,
                        "url": "https://www.amazon.in/dp/B0CF5QFH77",
                    },
                    {"store": "Flipkart", "price": 1899, "url": "https://flipkart.com/x"},
                ]
            }
        ]
        items = [
            {
                "asin": "B0CF5QFH77",
                "detailPageURL": "https://www.amazon.in/dp/B0CF5QFH77?tag=bestdaam0a-21",
                "offersV2": {
                    "listings": [
                        {
                            "availability": {"type": "InStock"},
                            "price": {"money": {"amount": 1799, "currency": "INR"}},
                        }
                    ]
                },
            }
        ]

        self.assertEqual(refresh_catalog(products, items, "2026-08-18T00:00:00+00:00"), 1)
        self.assertEqual(products[0]["prices"][0]["price"], 1799)
        self.assertEqual(products[0]["prices"][1]["price"], 1899)
        self.assertEqual(
            products[0]["prices"][0]["checkedAt"], "2026-08-18T00:00:00+00:00"
        )

    def test_preserves_offer_when_item_is_out_of_stock(self):
        products = [
            {
                "prices": [
                    {
                        "store": "Amazon",
                        "price": 1999,
                        "url": "https://www.amazon.in/dp/B0CF5QFH77",
                    }
                ]
            }
        ]
        items = [
            {
                "asin": "B0CF5QFH77",
                "offersV2": {
                    "listings": [
                        {
                            "availability": {"type": "OutOfStock"},
                            "price": {"money": {"amount": 1799, "currency": "INR"}},
                        }
                    ]
                },
            }
        ]

        self.assertEqual(refresh_catalog(products, items, "now"), 0)
        self.assertEqual(products[0]["prices"][0]["price"], 1999)


if __name__ == "__main__":
    unittest.main()
