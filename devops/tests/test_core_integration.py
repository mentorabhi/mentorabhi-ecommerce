"""Real Docker/PostgreSQL/Keycloak regressions, run by supersports test."""
import json
import os
from pathlib import Path
import sys
import time
import unittest
import uuid
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import manage

CATALOG = "http://127.0.0.1:8081"
CONFIGURATION = "http://127.0.0.1:8082"
PRICING = "http://127.0.0.1:8083"
INVENTORY = "http://127.0.0.1:8084"
CUSTOMER = "http://127.0.0.1:8085"
ORDERS = "http://127.0.0.1:8086"


@unittest.skipUnless(os.environ.get("SUPERSPORTS_INTEGRATION") == "1",
                     "Run through devops/scripts/supersports test against the local core profile.")
class CoreIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = manage.validated_project_name(os.environ.get("SUPERSPORTS_PROJECT", "supersports"))
        cls.credentials = manage.load_credentials(ROOT / "devops/.local/bootstrap.env")
        cls.customer = manage.token_for("customer", cls.credentials["DEMO_CUSTOMER_PASSWORD"])
        cls.store_customer = manage.customer_token_for("checkout-test-customer", cls.credentials["DEMO_CUSTOMER_PASSWORD"])
        cls.store_customer_b = manage.customer_token_for("checkout-test-customer-b", cls.credentials["DEMO_CUSTOMER_PASSWORD"])
        cls.checkout_worker = manage.checkout_worker_token()
        cls.local_admin = manage.token_for("admin", manage.configure_admin_login(ROOT))
        cls.admin = manage.token_for("platform-admin", cls.credentials["DEMO_PLATFORM_ADMIN_PASSWORD"])
        cls.catalog_admin = manage.token_for("catalog-admin", cls.credentials["DEMO_CATALOG_ADMIN_PASSWORD"])
        cls.inventory_operator = manage.token_for("inventory-operator", cls.credentials["DEMO_INVENTORY_OPERATOR_PASSWORD"])
        cls.wrong_audience = manage.token_for("customer", cls.credentials["DEMO_CUSTOMER_PASSWORD"],
                                       "supersports-other-cli")

    def test_public_health_is_up_without_sensitive_details(self):
        for base in (CATALOG, CONFIGURATION, PRICING, INVENTORY, CUSTOMER, ORDERS):
            for probe in ("liveness", "readiness"):
                with self.subTest(base=base, probe=probe):
                    status, body = manage.request_json(f"{base}/actuator/health/{probe}")
                    self.assertEqual(status, 200)
                    self.assertEqual(body, {"status": "UP"})

    def test_anonymous_api_access_is_unauthorized(self):
        for url in (f"{CATALOG}/api/v1/catalog/status", f"{CATALOG}/api/v1/catalog/admin/products",
                    f"{CONFIGURATION}/api/v1/configuration", f"{PRICING}/api/v1/pricing/prices",
                    f"{INVENTORY}/api/v1/inventory/balances", f"{CUSTOMER}/api/v1/customer/profile",
                    f"{ORDERS}/api/v1/orders", "http://127.0.0.1:3000/api/orders",
                    "http://127.0.0.1:3000/api/configuration"):
            self.assertEqual(manage.request_json(url)[0], 401)

    def test_public_customer_browsing_and_snapshots_are_available_without_signin(self):
        status, products = manage.request_json(f"{CATALOG}/api/v1/catalog/products?q=football")
        self.assertEqual(status, 200)
        self.assertTrue(products)
        football_codes = {sku["code"] for product in products for sku in product["skus"]}
        self.assertEqual(football_codes, {"SS-FB-BALL-001", "SS-FB-CONE-001", "SS-FB-GLOVE-001"})
        proxy_status, proxy_products = manage.request_json(
            "http://127.0.0.1:3000/api/catalog/products?q=football")
        self.assertEqual(proxy_status, 200)
        self.assertEqual(proxy_products, products)
        self.assertEqual(manage.request_json(f"{CATALOG}/api/v1/catalog/categories")[0], 200)
        sku = products[0]["skus"][0]["id"]
        self.assertEqual(manage.request_json(f"{CATALOG}/api/v1/catalog/public/skus/{sku}")[0], 200)
        self.assertEqual(manage.request_json(f"{PRICING}/api/v1/pricing/public/skus/{sku}")[0], 200)
        status, availability = manage.request_json(f"{INVENTORY}/api/v1/inventory/availability/{sku}")
        self.assertEqual(status, 200)
        self.assertTrue(availability["snapshot"])

    def test_operator_identity_cannot_access_customer_resources(self):
        self.assertEqual(manage.request_json(f"{CUSTOMER}/api/v1/customer/profile", token=self.local_admin)[0], 401)
        self.assertEqual(manage.request_json(f"{CUSTOMER}/api/v1/customer/cart", token=self.admin)[0], 401)
        self.assertEqual(manage.request_json(f"{ORDERS}/api/v1/orders", token=self.admin)[0], 401)

    def test_checkout_creates_owner_scoped_order_and_is_idempotent(self):
        _, products = manage.request_json(f"{CATALOG}/api/v1/catalog/products?q=football")
        sku_id = products[0]["skus"][0]["id"]
        _, profile = manage.request_json(f"{CUSTOMER}/api/v1/customer/profile", token=self.store_customer)
        address = {"fullName": "Checkout Test", "phone": "9876543210", "line1": "12 Test Road",
                   "line2": "", "city": "Pune", "state": "Maharashtra", "postalCode": "411001",
                   "country": "IN", "expectedRevision": profile["revision"]}
        self.assertEqual(manage.request_json(f"{CUSTOMER}/api/v1/customer/profile", token=self.store_customer,
                                             method="PUT", data=json.dumps(address).encode())[0], 200)
        key = "integration-" + uuid.uuid4().hex
        url = f"{ORDERS}/api/v1/orders/checkout"
        payload = {"lines": [{"skuId": sku_id, "quantity": 1}], "couponCode": None}
        status, first = manage.request_json(url, token=self.store_customer, method="POST", data=json.dumps(payload).encode(),
                                            headers={"Idempotency-Key": key})
        self.assertEqual(status, 202)
        self.assertEqual(first["status"], "ACCEPTED")
        self.assertEqual(first["state"], "PENDING_PAYMENT")
        self.assertGreater(first["totalMinor"], 0)
        order_status, order = manage.request_json(f"{ORDERS}/api/v1/orders/{first['orderId']}", token=self.store_customer)
        self.assertEqual(order_status, 200)
        self.assertEqual(order["addressSnapshot"]["postalCode"], "411001")
        self.assertEqual(order["lines"][0]["skuId"], sku_id)
        self.assertEqual(manage.request_json(f"{ORDERS}/api/v1/orders/{first['orderId']}", token=self.store_customer_b)[0], 404)
        status, replay = manage.request_json(url, token=self.store_customer, method="POST", data=json.dumps(payload).encode(),
                                             headers={"Idempotency-Key": key})
        self.assertEqual(status, 202)
        self.assertEqual(replay["requestId"], first["requestId"])
        self.assertEqual(replay["orderId"], first["orderId"])
        self.assertTrue(replay["replayed"])
        changed = {"lines": [{"skuId": sku_id, "quantity": 2}], "couponCode": None}
        status, _ = manage.request_json(url, token=self.store_customer, method="POST", data=json.dumps(changed).encode(),
                                        headers={"Idempotency-Key": key})
        self.assertEqual(status, 409)
        self.assertEqual(manage.request_json(f"{url.replace('/checkout','/checkout-requests')}/{first['requestId']}", token=self.store_customer)[0], 200)
        self.assertEqual(manage.request_json(f"{url.replace('/checkout','/checkout-requests')}/{first['requestId']}", token=self.store_customer_b)[0], 404)
        check = self.psql("orders", "orders", "SELECT concat((SELECT count(*) FROM customer_order WHERE id=$$"+first["orderId"]+"$$),chr(58),(SELECT count(*) FROM checkout_saga WHERE order_id=$$"+first["orderId"]+"$$),chr(58),(SELECT count(*) FROM order_outbox WHERE aggregate_id=$$"+first["orderId"]+"$$))")
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual(check.stdout.strip(), "1:1:1")
        claims_b = json.loads(__import__("base64").urlsafe_b64decode(self.store_customer_b.split(".")[1] + "=="))
        manage.request_json(f"{CUSTOMER}/api/v1/customer/profile", token=self.store_customer_b)
        rejected_key = "missing-address-" + uuid.uuid4().hex
        status, _ = manage.request_json(url, token=self.store_customer_b, method="POST", data=json.dumps(payload).encode(),
                                        headers={"Idempotency-Key": rejected_key})
        self.assertEqual(status, 422)
        self.assertEqual(manage.request_json(url, token=self.store_customer_b, method="POST", data=json.dumps(payload).encode(),
                                             headers={"Idempotency-Key": rejected_key})[0], 422)
        rejected = self.psql("orders", "orders", "SELECT count(*) FROM checkout_request r LEFT JOIN customer_order o ON o.checkout_request_id=r.id WHERE r.customer_subject=$$"+claims_b["sub"]+"$$ AND r.idempotency_key=$$"+rejected_key+"$$ AND r.status=$$REJECTED$$ AND o.id IS NULL")
        self.assertEqual(rejected.returncode, 0, rejected.stderr)
        self.assertEqual(rejected.stdout.strip(), "1")
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            _, current = manage.request_json(f"{ORDERS}/api/v1/orders/{first['orderId']}", token=self.store_customer)
            if current.get("state") in ("FULFILLMENT_SCHEDULED", "FAILED", "MANUAL_REVIEW"):
                break
            time.sleep(0.5)
        self.assertEqual(current.get("state"), "FULFILLMENT_SCHEDULED", current)
        payment_status, payments = manage.request_json(
            f"http://127.0.0.1:8087/api/v1/internal/checkout/payments/{first['orderId']}/status",
            token=self.checkout_worker)
        self.assertEqual(payment_status, 200)
        self.assertEqual([item["state"] for item in payments["operations"]], ["AUTHORIZED", "CAPTURED"])
        fulfillment_status, shipment = manage.request_json(
            f"http://127.0.0.1:8088/api/v1/internal/checkout/fulfillment/{first['orderId']}",
            token=self.checkout_worker)
        self.assertEqual(fulfillment_status, 200)
        self.assertEqual(shipment["state"], "SCHEDULED")

    def test_declined_payment_releases_stock_without_capture(self):
        settings_url=f"{CONFIGURATION}/api/v1/configuration"
        _,snapshot=manage.request_json(settings_url,token=self.admin)
        setting=next(item for item in snapshot["settings"] if item["key"]=="checkout.payment.authorization-mode")
        update_url=f"{CONFIGURATION}/api/v1/configuration/checkout/payment.authorization-mode"
        status,changed=manage.request_json(update_url,token=self.admin,method="PUT",data=json.dumps({"value":"DECLINE","expectedRevision":setting["revision"]}).encode())
        self.assertEqual(status,200,changed)
        try:
            _,products=manage.request_json(f"{CATALOG}/api/v1/catalog/products?q=football")
            sku=products[0]["skus"][0]["id"]
            payload={"lines":[{"skuId":sku,"quantity":1}],"couponCode":None}
            status,accepted=manage.request_json(f"{ORDERS}/api/v1/orders/checkout",token=self.store_customer,method="POST",data=json.dumps(payload).encode(),headers={"Idempotency-Key":"decline-"+uuid.uuid4().hex})
            self.assertEqual(status,202,accepted)
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                _,order=manage.request_json(f"{ORDERS}/api/v1/orders/{accepted['orderId']}",token=self.store_customer)
                if order.get("state") in ("FAILED","CONFIRMED","MANUAL_REVIEW"):break
                time.sleep(.5)
            self.assertEqual(order.get("state"),"FAILED",order)
            _,payments=manage.request_json(f"http://127.0.0.1:8087/api/v1/internal/checkout/payments/{accepted['orderId']}/status",token=self.checkout_worker)
            self.assertEqual([p["state"] for p in payments["operations"]],["DECLINED"])
            reservation=self.psql("inventory","inventory","SELECT state FROM inventory_reservation WHERE order_id=$$"+accepted["orderId"]+"$$")
            self.assertEqual(reservation.stdout.strip(),"RELEASED")
        finally:
            self.assertEqual(manage.request_json(update_url,token=self.admin,method="PUT",data=json.dumps({"value":setting["value"],"expectedRevision":changed["settingRevision"]}).encode())[0],200)

    def test_orders_worker_resumes_persisted_saga_after_restart(self):
        _,products=manage.request_json(f"{CATALOG}/api/v1/catalog/products?q=football")
        sku=products[0]["skus"][0]["id"]
        status,accepted=manage.request_json(f"{ORDERS}/api/v1/orders/checkout",token=self.store_customer,method="POST",data=json.dumps({"lines":[{"skuId":sku,"quantity":1}],"couponCode":None}).encode(),headers={"Idempotency-Key":"worker-restart-"+uuid.uuid4().hex})
        self.assertEqual(status,202,accepted)
        manage.compose(["stop","orders"],project=self.project)
        time.sleep(2)
        manage.compose(["start","orders"],project=self.project)
        manage.wait_status(f"{ORDERS}/actuator/health/readiness",timeout=120)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            _,order=manage.request_json(f"{ORDERS}/api/v1/orders/{accepted['orderId']}",token=self.store_customer)
            if order.get("state") in ("FULFILLMENT_SCHEDULED","FAILED","MANUAL_REVIEW"):break
            time.sleep(.5)
        self.assertEqual(order.get("state"),"FULFILLMENT_SCHEDULED",order)

    def test_checkout_worker_catalog_quote_and_audience_boundaries(self):
        _, products = manage.request_json(f"{CATALOG}/api/v1/catalog/products?q=willow")
        product = products[0]
        sku_id = product["skus"][0]["id"]
        facts_url = f"{CATALOG}/api/v1/internal/checkout/catalog/skus/{sku_id}"
        status, facts = manage.request_json(facts_url, token=self.checkout_worker)
        self.assertEqual(status, 200)
        self.assertTrue(facts["active"])
        self.assertEqual(manage.request_json(f"{CATALOG}/api/v1/catalog/admin/products", token=self.checkout_worker)[0], 403)
        self.assertEqual(manage.request_json(facts_url, token=self.catalog_admin)[0], 403)
        config_url = f"{CONFIGURATION}/api/v1/internal/checkout/configuration"
        config_status, checkout_config = manage.request_json(config_url, token=self.checkout_worker)
        self.assertEqual(config_status, 200)
        self.assertEqual(checkout_config["taxRateBps"], 1800)
        self.assertEqual(checkout_config["shippingInrMinor"], 9900)
        self.assertEqual(manage.request_json(config_url, token=self.admin)[0], 403)
        self.assertEqual(manage.request_json("http://127.0.0.1:8087/api/v1/internal/checkout/payments/authorize",token=self.admin,method="POST",data=b"{}" )[0],401)
        self.assertEqual(manage.request_json("http://127.0.0.1:8088/api/v1/internal/checkout/fulfillment",token=self.store_customer,method="POST",data=b"{}" )[0],401)

        claims = json.loads(__import__("base64").urlsafe_b64decode(self.store_customer.split(".")[1] + "=="))
        request_id = str(uuid.uuid4())
        payload = {"requestId": request_id, "customerSubject": claims["sub"], "couponCode": "WELCOME10",
                   "lines": [{"skuId": sku_id, "quantity": 1, "productId": facts["productId"],
                              "productTitle": facts["title"], "categoryId": facts["categoryId"],
                              "categorySlug": facts["categorySlug"], "skuRevision": facts["skuRevision"],
                              "productRevision": facts["productRevision"], "categoryRevision": facts["categoryRevision"]}]}
        quote_url = f"{PRICING}/api/v1/internal/checkout/pricing/quotes"
        status, quote = manage.request_json(quote_url, token=self.checkout_worker, method="POST",
                                            data=json.dumps(payload).encode())
        self.assertEqual(status, 200, quote)
        self.assertEqual(quote["snapshot"]["currency"], "INR")
        self.assertEqual(quote["snapshot"]["discountMinor"], 50000)
        status, replay = manage.request_json(quote_url, token=self.checkout_worker, method="POST",
                                             data=json.dumps(payload).encode())
        self.assertEqual(status, 200)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["quoteId"], quote["quoteId"])
        self.assertEqual(manage.request_json(f"{PRICING}/api/v1/pricing/prices", token=self.checkout_worker)[0], 403)
        self.assertEqual(manage.request_json(quote_url, token=self.catalog_admin, method="POST",
                                             data=json.dumps(payload).encode())[0], 403)
        order_id = str(uuid.uuid4())
        hold_payload = {"orderId": order_id, "quoteId": quote["quoteId"],
                        "customerSubject": claims["sub"],
                        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(), "fence": 1}
        hold_url = f"{PRICING}/api/v1/internal/checkout/pricing/coupon-holds"
        status, hold = manage.request_json(hold_url, token=self.checkout_worker, method="POST",
                                           data=json.dumps(hold_payload).encode())
        self.assertEqual(status, 200, hold)
        self.assertEqual(hold["state"], "HELD")
        status, replayed_hold = manage.request_json(hold_url, token=self.checkout_worker, method="POST",
                                                    data=json.dumps(hold_payload).encode())
        self.assertEqual(status, 200)
        self.assertTrue(replayed_hold["replayed"])
        wrong_owner = {**hold_payload, "customerSubject": claims["sub"] + "-other"}
        self.assertEqual(manage.request_json(hold_url, token=self.checkout_worker, method="POST",
                                             data=json.dumps(wrong_owner).encode())[0], 409)
        for action, expected_state in (("protect", "PROTECTED"), ("release", "RELEASED")):
            status, transition = manage.request_json(f"{hold_url}/{order_id}/{action}", token=self.checkout_worker, method="POST", data=b"{}", headers={"X-Checkout-Fence": "1"})
            self.assertEqual(status, 200, transition)
            self.assertEqual(transition["state"], expected_state)

        reservation_id = str(uuid.uuid4())
        reservation_payload = {"orderId": reservation_id,
                               "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                               "lines": [{"skuId": sku_id, "quantity": 1}], "fence": 1}
        reservation_url = f"{INVENTORY}/api/v1/internal/checkout/inventory/reservations"
        status, reservation = manage.request_json(reservation_url, token=self.checkout_worker, method="POST",
                                                  data=json.dumps(reservation_payload).encode())
        self.assertEqual(status, 200, reservation)
        self.assertEqual(reservation["state"], "HELD")
        status, reservation_replay = manage.request_json(reservation_url, token=self.checkout_worker, method="POST",
                                                         data=json.dumps(reservation_payload).encode())
        self.assertEqual(status, 200, reservation_replay)
        self.assertTrue(reservation_replay["replayed"])
        for action, expected_state in (("protect", "PROTECTED"), ("release", "RELEASED")):
            status, transition = manage.request_json(f"{reservation_url}/{reservation_id}/{action}",
                                                     token=self.checkout_worker, method="POST", data=b"{}", headers={"X-Checkout-Fence": "1"})
            self.assertEqual(status, 200, transition)
            self.assertEqual(transition["state"], expected_state)

    def test_customer_and_catalog_admin_can_read_catalog_status(self):
        for token in (self.customer, self.catalog_admin):
            status, body = manage.request_json(f"{CATALOG}/api/v1/catalog/status", token=token)
            self.assertEqual(status, 200)
            self.assertEqual(body, {"service": "catalog", "status": "ready", "schemaVersion": 2})

    def test_fixtures_expose_products_both_currencies_coupons_and_stock(self):
        _, products = manage.request_json(f"{CATALOG}/api/v1/catalog/products", token=self.customer)
        fixture_codes = {"SS-CR-BAT-001", "SS-CR-BALL-001", "SS-CR-GLOVE-001",
                         "SS-FB-BALL-001", "SS-FB-CONE-001", "SS-FB-GLOVE-001"}
        visible_codes = {sku["code"] for product in products for sku in product["skus"]}
        self.assertTrue(fixture_codes.issubset(visible_codes), fixture_codes - visible_codes)
        _, sports = manage.request_json(f"{CATALOG}/api/v1/catalog/sports", token=self.customer)
        self.assertEqual({item["slug"] for item in sports}, {"cricket", "football"})
        _, prices = manage.request_json(f"{PRICING}/api/v1/pricing/prices", token=self.catalog_admin)
        self.assertEqual({item["currency"] for item in prices}, {"INR", "USD"})
        _, coupons = manage.request_json(f"{PRICING}/api/v1/pricing/coupons", token=self.catalog_admin)
        self.assertTrue({"WELCOME10", "CRICKET250"}.issubset({item["code"] for item in coupons}))
        _, balances = manage.request_json(f"{INVENTORY}/api/v1/inventory/balances", token=self.inventory_operator)
        self.assertEqual(len(balances), 6)

    def test_signed_in_accounts_can_read_every_admin_section_without_admin_roles(self):
        for token in (self.customer, self.catalog_admin, self.inventory_operator, self.local_admin):
            for url in (f"{CATALOG}/api/v1/catalog/admin/products",
                        f"{INVENTORY}/api/v1/inventory/balances",
                        f"{PRICING}/api/v1/pricing/currency",
                        f"{PRICING}/api/v1/pricing/prices",
                        f"{PRICING}/api/v1/pricing/coupons"):
                with self.subTest(url=url):
                    self.assertEqual(manage.request_json(url, token=token)[0], 200)

    def test_inventory_adjustment_replay_and_payload_conflict(self):
        _, products = manage.request_json(f"{CATALOG}/api/v1/catalog/products", token=self.customer)
        sku = products[0]["skus"][0]["id"]
        url = f"{INVENTORY}/api/v1/inventory/adjustments"
        body = {"skuId": sku, "delta": 1, "reason": "Integration idempotency regression",
                "idempotencyKey": f"integration-replay-{uuid.uuid4()}"}
        status, first = manage.request_json(url, token=self.customer, method="POST",
                                            data=json.dumps(body).encode())
        self.assertEqual(status, 200)
        self.assertFalse(first["replayed"])
        status, replay = manage.request_json(url, token=self.customer, method="POST",
                                             data=json.dumps(body).encode())
        self.assertEqual(status, 200)
        self.assertTrue(replay["replayed"])
        changed = {**body, "delta": 2}
        status, body = manage.request_json(url, token=self.customer, method="POST",
                                           data=json.dumps(changed).encode())
        self.assertEqual(status, 409, body)

    def test_signed_in_accounts_can_read_platform_configuration(self):
        for token in (self.customer, self.catalog_admin):
            self.assertEqual(manage.request_json(f"{CONFIGURATION}/api/v1/configuration", token=token)[0], 200)

    def test_platform_configuration_has_categorized_non_secret_defaults(self):
        status, body = manage.request_json(f"{CONFIGURATION}/api/v1/configuration", token=self.admin)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(body["revision"], 3)
        categories = {item["id"] for item in body["categories"]}
        self.assertEqual(categories, {
            "store-localization", "commerce-simulations", "storage", "search-cache",
            "messaging-workflows", "identity-access", "observability", "nova-models",
        })
        settings = {item["key"]: item for item in body["settings"]}
        self.assertEqual(settings["store.currency"]["value"], "INR")
        self.assertEqual(settings["store.country"]["value"], "IN")
        self.assertEqual(settings["store.language"]["value"], "en")
        for item in settings.values():
            self.assertIn(item["category"], categories)
            self.assertIn(item["valueType"], {"STRING", "STRING_LIST", "BOOLEAN"})
            expected = "OPERATOR_EDITABLE" if item["key"].startswith("checkout.") else "MIGRATION_ONLY"
            self.assertEqual(item["activationMode"], expected)
        rendered = json.dumps(body)
        self.assertTrue(all(secret not in rendered for secret in self.credentials.values()))

    def test_checkout_simulation_configuration_is_revisioned_and_audited(self):
        url = f"{CONFIGURATION}/api/v1/configuration/checkout/tax.rate-bps"
        _, before = manage.request_json(f"{CONFIGURATION}/api/v1/configuration", token=self.admin)
        setting = next(item for item in before["settings"] if item["key"] == "checkout.tax.rate-bps")
        body = {"value": "1900", "expectedRevision": setting["revision"]}
        status, updated = manage.request_json(url, token=self.admin, method="PUT", data=json.dumps(body).encode())
        self.assertEqual(status, 200, updated)
        self.assertEqual(updated["value"], "1900")
        self.assertEqual(updated["settingRevision"], setting["revision"] + 1)
        status, _ = manage.request_json(url, token=self.admin, method="PUT", data=json.dumps(body).encode())
        self.assertEqual(status, 409)
        reset = {"value": setting["value"], "expectedRevision": updated["settingRevision"]}
        self.assertEqual(manage.request_json(url, token=self.admin, method="PUT", data=json.dumps(reset).encode())[0], 200)
        claims = json.loads(__import__("base64").urlsafe_b64decode(self.admin.split(".")[1] + "=="))
        audit = self.psql("configuration", "configuration", "SELECT count(*) FROM configuration_setting_audit WHERE setting_key=$$checkout.tax.rate-bps$$ AND actor=$$"+claims["sub"]+"$$")
        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertGreaterEqual(int(audit.stdout.strip()), 2)
        invalid = {"value": "10001", "expectedRevision": updated["settingRevision"] + 1}
        self.assertEqual(manage.request_json(url, token=self.admin, method="PUT", data=json.dumps(invalid).encode())[0], 422)

    def test_authenticated_mutation_methods_do_not_change_configuration(self):
        url = f"{CONFIGURATION}/api/v1/configuration"
        before = manage.request_json(url, token=self.admin)
        self.assertEqual(before[0], 200)
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            status, _ = manage.request_json(url, token=self.admin, method=method,
                                            data=b'{"store.currency":"USD"}')
            self.assertIn(status, (401, 403, 405), method)
            self.assertEqual(manage.request_json(url, token=self.admin), before, method)

    def test_wrong_audience_and_tampered_tokens_are_rejected(self):
        for token in (self.wrong_audience, self.customer[:-8] + "tampered"):
            for url in (f"{CATALOG}/api/v1/catalog/status", f"{CONFIGURATION}/api/v1/configuration",
                        f"{PRICING}/api/v1/pricing/currency", f"{INVENTORY}/api/v1/inventory/balances"):
                self.assertEqual(manage.request_json(url, token=token)[0], 401)

    def test_other_actuator_endpoints_are_not_exposed(self):
        self.assertIn(manage.request_json(f"{CATALOG}/actuator/env", token=self.customer)[0], (403, 404))

    def test_identity_discovery_advertises_exact_public_issuer(self):
        status, body = manage.request_json(
            "http://127.0.0.1:8180/realms/supersports/.well-known/openid-configuration")
        self.assertEqual(status, 200)
        self.assertEqual(body["issuer"], "http://localhost:8180/realms/supersports")
        status, body = manage.request_json(
            "http://127.0.0.1:8180/realms/supersports-customers/.well-known/openid-configuration")
        self.assertEqual(status, 200)
        self.assertEqual(body["issuer"], "http://localhost:8180/realms/supersports-customers")

    def psql(self, role, database, sql):
        keys = {"catalog": "CATALOG_DB_PASSWORD", "configuration": "CONFIGURATION_DB_PASSWORD",
                "pricing": "PRICING_DB_PASSWORD", "inventory": "INVENTORY_DB_PASSWORD",
                "customer": "CUSTOMER_DB_PASSWORD", "orders": "ORDERS_DB_PASSWORD",
                "payment": "PAYMENT_DB_PASSWORD", "fulfillment": "FULFILLMENT_DB_PASSWORD"}
        command = ('export PGPASSWORD="$' + keys[role] + '"; exec psql -X -A -t '
                   f'-h 127.0.0.1 -U supersports_{role} -d {database} -c \'{sql}\'')
        return manage.compose(["exec", "-T", "postgres", "sh", "-ec", command],
                              project=self.project, capture=True, check=False)

    def test_each_service_can_connect_to_its_own_migrated_database(self):
        for service in ("catalog", "configuration", "pricing", "inventory", "customer", "orders", "payment", "fulfillment"):
            result = self.psql(service, service,
                               "SELECT count(*) FROM flyway_schema_history WHERE success")
            self.assertEqual(result.returncode, 0)
            self.assertGreaterEqual(int(result.stdout.strip()), 1)

    def test_service_database_roles_cannot_connect_to_each_other_database(self):
        for owner, other in (("catalog", "configuration"), ("configuration", "catalog"),
                             ("pricing", "inventory"), ("inventory", "pricing"),
                             ("customer", "catalog"), ("catalog", "customer"),
                             ("orders", "customer"), ("customer", "orders"),
                             ("payment", "orders"), ("fulfillment", "orders")):
            result = self.psql(owner, other, "SELECT 1")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("permission denied", result.stderr.lower())

    def test_host_postgres_authentication_when_explicitly_enabled(self):
        import database_access
        if not database_access.configuration(ROOT,self.project)["enabled"]:
            self.skipTest("Default profile keeps PostgreSQL private; enable explicit local host inspection to verify TCP.")
        result=database_access.verify(manage,project=self.project)
        self.assertEqual(result["host"],"127.0.0.1")
        self.assertEqual(result["username"],"postgres")
        self.assertEqual(result["database"],"postgres")
        self.assertEqual(result["serverPort"],5432)

    def test_database_host_access_is_opt_in_and_all_host_bindings_are_loopback(self):
        import database_access
        host_access=database_access.configuration(ROOT,self.project)
        result = manage.compose(["ps", "--format", "json"], project=self.project, capture=True)
        # Compose emits one JSON object per line for multiple services.
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        core = {"postgres", "identity", "catalog", "configuration", "pricing", "inventory", "customer", "orders", "payment-simulator", "fulfillment-simulator", "storefront"}
        streaming = {"kafka", "kafka-connect", "order-history"}
        services = {row["Service"] for row in rows}
        self.assertTrue(core.issubset(services), services)
        self.assertTrue(services - core in (set(), streaming), services)
        for row in rows:
            publishers = row.get("Publishers") or []
            if row["Service"] == "postgres":
                published=[port for port in publishers if port.get("PublishedPort",0)]
                if host_access["enabled"]:
                    self.assertEqual(len(published),1)
                    self.assertEqual(published[0]["URL"],"127.0.0.1")
                    self.assertEqual(published[0]["PublishedPort"],host_access["port"])
                else:self.assertFalse(published)
            else:
                self.assertTrue(publishers)
                for port in publishers:
                    if port.get("PublishedPort", 0):
                        self.assertEqual(port["URL"], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
