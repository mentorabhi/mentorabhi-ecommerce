# Inventory service

Inventory owns one local warehouse, the stock movement ledger and an on-hand projection. Adjustments require an authenticated local account, an active Catalog SKU, a signed nonzero quantity, a reason and a replay-safe idempotency key. No application role assignment is required (ADR 0003). The service forwards the caller's bearer to Catalog and never reads Catalog tables.

Public API contract: `../../contracts/inventory/openapi.yaml`.
