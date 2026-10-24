# S1-M07 — Post-purchase service

Revision 2 · 2026-10-24 · Post-purchase design/review complete; Unit 1 implemented and Unit 2 development checkpoint written. Verification of new development is deferred by the user until all Stage 1 milestone development is complete.

Design: [post-purchase design](design.md). Review: [design review](design-review.md). Editable flow: [post-purchase-flow.mmd](post-purchase-flow.mmd). Manual checks: [manual acceptance](manual-acceptance.md). Requirements: R08 and AE10 in [accepted requirements](../../../requirements/accepted-requirements.md).

Repository intake and execution order: [implementation units](implementation-units.md). The first implementation unit closes existing Payment ledger caps and operation ownership before customer post-purchase actions are exposed.

## Development checkpoints

- Unit 1 Payment ledger bounds: implemented; see [design](payment-ledger-design.md) and [verification history](verification.md).
- Unit 2 tracking and handoff: owner API, shipment revision/audit, operator transition API, and owner-verified Orders tracking route are now implemented in source. Operator/storefront controls and versioned lifecycle mirroring remain for Unit 8. New build and test execution is deferred until Stage 1 development is complete; scope/evidence is in [Unit 2 design](tracking-handoff-design.md), [flow](tracking-handoff-flow.mmd), [review](tracking-handoff-review.md), and the revised [manual guide](manual-acceptance.md).
- Units 3–8 remain to be developed in dependency order.

## Objective

Complete the customer order lifecycle after checkout: fulfillment tracking, eligible cancellation, line-level returns, simulated refunds, verified-purchase reviews with moderation, and owned support requests. Preserve service ownership and money invariants from M05/M06.

## Exit gate

- Customer can track shipment and delivery states from their own account.
- Cancellation, return eligibility, partial returns, inspection/restock, and refund limits are deterministic, idempotent, and audited.
- Review submission requires a delivered purchase; moderation controls publication and can resolve reports.
- Support can inspect only authorized customer/order facts; no impersonation or private-table joins.
- UI, ownership, transition, concurrency, replay, and restart checks pass; end-user guide is completed.
