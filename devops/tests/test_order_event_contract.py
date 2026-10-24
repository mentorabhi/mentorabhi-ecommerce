"""Validate the public order event contract and privacy boundary."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "contracts/orders/order-lifecycle-v1.schema.json"


class OrderEventContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text())
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

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
        for event_type in self.schema["properties"]["eventType"]["enum"]:
            with self.subTest(event_type=event_type):
                self.validator.validate(self.sample(event_type))

    def test_rejects_sensitive_owner_data_and_invalid_sequence(self):
        event = self.sample("OrderAccepted")
        event["data"]["deliveryAddress"] = {"line1": "private"}
        self.assertTrue(list(self.validator.iter_errors(event)))
        event = self.sample("OrderAccepted", sequence=0)
        self.assertTrue(list(self.validator.iter_errors(event)))


if __name__ == "__main__":
    unittest.main()
