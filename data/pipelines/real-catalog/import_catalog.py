"""Reconcile the accepted photographic catalog through owner APIs only."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from datetime import date, timedelta
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import manage
from assets import verify_local
from catalog_data import validate_manifest

PORTS = {"catalog": 8081, "pricing": 8083, "inventory": 8084, "reviews": 8092}
REASON = "S1-M11 sourced catalog simulated initial stock"


def facts(model):
    return {"model": model["model"], "equipmentType": model["equipmentType"],
            "highlights": [f"{model['brand']} model: {model['model']}",
                           "Genuine sourced model photograph; local simulated commerce options"],
            "material": "See the linked source for manufacturer material specifications.",
            "intendedUse": f"{model['sport'].title()} practice and play",
            "fit": "Size, hand, colour and pack ranges are educational simulations; verify manufacturer availability separately.",
            "care": "Follow the manufacturer's instructions for the sourced model.",
            "packageContents": ["Selected simulated SKU option and pack quantity"],
            "provenance": {"sourceUrl": model["source"]["url"], "capturedOn": model["source"]["capturedOn"],
                           "rightsStatement": "Photograph and trademarks belong to their respective owners. Attributed local educational demonstration; no open licence is asserted."},
            "gallery": [{key: model["image"][key] for key in ("assetKey", "altText", "kind")}],
            "commerceProvenance": "Prices, stock, option ranges and DEMO reviews are simulated. INR/USD fixture conversion is 85.00 INR per USD, not a live exchange rate."}


def coupon_fixtures(manifest, completed):
    captured = date.fromisoformat(manifest["capturedOn"])
    coupons = []
    for sport, prefix in (("cricket", "REALCR10"), ("football", "REALFB10")):
        selected = sorted((m for m in manifest["products"] if m["sport"] == sport), key=lambda m: m["sourceKey"])[:10]
        selected_ids = [completed[m["sourceKey"]] for m in selected]
        for currency in ("INR", "USD"):
            coupons.append({"code": prefix if currency == "INR" else prefix + "USD", "active": True,
                "startsAt": captured.isoformat() + "T00:00:00Z",
                "endsAt": (captured + timedelta(days=365)).isoformat() + "T00:00:00Z",
                "currency": currency, "kind": "PERCENT", "value": 1000,
                "minimumSubtotalMinor": 0, "maximumDiscountMinor": 50000 if currency == "INR" else 600,
                "globalLimit": 10000, "perCustomerLimit": 5, "rules": {"productIds": selected_ids}})
    return coupons


class OwnerApi:
    def __init__(self):
        self.token = None
        self.expires = 0

    def __call__(self, service, path, method="GET", data=None):
        if time.monotonic() >= self.expires:
            self.token = manage.token_for("admin", manage.configure_admin_login())
            self.expires = time.monotonic() + 45
        prefix = "" if service == "reviews" else service + "/"
        status, body = manage.request_json(f"http://127.0.0.1:{PORTS[service]}/api/v1/{prefix}{path}",
                                          token=self.token, method=method,
                                          data=None if data is None else json.dumps(data).encode())
        if not 200 <= status < 300:
            # Avoid writing remote exception payloads or tokens into receipts.
            raise RuntimeError(f"{service} {method} {path}: HTTP {status}")
        return body


def reconcile_model(api, model, category_id):
    products = {p["slug"]: p for p in api("catalog", "admin/products")}
    product = products.get(model["slug"])
    base = {key: model[key] for key in ("slug", "brand", "title", "description")}
    if product is None:
        api("catalog", "products", "POST", {**base, "categoryId": category_id})
        product = next(p for p in api("catalog", "admin/products") if p["slug"] == model["slug"])
    if product["status"] == "retired" or product["categoryId"] != category_id:
        raise ValueError("Existing model is retired or has a different category")
    if any(product[k] != v for k, v in base.items()):
        raise ValueError("Existing catalog facts diverge from the accepted manifest")
    existing = {sku["code"]: sku for sku in product["skus"]}
    desired = {v["code"] for v in model["variants"]}
    if set(existing) - desired:
        raise ValueError("Existing product has additional SKU options")
    for variant in model["variants"]:
        target = {"code": variant["code"], "attributes": variant["attributes"],
                  "assetKey": model["image"]["assetKey"], "altText": model["image"]["altText"]}
        sku = existing.get(variant["code"])
        if sku is None:
            if product["status"] != "draft":
                raise ValueError("Missing options on an already active model")
            sku = {**target, **api("catalog", f"products/{product['id']}/skus", "POST", target)}
            existing[variant["code"]] = sku
        elif any(sku[k] != v for k, v in target.items()):
            raise ValueError("Existing SKU differs from accepted identity/options/photo")
    prices = {(p["skuId"], p["currency"]): p for p in api("pricing", "prices")}
    for variant in model["variants"]:
        sku = existing[variant["code"]]
        for currency, amount in variant["prices"].items():
            prior = prices.get((sku["id"], currency))
            if prior is None:
                api("pricing", f"prices/{sku['id']}/{currency}", "PUT",
                    {"amountMinor": amount, "expectedRevision": 0})
            elif prior["amountMinor"] != amount:
                raise ValueError("Existing price diverges; importer will not overwrite operator pricing")
    details = facts(model)
    if product["details"] != details:
        if product["details"]:
            raise ValueError("Existing sourced details diverge from accepted manifest")
        api("catalog", f"products/{product['id']}", "PUT",
            {**{k: model[k] for k in ("brand", "title", "description")}, "details": details,
             "expectedRevision": product["revision"], "idempotencyKey": "real-v1:facts:" + model["sourceKey"]})
        product = next(p for p in api("catalog", "admin/products") if p["id"] == product["id"])
    if product["status"] != "active":
        api("catalog", f"products/{product['id']}/activate", "POST", {"expectedRevision": product["revision"]})
    # Replay always uses the original delta; never replenish consumed inventory.
    for variant in model["variants"]:
        sku = existing[variant["code"]]
        api("inventory", "adjustments", "POST", {"skuId": sku["id"], "delta": variant["stock"],
            "reason": REASON, "idempotencyKey": f"real-v1:{model['sourceKey']}:{variant['key']}"})
    operation = str(uuid5(NAMESPACE_URL, "supersports:real-v1:reviews:" + model["sourceKey"]))
    api("reviews", "operator/reviews/demo-seed", "POST",
        {"operationId": operation, "productIds": [product["id"]], "reviewsPerProduct": model["reviewsPerProduct"]})
    return product["id"]


def import_manifest(api, manifest, receipt, save):
    validate_manifest(manifest)
    for model in manifest["products"]:
        verify_local(model["image"])
    categories = {c["slug"]: c for c in api("catalog", "categories")}
    for sport in ("cricket", "football"):
        if sport + "-equipment" not in categories:
            raise ValueError("Bootstrap the sport root categories before importing")
    for model in manifest["products"]:
        receipt["currentSourceKey"] = model["sourceKey"]
        save(receipt)
        product_id = reconcile_model(api, model, categories[model["sport"] + "-equipment"]["id"])
        receipt["completed"][model["sourceKey"]] = product_id
        save(receipt)
    # Observe replacement state afresh before any retirement.
    observed = api("catalog", "admin/products")
    replacements = set(receipt["completed"].values())
    for model in manifest["products"]:
        product = next(p for p in observed if p["id"] == receipt["completed"][model["sourceKey"]])
        if product["status"] != "active" or len(product["skus"]) != len(model["variants"]):
            raise ValueError("Replacement activation/SKU gate failed; legacy catalog retained")
    balances = {b["skuId"] for b in api("inventory", "balances") if b.get("skuId")}
    if any(s["id"] not in balances for p in observed if p["id"] in replacements for s in p["skus"]):
        raise ValueError("Replacement stock initialization incomplete; legacy catalog retained")
    sku_ids = [s["id"] for p in observed if p["id"] in replacements for s in p["skus"]]
    for start in range(0, len(sku_ids), 100):
        if not api("pricing", "completeness", "POST", {"skuIds": sku_ids[start:start + 100]})["complete"]:
            raise ValueError("Replacement price books incomplete; legacy catalog retained")
    existing_codes = {c["code"] for c in api("pricing", "coupons")}
    for coupon in coupon_fixtures(manifest, receipt["completed"]):
        if coupon["code"] not in existing_codes:
            api("pricing", "coupons", "POST", coupon)
    receipt["couponCodes"] = ["REALCR10", "REALCR10USD", "REALFB10", "REALFB10USD"]
    for product in observed:
        # Only known older unsourced listings are superseded. Preserve other sourced operator models.
        if product["id"] not in replacements and product["status"] == "active" and not product["details"]:
            api("catalog", f"products/{product['id']}/retire", "POST", {
                "expectedRevision": product["revision"], "idempotencyKey": "real-v1:retire:" + product["id"],
                "reason": "Superseded active fictional fixture with sourced photographic catalog; history preserved"})
            receipt.setdefault("retired", []).append(product["id"])
            save(receipt)
    receipt.pop("currentSourceKey", None)
    receipt["state"] = "imported-awaiting-final-tests"
    save(receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    directory = ROOT / "devops/.local/catalog-import"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (digest + ".json")
    if directory.is_symlink() or path.is_symlink():
        raise ValueError("Refusing symlinked import receipt")
    def save(value):
        temporary = path.with_suffix(".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2)
        temporary.replace(path)
    receipt = {"manifestSha256": digest, "state": "importing", "completed": {}}
    if path.exists():
        receipt = json.loads(path.read_text())
    try:
        import_manifest(OwnerApi(), json.loads(raw), receipt, save)
    except Exception as error:
        receipt["state"] = "interrupted"
        receipt["errorType"] = type(error).__name__
        save(receipt)
        raise
    print(f"Imported {len(receipt['completed'])} models; final automated acceptance pending")


if __name__ == "__main__":
    main()
