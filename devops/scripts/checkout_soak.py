"""Paced local Commerce/CDC checkout soak; no real payment or fulfillment."""
import argparse
import json
import math
import sys
import time
import uuid

import manage
import projection_operations
from acceptance_probe import ProbeFailure, connector_running, environment, group_offset, require, save_report, utc_now, verify_containers
from checkout_burst import docker_memory_mib, percentile


def planned_orders(duration, interval):
    require(60 <= duration <= 3600 and 10 <= interval <= 60,
            "Use a 60–3600 second duration and 10–60 second interval")
    count = math.ceil(duration / interval)
    require(count <= 100, "Limit a local soak to 100 orders")
    return count


def verify_projection(order, history):
    require(history.get("state") == "FULFILLMENT_SCHEDULED" and history.get("lastSequence") == 3,
            "Projection did not reach the three-event terminal sequence")
    require(history.get("currency") == order.get("currency") and history.get("totalMinor") == order.get("totalMinor"),
            "Projection money differs from owner Orders API")
    fields = ("skuId", "quantity", "unitPriceMinor", "discountMinor", "lineTotalMinor")
    normalize = lambda rows: sorted(tuple(str(row.get(key)) for key in fields) for row in rows)
    require(normalize(history.get("lines", [])) == normalize(order.get("lines", [])),
            "Projection lines differ from owner Orders API")


def submission_due(elapsed, duration, submitted, count, interval):
    require(elapsed < duration or submitted == count, "Planned submissions did not finish within the workload window")
    return elapsed < duration and submitted < count and elapsed >= submitted * interval


def prepare_dispatch(get_token, started, duration, clock=time.monotonic):
    token = get_token()
    sent = clock()
    require(sent - started < duration, "Authentication completed after the workload submission deadline")
    return token, sent


def completion_observed(started, duration, now):
    require(now - started <= duration + 180, "Observed terminal completion exceeded the drain deadline")
    return now


def verify_lifecycle(events, order_ids):
    expected = {(1, "OrderAccepted"), (2, "OrderConfirmed"), (3, "FulfillmentScheduled")}
    for order_id in order_ids:
        owned = [event for event in events if event["aggregateId"] == order_id]
        require(len(owned) == 3 and len({event["eventId"] for event in owned}) == 3 and
                {(event["aggregateSequence"], event["eventType"]) for event in owned} == expected,
                "Soak order does not have exactly the three expected lifecycle events")


