import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from acceptance_probe import ProbeFailure
import acceptance_probe
import checkout_soak
import retention_probe


class AcceptanceProbeTests(unittest.TestCase):
    def test_auth_refresh_cannot_dispatch_after_the_workload_deadline(self):
        now = [100]
        def refresh():
            now[0] = 1001
            return 'test-only'
        with self.assertRaises(ProbeFailure):
            checkout_soak.prepare_dispatch(refresh, 100, 900, lambda: now[0])

    def test_late_poll_cannot_accept_a_terminal_order_after_drain(self):
        self.assertEqual(checkout_soak.completion_observed(100, 900, 1179), 1179)
        with self.assertRaises(ProbeFailure):
            checkout_soak.completion_observed(100, 900, 1181)

    def test_resource_acceptance_includes_disappeared_stopped_and_oom_containers(self):
        before = [{"id": "a", "running": True, "oom": False, "restarts": 0}]
        acceptance_probe.verify_containers(before, before)
        for after in ([], [{"id": "a", "running": False, "oom": False, "restarts": 0}],
                      [{"id": "a", "running": False, "oom": True, "restarts": 0}]):
            with self.subTest(after=after):
                with self.assertRaises(ProbeFailure):
                    acceptance_probe.verify_containers(before, after)

    def test_failed_or_unassigned_connector_tasks_are_not_healthy(self):
        self.assertFalse(acceptance_probe.connector_running({"connector": {"state": "RUNNING"}, "tasks": []}))
        self.assertFalse(acceptance_probe.connector_running({"connector": {"state": "RUNNING"}, "tasks": [{"state": "FAILED"}]}))
        self.assertTrue(acceptance_probe.connector_running({"connector": {"state": "RUNNING"}, "tasks": [{"state": "RUNNING"}]}))

    def test_lost_connector_creation_response_does_not_orphan_owned_resources(self):
        state = {"databases": set(), "topics": set(), "connectors": set()}
        def sql_fake(project, database, statement, **kwargs):
            if statement.startswith("CREATE DATABASE "):
                state["databases"].add(statement.split()[-1])
            if statement.startswith("DROP DATABASE IF EXISTS "):
                state["databases"].discard(statement.split()[4])
            return SimpleNamespace(stdout="", returncode=0)
        def kafka_fake(project, command, arguments, **kwargs):
            if command == "kafka-topics":
                if "--create" in arguments:
                    state["topics"].add(arguments[arguments.index("--topic") + 1])
                if "--delete" in arguments:
                    state["topics"].discard(arguments[arguments.index("--topic") + 1])
                if "--list" in arguments:
                    return SimpleNamespace(stdout="\n".join(state["topics"]), returncode=0)
            return SimpleNamespace(stdout="", returncode=0)
        def request_fake(url, **kwargs):
            if url == retention_probe.BASE and kwargs.get("method") == "POST":
                state["connectors"].add(json.loads(kwargs["data"])["name"])
                return 0, {}  # Server created it; the response was lost.
            if url.endswith("/status"):
                return 200, {"connector": {"state": "RUNNING"}, "tasks": [{"state": "RUNNING"}]}
            return 200, {"name": "unchanged-main-config"}
        def connect_fake(url, method="GET", data=None):
            if method == "DELETE":
                state["connectors"].discard(url.rsplit("/", 1)[1])
            return 204, {}
        with patch.object(retention_probe, "environment", return_value={}), \
             patch.object(retention_probe, "sql", side_effect=sql_fake), \
             patch.object(retention_probe, "kafka", side_effect=kafka_fake), \
             patch.object(retention_probe.manage, "request_json", side_effect=request_fake), \
             patch.object(retention_probe.manage, "load_credentials", return_value={"CDC_DB_PASSWORD": "test-only"}), \
             patch.object(retention_probe, "connect_request", side_effect=connect_fake), \
             patch.object(retention_probe, "save_report", return_value=retention_probe.manage.ROOT / "devops/.local/test-report.json"):
            with self.assertRaises(ProbeFailure):
                retention_probe.run_probe(60, 15, "supersports")
        self.assertEqual(state, {"databases": set(), "topics": set(), "connectors": set()})

    def test_workload_deadline_cannot_submit_during_drain(self):
        self.assertTrue(checkout_soak.submission_due(885, 900, 59, 60, 15))
        self.assertFalse(checkout_soak.submission_due(900, 900, 60, 60, 15))
        with self.assertRaises(ProbeFailure):
            checkout_soak.submission_due(901, 900, 59, 60, 15)

    def test_recovery_budget_includes_connector_startup(self):
        self.assertEqual(retention_probe.remaining_recovery(100, 180), 100)
        with self.assertRaises(ProbeFailure):
            retention_probe.remaining_recovery(100, 281)

    def test_zero_lag_requires_every_expected_partition(self):
        partial = 'g t 0 10 10 0 - - -\ng t 1 20 20 0 - - -'
        with self.assertRaises(ProbeFailure):
            acceptance_probe.parse_group_offsets(partial, 'g', 't', {0, 1, 2})
        complete = partial + '\ng t 2 30 30 0 - - -'
        self.assertEqual(set(acceptance_probe.parse_group_offsets(complete, 'g', 't', {0, 1, 2})), {0, 1, 2})

    def test_terminal_sequence_alone_cannot_hide_a_missing_lifecycle_event(self):
        events = [{"aggregateId": "order", "eventId": "one", "aggregateSequence": 1, "eventType": "OrderAccepted"},
                  {"aggregateId": "order", "eventId": "three", "aggregateSequence": 3, "eventType": "FulfillmentScheduled"}]
        with self.assertRaises(ProbeFailure):
            checkout_soak.verify_lifecycle(events, {"order"})
        events.append({"aggregateId": "order", "eventId": "two", "aggregateSequence": 2, "eventType": "OrderConfirmed"})
        checkout_soak.verify_lifecycle(events, {"order"})

    def test_schedule_is_bounded_and_covers_the_full_window(self):
        self.assertEqual(checkout_soak.planned_orders(900, 15), 60)
        self.assertEqual(checkout_soak.planned_orders(61, 15), 5)
        for duration, interval in ((0, 15), (900, 1), (3600, 10)):
            with self.subTest(duration=duration, interval=interval):
                with self.assertRaises(ProbeFailure):
                    checkout_soak.planned_orders(duration, interval)

    def test_projection_rejects_missing_sequence_money_and_quantity_drift(self):
        order = {"currency": "INR", "totalMinor": 123, "lines": [{"skuId": "a", "quantity": 1}]}
        history = {**order, "state": "FULFILLMENT_SCHEDULED", "lastSequence": 3}
        checkout_soak.verify_projection(order, history)
        for change in ({"lastSequence": 2}, {"totalMinor": 124}, {"lines": [{"skuId": "a", "quantity": 2}]}):
            with self.subTest(change=change):
                with self.assertRaises(ProbeFailure):
                    checkout_soak.verify_projection(order, {**history, **change})

    def test_retained_fold_preserves_latest_row_and_deduplicates_identities(self):
        events = [{"op": op, "after": {"id": 1, "version": version, "payload": "x"}}
                  for op, version in (("r", 0), ("u", 1), ("u", 1))]
        state, identities = retention_probe.fold_records("\n".join(json.dumps(e) for e in events))
        self.assertEqual(state, {"1": {"id": 1, "version": 1, "payload": "x"}})
        self.assertEqual(identities, {("r", 1, 0), ("u", 1, 1)})
        with self.assertRaises(ProbeFailure):
            retention_probe.fold_records('{"op":"u","after":null}')

    def test_retention_rejects_lost_wal_truncation_and_changed_checkpoint(self):
        baseline = {"active": False, "confirmed": "0/100", "retainedBytes": 1000, "walStatus": "reserved"}
        retention_probe.retained_coordinates(baseline, baseline, (0, 20), (0, 20), 20)
        for slot, bounds, offset in (({**baseline, "active": True}, (0, 20), 20),
                                    ({**baseline, "walStatus": "lost"}, (0, 20), 20),
                                    ({**baseline, "confirmed": "0/200"}, (0, 20), 20),
                                    (baseline, (5, 20), 20), (baseline, (0, 20), 21)):
            with self.subTest(slot=slot, bounds=bounds, offset=offset):
                with self.assertRaises(ProbeFailure):
                    retention_probe.retained_coordinates(baseline, slot, (0, 20), bounds, offset)

    def test_connect_empty_success_is_not_an_api_failure(self):
        with patch.object(retention_probe, "urlopen") as opened:
            response = opened.return_value.__enter__.return_value
            response.status = 204
            response.read.return_value = b""
            self.assertEqual(retention_probe.connect_request("http://localhost:8090/connectors/fixture/stop", "PUT"), (204, {}))


if __name__ == "__main__":
    unittest.main()
