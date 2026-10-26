"""Authored during coding; execute in the final verification phase."""
import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog_data import equipment, prepare_model, source_key, validate_manifest, variants


class CatalogDataTest(unittest.TestCase):
    def test_distinct_pdf_models_have_distinct_stable_source_keys(self):
        url = "https://dsc-cricket.co.uk/media/ecatalog/UK-CATALOG-2022.pdf#page=19"
        first = source_key(url, "batting-gloves:krunch-1000")
        self.assertNotEqual(first, source_key(url, "batting-gloves:krunch-3000"))
        self.assertEqual(first, source_key(url.split("#")[0], "batting-gloves:krunch-1000"))

    def test_missing_manufacturer_price_remains_unknown_when_fixture_price_is_explicit(self):
        source = {"sport": "Cricket", "brand": "DSC", "title": "DSC Krunch 1000 Batting Gloves",
                  "sourceUrl": "https://dsc-cricket.co.uk/media/ecatalog/UK-CATALOG-2022.pdf#page=19",
                  "recordId": "batting-gloves:krunch-1000", "catalogYear": 2023,
                  "pdfImage": {"page": 19}, "fixtureBaseMinor": 349900, "fixtureCurrency": "INR",
                  "capturedOn": "2026-10-25"}
        model = prepare_model(source, {"sha256": "a" * 64, "assetKey": "catalog-real/a.png"})
        self.assertIsNone(model["source"]["priceMinor"])
        self.assertIsNone(model["source"]["currency"])
        self.assertEqual(349900, model["variants"][0]["prices"]["INR"])

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

    def test_goalkeeper_pairs_and_bag_bundle_options_match_equipment(self):
        gloves = variants("a" * 64, "football", "gloves", 2000, "USD")
        self.assertEqual([str(n) for n in range(4, 14)], [v["attributes"]["size"] for v in gloves])
        self.assertTrue(all(v["attributes"]["pack"] == "Pair" for v in gloves))
        bags = variants("b" * 64, "cricket", "bag", 100000, "INR")
        self.assertEqual({"1", "2", "3", "4", "5"}, {v["attributes"]["pack"] for v in bags})
        self.assertNotIn("size", bags[0]["attributes"])

    def test_explicit_equipment_type_keeps_bat_accessories_and_training_tee_out_of_bats_and_shirts(self):
        for title,kind in (("SG Bat Oil","bat-oil"),("Cricket Batting Tee","batting-tee"),("Cricket Bat Toe Guard","toe-guard")):
            source={"sport":"Cricket","brand":"SG","title":title,"equipmentType":kind,
                    "sourceUrl":"https://cricketershop.com/products/"+kind,"imageUrl":"https://cdn.shopify.com/test.jpg",
                    "capturedOn":"2026-10-26","sourcePriceMinor":10000,"sourceCurrency":"INR",
                    "fixtureOptions":[{"attributes":{"configuration":"As pictured","pack":"1"}}]}
            model=prepare_model(source,{"sha256":"a"*64,"assetKey":"catalog-real/test.jpg"})
            self.assertEqual(kind,model["equipmentType"])
            self.assertEqual(1,len(model["variants"]))
            self.assertNotIn("size",model["variants"][0]["attributes"])
    def test_ground_equipment_options_do_not_invent_clothing_sizes_and_reject_duplicates(self):
        options=[{"attributes":{"configuration":"Heavy roller","pack":"1"}}]
        result=variants("a"*64,"cricket","roller",25000000,"INR",options)
        self.assertEqual(1,len(result));self.assertEqual(25000000,result[0]["prices"]["INR"])
        for invalid in ([],options+options,[{"attributes":{"size":"<unsafe>"}}],[{"attributes":{"configuration":"bad\x00text"}}],[{"attributes":{},"pack":1}],[{"attributes":{"pack":"1"},"pack":0}]):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                variants("a"*64,"cricket","roller",10000,"INR",invalid)

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
