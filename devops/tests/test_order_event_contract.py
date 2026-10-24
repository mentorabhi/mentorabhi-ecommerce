"""Validate the public order event contract and privacy boundary."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATHS = {version: ROOT / f"contracts/orders/order-lifecycle-v{version}.schema.json" for version in (1, 2)}


class OrderEventContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas={version:json.loads(path.read_text()) for version,path in SCHEMA_PATHS.items()}
        for schema in cls.schemas.values():Draft202012Validator.check_schema(schema)
        cls.validators={version:Draft202012Validator(schema,format_checker=FormatChecker()) for version,schema in cls.schemas.items()}

    def sample(self, event_type: str, sequence: int = 1) -> dict:
        order_id = "59c0c4f8-8885-4a91-9f13-9b412907280d"
        data = {"orderId": order_id, "state": "PENDING_PAYMENT"}
        if event_type == "OrderAccepted":
            data.update({"checkoutRequestId": "6380b37c-3db8-47f9-93f3-fbe2016769ac", "currency": "INR",
                         "subtotalMinor": 1000, "discountMinor": 0, "taxMinor": 180,
                         "shippingMinor": 0, "totalMinor": 1180,
                         "lines": [{"skuId": "40b79031-2159-4be0-ad13-5d8d04bbb341",
                                    "productId": "31562747-0264-45fc-a822-fe8c01496d0a",
                                    "productTitle": "Training Football", "quantity": 1,
                                    "unitPriceMinor": 1000, "discountMinor": 0,
                                    "lineTotalMinor": 1000, "currency": "INR"}]})
        elif event_type in ("OrderConfirmed", "FulfillmentScheduled"):
            data["state"] = "CONFIRMED" if event_type == "OrderConfirmed" else "FULFILLMENT_SCHEDULED"
        else:
            data.update({"state": "FAILED", "reason": "PAYMENT_DECLINED" if event_type == "OrderPaymentDeclined" else "QUOTE_EXPIRED"})
        return {"eventId": "a669d205-b424-4261-84db-a76d37c68688", "eventType": event_type,
                "eventVersion": 1, "aggregateType": "Order", "aggregateId": order_id,
                "aggregateSequence": sequence, "occurredAt": "2026-10-24T12:00:00Z",
                "customerKey": "a" * 64, "data": data}

    def test_all_producer_event_types_match_v1(self):
        for event_type in self.schemas[1]["properties"]["eventType"]["enum"]:
            with self.subTest(event_type=event_type):
                self.validators[1].validate(self.sample(event_type))

    def test_rejects_sensitive_owner_data_and_invalid_sequence(self):
        event = self.sample("OrderAccepted")
        event["data"]["deliveryAddress"] = {"line1": "private"}
        self.assertTrue(list(self.validators[1].iter_errors(event)))
        event = self.sample("OrderAccepted", sequence=0)
        self.assertTrue(list(self.validators[1].iter_errors(event)))

    def test_v2_post_purchase_events_are_allowlisted_and_private_text_is_rejected(self):
        order_id="59c0c4f8-8885-4a91-9f13-9b412907280d"
        fixtures={
            "OrderCancelled":{"orderId":order_id,"state":"CANCELLED","operationId":"6380b37c-3db8-47f9-93f3-fbe2016769ac","refundMinor":1180,"currency":"INR","reasonCode":"CUSTOMER_REQUEST"},
            "OrderReturnRequested":{"orderId":order_id,"state":"DELIVERED","returnId":"6380b37c-3db8-47f9-93f3-fbe2016769ac","policyRevision":1,"lines":[{"skuId":"40b79031-2159-4be0-ad13-5d8d04bbb341","quantity":1}]},
            "OrderRefundCompleted":{"orderId":order_id,"state":"DELIVERED","refundId":"6380b37c-3db8-47f9-93f3-fbe2016769ac","amountMinor":1180,"currency":"INR","reasonCode":"RETURN"},
            "ShipmentMilestoneRecorded":{"orderId":order_id,"state":"FULFILLMENT_SCHEDULED","shipmentState":"IN_TRANSIT","shipmentRevision":2,"operationId":"6380b37c-3db8-47f9-93f3-fbe2016769ac"}}
        for event_type,data in fixtures.items():
            event={"eventId":"a669d205-b424-4261-84db-a76d37c68688","eventType":event_type,"eventVersion":2,
                "aggregateType":"Order","aggregateId":order_id,"aggregateSequence":4,"occurredAt":"2026-10-24T12:00:00Z","customerKey":"a"*64,"data":data}
            with self.subTest(event_type=event_type):self.validators[2].validate(event)
        event={"eventId":"a669d205-b424-4261-84db-a76d37c68688","eventType":"OrderCancelled","eventVersion":2,
            "aggregateType":"Order","aggregateId":order_id,"aggregateSequence":4,"occurredAt":"2026-10-24T12:00:00Z","customerKey":"a"*64,
            "data":{**fixtures["OrderCancelled"],"reason":"customer text"}}
        self.assertTrue(list(self.validators[2].iter_errors(event)))


if __name__ == "__main__":
    unittest.main()
