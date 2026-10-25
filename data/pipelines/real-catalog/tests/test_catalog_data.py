"""Authored during coding; execute in the final verification phase."""
import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog_data import equipment, prepare_model, source_key, validate_manifest, variants


class CatalogDataTest(unittest.TestCase):
    def test_football_apparel_is_not_classified_as_a_ball(self):
        self.assertEqual("jersey", equipment("Nike Football Home Jersey", "equipment"))
        self.assertEqual("boots", equipment("Puma Football Cleats", "equipment"))

    def model(self):
        return prepare_model({"sport": "Cricket", "brand": "SG", "title": "SG Test Bat",
                              "sourceUrl": "https://cricketershop.com/products/test-bat",
                              "imageUrl": "https://cdn.shopify.com/test.jpg", "capturedOn": "2026-10-25",
                              "sourcePriceMinor": 100000, "sourceCurrency": "INR"},
                             {"sha256": "a" * 64, "assetKey": "catalog-real/test.jpg"})

    def test_collection_alias_has_same_source_identity(self):
        self.assertEqual(source_key("https://soccer90.com/products/model"),
                         source_key("https://soccer90.com/collections/shirts/products/model?variant=2"))

    def test_ten_options_have_unique_identity_and_explicit_price_books(self):
        options = variants("a" * 64, "cricket", "gloves", 100000, "INR")
        self.assertEqual(10, len({tuple(sorted(v["attributes"].items())) for v in options}))
        self.assertEqual(10, len({v["code"] for v in options}))
        self.assertEqual({"INR": 100000, "USD": 1176}, options[0]["prices"])
        self.assertTrue(all(v["simulated"] for v in options))

    def test_default_scale_rejects_small_dataset(self):
        with self.assertRaisesRegex(ValueError, "100 genuine"):
            validate_manifest({"version": 1, "products": [self.model()]})

    def test_photo_reuse_and_model_alias_are_rejected(self):
        model = self.model()
        duplicate = copy.deepcopy(model)
        duplicate["source"]["url"] += "-second"
        duplicate["sourceKey"] = source_key(duplicate["source"]["url"])
        duplicate["slug"] += "-second"
        duplicate["model"] += " second"
        for v in duplicate["variants"]:
            v["code"] += "-second"
        with self.assertRaisesRegex(ValueError, "photograph"):
            validate_manifest({"version": 1, "products": [model, duplicate]}, {})
        duplicate["image"]["sha256"] = "b" * 64
        duplicate["model"] = model["model"]
        with self.assertRaisesRegex(ValueError, "identity"):
            validate_manifest({"version": 1, "products": [model, duplicate]}, {})

    def test_missing_currency_is_rejected(self):
        model = self.model()
        del model["variants"][0]["prices"]["USD"]
        with self.assertRaisesRegex(ValueError, "INR/USD"):
            validate_manifest({"version": 1, "products": [model]}, {})


if __name__ == "__main__":
    unittest.main()
