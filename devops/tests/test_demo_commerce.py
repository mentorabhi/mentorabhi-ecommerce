"""Generated data count, money and replay contract without local services."""
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
import unittest
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('demo_commerce',ROOT/'data/pipelines/demo-commerce/import.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

class DemoCommerceTest(unittest.TestCase):
    def test_state_file_is_atomically_replaced_and_remains_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            path.write_text('{"previous": true}\n')
            with patch.object(demo.os, 'replace', wraps=demo.os.replace) as replace:
                demo.secure_json(path, {'current': True})
            replace.assert_called_once()
            self.assertEqual(demo.json.loads(path.read_text()), {'current': True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_thousand_customers_have_one_to_hundred_items_partitioned_into_small_orders(self):
        skus = [{'id':str(i),'productId':'p','title':'Product','INR':10000,'USD':150} for i in range(100)]
        anchor = datetime(2026,10,24,tzinfo=timezone.utc)
        settings = {'checkout.tax.rate-bps':'1800','checkout.shipping.INR':'9900','checkout.shipping.USD':'199'}
        sources = set()
        totals = []
        for number in range(1,1001):
            args = (20261024,number,'subject',{'country':'IN'},skus,anchor,settings)
            orders = list(demo.orders_for(*args))
            self.assertEqual(orders,list(demo.orders_for(*args)))
            count = 0
            for order in orders:
                self.assertNotIn(order['sourceRef'],sources)
                sources.add(order['sourceRef'])
                self.assertGreaterEqual(len(order['lines']),1)
                self.assertLessEqual(len(order['lines']),5)
                self.assertEqual(len(order['lines']),len({s['skuId'] for s in order['lines']}))
                self.assertEqual(order['totalMinor'],order['subtotalMinor']+order['taxMinor']+order['shippingMinor'])
                self.assertTrue(all(line['quantity']==1 and line['currency']==order['currency'] for line in order['lines']))
                at = datetime.fromisoformat(order['occurredAt'])
                self.assertGreater((anchor-at).total_seconds(),0)
                self.assertLessEqual((anchor-at).days,364)
                count += len(order['lines'])
            self.assertGreaterEqual(count,1)
            self.assertLessEqual(count,100)
            totals.append(count)
        self.assertIn(1,totals)
        self.assertIn(100,totals)
        self.assertEqual(len(demo.MODELS)*10,100)

if __name__ == '__main__': unittest.main()

class PublicEventContractTest(unittest.TestCase):
    def test_real_envelope_accepts_money_and_rejects_unknown_contact_data(self):
        import sys, copy, json
        sys.path.insert(0,str(ROOT/'contracts'))
        from order_events import parse_event
        envelope = {'eventId':'00000000-0000-4000-8000-000000000001','aggregateId':'00000000-0000-4000-8000-000000000002',
            'aggregateType':'Order','aggregateSequence':1,'eventVersion':1,'eventType':'OrderConfirmed','occurredAt':'2026-10-24T10:00:00Z','customerKey':'a'*64,
            'data':{'orderId':'00000000-0000-4000-8000-000000000002','state':'CONFIRMED'}}
        self.assertEqual(parse_event(json.dumps(envelope)),envelope)
        nanos = copy.deepcopy(envelope); nanos['occurredAt']='2026-10-24T10:00:00.123456789+00:00'
        self.assertEqual(parse_event(json.dumps(nanos)),nanos)
        nanos_z = copy.deepcopy(envelope); nanos_z['occurredAt']='2026-10-24T10:00:00.123456789Z'
        self.assertEqual(parse_event(json.dumps(nanos_z)),nanos_z)
        bad = copy.deepcopy(envelope); bad['data']['email']='synthetic@example.invalid'
        with self.assertRaises(ValueError): parse_event(json.dumps(bad))
        for raw in [None,'null','{}','[]','not-json']:
            with self.assertRaises(ValueError): parse_event(raw)
