# M07 Unit 8 — operator and customer lifecycle integration

Revision 1 · 2026-10-24 · Design before implementation

## Goal

Close the usable customer/operator journeys for tracking, cancellation, returns, review moderation and support. Keep business authority in the owning service. Orders v2 events remain allowlisted and additive; v1 events/schema are immutable. Review/support text, customer identity details, addresses and payment instrument data never enter lifecycle events.

## UI and service contracts

- The operator storefront gets a shipment simulator. It reads one shipment through a fulfillment operator endpoint and posts the expected revision, stable operation UUID, sequential target and reason. Stale or competing transitions show a conflict and require refresh.
- Customer order detail reads authoritative tracking through the Orders owner route. Cancellation/return eligibility and progress remain owner-scoped Orders APIs.
- Customer review submission appears only for a delivered order line and enters pending moderation. Public product reads expose published reviews only.
- Customer support creates owner-scoped tickets and replies; operator support routes expose bounded ticket facts, replies and audited status transitions.
- Inventory inspection remains in its separate sellable/damaged/disputed operator queue. Restock is still independent of refund.
- Every customer/operator path is same-origin proxied by Storefront; identity realm and audience are enforced by the owning service.

## Events and recovery

The v2 compatibility parser/reconciliation work is in place. Cancellation and return/refund lifecycle events originate only after their Orders transaction commits. Fulfillment tracking remains available via the authoritative Orders-to-Fulfillment route; it is not copied into Orders' outbox until an owner-side, durable and idempotent mirror is implemented. No unsupported tracking event will be emitted.

## Acceptance artifacts

Tests cover operator revisions and transitions, customer ownership and polling, return inspection, verified review moderation, support ownership/replay, event privacy and v1/v2 history compatibility. Selenium covers shipment progression, delivered review, ticket/reply and moderation/inspection queues. The M07 manual guide and unit guides list service health, UI, database and direct ownership checks. Tests and builds remain deferred until Stage 1 development finishes.
