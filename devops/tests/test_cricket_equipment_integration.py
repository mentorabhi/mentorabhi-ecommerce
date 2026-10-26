"""Opt-in owner-API and photo/replay acceptance for the M13 Cricket expansion."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
import uuid
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'data/pipelines/real-catalog'))
from equipment_coverage import audit
from import_catalog import OwnerApi,reconcile_model


@unittest.skipUnless(os.getenv('SUPERSPORTS_CRICKET_EQUIPMENT')=='1','Enable after M13 source import and frontend deployment')
class CricketEquipmentIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api=OwnerApi()
        cls.manifest=json.loads((ROOT/'data/pipelines/real-catalog/manifest.json').read_text())
        cls.registry=json.loads((ROOT/'data/pipelines/real-catalog/cricket-equipment-coverage.json').read_text())
        cls.new_keys={m['sourceKey'] for m in json.loads((ROOT/'data/pipelines/real-catalog/cricket-equipment-sources.json').read_text())}
        cls.models=[m for m in cls.manifest['products'] if m['sourceKey'] in cls.new_keys]
        cls.products={p['slug']:p for p in cls.api('catalog','admin/products')}
    def test_all_requested_families_are_active_with_real_photos_prices_stock_and_demo_reviews(self):
        report=audit(self.manifest,self.registry,require_complete=True)
        self.assertEqual(54,report['coveredFamilies'])
        prices={(p['skuId'],p['currency']):p['amountMinor'] for p in self.api('pricing','prices')}
        stock={b['skuId']:b['onHand'] for b in self.api('inventory','balances')}
        for model in self.models:
            with self.subTest(model=model['title']):
                product=self.products[model['slug']]
                self.assertEqual('active',product['status'])
                self.assertEqual(model['equipmentType'],product['details']['equipmentType'])
                self.assertEqual(model['source']['url'],product['details']['provenance']['sourceUrl'])
                actual={s['code']:s for s in product['skus']}
                self.assertEqual({v['code'] for v in model['variants']},set(actual))
                for option in model['variants']:
                    sku=actual[option['code']]
                    self.assertEqual(option['attributes'],sku['attributes'])
                    self.assertGreaterEqual(stock[sku['id']],0)
                    for currency in ('INR','USD'):self.assertEqual(option['prices'][currency],prices[sku['id'],currency])
                reviews=self.api('reviews',f"reviews/products/{product['id']}")
                demo=[r for r in reviews if r['origin']=='DEMO']
                self.assertEqual(model['reviewsPerProduct'],len(demo))
                self.assertTrue(all(3<=r['rating']<=5 and not r['verifiedDelivered'] for r in demo))
        def photo(model):
            observed={}
            for port in (3000,3002):
                with urlopen(f'http://localhost:{port}/'+model['image']['assetKey'],timeout=15) as r:
                    observed[port]=(r.status,hashlib.sha256(r.read()).hexdigest())
            return observed
        with ThreadPoolExecutor(max_workers=3) as pool:
            for model,result in zip(self.models,pool.map(photo,self.models)):
                self.assertEqual({port:(200,model['image']['sha256']) for port in (3000,3002)},result,model['title'])
    def test_new_equipment_uses_exact_owner_facts_and_integer_money_in_checkout_quotes(self):
        import manage
        worker=manage.checkout_worker_token()
        currency=self.api('pricing','currency')['code']
        for kind in ('roller','padded-inners','batting-tee','bat-care-kit'):
            model=next(m for m in self.models if m['equipmentType']==kind)
            product=self.products[model['slug']];sku=product['skus'][0]
            status,fact=manage.request_json('http://localhost:8081/api/v1/internal/checkout/catalog/skus/'+sku['id'],token=worker)
            self.assertEqual(200,status)
            payload={'requestId':str(uuid.uuid4()),'customerSubject':'m13-equipment-quote-fixture','couponCode':None,
                     'lines':[{'skuId':sku['id'],'quantity':2,'productId':fact['productId'],'productTitle':fact['title'],
                               'categoryId':fact['categoryId'],'categorySlug':fact['categorySlug'],'skuRevision':fact['skuRevision'],
                               'productRevision':fact['productRevision'],'categoryRevision':fact['categoryRevision']}]}
            status,quote=manage.request_json('http://localhost:8083/api/v1/internal/checkout/pricing/quotes',token=worker,method='POST',data=json.dumps(payload).encode())
            self.assertEqual(200,status)
            self.assertEqual(currency,quote['snapshot']['currency'])
            self.assertEqual(model['variants'][0]['prices'][currency]*2,quote['snapshot']['subtotalMinor'])
            self.assertEqual(0,quote['snapshot']['discountMinor'])

    def test_replay_preserves_stock_prices_and_existing_coupon_rules(self):
        def snapshot():
            return {'balances':sorted(self.api('inventory','balances'),key=lambda row:row['skuId']),
                    'prices':sorted(self.api('pricing','prices'),key=lambda row:(row['skuId'],row['currency'])),
                    'coupons':sorted(self.api('pricing','coupons'),key=lambda row:row['code'])}
        before=snapshot()
        category=next(c['id'] for c in self.api('catalog','categories') if c['slug']=='cricket-equipment')
        for model in self.models:
            self.assertEqual(self.products[model['slug']]['id'],reconcile_model(self.api,model,category))
        self.assertEqual(before,snapshot(),'Replay must not replenish stock, revise prices or change existing coupon allowlists')
