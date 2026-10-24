# S1-M07 design review

Revision 1 · 2026-10-24 · Reviewed against accepted R08/AE10, ADRs 0003–0006, and current M05/M06 ownership contracts before implementation.

## Findings and resolutions

1. **Refund arithmetic can drift if calculated from current catalog prices.** Resolved: derive from immutable captured order-line allocation and the original tax/shipping snapshot; cap cumulative refunds against captured funds.
2. **Return request and physical inspection are different facts.** Resolved: keep return eligibility/quantity in Orders and inspection/restock in Inventory; never restock on request alone.
3. **Cancellation near fulfillment handoff is a race.** Resolved: Orders claims the transition under its row lock/revision and checks Fulfillment's idempotent handoff state; uncertain external outcome becomes `MANUAL_REVIEW`.
4. **Customer-owned support text and reviews are sensitive/untrusted inputs.** Resolved: store them in their owner service, exclude from events, render as escaped text, and never treat text as authorization or tool instructions.
5. **Broad operator authentication could create customer impersonation.** Resolved: no impersonation endpoint; support reads narrow public service contracts and records actor/reason.
6. **The local simulator could be mistaken for a real provider.** Resolved: names, UI labels, test guide, and API responses explicitly identify synthetic tracking and refunds.

## Review outcome

Design is implementation-ready. Before coding each workflow, inspect existing Orders, Payment, Fulfillment, Inventory, Reviews/Support structure and integration tests. Add narrow versioned contracts and owner-side data model. Reconciliation and M09 recovery evidence must include post-purchase operations. The diagram and manual acceptance guide are part of this milestone and must evolve with implementation.
