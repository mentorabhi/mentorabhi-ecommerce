"""Projection reconciliation must detect content corruption even at equal counts."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("projection_operations",ROOT/"devops/scripts/projection_operations.py")
projection=importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


class ReconciliationTests(unittest.TestCase):
    def fixtures(self):
        order="00000000-0000-4000-8000-000000000001"
        event={"eventId":"00000000-0000-4000-8000-000000000002","aggregateId":order,
               "aggregateSequence":1,"eventType":"OrderAccepted","occurredAt":"2026-10-24T00:00:00Z",
               "customerKey":"a"*64,"data":{"lines":[{"skuId":"sku","quantity":1}],"totalMinor":123,"currency":"INR"}}
        row={"orderId":order,"state":"PENDING_PAYMENT","currency":"INR","totalMinor":123,
             "customerKey":"a"*64,"lastSequence":1,"lines":event["data"]["lines"]}
        source={"events":[event],"orders":[row]}
        inspection={"scan":{"events":[{"eventId":event["eventId"],"canonicalHash":digest(event),"rawHashes":["legacy"]}],
                            "poison":[],"conflicts":[],"highWater":{"0":1}},
                    "snapshot":{"events":[{"eventId":event["eventId"],"rawHash":"legacy","canonicalHash":digest(event)}],
                                "orders":[copy.deepcopy(row)],"pendingEvents":0,"audit":[],"deliveries":[],
                                "timeline":[{"eventId":event["eventId"],"orderId":order,"sequence":1,
                                             "eventType":"OrderAccepted","state":"PENDING_PAYMENT","occurredAt":"2026-10-24T00:00:00+00:00"}]}}
        return source,inspection

    def test_matching_history_reports_exact_event_order_and_money_totals(self):
        source,inspection=self.fixtures()
        result=projection.compare_snapshot(source,inspection)
        self.assertTrue(result["ok"],result["errors"])
        self.assertEqual(result["events"],1)
        self.assertEqual(result["orders"],1)
        self.assertEqual(result["totalsMinor"],{"INR":123})

    def test_v2_order_state_is_reconciled_from_the_versioned_event_payload(self):
        source,inspection=self.fixtures()
        event=source["events"][0]
        event.update(eventVersion=2,eventType="OrderCancelled",aggregateSequence=2,
            data={"orderId":event["aggregateId"],"state":"CANCELLED","operationId":"op","refundMinor":123,"currency":"INR","reasonCode":"CUSTOMER_REQUEST"})
        source["orders"][0].update(state="CANCELLED",lastSequence=2)
        inspection["scan"]["events"][0].update(canonicalHash=digest(event))
        inspection["snapshot"]["events"][0].update(canonicalHash=digest(event))
        inspection["snapshot"]["orders"][0].update(state="CANCELLED",lastSequence=2)
        inspection["snapshot"]["timeline"][0].update(eventType="OrderCancelled",state="CANCELLED",sequence=2)
        self.assertTrue(projection.compare_snapshot(source,inspection)["ok"])

    def test_equal_counts_do_not_hide_hash_id_owner_state_amount_or_timeline_corruption(self):
        mutations=[lambda i:i["scan"]["events"][0].update(canonicalHash="bad"),
                   lambda i:i["snapshot"]["events"][0].update(eventId="other"),
                   lambda i:i["snapshot"]["orders"][0].update(customerKey="b"*64),
                   lambda i:i["snapshot"]["orders"][0].update(state="CONFIRMED"),
                   lambda i:i["snapshot"]["orders"][0].update(totalMinor=124),
                   lambda i:i["snapshot"]["timeline"][0].update(state="CONFIRMED")]
        for mutation in mutations:
            source,inspection=self.fixtures();mutation(inspection)
            with self.subTest(mutation=mutation):self.assertFalse(projection.compare_snapshot(source,inspection)["ok"])

    def test_legacy_hash_is_accepted_only_when_retained_kafka_proves_original_bytes(self):
        source,inspection=self.fixtures();inspection["snapshot"]["events"][0]["canonicalHash"]=None
        self.assertTrue(projection.compare_snapshot(source,inspection)["ok"])
        inspection["snapshot"]["events"][0]["rawHash"]="unknown"
        self.assertFalse(projection.compare_snapshot(source,inspection)["ok"])

    def test_sequence_gaps_conflicting_events_and_unresolved_poison_prevent_cutover(self):
        for field,value in (("pendingEvents",1),("conflicts",["event"]),("poison",[{"coordinate":"topic:0:1","code":"INVALID_EVENT"}])):
            source,inspection=self.fixtures()
            (inspection["snapshot"] if field=="pendingEvents" else inspection["scan"])[field]=value
            with self.subTest(field=field):self.assertFalse(projection.compare_snapshot(source,inspection)["ok"])

    def test_replayed_poison_requires_matching_audit_and_published_delivery(self):
        source,inspection=self.fixtures()
        inspection["scan"]["poison"]=[{"coordinate":"topic:0:1","code":"INVALID_EVENT","rawHash":"poison-hash"}]
        audit={"operation_id":"operation","source_coordinate":"topic:0:1","event_id":source["events"][0]["eventId"],"replay_payload_hash":digest(source["events"][0]),"original_payload_hash":"poison-hash"}
        inspection["snapshot"]["audit"]=[audit]
        self.assertFalse(projection.compare_snapshot(source,inspection)["ok"])
        inspection["snapshot"]["deliveries"]=[{"operation_id":"operation","published_offset":2}]
        self.assertTrue(projection.compare_snapshot(source,inspection)["ok"])
        self.assertFalse(projection.compare_snapshot(source,inspection,expected_audit={"audit":[],"deliveries":[]})["ok"])

    def test_readiness_failure_restores_original_target_and_recreates_old_service(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"target.json"
            old={"database":"order_history","group":"order-history-v1"}
            candidate={"database":"order_history_r_012345abcdef","group":"order-history-r-012345abcdef"}
            path.write_text(json.dumps(old))
            fake=SimpleNamespace(history_target=lambda **kwargs:json.loads(path.read_text()),
                history_target_path=lambda **kwargs:path,set_history_target=lambda value,**kwargs:path.write_text(json.dumps(value)),
                compose=Mock(side_effect=[RuntimeError("readiness failed"),None]))
            with self.assertRaisesRegex(RuntimeError,"OLD_TARGET_RESTORED"):projection.activate(fake,candidate)
            self.assertEqual(json.loads(path.read_text()),old)
            self.assertEqual(fake.compose.call_count,2)
            self.assertEqual(fake.compose.call_args_list[0].kwargs["history_override"],candidate)
            self.assertEqual(fake.compose.call_args_list[1].kwargs["history_override"],old)


if __name__=="__main__":unittest.main()
