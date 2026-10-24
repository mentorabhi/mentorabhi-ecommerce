# M07 event compatibility foundation

Revision 1 · 2026-10-24 · Design before implementation

## Goal

Prepare Orders and Order History for post-purchase lifecycle facts without changing the immutable `order-lifecycle-v1` contract or sending unsupported messages to the current consumer. This compatibility foundation is scheduled before cancellation/return implementation because those owner transactions must emit durable events when their state changes.

## Contract

Version 2 keeps the common event envelope: stable event UUID, Order aggregate UUID, monotonic aggregate sequence, occurred-at instant and opaque HMAC customer key. It adds a narrow allowlist for `OrderCancelled`, `OrderReturnRequested`, `OrderRefundCompleted` and `ShipmentMilestoneRecorded`. Payloads contain operation/return IDs, amounts and currencies, SKU quantities, simulator state/revision and reason codes only. They exclude addresses, bearer tokens, review/support text, raw customer subjects and payment instruments.

`order-lifecycle-v1.schema.json` remains unchanged. A new v2 JSON Schema is validated by the producer and CI. Orders keeps the legacy writer path pinned to version 1; a separate v2 writer method is used only for these reviewed types. Event version is determined by the event type, not caller-supplied arbitrary data.

## Consumer behavior

Order History accepts both versions. It uses the same inbox identity/hash and contiguous per-order sequence rules. Version 2 cancellation changes the order projection to `CANCELLED`; return/refund and shipment facts update the order state only from the explicit allowed state in the envelope and remain in the immutable timeline. Unknown version/type/field combinations continue to go to the transactional DLQ. Rebuild/reconciliation must validate both versions from the same retained outbox.

## Rollout

1. Add v2 schema and producer/consumer parser tests.
2. Teach Orders writer and History consumer both versions while production still emits v1 only.
3. Update reconciliation, fixtures and contract validation for v2.
4. Only then let Units 3/4 publish v2 cancellation/refund/return facts.

This is source compatibility only; the later consolidated verification phase must test a live v1/v2 mixed stream, crash/offset semantics and rebuild reconciliation before release.
