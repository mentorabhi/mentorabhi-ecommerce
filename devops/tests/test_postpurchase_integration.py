"""Real owner-API cancellation, verified review and support acceptance."""
import json
import os
from pathlib import Path
import sys
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import manage

@unittest.skipUnless(os.getenv('SUPERSPORTS_POSTPURCHASE_LIVE')=='true','Explicit post-purchase acceptance pass')
class PostPurchaseIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.credentials=manage.load_credentials(manage.ROOT/'devops/.local/bootstrap.env')
        cls.customer=manage.customer_token_for('checkout-test-customer',cls.credentials['DEMO_CUSTOMER_PASSWORD'])
        cls.other=manage.customer_token_for('checkout-test-customer-b',cls.credentials['DEMO_CUSTOMER_PASSWORD'])
        cls.admin=manage.token_for('admin',manage.configure_admin_login())
        cls.worker=manage.checkout_worker_token()

    def call(self,port,path,token=None,method='GET',body=None,key=None):
        return manage.request_json(f'http://127.0.0.1:{port}/api/v1/'+path,token=token,method=method,
            data=json.dumps(body).encode() if body is not None else None,headers={'Idempotency-Key':key} if key else None)

    def wait(self,read,predicate,seconds=90):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            status,result=read()
            if status==200 and predicate(result): return result
            time.sleep(.5)
        self.fail(f'Expected state not reached; last status={status}, result={result}')

    def order(self):
        status,products=self.call(8081,'catalog/products?q=football')
        self.assertEqual(status,200)
        product=next(p for p in products if p['slug']=='ss-control-football')
        sku=product['skus'][0]['id']
        status,_=self.call(8084,'inventory/adjustments',self.admin,'POST',{'skuId':sku,'delta':5,'reason':'Post-purchase acceptance capacity','idempotencyKey':'postpurchase-'+uuid.uuid4().hex})
        self.assertEqual(status,200)
        _,profile=self.call(8085,'customer/profile',self.customer)
        self.assertEqual(self.call(8085,'customer/profile',self.customer,'PUT',{'fullName':'Synthetic Acceptance','phone':'9000000001','line1':'12 Demo Road','line2':'','city':'Pune','state':'Maharashtra','postalCode':'411001','country':'IN','expectedRevision':profile['revision']})[0],200)
        status,accepted=self.call(8086,'orders/checkout',self.customer,'POST',{'lines':[{'skuId':sku,'quantity':1}],'couponCode':None},'postpurchase-'+uuid.uuid4().hex)
        self.assertEqual(status,202,accepted)
        order_id=accepted['orderId']
        self.wait(lambda:self.call(8086,'orders/'+order_id,self.customer),lambda o:o['state']=='FULFILLMENT_SCHEDULED')
        return order_id,product['id'],sku

    def transition(self,order_id,target):
        _,tracking=self.call(8086,f'orders/{order_id}/tracking',self.customer)
        return self.call(8088,f'operator/shipments/{order_id}/transitions',self.admin,'POST',{
            'expectedRevision':tracking['tracking']['revision'],'operationId':str(uuid.uuid4()),'targetState':target,'reason':'Synthetic post-purchase acceptance'})

    def test_verified_review_moderation_support_ownership_and_restart(self):
        order_id,product,sku=self.order()
        for state in ['HANDED_OFF','IN_TRANSIT','DELIVERED']:
            status,value=self.transition(order_id,state)
            self.assertEqual(status,200,value)
        self.call(8086,f'orders/{order_id}/tracking',self.customer)
        review={'orderId':order_id,'productId':product,'skuId':sku,'rating':5,'title':'Club practice feedback','body':'Synthetic review: balanced feel in local practice.'}
        self.assertEqual(self.call(8092,'customer/reviews',self.other,'POST',review)[0],404)
        self.assertEqual(self.call(8092,'customer/reviews',self.customer,'POST',{**review,'productId':str(uuid.uuid4())})[0],422)
        status,submitted=self.call(8092,'customer/reviews',self.customer,'POST',review)
        self.assertEqual(status,201,submitted)
        review_id=submitted['reviewId']
        _,public=self.call(8092,'reviews/products/'+product)
        self.assertNotIn(review_id,[r['reviewId'] for r in public])
        body={'state':'PUBLISHED','reason':'Synthetic acceptance moderation','operationId':str(uuid.uuid4())}
        path=f'operator/reviews/{review_id}/moderation'
        self.assertEqual(self.call(8092,path,self.admin,'POST',body)[0],200)
        self.assertTrue(self.call(8092,path,self.admin,'POST',body)[1]['replayed'])
        self.assertEqual(self.call(8092,path,self.admin,'POST',{**body,'state':'HIDDEN'})[0],409)
        _,public=self.call(8092,'reviews/products/'+product)
        self.assertIn(review_id,[r['reviewId'] for r in public])
        ticket={'orderId':order_id,'subject':'Synthetic delivery question','message':'Please confirm the simulated delivery.','operationId':str(uuid.uuid4())}
        self.assertEqual(self.call(8093,'customer/support/tickets',self.other,'POST',ticket)[0],404)
        status,created=self.call(8093,'customer/support/tickets',self.customer,'POST',ticket)
        self.assertEqual(status,200,created)
        ticket_id=created['ticketId']
        self.assertEqual(self.call(8093,'customer/support/tickets',self.customer,'POST',ticket)[1]['ticketId'],ticket_id)
        self.assertEqual(self.call(8093,'customer/support/tickets/'+ticket_id,self.other)[0],404)
        message={'body':'Delivery confirmed in the local simulator.','operationId':str(uuid.uuid4())}
        path=f'operator/support/tickets/{ticket_id}/messages'
        self.assertEqual(self.call(8093,path,self.admin,'POST',message)[0],200)
        self.assertTrue(self.call(8093,path,self.admin,'POST',message)[1]['replayed'])
        self.assertEqual(self.call(8093,path,self.admin,'POST',{**message,'body':'Changed'})[0],409)
        self.assertEqual(self.call(8093,f'operator/support/tickets/{ticket_id}/status',self.admin,'PUT',{'status':'RESOLVED','reason':'Acceptance complete'})[0],200)
        manage.compose(['restart','reviews','support'])
        for port in (8092,8093):
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                try:
                    if manage.request_json(f'http://127.0.0.1:{port}/actuator/health/readiness')[0]==200:break
                except Exception:pass
                time.sleep(1)
            else:self.fail('Service restart did not recover')
        _,detail=self.call(8093,'customer/support/tickets/'+ticket_id,self.customer)
        self.assertEqual(len(detail['messages']),2)
        self.assertEqual(detail['status'],'RESOLVED')
        self.assertEqual(self.call(8093,f'customer/support/tickets/{ticket_id}/messages',self.customer,'POST',{'body':'Synthetic follow-up','operationId':str(uuid.uuid4())})[0],200)
        self.assertEqual(self.call(8093,'customer/support/tickets/'+ticket_id,self.customer)[1]['status'],'OPEN')
        self.assertIn(review_id,[r['reviewId'] for r in self.call(8092,'reviews/products/'+product)[1]])

    def test_cancellation_recovers_payment_outage_and_is_owned_idempotent(self):
        order_id,_,_=self.order()
        path=f'orders/{order_id}/cancellations'
        body={'reasonCode':'CUSTOMER_REQUEST'}; key='cancel-'+uuid.uuid4().hex
        self.assertEqual(self.call(8086,path,self.other,'POST',body,key)[0],404)
        manage.compose(['stop','payment-simulator'])
        try:
            status,accepted=self.call(8086,path,self.customer,'POST',body,key)
            self.assertEqual(status,202,accepted)
            self.assertEqual(self.call(8086,path,self.customer,'POST',body,key)[1]['operationId'],accepted['operationId'])
            self.assertEqual(self.call(8086,path,self.customer,'POST',{'reasonCode':'SIMULATED_POLICY'},key)[0],422)
        finally:
            manage.compose(['up','-d','--no-deps','--wait','--wait-timeout','120','payment-simulator'])
        self.wait(lambda:self.call(8086,'orders/'+order_id,self.customer),lambda o:o['state']=='CANCELLED')
        self.assertEqual(self.transition(order_id,'HANDED_OFF')[0],409)
        status,ledger=self.call(8087,f'internal/checkout/payments/{order_id}/status',self.worker)
        self.assertEqual(status,200,ledger)
        self.assertEqual(sum(p['state']=='REFUNDED' for p in ledger['operations']),1)

    def test_handoff_and_cancellation_have_one_winner(self):
        order_id,_,_=self.order()
        _,tracking=self.call(8086,f'orders/{order_id}/tracking',self.customer)
        def handoff():
            return self.call(8088,f'operator/shipments/{order_id}/transitions',self.admin,'POST',{'expectedRevision':tracking['tracking']['revision'],'operationId':str(uuid.uuid4()),'targetState':'HANDED_OFF','reason':'Concurrent handoff acceptance'})
        def cancel():
            return self.call(8086,f'orders/{order_id}/cancellations',self.customer,'POST',{'reasonCode':'CUSTOMER_REQUEST'},'cancel-race-'+uuid.uuid4().hex)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(handoff); b=pool.submit(cancel); handed,cancelled=a.result(),b.result()
        self.assertIn((handed[0],cancelled[0]),[(200,409),(409,202)],(handed,cancelled))
        if cancelled[0]==202:
            self.wait(lambda:self.call(8086,'orders/'+order_id,self.customer),lambda o:o['state']=='CANCELLED')
        else:
            self.assertEqual(self.call(8086,f'orders/{order_id}/cancellation-eligibility',self.customer)[1]['eligible'],False)

if __name__=='__main__':unittest.main(verbosity=2)
