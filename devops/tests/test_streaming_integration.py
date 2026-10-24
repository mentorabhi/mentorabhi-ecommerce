"""Live checks for the local Orders CDC and owner-scoped history projection."""
from __future__ import annotations

import os
import json
from pathlib import Path
import sys
import time
import unittest
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import manage


class StreamingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("SUPERSPORTS_INTEGRATION") != "1":
            raise unittest.SkipTest("Run through devops/scripts/supersports test")
        try:
            with urlopen("http://127.0.0.1:8089/actuator/health/readiness", timeout=3) as response:
                if response.status != 200:
                    raise unittest.SkipTest("Start the streaming profile before these checks")
        except (HTTPError, URLError, TimeoutError):
            raise unittest.SkipTest("Start the streaming profile before these checks")
        cls.credentials = manage.load_credentials(manage.ROOT / "devops/.local/bootstrap.env")
        cls.project = manage.validated_project_name(os.environ.get("SUPERSPORTS_PROJECT", "supersports"))
        cls.customer = manage.customer_token_for("checkout-test-customer", cls.credentials["DEMO_CUSTOMER_PASSWORD"])
        cls.other = manage.customer_token_for("checkout-test-customer-b", cls.credentials["DEMO_CUSTOMER_PASSWORD"])

    def consumer_restart_count(self):
        result = manage.compose(["ps", "-q", "order-history"], project=self.project, capture=True)
        container = result.stdout.strip()
        self.assertTrue(container, "Order History container is not running")
        inspected = manage.run(["docker", "inspect", "--format", "{{.RestartCount}}", container], capture=True)
        return int(inspected.stdout.strip())

    def wait_for_zero_lag(self):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            result = manage.compose(["--profile", "streaming", "exec", "-T", "kafka",
                "/opt/kafka/bin/kafka-consumer-groups.sh", "--bootstrap-server", "localhost:9092",
                "--describe", "--group", "order-history-v1"], project=self.project, capture=True, check=False)
            rows = [line.split() for line in result.stdout.splitlines()
                    if line.strip().startswith("order-history-v1 commerce.order.events.v1")]
            if len(rows) == 3 and all(row[5] == "0" for row in rows):
                return
            time.sleep(1)
        self.fail("Order History consumer did not drain to zero lag before fault injection")

    def test_cdc_projection_and_tenant_scoped_read_api(self):
        with urlopen("http://127.0.0.1:8090/connectors/supersports-orders-outbox/status", timeout=5) as response:
            connector = __import__("json").loads(response.read())
        self.assertEqual(connector["connector"]["state"], "RUNNING")
        self.assertEqual(connector["tasks"][0]["state"], "RUNNING")

        status, history = manage.request_json("http://127.0.0.1:8089/api/v1/order-history", token=self.customer)
        self.assertEqual(status, 200)
        self.assertTrue(history["orders"])
        order = history["orders"][0]
        self.assertIsInstance(order["lines"], list)
        self.assertGreater(order["lastSequence"], 0)
        self.assertEqual(manage.request_json("http://127.0.0.1:8089/api/v1/order-history?customerKey=forged", token=self.customer)[0], 400)
        self.assertEqual(manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{order['id']}", token=self.other)[0], 404)

        _, products = manage.request_json("http://127.0.0.1:8081/api/v1/catalog/products?q=football")
        sku_id = products[0]["skus"][0]["id"]
        _, profile = manage.request_json("http://127.0.0.1:8085/api/v1/customer/profile", token=self.customer)
        address = {"fullName": "Streaming Test", "phone": "9876543210", "line1": "12 Test Road",
                   "line2": "", "city": "Pune", "state": "Maharashtra", "postalCode": "411001",
                   "country": "IN", "expectedRevision": profile["revision"]}
        self.assertEqual(manage.request_json("http://127.0.0.1:8085/api/v1/customer/profile", token=self.customer,
                                             method="PUT", data=json.dumps(address).encode())[0], 200)
        self.wait_for_zero_lag()
        restart_count = self.consumer_restart_count()
        manage.stream_fault("consumer-after-db-commit", next_event=True, project=self.project)
        key = "streaming-" + uuid.uuid4().hex
        status, accepted = manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout", token=self.customer,
                                               method="POST", data=json.dumps({"lines": [{"skuId": sku_id, "quantity": 1}], "couponCode": None}).encode(),
                                               headers={"Idempotency-Key": key})
        self.assertEqual(status, 202)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline and self.consumer_restart_count() <= restart_count:
            time.sleep(1)
        self.assertGreater(self.consumer_restart_count(), restart_count,
                           "One-shot fault did not crash the consumer after its database commit")
        deadline = time.monotonic() + 45
        projected = None
        while time.monotonic() < deadline:
            projected_status, projected = manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{accepted['orderId']}", token=self.customer)
            if projected_status == 200 and projected["lastSequence"] >= 1:
                break
            time.sleep(0.5)
        self.assertEqual(projected_status, 200, "CDC event did not reach the owner-scoped projection")
        self.assertEqual(projected["totalMinor"], accepted["totalMinor"])
        self.assertEqual(len(projected["lines"]), 1)
        inbox = manage.compose(["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "order_history",
            "-tA", "-c", f"SELECT count(*),count(DISTINCT aggregate_sequence) FROM order_history_state_event WHERE order_id='{accepted['orderId']}'"],
            project=self.project, capture=True).stdout.strip().split("|")
        self.assertEqual(int(inbox[0]), int(inbox[1]))
        self.assertEqual(int(inbox[0]), projected["lastSequence"],
                         "Redelivery after database commit must not duplicate projected sequence events")
        self.assertEqual(manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{accepted['orderId']}", token=self.other)[0], 404)

        schema = json.loads((ROOT / "contracts/orders/order-lifecycle-v1.schema.json").read_text())
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        query = manage.compose_command(ROOT, self.project, ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "orders", "-tA", "-c", "SELECT payload::text FROM order_outbox ORDER BY id"])
        rows = manage.run(query, environment=manage.deployment_env(ROOT), capture=True).stdout.splitlines()
        self.assertGreaterEqual(len(rows), 60)
        for index, row in enumerate(rows):
            with self.subTest(outbox_row=index + 1):
                validator.validate(json.loads(row))

        private_read = manage.compose(["exec", "-T", "postgres", "sh", "-ec",
            'export PGPASSWORD="$ORDER_HISTORY_DB_PASSWORD"; exec psql -X -A -t -h 127.0.0.1 -U supersports_order_history -d orders -c "SELECT 1"'],
            project=self.project, capture=True, check=False)
        self.assertNotEqual(private_read.returncode, 0)
        self.assertIn("permission denied for database", private_read.stderr.lower())
        self.assertIn("does not have connect privilege", private_read.stderr.lower())


if __name__ == "__main__":
    unittest.main()
