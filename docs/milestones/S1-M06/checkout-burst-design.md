# Bounded concurrent checkout capacity probe

Revision 1 · 2026-10-25 · Design before implementation

## Goal

Measure a repeatable short checkout burst on the 16 GB local ARM64 profile and verify successful requests preserve stock, order ownership, event delivery and eventual terminal state. This is a bounded acceptance observation, not a sustained-load or production-capacity claim.

## Safety and bounds

- Use the existing local synthetic customer, active football SKU, and local simulated payment/fulfillment only. Create a unique idempotency key per order; no external provider is called.
- Default to 20 checkouts and at most 8 simultaneous requests; reject requests above 50 orders or 16 workers.
- Read current available stock first and add a keyed synthetic stock receipt only if required. Persist the generated order IDs and receipt key in the ignored `.local` report; never write credentials/tokens to output or repository.
- Keep full Commerce and streaming profiles active; stop optional Analytics, graph and observability profiles during the measurement. Verify all required services healthy first.
- Record each checkout acceptance latency, status, end-to-end terminal latency/state, Kafka lag, sampled container memory, Docker allocation, image revisions, dataset and time window.
- Require no declined/failed orders, no negative stock, one owned order per accepted idempotency key, complete event delivery and zero Kafka lag. If a precondition fails, stop before load and report it.

## Procedure

1. Capture service health, current stock, memory and Kafka offsets.
2. Select an active football SKU and authenticated local synthetic customer.
3. Submit a synchronized bounded burst of unique one-unit orders using the requested worker count.
4. Poll each returned order to a terminal result with a fixed timeout; collect request and completion latencies.
5. Verify order IDs/states through the customer Orders API, SKU stock through the Inventory owner API, and Kafka consumer lag through the local CLI. Sample process memory while requests and order processing are active.
6. Write a privacy-safe result JSON under ignored `devops/.local/load-probes/` and summarize measured results and limits in M06 verification.

## Pass and interpretation

The burst passes when every request is accepted exactly once, all orders reach the expected simulated confirmed/shipment-scheduled terminal state, stock remains nonnegative, event consumers catch up, and memory remains within measured container/host allocation. Report p50/p95/max acceptance and completion latency and maximum sampled memory. This finite burst does not show what happens during an hour-long soak, a broker outage beyond tested recovery, or on larger production traffic.
