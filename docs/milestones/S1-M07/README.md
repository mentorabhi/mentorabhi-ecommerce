# S1-M07 — Post-purchase service

Revision 1 · 2026-10-24 · Design and review complete; implementation not started.

Design: [post-purchase design](design.md). Review: [design review](design-review.md). Editable flow: [post-purchase-flow.mmd](post-purchase-flow.mmd). Manual checks: [manual acceptance](manual-acceptance.md). Requirements: R08 and AE10 in [accepted requirements](../../requirements/accepted-requirements.md).

## Objective

Complete the customer order lifecycle after checkout: fulfillment tracking, eligible cancellation, line-level returns, simulated refunds, verified-purchase reviews with moderation, and owned support requests. Preserve service ownership and money invariants from M05/M06.

## Exit gate

- Customer can track shipment and delivery states from their own account.
- Cancellation, return eligibility, partial returns, inspection/restock, and refund limits are deterministic, idempotent, and audited.
- Review submission requires a delivered purchase; moderation controls publication and can resolve reports.
- Support can inspect only authorized customer/order facts; no impersonation or private-table joins.
- UI, ownership, transition, concurrency, replay, and restart checks pass; end-user guide is completed.
