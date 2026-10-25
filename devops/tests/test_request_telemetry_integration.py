"""Real local OTLP pipeline acceptance. Execute only in final testing phase."""
import base64
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlencode
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import manage


@unittest.skipUnless(os.environ.get("SUPERSPORTS_TELEMETRY") == "1", "Enable local telemetry and run the explicit final integration profile")
class RequestTelemetryIntegrationTest(unittest.TestCase):
    def proxy(self, uid, path):
        basic = base64.b64encode(b"admin:admin").decode()
        return manage.request_json(f"http://127.0.0.1:3001/api/datasources/proxy/uid/{uid}/{path}",
                                   headers={"Authorization": "Basic " + basic})

    def wait_for(self, read, predicate, seconds=60):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            status, result = read()
            if status == 200 and predicate(result):
                return result
            time.sleep(1)
        self.fail("Telemetry observation did not arrive within the measured window")

    def test_request_produces_metrics_sanitized_jdbc_trace_and_linked_safe_log(self):
        trace = uuid.uuid4().hex
        sentinel = "private-sentinel-" + uuid.uuid4().hex
        header = {"traceparent": f"00-{trace}-{uuid.uuid4().hex[:16]}-01", "tracestate": "test=" + sentinel,
                  "X-Private-Test": sentinel}
        status, result = manage.request_json("http://127.0.0.1:8081/api/v1/catalog/public/products?pageSize=1&private=" + sentinel,
                                             headers=header)
        self.assertEqual(200, status)
        self.assertTrue(result["items"])
        spans = self.wait_for(lambda: self.proxy("supersports-tempo", f"api/traces/{trace}"),
                              lambda body: bool(body.get("batches") or body.get("resourceSpans")))
        serialized = json.dumps(spans)
        self.assertNotIn(sentinel, serialized)
        self.assertNotIn("db.statement", serialized)
        self.assertNotIn("url.query", serialized)
        self.assertNotIn("exception.message", serialized)
        batches = spans.get("batches", spans.get("resourceSpans", []))
        all_spans = [span for batch in batches for scope in batch.get("scopeSpans", []) for span in scope.get("spans", [])]
        self.assertGreaterEqual(len(all_spans), 2, "Expected server and JDBC child spans")
        query = '{service_name="catalog"} | trace_id="' + trace + '"'
        logs = self.wait_for(lambda: self.proxy("supersports-loki", "loki/api/v1/query_range?" + urlencode({"query": query, "limit": 20})),
                             lambda body: bool(body.get("data", {}).get("result")))
        self.assertNotIn(sentinel, json.dumps(logs))
        self.assertIn("http_request", json.dumps(logs))
        self.assertIn(trace, json.dumps(logs))
        metrics = self.wait_for(lambda: self.proxy("supersports-prometheus", "api/v1/query?" + urlencode({
            "query": 'sum(http_server_request_duration_seconds_count{service_name="catalog"})'})),
            lambda body: bool(body.get("data", {}).get("result")))
        self.assertGreater(float(metrics["data"]["result"][0]["value"][1]), 0)

    def test_collector_removes_untrusted_event_link_and_propagation_data(self):
        trace, sentinel = uuid.uuid4().hex, "private-sentinel-" + uuid.uuid4().hex
        now = time.time_ns()
        attribute = {"key": "private", "value": {"stringValue": sentinel}}
        payload = {"resourceSpans": [{"resource": {"attributes": [
            {"key": "service.name", "value": {"stringValue": "privacy-fixture"}}, attribute]},
            "scopeSpans": [{"scope": {"name": "privacy-fixture"}, "spans": [{
                "traceId": trace, "spanId": uuid.uuid4().hex[:16], "name": sentinel, "kind": 2,
                "startTimeUnixNano": str(now), "endTimeUnixNano": str(now + 1000000),
                "traceState": "test=" + sentinel, "attributes": [attribute],
                "status": {"code": 2, "message": sentinel},
                "events": [{"timeUnixNano": str(now), "name": sentinel, "attributes": [attribute]}],
                "links": [{"traceId": uuid.uuid4().hex, "spanId": uuid.uuid4().hex[:16],
                           "traceState": "test=" + sentinel, "attributes": [attribute]}]}]}]}]}
        sender = "import sys,urllib.request; urllib.request.urlopen(urllib.request.Request('http://otel-collector:4318/v1/traces',data=sys.stdin.buffer.read(),headers={'Content-Type':'application/json'}),timeout=10).read()"
        sent = manage.compose(["--profile", "observability", "exec", "-T", "health-exporter", "python", "-c", sender],
                              input_text=json.dumps(payload), capture=True, check=False)
        self.assertEqual(sent.returncode, 0, sent.stderr[-1500:].replace(sentinel, "[sentinel]"))
        stored = self.wait_for(lambda: self.proxy("supersports-tempo", f"api/traces/{trace}"),
                               lambda body: bool(body.get("batches") or body.get("resourceSpans")))
        self.assertNotIn(sentinel, json.dumps(stored))
        spans = [span for batch in stored.get("batches", stored.get("resourceSpans", []))
                 for scope in batch.get("scopeSpans", []) for span in scope.get("spans", [])]
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["name"], "operation")
        self.assertFalse(spans[0].get("events"))
        self.assertFalse(spans[0].get("links"))
        self.assertFalse(spans[0].get("traceState"))

    def test_owned_tracking_links_orders_and_fulfillment_spans(self):
        credentials = manage.load_credentials(manage.ROOT / "devops/.local/bootstrap.env")
        token = manage.customer_token_for("checkout-test-customer", credentials["DEMO_CUSTOMER_PASSWORD"])
        status, orders = manage.request_json("http://127.0.0.1:8086/api/v1/orders", token=token)
        self.assertEqual(status, 200)
        self.assertTrue(orders)
        trace = uuid.uuid4().hex
        order_id = orders[0]["id"]
        status, _ = manage.request_json(f"http://127.0.0.1:8086/api/v1/orders/{order_id}/tracking", token=token,
            headers={"traceparent": f"00-{trace}-{uuid.uuid4().hex[:16]}-01"})
        self.assertEqual(status, 200)

        def spans_by_service(body):
            result = {}
            for batch in body.get("batches", body.get("resourceSpans", [])):
                name = next(a["value"]["stringValue"] for a in batch["resource"]["attributes"] if a["key"] == "service.name")
                result.setdefault(name, []).extend(span for scope in batch.get("scopeSpans", []) for span in scope.get("spans", []))
            return result

        def linked(body):
            services = spans_by_service(body)
            clients = {span["spanId"] for span in services.get("orders", []) if span.get("kind") in (3, "SPAN_KIND_CLIENT")}
            return any(span.get("parentSpanId") in clients for span in services.get("fulfillment-simulator", [])
                       if span.get("kind") in (2, "SPAN_KIND_SERVER"))

        stored = self.wait_for(lambda: self.proxy("supersports-tempo", f"api/traces/{trace}"),
                               linked)
        self.assertNotIn(order_id, json.dumps(stored))
        by_service = spans_by_service(stored)
        clients = {span["spanId"] for span in by_service["orders"] if span.get("kind") in (3, "SPAN_KIND_CLIENT")}
        remote = [span for span in by_service["fulfillment-simulator"] if span.get("kind") in (2, "SPAN_KIND_SERVER")]
        self.assertTrue(clients)
        self.assertTrue(any(span.get("parentSpanId") in clients for span in remote), "Remote server must be a child of Orders HTTP client")

    @unittest.skipUnless(os.getenv("SUPERSPORTS_TELEMETRY_FAULTS") == "1", "Explicit Collector/backend restart acceptance")
    def test_telemetry_outage_preserves_commerce_and_stored_trace_survives_restart(self):
        trace = uuid.uuid4().hex
        manage.compose(["--profile", "observability", "stop", "otel-collector"], capture=True)
        try:
            for _ in range(5):
                self.assertEqual(manage.request_json("http://127.0.0.1:8081/api/v1/catalog/public/products?pageSize=1")[0], 200)
            self.assertEqual(manage.request_json("http://127.0.0.1:8081/actuator/health/readiness")[0], 200)
        finally:
            manage.compose(["--profile", "observability", "up", "-d", "--no-deps", "otel-collector"], capture=True)
        present = lambda body: bool(body.get("batches") or body.get("resourceSpans"))
        def recovered_trace():
            self.assertEqual(manage.request_json("http://127.0.0.1:8081/api/v1/catalog/public/products?pageSize=1",
                headers={"traceparent": f"00-{trace}-{uuid.uuid4().hex[:16]}-01"})[0], 200)
            return self.proxy("supersports-tempo", f"api/traces/{trace}")
        self.wait_for(recovered_trace, present)
        manage.compose(["--profile", "observability", "restart", "tempo", "loki"], capture=True)
        self.wait_for(lambda: self.proxy("supersports-tempo", f"api/traces/{trace}"), present)

    @unittest.skipUnless(os.getenv("SUPERSPORTS_TELEMETRY_FAULTS") == "1", "Explicit dependency-outage/server-error acceptance")
    def test_dependency_failure_records_server_error_without_changing_catalog(self):
        token = manage.token_for("admin", manage.configure_admin_login())
        status, products = manage.request_json("http://127.0.0.1:8081/api/v1/catalog/admin/products", token=token)
        self.assertEqual(status, 200)
        product = next(row for row in products if row["status"] == "active")
        trace, sentinel = uuid.uuid4().hex, "private-sentinel-" + uuid.uuid4().hex
        manage.compose(["stop", "pricing"], capture=True)
        try:
            status, _ = manage.request_json(f"http://127.0.0.1:8081/api/v1/catalog/products/{product['id']}/activate?private={sentinel}",
                token=token, method="POST", data=json.dumps({"expectedRevision": product["revision"]}).encode(),
                headers={"traceparent": f"00-{trace}-{uuid.uuid4().hex[:16]}-01", "tracestate": "test=" + sentinel})
            self.assertEqual(status, 502)
        finally:
            manage.compose(["up", "-d", "--no-deps", "--no-build", "--wait", "--wait-timeout", "120", "pricing"], capture=True)
        stored = self.wait_for(lambda: self.proxy("supersports-tempo", f"api/traces/{trace}"),
                               lambda body: bool(body.get("batches") or body.get("resourceSpans")))
        self.assertNotIn(sentinel, json.dumps(stored))
        self.assertNotIn(product["id"], json.dumps(stored))
        self.assertNotIn("exception.message", json.dumps(stored))
        metrics = self.wait_for(lambda: self.proxy("supersports-prometheus", "api/v1/query?" + urlencode({
            "query": 'sum(http_server_request_duration_seconds_count{service_name="catalog",http_response_status_code="502"})'})),
            lambda body: bool(body.get("data", {}).get("result")) and float(body["data"]["result"][0]["value"][1]) >= 1)
        self.assertGreaterEqual(float(metrics["data"]["result"][0]["value"][1]), 1)
        token = manage.token_for("admin", manage.configure_admin_login())
        status, products = manage.request_json("http://127.0.0.1:8081/api/v1/catalog/admin/products", token=token)
        self.assertEqual(status, 200)
        current = next(row for row in products if row["id"] == product["id"])
        self.assertEqual((current["status"], current["revision"]), (product["status"], product["revision"]))


if __name__ == "__main__":
    unittest.main()
