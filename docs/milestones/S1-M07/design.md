# S1-M07 design — Post-purchase lifecycle

Revision 1 · 2026-10-24 · Reviewed before implementation.

## Goal and boundaries

Implement accepted requirement R08 on top of the M05 persisted order Saga and M06 event stream. Orders remains authoritative for order state and customer ownership. Fulfillment remains authoritative for shipment and delivery simulation. Payment remains authoritative for captures and refunds. Inventory remains authoritative for returned stock. Reviews and Support each own their own records and database. No real carrier, payment/refund provider, or customer impersonation is introduced.

## State and ownership

| Capability | Owner | Contract |
|---|---|---|
| Cancellation eligibility and order transition | Orders | Customer token subject; only before fulfillment handoff; idempotency key and immutable order terms |
| Shipment/tracking simulation | Fulfillment | Stable shipment ID; queued → in transit → delivered; deterministic local milestones |
| Return request and decision | Orders | Delivered line quantities; cumulative return quantity cannot exceed purchased quantity |
| Refund | Payment | Cumulative refund cannot exceed captured amount minus prior refunds; stable operation ID |
| Returned-item inspection/restock | Inventory | Explicit accepted/rejected condition and reason; restock only after accepted inspection |
| Review | Reviews | Verified delivered order line; one review per customer/order line; edit/delete policy recorded |
| Moderation/report | Reviews | Pending → published/rejected/hidden; append-only moderation audit |
| Support request | Support | Customer owns ticket; staff reads minimum order facts via public APIs; no impersonation |

Order, payment, fulfillment, inventory, review, and support records are changed only through their owning APIs. Cross-service operations use persisted Orders workflow steps with stable operation IDs and outbox events. No direct cross-service database reads are allowed.

## Workflows and invariants

1. Tracking reads the customer-owned Order projection and a shipment summary. A tracking link is local and synthetic; no external carrier network call occurs.
2. Cancellation claims a customer-scoped idempotency key and snapshots the current revision. Orders accepts only before shipment handoff. It coordinates payment void/refund and reservation release with persisted steps; uncertain outcomes enter visible `MANUAL_REVIEW` instead of releasing twice.
3. Return request specifies order line and positive quantity. Eligibility requires delivered state and the configured local return window. Concurrent requests lock/claim available returnable quantity so accepted quantities cannot exceed purchased quantity.
4. Inspection is a separate inventory decision per returned unit. Accepted units can restock once; rejected units never restock. Refund amount derives from immutable captured line allocation, tax and shipping policy snapshots; cumulative refunds cannot exceed captured amount. Every step is idempotent and auditable.
5. Review submission is accepted only for the authenticated customer and a delivered order line. Content is pending moderation by default. Moderation actions retain actor, reason, prior/new state, and timestamp. Public catalog output includes only published reviews and aggregate statistics.
6. Support tickets are customer-owned. Support lookup uses narrowly scoped public Orders/History APIs. Staff cannot impersonate a customer; access and state changes are audited.

## API and UI

Customer pages: order tracking/detail, cancel request where eligible, return request per line, review submission, and support ticket list/detail. Admin workspace: shipment simulator controls, return inspection, review moderation/report queue, and support queue. Customer API derives ownership from verified token subject and rejects owner override query/body fields. Operator API uses the existing local operator realm. Service-to-service work uses dedicated audiences and scopes rather than the broad operator audience.

Add versioned endpoints under the owning service APIs. Use explicit `409` for stale revisions, exhausted quantities, conflicting idempotency payloads, and invalid transitions; `422` for policy ineligibility; and stable operation IDs for retries. Do not expose internal exception messages.

## Data and events

Persist return request/line quantities, inspection decisions, refund operations, review/moderation history, support ticket ownership, and simulator tracking milestones. Add versioned contracts to `contracts/` before publishing event types. Events contain opaque customer keys and order IDs only; omit addresses, free-form support text, review text, tokens, and payment details. Review/support content is retrieved from its owner API under authorization.

## Failure behavior and test matrix

Prove concurrent final-unit return requests cannot over-return; refund cap under concurrent retries; crash/restart between every cross-service workflow boundary; same operation ID/same payload returns original result; changed payload conflicts; duplicate events do not duplicate refunds/restocks/reviews; stale worker fencing; ownership isolation on UI and direct APIs; moderation audit completeness; unsupported transitions; delivery simulator progression; database-owner access checks.

## Manual acceptance and limits

Manual steps are in `manual-acceptance.md`. The guide must check service health, customer/admin UI, owned state in each owning database using read-only owner credentials, and leave a dated result record. Simulated tracking does not represent carrier delivery; return/refund policies are local examples, not a real payment integration.
