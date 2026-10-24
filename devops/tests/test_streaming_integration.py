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
import stream_operations
import projection_operations


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
            group=manage.history_target(project=self.project)["group"]
            result = manage.compose(["--profile", "streaming", "exec", "-T", "kafka",
                "/opt/kafka/bin/kafka-consumer-groups.sh", "--bootstrap-server", "localhost:9092",
                "--describe", "--group", group], project=self.project, capture=True, check=False)
            rows = [line.split() for line in result.stdout.splitlines()
                    if line.strip().startswith(group+" commerce.order.events.v1")]
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
        inbox = manage.compose(["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", manage.history_target(project=self.project)["database"],
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

    def test_operator_poison_replay_is_audited_idempotent_and_restartable(self):
        self.wait_for_zero_lag()
        demo=stream_operations.demo(manage,project=self.project)
        path=Path(demo["correctedPayloadFile"])
        try:
            corrected=path.read_text()
            event=json.loads(corrected)
            operation=demo["operationId"]
            request={"action":"replay","sourceCoordinate":demo["sourceCoordinate"],"correctedPayload":corrected,
                     "operationId":operation,"reason":"integration poison version correction"}
            def sql(query,check=True):
                return manage.compose(["exec","-T","postgres","psql","-U","postgres","-d",manage.history_target(project=self.project)["database"],"-tA","-c",query],
                                      project=self.project,capture=True,check=check)
            before=sql("SELECT count(*) FROM event_inbox").stdout.strip()
            with self.assertRaisesRegex(RuntimeError,"OPERATOR_AUTHENTICATION_REQUIRED"):
                stream_operations.operator(manage,request,project=self.project,token=self.customer)
            with self.assertRaisesRegex(RuntimeError,"INJECTED_BEFORE_PUBLISH"):
                stream_operations.operator(manage,{**request,"failBeforePublish":True},project=self.project)
            self.assertEqual(sql(f"SELECT count(*) FROM order_history_replay_audit WHERE operation_id='{operation}'").stdout.strip(),"1")
            with self.assertRaisesRegex(RuntimeError,"INJECTED_AFTER_PUBLISH"):
                stream_operations.operator(manage,{**request,"failAfterPublish":True},project=self.project)
            self.wait_for_zero_lag()
            self.assertEqual(sql(f"SELECT count(*) FROM order_history_replay_delivery WHERE operation_id='{operation}' AND published_at IS NULL").stdout.strip(),"1")
            result=stream_operations.replay(manage,demo["sourceCoordinate"],path,operation,request["reason"],project=self.project)
            self.assertEqual(result["status"],"PUBLISHED")
            self.assertEqual(result["eventId"],event["eventId"])
            self.assertEqual(result,stream_operations.replay(manage,demo["sourceCoordinate"],path,operation,request["reason"],project=self.project))
            self.wait_for_zero_lag()
            self.assertEqual(sql("SELECT count(*) FROM event_inbox").stdout.strip(),before)
            with self.assertRaisesRegex(RuntimeError,"REPLAY_OPERATION_ID_CONFLICT"):
                stream_operations.operator(manage,{**request,"reason":"changed reason"},project=self.project)
            changed={**event,"occurredAt":"2026-10-24T01:02:03Z"}
            with self.assertRaisesRegex(RuntimeError,"APPLIED_EVENT_CANNOT_BE_REWRITTEN"):
                stream_operations.operator(manage,{**request,"operationId":str(uuid.uuid4()),"correctedPayload":json.dumps(changed)},project=self.project)
            formatted=json.dumps(event,sort_keys=True,indent=2)
            second=stream_operations.operator(manage,{**request,"operationId":str(uuid.uuid4()),"correctedPayload":formatted},project=self.project)
            self.assertEqual(second["status"],"PUBLISHED")
            self.wait_for_zero_lag()
            self.assertEqual(sql("SELECT count(*) FROM event_inbox").stdout.strip(),before)
            immutable=sql(f"UPDATE order_history_replay_audit SET reason='rewrite' WHERE operation_id='{operation}'",check=False)
            self.assertNotEqual(immutable.returncode,0)
            self.assertIn("append-only",immutable.stderr)
        finally:
            path.unlink(missing_ok=True)

    def test_z_isolated_rebuild_failure_dry_run_cutover_and_new_event_delivery(self):
        self.wait_for_zero_lag()
        old=manage.history_target(project=self.project)
        self.assertTrue(projection_operations.reconcile(manage,project=self.project)["ok"])
        with stream_operations.exclusive(manage,self.project):
            dry=projection_operations.rebuild(manage,project=self.project,dry_run=True)
            self.assertTrue(dry["ok"],dry)
            self.assertEqual(dry["status"],"DRY_RUN_VERIFIED")
            self.assertEqual(manage.history_target(project=self.project),old)
            failed=projection_operations.rebuild(manage,project=self.project,inject_mismatch=True)
            self.assertFalse(failed["ok"],failed)
            self.assertEqual(failed["status"],"RECONCILIATION_FAILED")
            self.assertTrue(any(error.startswith("ORDER_STATE_OWNER_MONEY_MISMATCH") for error in failed["reconciliation"]["errors"]))
            self.assertEqual(manage.history_target(project=self.project),old)
            healthy=manage.request_json("http://127.0.0.1:8089/actuator/health/readiness")
            self.assertEqual(healthy[0],200)
            active=projection_operations.rebuild(manage,project=self.project)
            self.assertTrue(active["ok"],active)
            self.assertEqual(active["status"],"ACTIVE")
        self.assertEqual(manage.history_target(project=self.project),active["candidate"])
        self.assertNotEqual(active["candidate"],old)
        first=active["watermarks"]["firstHighWater"]; second=active["watermarks"]["secondHighWater"]
        self.assertEqual(set(first),{"0","1","2"})
        self.assertTrue(all(second[key]>=first[key] for key in first))
        self.customer=manage.customer_token_for("checkout-test-customer",self.credentials["DEMO_CUSTOMER_PASSWORD"])
        self.other=manage.customer_token_for("checkout-test-customer-b",self.credentials["DEMO_CUSTOMER_PASSWORD"])
        status,history=manage.request_json("http://127.0.0.1:8089/api/v1/order-history",token=self.customer)
        self.assertEqual(status,200);self.assertTrue(history["orders"])
        existing=history["orders"][0]["id"]
        self.assertEqual(manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{existing}",token=self.other)[0],404)
        _,products=manage.request_json("http://127.0.0.1:8081/api/v1/catalog/products?q=football")
        sku=products[0]["skus"][0]["id"]
        status,accepted=manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout",token=self.customer,method="POST",
            data=json.dumps({"lines":[{"skuId":sku,"quantity":1}],"couponCode":None}).encode(),headers={"Idempotency-Key":"post-rebuild-"+uuid.uuid4().hex})
        self.assertEqual(status,202)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            projected_status,projected=manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{accepted['orderId']}",token=self.customer)
            if projected_status==200 and projected["lastSequence"]>=3:break
            time.sleep(0.5)
        self.assertEqual(projected_status,200)
        self.assertEqual(projected["state"],"FULFILLMENT_SCHEDULED")
        self.assertEqual(projected["totalMinor"],accepted["totalMinor"])
        self.wait_for_zero_lag()
        reconciled=projection_operations.reconcile(manage,project=self.project)
        self.assertTrue(reconciled["ok"],reconciled)
        self.assertEqual(reconciled["target"],active["candidate"])


if __name__ == "__main__":
    unittest.main()
