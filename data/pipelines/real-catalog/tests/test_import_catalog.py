import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from import_catalog import REASON, coupon_fixtures, reconcile_model


class ImportReplayTest(unittest.TestCase):
    def test_coupon_selection_is_product_scoped_and_independent_of_input_order(self):
        products = [{"sourceKey": f"{sport}-{i:02}", "sport": sport}
                    for sport in ("cricket", "football") for i in range(12)]
        completed = {m["sourceKey"]: "id-" + m["sourceKey"] for m in products}
        manifest = {"capturedOn": "2026-10-25", "products": products}
        expected = coupon_fixtures(manifest, completed)
        manifest["products"].reverse()
        self.assertEqual(expected, coupon_fixtures(manifest, completed))
        self.assertEqual({"INR", "USD"}, {c["currency"] for c in expected})
        self.assertEqual(4, len(expected))
        self.assertEqual([f"id-cricket-{i:02}" for i in range(10)], expected[0]["rules"]["productIds"])
        self.assertNotIn("id-cricket-11", expected[0]["rules"]["productIds"])
        self.assertEqual("2027-10-25T00:00:00Z", expected[0]["endsAt"])

    def test_interrupted_stock_reply_replays_without_replenishing_consumed_units(self):
        model = {"sourceKey": "a" * 64, "slug": "source-model", "brand": "SG", "model": "Model",
                 "title": "SG Model", "description": "Sourced model", "sport": "cricket", "equipmentType": "bat",
                 "source": {"url": "https://cricketershop.com/products/model", "capturedOn": "2026-10-25"},
                 "image": {"assetKey": "catalog-real/model.jpg", "altText": "SG Model", "kind": "photograph"},
                 "reviewsPerProduct": 3,
                 "variants": [{"code": "MODEL-1", "key": "v01", "attributes": {"size": "6"}, "stock": 61,
                               "prices": {"INR": 10000, "USD": 118}}]}
        from import_catalog import facts
        product = {"id": "product-1", "categoryId": "category-1", "status": "active", "revision": 3,
                   **{key: model[key] for key in ("slug", "brand", "title", "description")}, "details": facts(model),
                   "skus": [{"id": "sku-1", "code": "MODEL-1", "attributes": {"size": "6"},
                             "assetKey": "catalog-real/model.jpg", "altText": "SG Model"}]}
        stock, receipts, requests = [0], {}, []
        def owner(service, path, method="GET", data=None):
            requests.append((service, path, method, copy.deepcopy(data)))
            if (service, path) == ("catalog", "admin/products"):
                return [copy.deepcopy(product)]
            if (service, path) == ("pricing", "prices"):
                return [{"skuId": "sku-1", "currency": "INR", "amountMinor": 10000},
                        {"skuId": "sku-1", "currency": "USD", "amountMinor": 118}]
            if (service, path) == ("inventory", "adjustments"):
                key = data["idempotencyKey"]
                if key not in receipts:
                    stock[0] += data["delta"]
                    receipts[key] = copy.deepcopy(data)
                    raise TimeoutError("committed response was lost")
                if receipts[key] != data:
                    raise ValueError("changed idempotent request")
                return {"replayed": True}
            if (service, path) == ("reviews", "operator/reviews/demo-seed"):
                return {"replayed": True}
            self.fail(f"Unexpected owner mutation: {service} {path} {method}")
        with self.assertRaises(TimeoutError):
            reconcile_model(owner, model, "category-1")
        self.assertEqual(61, stock[0])
        stock[0] -= 2  # Customer checkout between interruption and replay.
        self.assertEqual("product-1", reconcile_model(owner, model, "category-1"))
        self.assertEqual(59, stock[0])
        adjustments = [r[3] for r in requests if r[1] == "adjustments"]
        self.assertEqual(adjustments[0], adjustments[1])
        self.assertEqual(REASON, adjustments[1]["reason"])


if __name__ == "__main__":
    unittest.main()
