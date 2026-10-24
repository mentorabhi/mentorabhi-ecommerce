# M07 Unit 5 — return inspection and restock

Revision 1 · 2026-10-24 · Design before implementation

## Goal and ownership

Inventory alone records physical return receipt, per-unit condition decisions and stock movements. Orders remains the owner of customer identity, refund allocation and return claims. Orders sends a narrow internal manifest after a return refund is confirmed; Inventory never reads Orders' database. Customer refunds remain complete even when a returned unit is damaged or rejected for resale.

## Registration and inspection

1. Orders exposes an internal worker-only manifest endpoint with `returnId`, `orderId`, and the exact claimed `(skuId, unitOrdinal)` list. It excludes customer subjects, address, prices, refund details and free text.
2. The existing fenced Orders worker posts that manifest to Inventory using the worker identity, `checkout:inventory.return.receive`, and a stable `returnId` operation key. A separate Orders inspection-registration lease retries this delivery if the worker stops after the refund receipt commits.
3. Inventory inserts one immutable received-unit row per allocation. The operation key and `(returnId, skuId, unitOrdinal)` are unique. A matching replay returns the prior receipt; changed content conflicts.
4. Operators read pending units from Inventory and submit one inspection operation with expected return revision, operation UUID, actor from the JWT, and one decision/reason per received unit.
5. Decisions are `SELLABLE`, `DAMAGED`, or `DISPUTED`. Only `SELLABLE` increments on-hand and writes one positive `stock_movement` in the same transaction. Other decisions remain unavailable and audited; the already completed refund is not reversed.
6. A whole manifest is inspected atomically, so stale revision or incomplete/duplicate unit decisions change nothing. An exact operation retry returns its original result; reusing the operation ID with changed decisions conflicts.

## API and data

- Internal `POST /api/v1/internal/checkout/inventory/returns/{returnId}/receive` registers a returned-unit manifest under the checkout worker scope.
- Operator `GET /api/v1/inventory/returns/pending` lists only received units that still need inspection.
- Operator `POST /api/v1/inventory/returns/{returnId}/inspection` commits all unit decisions with expected revision and reason.
- Inventory migration stores receipt, inspection, actor/reason audit, and the existing append-only stock movement ledger. No returned item modifies an existing checkout reservation.

## Retry and test cases

Prove registration at-least-once behavior after Orders restart; identical manifest replay and changed manifest conflict; worker-scope isolation; operator-audience isolation; complete versus incomplete inspection; stale revision and changed operation payload; two operators racing on one return; sellable stock increments exactly once; damaged/disputed units never increment stock; unrelated orders and existing checkout behavior remain unchanged.

## Manual acceptance

Unit 5 receives a separate service/UI/database manual guide. All commands and outcomes remain unexecuted until the Stage 1 development-first pass ends.
