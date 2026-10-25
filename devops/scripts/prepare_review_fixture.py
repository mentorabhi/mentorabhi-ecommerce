"""Prepare one owned, simulated delivered purchase for the M11 Selenium journey."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import time
import uuid
import manage


def call(port, path, token=None, method="GET", body=None, key=None, expected=200):
    status, result = manage.request_json(f"http://127.0.0.1:{port}/api/v1/{path}", token=token,
        method=method, data=None if body is None else json.dumps(body).encode(),
        headers={"Idempotency-Key": key} if key else None)
    if status != expected:
        raise RuntimeError(f"Review fixture operation failed (HTTP {status}); private receipt is retained for resume.")
    return result


def save(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        os.fchmod(handle.fileno(), 0o600)
        json.dump(data, handle, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def prepare(resume: Path | None = None):
    from ui_access import private_directory, read_private
    directory = private_directory(manage.ROOT) / "ui-fixtures"
    if directory.is_symlink():
        raise ValueError("Refusing a symlinked fixture directory")
    directory.mkdir(mode=0o700, exist_ok=True)
    if resume:
        if resume.is_symlink() or resume.resolve().parent != directory.resolve():
            raise ValueError("Resume requires a private UI fixture receipt")
        path, fixture = resume, json.loads(read_private(resume))
    else:
        fixture_id = uuid.uuid4()
        page = call(8081, "catalog/public/products?pageSize=24")
        last = max(1, (page["total"] + 23) // 24)
        candidates = call(8081, f"catalog/public/products?pageSize=24&page={last}")["items"]
        product, sku = None, None
        for candidate in candidates:
            if len(candidate["skus"]) < 2:
                continue
            variants = candidate["skus"][:100]
            available = call(8084, "inventory/availability?skuIds=" + ",".join(row["id"] for row in variants))
            stocked = {row["skuId"] for row in available if row["available"] > 0}
            selected = next((row for row in variants if row["id"] in stocked), None)
            if selected:
                product, sku = candidate, selected
                break
        if not product or not sku:
            raise RuntimeError("No stocked multi-variant product is available for this fixture")
        fixture = {"fixtureId": str(fixture_id), "checkoutKey": "m11-review-" + fixture_id.hex,
                   "productId": product["id"], "productSlug": product["slug"], "productTitle": product["title"],
                   "skuId": sku["id"], "createdAt": time.time()}
        path = directory / f"m11-review-{fixture_id.hex}.json"
        save(path, fixture)
    credentials = manage.load_credentials(manage.ROOT / "devops/.local/bootstrap.env")
    customer = manage.customer_token_for("checkout-test-customer", credentials["DEMO_CUSTOMER_PASSWORD"])
    operator = manage.token_for("admin", manage.configure_admin_login())
    profile = call(8085, "customer/profile", customer)
    if not all(profile.get(field) for field in ("fullName", "line1", "city", "state", "postalCode")):
        call(8085, "customer/profile", customer, "PUT", {"fullName": "Synthetic Review Test", "phone": "9000000001",
             "line1": "12 Demo Road", "line2": "", "city": "Pune", "state": "Maharashtra", "postalCode": "411001",
             "country": "IN", "expectedRevision": profile["revision"]})
    accepted = call(8086, "orders/checkout", customer, "POST", {
        "lines": [{"skuId": fixture["skuId"], "quantity": 1}], "couponCode": None}, fixture["checkoutKey"], 202)
    fixture["orderId"] = accepted["orderId"]; save(path, fixture)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        order = call(8086, "orders/" + fixture["orderId"], customer)
        if order["state"] == "FULFILLMENT_SCHEDULED":
            break
        if order["state"] in ("FAILED", "MANUAL_REVIEW", "CANCELLED"):
            raise RuntimeError("Fixture checkout did not complete; inspect the private order receipt")
        time.sleep(1)
    else:
        raise RuntimeError("Fixture checkout deadline exceeded; resume using its private receipt")
    states = ["SCHEDULED", "HANDED_OFF", "IN_TRANSIT", "DELIVERED"]
    for target in states[1:]:
        tracking = call(8086, f"orders/{fixture['orderId']}/tracking", customer)["tracking"]
        if states.index(tracking["state"]) >= states.index(target):
            continue
        call(8088, f"operator/shipments/{fixture['orderId']}/transitions", operator, "POST", {
            "expectedRevision": tracking["revision"], "targetState": target,
            "operationId": str(uuid.uuid5(uuid.UUID(fixture["fixtureId"]), target)), "reason": "M11 Selenium delivery fixture"})
    fixture["deliveryVerified"] = True; save(path, fixture)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", type=Path)
    print(prepare(parser.parse_args().resume))
