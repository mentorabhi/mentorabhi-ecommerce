# M07 Unit 1 — Payment ledger bounds

2026-10-24 · Design/review before implementation · Implements the first dependency unit in `implementation-units.md`.

## Current defect and objective

`PaymentSimulator.execute` serializes on a per-order fence but asks only whether an `AUTHORIZED`/`CAPTURED` row exists. A second operation key can therefore capture repeatedly or refund beyond the captured amount. A VOID row does not remove the earlier AUTHORIZED row. Idempotency lookup is global but its replay check ignores the owning order.

Preserve the endpoint contract and existing checkout Saga while making the payment service's own ledger authoritative for every decision.

## Decision rules

1. Validate operation, operation key, amount, ISO-style currency token and authorization mode before mutation.
2. Keep the existing order fence row lock. Look up the operation key globally; replay only when order, operation and complete payload all match. Any owner/payload mismatch is conflict.
3. Read the order ledger after acquiring its fence. Permit one authorization decision (approved or declined). Capture once, only from an approved authorization, for exactly its authorized amount and currency, and never after void. Void only an uncaptured authorization at the original amount/currency. Refund only a captured order, for a positive amount in the original currency, while cumulative refunds remain within captured amount.
4. Preserve zero-value authorization/capture so zero-total checkout remains valid; a zero-value refund is invalid.
5. Use a conditional insert on the existing globally unique operation key to handle a same-key race across order locks. On conflict, reread the winning row and return an identical replay or the ordinary conflict.
6. Add partial unique indexes for one authorization decision, one capture and one void per order, plus a refund-positive check. Before migration, inspect existing data for conflicts; the release must stop with evidence if an existing ledger violates them.

No network/provider semantics are implied. Payment remains a deterministic local simulator. The Orders service continues to own checkout progress; Payment owns captured/refunded totals.

## Review

Implementation-owner review against the M07 intake resolves stale/current fence order, the cross-order global idempotency key race, capture-after-void, cumulative refund checks, currency/amount immutability, zero-value orders and concurrent same-order payments. Per-order `FOR UPDATE` fence serializes ledger decisions; unique indexes backstop operation cardinality. Conditional insert and reread handles concurrent reuse of the globally unique key without leaking a database uniqueness error. No open implementation blocker.

## Verification

Unit rule tests cover each transition, exact amount/currency and boundaries. Live service integration uses the authorized local checkout-worker client and synthetic order IDs to exercise repeated capture, cumulative refunds, capture after void, currency mismatch and cross-order key reuse. Run all service unit tests and M05 core integration; verify existing checkout payment rows remain unchanged and normal checkout still captures once. Manual inspection later uses the Payment database owner role.
