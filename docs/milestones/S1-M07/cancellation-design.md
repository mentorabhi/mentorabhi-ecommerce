# M07 Unit 3 — pre-handoff cancellation design

Revision 1 · 2026-10-24 · Design before implementation

## Goal and eligibility

Customers may cancel only after checkout has captured/committed its simulated effects and before Fulfillment has claimed handoff. Orders is authoritative for customer ownership, eligibility, request identity and final order state. Fulfillment's shipment-row lock serializes cancellation claim against operator handoff. A processing checkout returns `CHECKOUT_IN_PROGRESS`; the customer may retry when checkout settles. Handoff won returns an ineligible response.

## Persisted workflow

Orders stores a cancellation operation, immutable request hash, current step, fence/lease, per-step result and audit timestamps. Steps are stable and idempotent: claim Fulfillment shipment; refund the full captured order amount in Payment; restore committed stock through Inventory's dedicated cancellation operation; finalize Fulfillment `CANCELLED`; update Orders state and append `OrderCancelled` v2 in one Orders transaction. Zero-value captures skip the zero-amount refund call but still finalize. Downstream operation UUIDs derive deterministically from the customer operation ID.

The Fulfillment claim changes only a scheduled shipment to `CANCEL_CLAIMED`, increments its revision and retains the operation identity. Operator handoff accepts only `SCHEDULED`; whichever transaction locks the row first owns the outcome. The claim remains protected while payment/stock operations run. Finalization uses its own stable idempotency key. Cancellation does not reuse return inspection/restock identities.

## Failure and recovery

The worker persists each successful API outcome before advancing. A timeout with unknown downstream result retries the same deterministic operation ID. Repeated ambiguity or an irreconcilable downstream conflict moves the workflow to visible `MANUAL_REVIEW`; it never silently releases stock or reports cancellation complete. A manual resolution is separately authenticated/audited and resumes from recorded facts. Checkout worker fencing does not supersede an accepted post-purchase claim; eligibility requires checkout Saga `COMPLETED`.

## Data and events

Order totals and currency come from the immutable Orders snapshot; Payment independently checks remaining captured funds. Inventory reads only its own committed reservation lines, emits a positive stock movement for each line once, and marks the reservation cancelled. V2 `OrderCancelled` contains operation ID, refund amount/currency and bounded reason code only. No address or user-provided prose enters the event.

## API and UI

Customer APIs are `GET /api/v1/orders/{id}/cancellation-eligibility` and `POST /api/v1/orders/{id}/cancellations` with required Idempotency-Key. Eligibility reveals a stable reason and current order revision without exposing another customer's records. UI confirmation and operation state display land in Unit 8.

## Review and limits

This is a local simulator policy, not a real payment refund or carrier guarantee. Full pre-handoff cancellation refunds the captured order total including simulated shipping. No partial cancellation is introduced. Unit 3 source and test code are authored during the development-first pass; execution waits until all Stage 1 development is complete.
