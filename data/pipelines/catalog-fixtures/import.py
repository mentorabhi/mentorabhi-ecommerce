"""Idempotently load synthetic SuperSports catalog fixtures through public APIs."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import manage

CATALOG = "http://127.0.0.1:8081/api/v1/catalog"
PRICING = "http://127.0.0.1:8083/api/v1/pricing"
INVENTORY = "http://127.0.0.1:8084/api/v1/inventory"


def call(url, token, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read()) if response.status != 204 else None
    except HTTPError as error:
        with error:
            detail = error.read().decode(errors="replace")
            raise RuntimeError(f"Local API returned HTTP {error.code} for {method} {url}: {detail[:500]}") from None


def main():
    credentials = manage.load_credentials(ROOT / "devops/.local/bootstrap.env")
    catalog_token = manage.token_for("catalog-admin", credentials["DEMO_CATALOG_ADMIN_PASSWORD"])
    inventory_token = manage.token_for("inventory-operator", credentials["DEMO_INVENTORY_OPERATOR_PASSWORD"])
    manifest = json.loads((Path(__file__).parent / "manifest.json").read_text())
    sports = {x["slug"]: x["id"] for x in call(f"{CATALOG}/sports", catalog_token)}
    categories = {x["slug"]: x["id"] for x in call(f"{CATALOG}/categories", catalog_token)}
    for sport in manifest["sports"]:
        sport_id = sports.get(sport["slug"])
        if not sport_id:
            sport_id = call(f"{CATALOG}/sports", catalog_token, "POST", sport)["id"]
        category = sport["category"]
        if category["slug"] not in categories:
            categories[category["slug"]] = call(f"{CATALOG}/categories", catalog_token, "POST", {
                "sportId": sport_id, **category})["id"]
    products = {p["slug"]: p for p in call(f"{CATALOG}/admin/products", catalog_token)}
    prices = {(str(p["skuId"]), p["currency"]): (int(p["amountMinor"]), int(p["revision"]))
              for p in call(f"{PRICING}/prices", catalog_token)}
    coupon_codes = {c["code"] for c in call(f"{PRICING}/coupons", catalog_token)}
    for fixture in manifest["products"]:
        category_slug = next(x["category"]["slug"] for x in manifest["sports"] if x["slug"] == fixture["sport"])
        product = products.get(fixture["slug"])
        if product is None:
            product_id = call(f"{CATALOG}/products", catalog_token, "POST", {
                "categoryId": categories[category_slug], "slug": fixture["slug"],
                "brand": fixture["brand"], "title": fixture["title"],
                "description": fixture["description"]})["id"]
            sku = call(f"{CATALOG}/products/{product_id}/skus", catalog_token, "POST", {
                "code": fixture["code"], "attributes": {}, "assetKey": fixture["asset"],
                "altText": fixture["alt"]})
            product = {"id": product_id, "revision": 1, "status": "draft", "skus": [{**sku, "code": fixture["code"]}]}
        elif not product["skus"]:
            sku = call(f"{CATALOG}/products/{product['id']}/skus", catalog_token, "POST", {
                "code": fixture["code"], "attributes": {}, "assetKey": fixture["asset"],
                "altText": fixture["alt"]})
            product["skus"] = [{**sku, "code": fixture["code"]}]
        sku = next((s for s in product["skus"] if s["code"] == fixture["code"]), None)
        if sku is None:
            raise RuntimeError(f"Fixture SKU {fixture['code']} is missing from its product")
        sku_id = str(sku["id"])
        for currency, amount in (("INR", fixture["inr"]), ("USD", fixture["usd"])):
            existing = prices.get((sku_id, currency))
            if existing is None or existing[0] != amount:
                call(f"{PRICING}/prices/{sku_id}/{currency}", catalog_token, "PUT", {"amountMinor": amount, "expectedRevision": existing[1] if existing else 0})
        if product["status"] == "draft":
            call(f"{CATALOG}/products/{product['id']}/activate", catalog_token, "POST", {"expectedRevision": product["revision"]})
        call(f"{INVENTORY}/adjustments", inventory_token, "POST", {
            "skuId": sku_id, "delta": fixture["stock"],
            "reason": "Initial synthetic fixture stock", "idempotencyKey": f"catalog-fixture-v{manifest['version']}-{fixture['code']}"})
    for coupon in manifest["coupons"]:
        if coupon["code"] not in coupon_codes:
            call(f"{PRICING}/coupons", catalog_token, "POST", coupon)
    print(f"Imported {len(manifest['products'])} synthetic products, {len(manifest['coupons'])} coupons; repeated imports preserve initial stock movements.")


if __name__ == "__main__":
    main()
