# Inventory service

Inventory owns one local warehouse, the stock movement ledger, the on-hand projection and checkout reservations. Admin adjustments require an authenticated local account, an active Catalog SKU, a signed nonzero quantity, a reason and a replay-safe idempotency key. Checkout reservations are order-scoped, all-or-nothing under sorted row locks, expire within 30 minutes, and require the exact checkout-worker client, audience and operation scope. Protect/commit/release transitions are idempotent; commit appends stock movements and decrements on-hand in the same transaction. No application role assignment is required for the local operator API (ADR 0003). The service never reads Catalog tables.

Public API contract: `../../contracts/inventory/openapi.yaml`.
