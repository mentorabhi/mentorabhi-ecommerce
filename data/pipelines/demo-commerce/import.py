"""Reproducible local commerce dataset. All writes use owner APIs."""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import secrets
import tempfile
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'devops/scripts'))
import manage
spec = importlib.util.spec_from_file_location('catalog_import', ROOT / 'data/pipelines/catalog-fixtures/import.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
def call(url, token, method='GET', body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {'Authorization':'Bearer '+token,'Accept':'application/json'}
    if data is not None: headers['Content-Type'] = 'application/json'
    try:
        with urlopen(Request(url,data=data,headers=headers,method=method),timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except HTTPError as error:
        with error:
            raise RuntimeError(f'HTTP {error.code} {method} {url}: {error.read().decode()[:300]}') from None
MODELS = [
 ('cricket', 'bat', 'Tournament Willow Cricket Bat', 649900, 7999, ['Short handle','Long handle','Harrow','Size 6','Size 5'], 'Selected willow blade with a balanced pickup and cushioned handle for club training and weekend matches.'),
 ('cricket', 'ball', 'Club Leather Cricket Ball', 79900, 999, ['156 g','142 g','135 g','120 g','110 g'], 'Hand stitched four piece leather ball with a cork core and prominent seam for practice on turf wickets.'),
 ('cricket', 'gloves', 'Elite Batting Gloves', 229900, 2899, ['Youth S','Youth M','Adult S','Adult M','Adult L'], 'Flexible finger rolls, ventilated palms and padded knuckles for comfortable batting practice.'),
 ('cricket', 'pads', 'Club Batting Pads', 299900, 3699, ['Youth S','Youth M','Adult S','Adult M','Adult L'], 'Lightweight batting leg guards with broad straps, contoured knee protection and breathable lining.'),
 ('cricket', 'helmet', 'Match Cricket Helmet', 249900, 3099, ['XS','S','M','L','XL'], 'Adjustable practice helmet with a steel face grille and ventilated shell. Synthetic demonstration product.'),
 ('cricket', 'kit-bag', 'Club Cricket Kit Bag', 349900, 4399, ['35 L','45 L','55 L','65 L','75 L'], 'Durable cricket equipment bag with bat sleeves, reinforced carry handles and a separate footwear pocket.'),
 ('football', 'ball', 'Precision Match Football', 189900, 2399, ['Size 1','Size 2','Size 3','Size 4','Size 5'], 'Textured panel football with a resilient bladder for passing drills and club matches on grass.'),
 ('football', 'boots', 'Velocity Football Boots', 399900, 4999, ['UK 6','UK 7','UK 8','UK 9','UK 10'], 'Lightweight football boots with a textured upper, cushioned heel and firm ground stud pattern.'),
 ('football', 'keeper-gloves', 'Control Goalkeeper Gloves', 199900, 2499, ['Size 6','Size 7','Size 8','Size 9','Size 10'], 'Latex palm goalkeeper gloves with wrist support and flexible fingers for training and match days.'),
 ('football', 'shin-guards', 'Flex Football Shin Guards', 89900, 1199, ['XS','S','M','L','XL'], 'Contoured shin guards with an impact distributing shell, soft backing and breathable sleeve.'),
]
FIRST = ['Aarav','Vivaan','Aditya','Arjun','Ishaan','Rohan','Kabir','Rahul','Vikram','Kunal','Ananya','Diya','Isha','Meera','Kavya','Aditi','Riya','Sneha','Nisha','Pooja']
LAST = ['Sharma','Patel','Singh','Verma','Gupta','Rao','Nair','Reddy','Iyer','Mehta','Das','Bose','Joshi','Shah','Kumar','Kulkarni','Pillai','Saxena','Kapoor','Bhat']
CITIES = [('Mumbai','Maharashtra','400001'),('Pune','Maharashtra','411001'),('Bengaluru','Karnataka','560001'),('Delhi','Delhi','110001'),('Chennai','Tamil Nadu','600001'),('Hyderabad','Telangana','500001'),('Kolkata','West Bengal','700001'),('Jaipur','Rajasthan','302001'),('Ahmedabad','Gujarat','380001'),('Kochi','Kerala','682001')]


def secure_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(value, output, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Admin:
    def __init__(self, password):
        self.password = password
        self.token = None
        self.expires = 0
        self.lock = threading.Lock()

    def call(self, path, method='GET', body=None):
        with self.lock:
            if time.monotonic() >= self.expires:
                data = urlencode({'grant_type':'password','client_id':'admin-cli','username':'bootstrap-admin','password':self.password}).encode()
                with urlopen(Request('http://127.0.0.1:8180/realms/master/protocol/openid-connect/token', data=data), timeout=30) as response:
                    self.token = json.load(response)['access_token']
                self.expires = time.monotonic() + 40
            token = self.token
        return call('http://127.0.0.1:8180/admin/realms/supersports-customers' + path, token, method, body)

    def user(self, username, password, first, last):
        users = self.call('/users?' + urlencode({'username':username,'exact':'true'}))
        if not users:
            self.call('/users', 'POST', {'username':username,'enabled':True,'emailVerified':True,
                'email':username+'@supersports.invalid','firstName':first,'lastName':last,
                'credentials':[{'type':'password','value':password,'temporary':False}]})
            users = self.call('/users?' + urlencode({'username':username,'exact':'true'}))
        if len(users) != 1 or users[0]['email'] != username+'@supersports.invalid':
            raise RuntimeError('Reserved dataset identity conflicts with an existing user')
        return users[0]['id']


def profile_for(seed, number):
    rng = random.Random(f'{seed}:profile:{number}')
    first, last = rng.choice(FIRST), rng.choice(LAST)
    city, state, pin = rng.choice(CITIES)
    return first, last, {'fullName':first+' '+last,'phone':f'9{number:09d}',
        'line1':f'{rng.randint(1,499)}, Demo Sports Residency','line2':'Synthetic demonstration address',
        'city':city,'state':state,'postalCode':pin,'country':'IN'}


def orders_for(seed, number, subject, address, skus, anchor, settings, max_items=100):
    rng = random.Random(f'{seed}:orders:{number}')
    remaining = rng.randint(1, max_items)
    order_number = 0
    while remaining:
        count = min(remaining, rng.randint(1,5))
        remaining -= count
        order_number += 1
        currency = 'USD' if rng.random() < .1 else 'INR'
        selected = rng.sample(skus, count)
        lines = [{'skuId':s['id'],'productId':s['productId'],'productTitle':s['title'],'quantity':1,
                  'unitPriceMinor':s[currency],'discountMinor':0,'lineTotalMinor':s[currency],'currency':currency} for s in selected]
        subtotal = sum(x['lineTotalMinor'] for x in lines)
        tax = (subtotal * int(settings['checkout.tax.rate-bps']) + 5000) // 10000
        shipping = int(settings['checkout.shipping.' + currency])
        at = anchor - timedelta(seconds=rng.randint(300, 364*86400))
        yield {'sourceRef':f'demo-{seed}-u{number:04d}-o{order_number:03d}','customerSubject':subject,
            'occurredAt':at.isoformat().replace('+00:00','Z'),'currency':currency,'subtotalMinor':subtotal,
            'discountMinor':0,'taxMinor':tax,'shippingMinor':shipping,'totalMinor':subtotal+tax+shipping,
            'addressSnapshot':address,'lines':lines}


def catalog(token):
    categories = {c['slug']:c['id'] for c in call(fixture.CATALOG+'/categories', token)}
    products = {p['slug']:p for p in call(fixture.CATALOG+'/admin/products', token)}
    prices = {(p['skuId'],p['currency']):p for p in call(fixture.PRICING+'/prices', token)}
    result = []
    for sport, model, title, inr, usd, sizes, description in MODELS:
        slug = 'demo-'+sport+'-'+model
        product = products.get(slug)
        if not product:
            product = call(fixture.CATALOG+'/products',token,'POST',{'categoryId':categories[sport+'-equipment'],
                'slug':slug,'brand':'SuperSports','title':title,'description':description})
            product = {'id':product['id'],'skus':[],'status':'draft','revision':1}
        known = {s['code']:s for s in product['skus']}
        for index in range(10):
            code = f'DEMO-{sport[:2].upper()}-{model.upper()}-{index+1:02d}'
            sku = known.get(code)
            if not sku:
                sku = call(fixture.CATALOG+f"/products/{product['id']}/skus",token,'POST',{
                    'code':code,'attributes':{'size':sizes[index//2],'edition':['Club','Pro'][index%2]},
                    'assetKey':f'products/synthetic/{sport}-{model}.jpg','altText':title+' product photograph'})
            row = {'id':sku['id'],'code':code,'productId':product['id'],'title':title}
            for currency, amount in [('INR',inr+index*5000),('USD',usd+index*60)]:
                old = prices.get((sku['id'],currency))
                if not old or old['amountMinor'] != amount:
                    call(fixture.PRICING+f"/prices/{sku['id']}/{currency}",token,'PUT',{'amountMinor':amount,'expectedRevision':old['revision'] if old else 0})
                row[currency] = amount
            result.append(row)
        if product['status'] == 'draft':
            call(fixture.CATALOG+f"/products/{product['id']}/activate",token,'POST',{'expectedRevision':product['revision']})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--users',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=20261024)
    parser.add_argument('--max-items',type=int,default=100)
    args = parser.parse_args()
    if not 1 <= args.users <= 1000 or not 1 <= args.max_items <= 100:
        parser.error('users must be 1..1000 and max-items must be 1..100')
    started = time.monotonic()
    credentials = manage.load_credentials(ROOT/'devops/.local/bootstrap.env')
    state_path = ROOT/f'devops/.local/demo-commerce-{args.seed}.json'
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state['maxItems'] != args.max_items:
            parser.error('Use a new --seed when changing max-items')
    else:
        token = manage.token_for('platform-admin',credentials['DEMO_PLATFORM_ADMIN_PASSWORD'])
        config = call('http://127.0.0.1:8082/api/v1/configuration',token)
        state = {'seed':args.seed,'maxItems':args.max_items,'anchor':datetime.now(timezone.utc).isoformat(),
                 'settings':{s['key']:s['value'] for s in config['settings']},
                 'seederPassword':secrets.token_urlsafe(24),'customers':{}}
    for number in range(1,args.users+1):
        state['customers'].setdefault(str(number),{'username':f'ss-demo-{args.seed}-{number:04d}','password':secrets.token_urlsafe(20)})
    secure_json(state_path,state)
    admin = Admin(credentials['KEYCLOAK_ADMIN_PASSWORD'])
    seeder_id = admin.user('supersports-demo-seeder',state['seederPassword'],'Synthetic','Seeder')
    admin.call(f'/users/{seeder_id}/reset-password','PUT',{'type':'password','value':state['seederPassword'],'temporary':False})
    try:
        role = admin.call('/roles/supersports-synthetic-seeder')
    except RuntimeError as error:
        if 'HTTP 404' not in str(error): raise
        admin.call('/roles','POST',{'name':'supersports-synthetic-seeder','description':'Explicit local dataset importer'})
        role = admin.call('/roles/supersports-synthetic-seeder')
    admin.call(f'/users/{seeder_id}/role-mappings/realm','POST',[role])
    token = manage.token_for('catalog-admin',credentials['DEMO_CATALOG_ADMIN_PASSWORD'])
    skus = catalog(token)
    state['skus'] = skus
    secure_json(state_path,state)
    print(f'Catalog ready: {len(skus)} sellable variants with 10 product photographs.',flush=True)
    def create_profile(number):
        customer = state['customers'][str(number)]
        first,last,address = profile_for(args.seed,number)
        subject = admin.user(customer['username'],customer['password'],first,last)
        token = manage.customer_token_for(customer['username'],customer['password'])
        profile = call('http://127.0.0.1:8085/api/v1/customer/profile',token)
        if any(profile.get(k) != v for k,v in address.items()):
            call('http://127.0.0.1:8085/api/v1/customer/profile',token,'PUT',{**address,'expectedRevision':profile['revision']})
        return number,subject
    with ThreadPoolExecutor(max_workers=4) as executor:
        for completed,(number,subject) in enumerate(executor.map(create_profile,range(1,args.users+1)),1):
            state['customers'][str(number)]['subject'] = subject
            if completed % 50 == 0:
                secure_json(state_path,state)
                print(f'Profiles ready: {completed}/{args.users}',flush=True)
    secure_json(state_path,state)
    anchor = datetime.fromisoformat(state['anchor'])
    def orders():
        for number in range(1,args.users+1):
            yield from orders_for(args.seed,number,state['customers'][str(number)]['subject'],profile_for(args.seed,number)[2],skus,anchor,state['settings'],args.max_items)
    demand = Counter(line['skuId'] for order in orders() for line in order['lines'])
    inventory_token = manage.token_for('inventory-operator',credentials['DEMO_INVENTORY_OPERATOR_PASSWORD'])
    for sku in skus:
        sold = demand[sku['id']]
        buffer = max(50, math.ceil(sold*.1))
        for suffix, delta in [('supply',sold+buffer),('historical-sales',-sold)]:
            if delta:
                call(fixture.INVENTORY+'/adjustments',inventory_token,'POST',{'skuId':sku['id'],'delta':delta,
                    'reason':'Synthetic dataset '+suffix,'idempotencyKey':f'demo-{args.seed}-u{args.users}-{sku["code"]}-{suffix}'})
    total = created = lines = 0
    currency_totals = Counter()
    dates = []
    batch = []
    seeder_token = None
    token_at = 0
    def send(batch):
        nonlocal seeder_token,token_at
        if time.monotonic()-token_at > 40:
            seeder_token = manage.customer_token_for('supersports-demo-seeder',state['seederPassword'])
            token_at = time.monotonic()
        return call('http://127.0.0.1:8086/api/v1/admin/synthetic-orders/batch',seeder_token,'POST',{'orders':batch})
    for order in orders():
        batch.append(order)
        lines += len(order['lines'])
        currency_totals[order['currency']] += order['totalMinor']
        dates.append(order['occurredAt'])
        if len(batch) == 100:
            response = send(batch)
            total += response['accepted']; created += response['created']; batch = []
            if total % 1000 == 0: print(f'Orders imported/replayed: {total}',flush=True)
    if batch:
        response = send(batch); total += response['accepted']; created += response['created']
    report = {'seed':args.seed,'customers':args.users,'products':10,'skus':len(skus),'orders':total,'createdThisRun':created,
        'items':lines,'itemsPerCustomer':'1..'+str(args.max_items),'itemsPerOrder':'1..5',
        'firstOrder':min(dates),'lastOrder':max(dates),'totalMinorByCurrency':dict(currency_totals),
        'elapsedSeconds':round(time.monotonic()-started,2),'credentialsFile':str(state_path.relative_to(ROOT))}
    secure_json(ROOT/f'devops/.local/demo-commerce-{args.seed}-report.json',report)
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
