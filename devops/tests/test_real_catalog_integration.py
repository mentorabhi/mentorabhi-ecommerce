"""Owner APIs, deployed photo bundle and replay evidence for the sourced catalog."""
import hashlib
import json
import os
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "devops/scripts"))
sys.path.insert(0, str(ROOT / "data/pipelines/real-catalog"))
import manage
from import_catalog import OwnerApi, import_manifest


@unittest.skipUnless(os.getenv("SUPERSPORTS_REAL_CATALOG") == "1", "Run the sourced-catalog integration profile after data import")
class RealCatalogIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = OwnerApi()
        cls.manifest = json.loads((ROOT / "data/pipelines/real-catalog/manifest.json").read_text())
        cls.products = {p["slug"]: p for p in cls.api("catalog", "admin/products")}
        cls.project = manage.validated_project_name(os.getenv("SUPERSPORTS_PROJECT", "supersports"))

    def test_active_scale_price_books_stock_and_every_deployed_photo(self):
        categories = {c["id"]: c for c in self.api("catalog", "categories")}
        prices = {(p["skuId"], p["currency"]): p["amountMinor"] for p in self.api("pricing", "prices")}
        balances = {b["skuId"]: b["onHand"] for b in self.api("inventory", "balances") if b.get("skuId")}
        counts = {sport: [0, 0] for sport in ("cricket", "football")}
        for model in self.manifest["products"]:
            product = self.products[model["slug"]]
            self.assertEqual("active", product["status"])
            self.assertEqual(model["sport"] + "-equipment", categories[product["categoryId"]]["slug"])
            actual = {s["code"]: s for s in product["skus"]}
            self.assertEqual({v["code"] for v in model["variants"]}, set(actual))
            for variant in model["variants"]:
                sku = actual[variant["code"]]
                self.assertEqual(variant["attributes"], sku["attributes"])
                self.assertEqual(model["image"]["assetKey"], sku["assetKey"])
                self.assertGreaterEqual(balances[sku["id"]], 0)
                for currency in ("INR", "USD"):
                    self.assertEqual(variant["prices"][currency], prices[(sku["id"], currency)])
            counts[model["sport"]][0] += 1
            counts[model["sport"]][1] += len(actual)
        for sport, (models, skus) in counts.items():
            self.assertGreaterEqual(models, 100, sport)
            self.assertGreaterEqual(skus, 1000, sport)
        def photo(model):
            with urlopen("http://127.0.0.1:3000/" + model["image"]["assetKey"], timeout=10) as response:
                return response.status, hashlib.sha256(response.read()).hexdigest()
        with ThreadPoolExecutor(max_workers=4) as pool:
            for model, observed in zip(self.manifest["products"], pool.map(photo, self.manifest["products"])):
                self.assertEqual((200, model["image"]["sha256"]), observed, model["title"])

    def test_every_model_has_published_demo_provenance_and_consistent_summary(self):
        ids = []
        expected = {}
        for model in self.manifest["products"]:
            product_id = self.products[model["slug"]]["id"]
            rows = self.api("reviews", f"reviews/products/{product_id}")
            demo = [r for r in rows if r["origin"] == "DEMO"]
            self.assertEqual(model["reviewsPerProduct"], len(demo))
            self.assertTrue(all(3 <= r["rating"] <= 5 and not r["verifiedDelivered"] for r in demo))
            self.assertTrue(all("customerSubject" not in r and "orderId" not in r for r in rows))
            expected[product_id] = rows
            ids.append(product_id)
        for start in range(0, len(ids), 100):
            summaries = self.api("reviews", "reviews/products/summaries?productIds=" + ",".join(ids[start:start + 100]))
            for summary in summaries:
                rows = expected[summary["productId"]]
                self.assertEqual(len(rows), summary["count"])
                self.assertAlmostEqual(sum(r["rating"] for r in rows) / len(rows), float(summary["mean"]), places=2)

    def test_product_scoped_coupon_discounts_only_eligible_line(self):
        currency = self.api("pricing", "currency")["code"]
        coupon = next(c for c in self.api("pricing", "coupons") if c["code"] == ("REALCR10" if currency == "INR" else "REALCR10USD"))
        rules = coupon["rules"]
        if isinstance(rules, str):
            rules = json.loads(rules)
        elif "value" in rules:
            rules = json.loads(rules["value"])
        eligible = set(rules["productIds"])
        self.assertEqual(10, len(eligible))
        models = [self.products[m["slug"]] for m in self.manifest["products"] if m["sport"] == "cricket"]
        selected = next(p for p in models if p["id"] in eligible)
        unselected = next(p for p in models if p["id"] not in eligible)
        worker = manage.checkout_worker_token()
        lines = []
        for product in (selected, unselected):
            sku_id = product["skus"][0]["id"]
            status, facts = manage.request_json(f"http://127.0.0.1:8081/api/v1/internal/checkout/catalog/skus/{sku_id}", token=worker)
            self.assertEqual(200, status)
            lines.append({"skuId": sku_id, "quantity": 1, "productId": facts["productId"], "productTitle": facts["title"],
                          "categoryId": facts["categoryId"], "categorySlug": facts["categorySlug"], "skuRevision": facts["skuRevision"],
                          "productRevision": facts["productRevision"], "categoryRevision": facts["categoryRevision"]})
        status, quote = manage.request_json("http://127.0.0.1:8083/api/v1/internal/checkout/pricing/quotes", token=worker,
            method="POST", data=json.dumps({"requestId": str(uuid.uuid4()), "customerSubject": "synthetic-coupon-acceptance",
                                             "couponCode": coupon["code"], "lines": lines}).encode())
        self.assertEqual(200, status)
        actual = {line["productId"]: line for line in quote["snapshot"]["lines"]}
        self.assertEqual(0, actual[unselected["id"]]["discountMinor"])
        selected_line = actual[selected["id"]]
        self.assertEqual(min((selected_line["unitPriceMinor"] * 1000 + 5000) // 10000, coupon["maximumDiscountMinor"]), selected_line["discountMinor"])

    def test_replay_preserves_seed_movements_catalog_revisions_and_owned_history(self):
        sql = "SELECT count(*),md5(string_agg(id::text||':'||idempotency_key||':'||delta::text,',' ORDER BY id)) FROM stock_movement WHERE idempotency_key LIKE 'real-v1:%'"
        def seed_ledger():
            return manage.compose(["exec", "-T", "postgres", "psql", "-U", "supersports_inventory", "-d", "inventory", "-Atqc", sql],
                                  project=self.project, capture=True).stdout.strip()
        before = seed_ledger()
        credentials = manage.load_credentials(ROOT / "devops/.local/bootstrap.env")
        customer = manage.customer_token_for("checkout-test-customer", credentials["DEMO_CUSTOMER_PASSWORD"])
        status, history = manage.request_json("http://127.0.0.1:8086/api/v1/orders", token=customer)
        self.assertEqual(200, status)
        revisions = {p["id"]: p["revision"] for p in self.api("catalog", "admin/products")}
        receipt = {"completed": {}}
        import_manifest(self.api, self.manifest, receipt, lambda value: None)
        self.assertEqual(before, seed_ledger())
        self.assertEqual(sum(len(p["variants"]) for p in self.manifest["products"]), int(before.split("|")[0]))
        self.assertEqual(revisions, {p["id"]: p["revision"] for p in self.api("catalog", "admin/products")})
        self.assertEqual((200, history), manage.request_json("http://127.0.0.1:8086/api/v1/orders", token=customer))


if __name__ == "__main__":
    unittest.main()