def run_probe(duration, interval, project):
    count = planned_orders(duration, interval)
    report = {"kind": "checkout-soak", "startedAt": utc_now(), "durationSeconds": duration,
              "intervalSeconds": interval, "plannedOrders": count, "checkouts": [], "samples": []}
    pending = {}
    started = None
    try:
        report["environmentBefore"] = environment(project)
        for port in (8081, 8083, 8084, 8085, 8086, 8087, 8088, 8089):
            manage.wait_status(f"http://127.0.0.1:{port}/actuator/health/readiness", timeout=5)
        code, connector = manage.request_json("http://127.0.0.1:8090/connectors/supersports-orders-outbox/status")
        require(code == 200 and connector_running(connector),
                "Main CDC connector is unavailable")
        credentials = manage.load_credentials(manage.ROOT / "devops/.local/bootstrap.env")
        token, refreshed = None, 0

        def customer_token():
            nonlocal token, refreshed
            if token is None or time.monotonic() - refreshed >= 45:
                token = manage.customer_token_for("checkout-test-customer", credentials["DEMO_CUSTOMER_PASSWORD"])
                refreshed = time.monotonic()
            return token

        code, products = manage.request_json("http://127.0.0.1:8081/api/v1/catalog/products?q=football")
        require(code == 200, "Football catalog unavailable")
        sku = next(item for product in products for item in product["skus"] if item.get("active", True))
        sku_id = report["skuId"] = sku["id"]
        inventory_url = f"http://127.0.0.1:8084/api/v1/inventory/availability/{sku_id}"
        code, stock = manage.request_json(inventory_url)
        require(code == 200 and stock["available"] >= count, "Insufficient synthetic stock; preflight stops before checkout")
        report["stockBefore"] = stock["available"]
        code, rows = manage.request_json("http://127.0.0.1:8086/api/v1/orders", token=customer_token())
        require(code == 200 and not any(row["state"] == "PENDING_PAYMENT" for row in rows),
                "The synthetic customer's earlier checkout queue must drain first")
        group = manage.history_target(project=project)["group"]
        topic = "commerce.order.events.v1"
        initial_lag = group_offset(project, group, topic, (0, 1, 2))
        require(all(row["lag"] == 0 for row in initial_lag.values()), "History must start caught up")
        report["initialOffsets"] = initial_lag
        started = time.monotonic()
        next_poll, next_sample = 0, 0
        while time.monotonic() - started < duration or pending:
            elapsed = time.monotonic() - started
            require(elapsed <= duration + 180, "Checkout drain exceeded 180 seconds")
            if submission_due(elapsed, duration, len(report["checkouts"]), count, interval):
                index = len(report["checkouts"])
                key = "s1-soak-" + uuid.uuid4().hex
                request_token, sent = prepare_dispatch(customer_token, started, duration)
                item = {"index": index, "key": key, "scheduledSeconds": index * interval,
                        "sentAt": utc_now(), "sentSeconds": sent - started}
                report["checkouts"].append(item)
                payload = json.dumps({"lines": [{"skuId": sku_id, "quantity": 1}], "couponCode": None}).encode()
                code, body = manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout",
                    token=request_token, method="POST", data=payload, headers={"Idempotency-Key": key})
                item.update(status=code, orderId=body.get("orderId"), acceptMs=round((time.monotonic() - sent) * 1000, 2))
                require(code == 202 and item["orderId"], f"Checkout {index} was not accepted (HTTP {code})")
                pending[item["orderId"]] = (item, sent)
                code, replay = manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout",
                    token=customer_token(), method="POST", data=payload, headers={"Idempotency-Key": key})
                item["replaySameOrder"] = code == 202 and replay.get("orderId") == item["orderId"]
                require(item["replaySameOrder"], "Checkout idempotency replay returned a different result")
            if elapsed >= next_poll:
                code, rows = manage.request_json("http://127.0.0.1:8086/api/v1/orders", token=customer_token())
                observed = completion_observed(started, duration, time.monotonic())
                require(code == 200, "Owner order polling failed")
                states = {row["id"]: row for row in rows}
                for order_id, (item, sent) in list(pending.items()):
                    state = states.get(order_id, {}).get("state")
                    require(state not in {"FAILED", "MANUAL_REVIEW"}, "An accepted soak order failed")
                    if state == "FULFILLMENT_SCHEDULED":
                        item.update(state=state, completedAt=utc_now(), endToEndMs=round((observed - sent) * 1000, 2))
                        pending.pop(order_id)
                report["maxPending"] = max(report.get("maxPending", 0), len(pending))
                next_poll = elapsed + 3
            if elapsed >= next_sample:
                code, view = manage.request_json("http://127.0.0.1:8089/api/v1/order-history", token=customer_token())
                require(code == 200, "History freshness API unavailable")
                code, stock = manage.request_json(inventory_url)
                require(code == 200 and stock["available"] >= 0, "Inventory unavailable or negative during soak")
                sample = {"at": utc_now(), "elapsedSeconds": round(time.monotonic() - started, 2),
                          "freshness": view.get("freshness", {}).get("state"), "stockAvailable": stock["available"],
                          "memoryMiB": docker_memory_mib(), "pending": len(pending),
                          "offsets": group_offset(project, group, topic, (0, 1, 2))}
                report["samples"].append(sample)
                print(f"Soak {sample['elapsedSeconds']:.0f}s: {len(report['checkouts'])}/{count} accepted, "
                      f"{len(pending)} pending, freshness={sample['freshness']}", flush=True)
                next_sample = elapsed + 30
            time.sleep(.5)

        require(len(report["checkouts"]) == count and len({row["orderId"] for row in report["checkouts"]}) == count,
                "Soak order identities are incomplete or duplicated")
        deadline = time.monotonic() + 90
        while True:
            offsets = group_offset(project, group, topic, (0, 1, 2))
            if all(row["lag"] == 0 for row in offsets.values()):
                break
            require(time.monotonic() < deadline, "History failed to reach final zero lag")
            time.sleep(2)
        report["finalOffsets"] = offsets
        for item in report["checkouts"]:
            code, order = manage.request_json(f"http://127.0.0.1:8086/api/v1/orders/{item['orderId']}", token=customer_token())
            require(code == 200, "Owner order detail unavailable")
            code, history = manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{item['orderId']}", token=customer_token())
            require(code == 200, "Soak order missing from History")
            verify_projection(order, history)
        other = manage.customer_token_for("checkout-test-customer-b", credentials["DEMO_CUSTOMER_PASSWORD"])
        for item in (report["checkouts"][0], report["checkouts"][-1]):
            for port, route in ((8086, "orders"), (8089, "order-history")):
                code, _ = manage.request_json(f"http://127.0.0.1:{port}/api/v1/{route}/{item['orderId']}", token=other)
                require(code == 404, "Cross-owner soak order became readable")
        code, stock = manage.request_json(inventory_url)
        require(code == 200 and stock["available"] == report["stockBefore"] - count, "Final stock delta differs from unique one-unit orders")
        report["stockAfter"] = stock["available"]
        report["measuredSeconds"] = round(time.monotonic() - started, 2)
        source = projection_operations.source_snapshot(manage, project=project)
        verify_lifecycle(source["events"], {item["orderId"] for item in report["checkouts"]})
        report["reconciliation"] = projection_operations.reconcile(manage, project=project)
        require(report["reconciliation"]["ok"], "Full source/Kafka/inbox/timeline reconciliation failed")
        for field, key in (("acceptMs", "acceptLatencyMs"), ("endToEndMs", "endToEndLatencyMs")):
            values = [item[field] for item in report["checkouts"]]
            report[key] = {"p50": percentile(values, .5), "p95": percentile(values, .95), "max": max(values)}
        report["environmentAfter"] = environment(project, [c["id"] for c in report["environmentBefore"]["containers"]])
        verify_containers(report["environmentBefore"]["containers"], report["environmentAfter"]["containers"])
        report["outcome"] = "PASS"
    except Exception as error:
        report.update(outcome="FAIL", failureType=type(error).__name__, failure=str(error)[:240])
        raise
    finally:
        report["pendingOrderIds"] = list(pending)
        report["finishedAt"] = utc_now()
        path = save_report(report, "checkout-soak")
        print(f"Soak report: {path.relative_to(manage.ROOT)}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=int, default=900)
    parser.add_argument("--interval-seconds", type=int, default=15)
    parser.add_argument("--project", default="supersports")
    args = parser.parse_args()
    try:
        report = run_probe(args.duration_seconds, args.interval_seconds, manage.validated_project_name(args.project))
        print(json.dumps({key: report[key] for key in ("outcome", "measuredSeconds", "acceptLatencyMs", "endToEndLatencyMs", "maxPending", "stockBefore", "stockAfter")}))
        return 0
    except Exception as error:
        print(f"Soak failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
