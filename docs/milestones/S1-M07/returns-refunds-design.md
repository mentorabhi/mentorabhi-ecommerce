# M07 Unit 4 — partial returns and simulated refunds

Revision 1 · 2026-10-24 · Design before implementation

## Goal and boundaries

Allow an authenticated customer to request a partial return of a delivered order line. Orders owns the customer's request, return window, cumulative quantities and immutable refund allocation. Fulfillment is queried through the Orders service identity to verify delivery. Payment owns the refund ledger and rejects cumulative refunds above capture. Inventory inspection/restock is deliberately a separate Unit 5; requesting a return never changes sellable stock.

No real return shipping label, carrier, payment provider, or cloud dependency is introduced. Return-window days are a revisioned local setting applied at the accepted return request; accepted requests preserve the policy revision and deadline they were evaluated against.

## Allocation and concurrency

1. Lock the owned order and its line rows in a stable SKU order. Verify Fulfillment state is `DELIVERED`, then persist that delivered fact on the Orders aggregate.
2. Require `now <= delivered_at + configured_window`. Reject requests outside the window with a stable policy reason.
3. Enforce `requested quantity <= purchased quantity - previously claimed quantity`, counting every accepted or pending request. The order lock serializes competing partial-return requests.
4. Compute line merchandise after discount from immutable `customer_order_line.line_total_minor`. Allocate the order's captured tax across lines proportional to those line totals with integer largest-remainder rounding; ties resolve by canonical SKU UUID order. Split each line allocation into stable unit slots, distributing remainder to lower unit ordinals. Reserve unit slots in the same transaction as the request.
5. Refund only returned merchandise plus its precomputed tax share. Simulated shipping is nonrefundable for partial returns. A full pre-handoff cancellation continues to refund the full capture under Unit 3.
6. Orders writes an idempotent return operation with stable downstream Payment operation key. Payment remains the final cumulative-capture cap. Retry and restart reuse the same operation ID and exact amount. Changed payload under the same customer idempotency key conflicts.

The unit refund value is stored at claim time. It is not recomputed from current Catalog prices, a new currency setting, or a later order edit. Duplicate requests cannot reserve the same `(order, SKU, unit ordinal)`.

## API and event

- `POST /api/v1/orders/{orderId}/returns` requires `Idempotency-Key` and a non-empty list of `{skuId, quantity}`.
- `GET /api/v1/orders/{orderId}/returns/{returnId}` is owner-scoped and returns policy revision, status, requested lines, refund amount and stable failure/review code.
- `OrderReturnRequested` v2 is appended after the return claim commits; it contains opaque IDs, delivered state, requested quantities, and policy revision only.
- `OrderRefundCompleted` v2 is appended after Payment confirms the refund and Orders commits its receipt. It carries the immutable amount/currency and reason code, no payment instrument details.

Both outbox events commit with their corresponding Orders-owned transaction. A crash after a remote refund but before Orders records the receipt replays the same Payment operation key and amount.

## Data ownership

Orders stores policy revision/deadline, idempotency payload hash, status, lease/fence, requested quantities, unit ordinals and allocated unit refund values. Payment stores only its own refund ledger. Fulfillment remains the delivery source. Inventory receives no stock mutation until Unit 5 inspection accepts units for restock.

## Failure and test cases

- Customer ownership and cross-customer return ID lookup.
- Delivered and within-window happy path; scheduled, handoff, unavailable, and expired-window rejection.
- Same-key retry, changed-payload conflict, and two concurrent requests competing for the last unit.
- Multi-line tax allocation where minor-unit remainders tie; deterministic SKU tie-break and exact sum to captured tax.
- Zero-refund line allocations, partial quantities over multiple requests, and cumulative refund cap.
- Worker crash before and after Payment refund, retry/restart, event identity/sequence, and no stock change before inspection.

## Manual acceptance

Separate service, customer UI, API, database-owner, concurrency and result-record checks will be added under `returns-refunds-manual-checks.md`. All verification is deferred until the user-directed Stage 1 development pass is complete.
