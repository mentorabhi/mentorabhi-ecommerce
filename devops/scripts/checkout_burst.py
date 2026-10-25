"""Bounded local-only checkout burst for S1-M06 capacity observations."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import manage


class ProbeFailure(RuntimeError):
    pass


def percentile(values: list[float], rank: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(rank * len(ordered)) - 1)]


def docker_memory_mib() -> float | None:
    result = manage.run(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}"],
                        capture=True, check=False, timeout=10)
    if result.returncode:
        return None
    total = 0.0
    for line in result.stdout.splitlines():
        match = re.match(r"\s*([0-9.]+)\s*(B|KiB|MiB|GiB|kB|MB|GB)", line)
        if not match:
            continue
        amount, unit = float(match.group(1)), match.group(2)
        scale = {"B": 1 / 1048576, "KiB": 1 / 1024, "MiB": 1, "GiB": 1024,
                 "kB": 1000 / 1048576, "MB": 1_000_000 / 1048576,
                 "GB": 1_000_000_000 / 1048576}[unit]
        total += amount * scale
    return round(total, 2)


def zero_lag(project: str, timeout: int = 120) -> bool:
    group = manage.history_target(project=project)["group"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = manage.compose(["--profile", "streaming", "exec", "-T", "kafka",
            "/opt/kafka/bin/kafka-consumer-groups.sh", "--bootstrap-server", "localhost:9092",
            "--describe", "--group", group], project=project, capture=True, check=False, timeout=15)
        rows = [line.split() for line in result.stdout.splitlines()
                if line.strip().startswith(group + " commerce.order.events.v1")]
        if len(rows) == 3 and all(int(row[5]) == 0 for row in rows):
            return True
        time.sleep(1)
    return False


def persist_report(report: dict, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = directory / f"checkout-burst-{stamp}-{uuid.uuid4().hex[:8]}.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    return target


def run_probe(orders: int, workers: int, project: str) -> dict:
    if not 1 <= orders <= 50 or not 1 <= workers <= 16 or workers > orders:
        raise ProbeFailure("Use 1–50 orders and 1–16 workers, with workers no greater than orders.")
    for port in (8081, 8083, 8084, 8085, 8086, 8087, 8088, 8089):
        manage.wait_status(f"http://127.0.0.1:{port}/actuator/health/readiness", timeout=5)
    with manage.urlopen("http://127.0.0.1:8090/connectors/supersports-orders-outbox/status", timeout=5) as response:
        connector = json.loads(response.read())
    if connector.get("connector", {}).get("state") != "RUNNING" or not connector.get("tasks") or connector["tasks"][0].get("state") != "RUNNING":
        raise ProbeFailure("Orders CDC connector/task is not RUNNING.")

    credentials = manage.load_credentials(ROOT / "devops/.local/bootstrap.env")
    customer = manage.customer_token_for("checkout-test-customer", credentials["DEMO_CUSTOMER_PASSWORD"])
    inventory_operator = manage.token_for("inventory-operator", credentials["DEMO_INVENTORY_OPERATOR_PASSWORD"])
    status, products = manage.request_json("http://127.0.0.1:8081/api/v1/catalog/products?q=football")
    if status != 200:
        raise ProbeFailure("Football catalog is not available.")
    sku = next((item for product in products for item in product.get("skus", []) if item.get("active", True)), None)
    if not sku:
        raise ProbeFailure("No active football SKU is available.")
    sku_id = sku["id"]
    status, stock = manage.request_json(f"http://127.0.0.1:8084/api/v1/inventory/availability/{sku_id}")
    if status != 200:
        raise ProbeFailure("Inventory snapshot is unavailable.")
    stock_receipt = None
    if int(stock.get("available", 0)) < orders:
        delta = orders - int(stock.get("available", 0))
        stock_receipt = "s1-burst-stock-" + uuid.uuid4().hex
        payload = {"skuId": sku_id, "delta": delta, "reason": "Bounded S1-M06 local checkout capacity probe",
                   "idempotencyKey": stock_receipt}
        status, receipt = manage.request_json("http://127.0.0.1:8084/api/v1/inventory/adjustments",
            token=inventory_operator, method="POST", data=json.dumps(payload).encode())
        if status != 200:
            raise ProbeFailure(f"Could not ensure bounded synthetic stock (HTTP {status}).")

    report = {"startedAt": datetime.now(timezone.utc).isoformat(), "project": project,
              "ordersRequested": orders, "workers": workers, "skuId": sku_id,
              "stockAvailableBefore": int(stock.get("available", 0)), "stockReceiptKey": stock_receipt,
              "dockerMemorySamplesMiB": [], "checkouts": [], "connectorVersion": connector.get("connector", {}).get("version")}
    stop_sampler = threading.Event()
    def sample_memory():
        while not stop_sampler.is_set():
            sample = docker_memory_mib()
            if sample is not None:
                report["dockerMemorySamplesMiB"].append({"at": datetime.now(timezone.utc).isoformat(), "total": sample})
            stop_sampler.wait(1)
    sampler = threading.Thread(target=sample_memory, daemon=True)
    sampler.start()

    start_gate = threading.Event()
    def submit(index: int) -> dict:
        if not start_gate.wait(timeout=15):
            raise ProbeFailure("Checkout burst start gate timed out before all workers were scheduled.")
        key = "s1-burst-" + uuid.uuid4().hex
        payload = {"lines": [{"skuId": sku_id, "quantity": 1}], "couponCode": None}
        start = time.monotonic()
        status, body = manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout", token=customer,
            method="POST", data=json.dumps(payload).encode(), headers={"Idempotency-Key": key})
        elapsed = (time.monotonic() - start) * 1000
        return {"index": index, "key": key, "status": status, "orderId": body.get("orderId"),
                "error": body.get("error") if status != 202 else None, "acceptMs": round(elapsed, 2),
                "acceptedAt": datetime.now(timezone.utc).isoformat()}

    accepted_at = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(submit, index) for index in range(orders)]
            start_gate.set()
            report["checkouts"] = [future.result() for future in futures]
        for item in report["checkouts"]:
            item["acceptedOffsetMs"] = round((datetime.fromisoformat(item["acceptedAt"]).timestamp() -
                datetime.fromisoformat(report["startedAt"]).timestamp()) * 1000, 2)
        acceptance_done = time.monotonic()
        report["acceptanceElapsedMs"] = round((acceptance_done - accepted_at) * 1000, 2)
        accepted = [item for item in report["checkouts"] if item["status"] == 202 and item["orderId"]]
        if len(accepted) != orders:
            raise ProbeFailure(f"Only {len(accepted)} of {orders} checkouts were accepted; see local report.")

        pending = {item["orderId"]: item for item in accepted}
        report["completionDeadlineSeconds"] = 360
        deadline = time.monotonic() + report["completionDeadlineSeconds"]
        terminal = {"FULFILLMENT_SCHEDULED", "FAILED", "MANUAL_REVIEW"}
        orders_url = "http://127.0.0.1:8086/api/v1/orders"
        while pending and time.monotonic() < deadline:
            status, rows = manage.request_json(orders_url, token=customer)
            if status == 200:
                states = {row.get("id"): row for row in rows}
                for order_id, item in list(pending.items()):
                    body = states.get(order_id)
                    if body and body.get("state") in terminal:
                        item["state"] = body["state"]
                        item["totalMinor"] = body.get("totalMinor")
                        item["completedAt"] = datetime.now(timezone.utc).isoformat()
                        item["endToEndMs"] = round(item["acceptedOffsetMs"] +
                            (time.monotonic() - accepted_at) * 1000, 2)
                        pending.pop(order_id)
            if pending:
                time.sleep(1)
        if pending:
            report["outcome"] = "FAIL"
            report["pendingOrderIds"] = sorted(pending)
            raise ProbeFailure(f"{len(pending)} accepted orders did not reach a terminal state within {report['completionDeadlineSeconds']} seconds.")

        status, final_stock = manage.request_json(f"http://127.0.0.1:8084/api/v1/inventory/availability/{sku_id}")
        if status != 200 or int(final_stock.get("available", -1)) < 0:
            raise ProbeFailure("Final stock is unavailable or negative.")
        report["stockAvailableAfter"] = int(final_stock["available"])
        report["stockNonnegative"] = True
        report["zeroLag"] = zero_lag(project)
        if not report["zeroLag"]:
            raise ProbeFailure("Order History did not catch up within 120 seconds.")
        for item in report["checkouts"]:
            if item.get("state") != "FULFILLMENT_SCHEDULED":
                raise ProbeFailure("At least one accepted checkout did not reach FULFILLMENT_SCHEDULED.")
        accept_latencies = [item["acceptMs"] for item in report["checkouts"]]
        end_to_end = [item["endToEndMs"] for item in report["checkouts"]]
        report["acceptLatencyMs"] = {"p50": percentile(accept_latencies, .50), "p95": percentile(accept_latencies, .95),
                                     "max": max(accept_latencies)}
        report["endToEndLatencyMs"] = {"p50": percentile(end_to_end, .50), "p95": percentile(end_to_end, .95),
                                       "max": max(end_to_end)}
        report["outcome"] = "PASS"
        return report
    except Exception as error:
        report.setdefault("outcome", "FAIL")
        report["failureType"] = type(error).__name__
        report["failureSummary"] = str(error)[:240]
        report["pendingOrderIds"] = [item["orderId"] for item in report.get("checkouts", [])
                                     if item.get("orderId") and not item.get("state")]
        raise
    finally:
        stop_sampler.set()
        sampler.join(timeout=5)
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        target = persist_report(report, ROOT / "devops/.local/load-probes")
        print(f"Local checkout-burst report saved to {target.relative_to(ROOT)}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orders", type=int, default=20)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--project", default="supersports")
    args = parser.parse_args()
    try:
        report = run_probe(args.orders, args.workers, manage.validated_project_name(args.project))
    except (ProbeFailure, RuntimeError, ValueError) as error:
        print(f"Checkout burst did not pass: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
