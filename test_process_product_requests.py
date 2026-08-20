import unittest

from process_product_requests import is_reliable_match


class ProductRequestMatchingTests(unittest.TestCase):
    def test_accepts_exact_title_when_search_card_omits_variant_suffix(self):
        requested = (
            "GREENARTZ Heat Shrink tube 4.5cm cut size Heat shrink Wire "
            "Connector (Multicolor, Pack of 100)"
        )
        candidate = (
            "GREENARTZ Heat Shrink tube 4.5cm cut size Heat shrink Wire Connector"
        )
        self.assertTrue(is_reliable_match(candidate, requested))

    def test_rejects_unrelated_short_product(self):
        requested = "GREENARTZ Heat Shrink tube 4.5cm Pack of 100"
        candidate = "Generic Heat Shrink Wire"
        self.assertFalse(is_reliable_match(candidate, requested))


if __name__ == "__main__":
    unittest.main()
