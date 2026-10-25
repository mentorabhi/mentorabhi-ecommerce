"""Opt-in signed-JWT checks for the deployed M11 owner APIs."""
import json
import os
from pathlib import Path
import sys
import unittest
import uuid
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import manage


def contract(group, name):
    path = ROOT / "contracts" / group / ("storefront.schema.json" if group == "catalog" else "public.schema.json")
    source = json.loads(path.read_text())
    return Draft202012Validator({"$ref": "#/$defs/" + name, "$defs": source["$defs"]},
                                format_checker=Draft202012Validator.FORMAT_CHECKER)


class PublicContractTests(unittest.TestCase):
    def test_contract_definitions_are_valid_schemas(self):
        for group, filename in (("catalog", "storefront.schema.json"), ("reviews", "public.schema.json")):
            schema = json.loads((ROOT / "contracts" / group / filename).read_text())
            Draft202012Validator.check_schema(schema)

    def test_demo_review_contract_rejects_fake_verified_badges_and_private_fields(self):
        review = {"reviewId": str(uuid.uuid4()), "rating": 4, "title": "Demo", "body": "Synthetic review",
                  "createdAt": "2026-10-25T00:00:00Z", "origin": "DEMO", "verifiedDelivered": False}
        validator = contract("reviews", "PublishedReview")
        self.assertTrue(validator.is_valid(review))
        self.assertFalse(validator.is_valid({**review, "verifiedDelivered": True}))
        self.assertFalse(validator.is_valid({**review, "customerSubject": "private-owner"}))
        self.assertFalse(validator.is_valid({**review, "rating": 2}))


@unittest.skipUnless(os.getenv("SUPERSPORTS_CATALOG_REVIEWS_INTEGRATION") == "1", "Enable with M11 services running")
class CatalogReviewsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.operator = manage.token_for("admin", manage.configure_admin_login())
        credentials = manage.load_credentials(ROOT / "devops/.local/bootstrap.env")
        cls.customer = manage.customer_token_for("checkout-test-customer", credentials["DEMO_CUSTOMER_PASSWORD"])

    def call(self, port, path, *, token=None, method="GET", body=None):
        return manage.request_json(f"http://127.0.0.1:{port}/api/v1/{path}", token=token, method=method,
                                   data=None if body is None else json.dumps(body).encode())

    def product(self):
        status, result = self.call(8081, "catalog/public/products?pageSize=1")
        self.assertEqual(status, 200)
        contract("catalog", "CatalogPage").validate(result)
        self.assertTrue(result["items"])
        return result["items"][0], result

    def test_paginated_detail_saved_variants_and_identity_boundaries(self):
        product, page = self.product()
        self.assertEqual(page["pageSize"], 1)
        self.assertGreaterEqual(page["total"], 1)
        status, direct = self.call(8081, "catalog/public/products/" + product["slug"])
        self.assertEqual(status, 200)
        self.assertEqual(direct["id"], product["id"])
        contract("catalog", "Product").validate(direct)
        status, related = self.call(8081, "catalog/public/products/" + product["slug"] + "/similar?limit=12")
        self.assertEqual(status, 200)
        self.assertLessEqual(len(related), 12)
        contract("catalog", "SimilarProducts").validate(related)
        self.assertNotIn(product["id"], [row["id"] for row in related])
        if product["skus"]:
            status, found = self.call(8081, "catalog/public/products/by-skus?skuIds=" + product["skus"][0]["id"])
            self.assertEqual(status, 200)
            self.assertEqual([row["id"] for row in found], [product["id"]])
            contract("catalog", "SavedProducts").validate(found)
        self.assertEqual(self.call(8081, "catalog/public/products?page=0")[0], 400)
        self.assertEqual(self.call(8081, "catalog/products/" + product["id"], method="PUT", body={})[0], 401)
        self.assertEqual(self.call(8081, "catalog/products/" + product["id"], token=self.customer, method="PUT", body={})[0], 401)

    def test_demo_seed_replay_public_summary_privacy_and_customer_isolation(self):
        product, _ = self.product()
        path = "reviews/products/summaries?productIds=" + product["id"]
        status, before = self.call(8092, path)
        self.assertEqual(status, 200)
        body = {"operationId": str(uuid.uuid5(uuid.NAMESPACE_URL, "supersports:m11:review-api:" + product["id"])),
                "productIds": [product["id"]], "reviewsPerProduct": 3}
        self.assertEqual(self.call(8092, "operator/reviews/demo-seed", method="POST", body=body)[0], 401)
        self.assertEqual(self.call(8092, "operator/reviews/demo-seed", token=self.customer, method="POST", body=body)[0], 403)
        status, receipt = self.call(8092, "operator/reviews/demo-seed", token=self.operator, method="POST", body=body)
        self.assertEqual(status, 200)
        status, replay = self.call(8092, "operator/reviews/demo-seed", token=self.operator, method="POST", body=body)
        self.assertEqual(status, 200)
        self.assertTrue(replay["replayed"])
        status, after = self.call(8092, path)
        self.assertEqual(status, 200)
        added = 0 if receipt["replayed"] else receipt["createdCount"]
        self.assertEqual(after[0]["count"], before[0]["count"] + added)
        self.assertEqual(sum(after[0]["histogram"].values()), after[0]["count"])
        contract("reviews", "RatingSummaries").validate(after)
        self.assertGreaterEqual(after[0]["count"], 3)
        status, reviews = self.call(8092, "reviews/products/" + product["id"])
        self.assertEqual(status, 200)
        contract("reviews", "PublishedReviews").validate(reviews)
        for review in reviews:
            self.assertEqual(set(review), {"reviewId", "rating", "title", "body", "createdAt", "origin", "verifiedDelivered"})
            if review["origin"] == "DEMO":
                self.assertIn(review["rating"], [3, 4, 5])
                self.assertFalse(review["verifiedDelivered"])
        self.assertEqual(self.call(8092, "customer/reviews", token=self.operator)[0], 403)


if __name__ == "__main__":
    unittest.main()
