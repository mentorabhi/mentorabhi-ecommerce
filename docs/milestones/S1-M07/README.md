# S1-M07 — Post-purchase service

Revision 5 · 2026-10-25 · Automated local acceptance is complete for exercised post-purchase paths, including three live integration journeys and the consolidated Selenium suite. Owner manual acceptance remains pending. See the dated [verification record](verification.md).

Design: [post-purchase design](design.md). Review: [design review](design-review.md). Editable flow: [post-purchase-flow.mmd](post-purchase-flow.mmd). Manual checks: [manual acceptance](manual-acceptance.md). Requirements: R08 and AE10 in [accepted requirements](../../../requirements/accepted-requirements.md).

Repository intake and execution order: [implementation units](implementation-units.md). The first implementation unit closes existing Payment ledger caps and operation ownership before customer post-purchase actions are exposed.

## Development checkpoints

- Unit 1 Payment ledger bounds: implemented; see [design](payment-ledger-design.md) and [verification history](verification.md).
- Unit 2 tracking and handoff: owner API, shipment revision/audit, operator transition API, and owner-verified Orders tracking route are implemented. Live handoff/cancellation concurrency verified one winner; the browser/operator scenarios are included in the upcoming Selenium pass. Scope/evidence is in [Unit 2 design](tracking-handoff-design.md), [flow](tracking-handoff-flow.mmd), [review](tracking-handoff-review.md), and the [manual guide](manual-acceptance.md).
- Event compatibility foundation: immutable v1 plus allowlisted v2 post-purchase schema and dual-version History parser are implemented ahead of Units 3/4; no v2 event is emitted yet. See [event design](post-purchase-events-design.md), [flow](post-purchase-events-flow.mmd), and [review](post-purchase-events-review.md).
- Unit 3 cancellation workflow: Orders, Inventory, Fulfillment, customer API/UI and v2 event emission are implemented. Live cancellation passed ownership, idempotency and Payment-simulator outage/recovery checks. See [cancellation design](cancellation-design.md), [flow](cancellation-flow.mmd), [review](cancellation-review.md), and [manual checks](cancellation-manual-checks.md).
- Unit 4 partial returns/refunds: Orders request ledger, deterministic immutable allocation, Payment refund worker, revisioned Configuration policy and customer UI/API are implemented. Live core and post-purchase scenarios verified one partial return/refund and duplicate protection. See [design](returns-refunds-design.md), [flow](returns-refunds-flow.mmd), [review](returns-refunds-review.md), and [manual checks](returns-refunds-manual-checks.md).
- Unit 5 return inspection/restock: Orders registration retry, Inventory receipt/inspection audit and stock movement, operator UI and contract are implemented. Live post-purchase journey verified inspection/retry; browser checks remain.
- Unit 6 verified reviews and Unit 7 owned support: independent service projects/databases, owner verification through Orders, customer/operator APIs and UI are implemented. Live checks passed product-bound verified-purchase reviews, moderation replay/conflict, support ownership/reply/status/restart. See [review/support design](reviews-support-design.md), [flow](reviews-support-flow.mmd), [review](reviews-support-review.md), and [manual checks](reviews-support-manual-checks.md).
- Unit 8 customer/operator integration includes shipment progression and customer tracking detail. Tracking remains an owner query rather than a mirrored Orders event. Fixture-backed Selenium journeys for shipment handoff, cancellation, returns/refunds, review submission and inspection/restock passed; the owner-run manual checklist remains an acceptance gate.

## Objective

Complete the customer order lifecycle after checkout: fulfillment tracking, eligible cancellation, line-level returns, simulated refunds, verified-purchase reviews with moderation, and owned support requests. Preserve service ownership and money invariants from M05/M06.

## Exit gate

- Customer can track shipment and delivery states from their own account.
- Cancellation, return eligibility, partial returns, inspection/restock, and refund limits are deterministic, idempotent, and audited.
- Review submission requires a delivered purchase; moderation controls publication and can resolve reports.
- Support can inspect only authorized customer/order facts; no impersonation or private-table joins.
- UI, ownership, transition, concurrency, replay, and restart checks pass; end-user guide is completed.
