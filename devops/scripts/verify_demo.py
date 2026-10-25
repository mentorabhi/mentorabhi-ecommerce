"""Read-only owner/admin acceptance of the generated commerce dataset."""
import argparse
import json
import uuid
import manage


def sql(database,query):
    result=manage.compose(['exec','-T','postgres','psql','-X','-U','postgres','-d',database,'-tA','-v','ON_ERROR_STOP=1','-c',query],capture=True)
    return json.loads(result.stdout.strip())


def verify(seed):
    state=json.loads((manage.ROOT/f'devops/.local/demo-commerce-{seed}.json').read_text())
    report=json.loads((manage.ROOT/f'devops/.local/demo-commerce-{seed}-report.json').read_text())
    subjects=[str(uuid.UUID(c['subject'])) for c in state['customers'].values()]
    subject_array='ARRAY['+','.join("'"+value+"'" for value in subjects)+']::text[]'
    catalog=sql('catalog',"SELECT json_build_object('products',count(DISTINCT p.id),'skus',count(s.id)) FROM products p JOIN skus s ON s.product_id=p.id WHERE p.slug LIKE 'demo-%' AND p.status='active' AND s.active")
    assert catalog=={'products':10,'skus':100},catalog
    customers=sql('customer',f"SELECT json_build_object('profiles',count(*),'indianProfiles',count(*) FILTER(WHERE country='IN' AND postal_code ~ '^[0-9]{{6}}$')) FROM customer_profile WHERE subject=ANY({subject_array})")
    assert customers=={'profiles':report['customers'],'indianProfiles':report['customers']},customers
    identities=sql('identity',f"SELECT json_build_object('identities',count(*),'invalidDomain',count(*) FILTER(WHERE email LIKE '%@supersports.invalid')) FROM user_entity WHERE username LIKE 'ss-demo-{seed}-%'")
    assert identities=={'identities':report['customers'],'invalidDomain':report['customers']},identities
    prefix=f"demo-{seed}-%"
    facts=sql('orders',f"""WITH seeded AS (SELECT o.* FROM customer_order o JOIN synthetic_order_source s ON s.order_id=o.id WHERE s.source_ref LIKE '{prefix}'),
    by_customer AS (SELECT customer_subject,sum(l.quantity) AS items FROM seeded o JOIN customer_order_line l ON l.order_id=o.id GROUP BY customer_subject),
    by_order AS (SELECT o.id,count(*) AS lines,sum(l.quantity) AS items FROM seeded o JOIN customer_order_line l ON l.order_id=o.id GROUP BY o.id)
    SELECT json_build_object('orders',(SELECT count(*) FROM seeded),'owners',(SELECT count(*) FROM by_customer),
    'items',(SELECT sum(items) FROM by_customer),'minItemsPerCustomer',(SELECT min(items) FROM by_customer),
    'maxItemsPerCustomer',(SELECT max(items) FROM by_customer),'minLinesPerOrder',(SELECT min(lines) FROM by_order),'maxLinesPerOrder',(SELECT max(lines) FROM by_order),
    'outsidePriorYear',(SELECT count(*) FROM seeded WHERE created_at < now()-interval '365 days' OR created_at>now()),
    'events',(SELECT count(*) FROM order_outbox b JOIN seeded o ON b.aggregate_id=o.id),
    'totals',(SELECT json_object_agg(currency,total) FROM (SELECT currency,sum(total_minor) AS total FROM seeded GROUP BY currency) t))""")
    assert facts['orders']==report['orders'] and facts['owners']==report['customers'] and facts['items']==report['items'],facts
    assert 1<=facts['minItemsPerCustomer']<=facts['maxItemsPerCustomer']<=100,facts
    assert 1<=facts['minLinesPerOrder']<=facts['maxLinesPerOrder']<=5,facts
    assert facts['events']==2*report['orders'] and facts['outsidePriorYear']==0,facts
    assert facts['totals']==report['totalMinorByCurrency'],facts
    sku_array='ARRAY['+','.join("'"+str(uuid.UUID(s['id']))+"'::uuid" for s in state['skus'])+']'
    inventory=sql('inventory',f"SELECT json_build_object('balances',count(*),'negative',count(*) FILTER(WHERE on_hand<0),'minOnHand',min(on_hand),'maxOnHand',max(on_hand)) FROM inventory_balance WHERE sku_id=ANY({sku_array})")
    assert inventory['balances']==100 and inventory['negative']==0,inventory
    sample=state['customers']['1']; other=state['customers']['2']
    token=manage.customer_token_for(sample['username'],sample['password'])
    other_token=manage.customer_token_for(other['username'],other['password'])
    status,orders=manage.request_json('http://127.0.0.1:8086/api/v1/orders',token=token)
    assert status==200 and orders
    order_id=orders[0]['id']
    assert manage.request_json('http://127.0.0.1:8086/api/v1/orders/'+order_id,token=other_token)[0]==404
    result={'catalog':catalog,'customers':customers,'identities':identities,'orders':facts,'inventory':inventory,'sampleOwnerIsolation':True}
    print(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--seed',type=int,default=20261024)
    verify(parser.parse_args().seed)
