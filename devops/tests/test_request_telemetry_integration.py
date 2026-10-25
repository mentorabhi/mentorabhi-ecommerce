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
        header = {"traceparent": f"00-{trace}-{uuid.uuid4().hex[:16]}-01", "X-Private-Test": sentinel}
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


if __name__ == "__main__":
    unittest.main()
