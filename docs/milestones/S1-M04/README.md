# S1-M04 — Customer storefront and browsing

Revision 1 · 2026-10-24 · Status: design in progress; implementation not started.

Design: [storefront and customer boundary](../../../design/S1-M04/storefront.md). Editable architecture diagram: [storefront.mmd](../../../design/S1-M04/storefront.mmd).
Manual end-user checks: [manual acceptance](manual-acceptance.md).

## Scope

Customer product discovery, search, filters, sorting, product details, wishlist, cart and profile/address. Catalog, Pricing and Inventory remain authoritative. Customer-owned records belong to a separate service and are isolated by authenticated subject. Checkout, stock reservation, payment and order fulfillment are deferred to S1-M05.

## Decision needed before implementation

ADR 0003 permits any authenticated local account to administer M03. Publicly registering customers in that same API audience would give customers operator access. The design recommends a customer-scoped local identity client/token audience with ownership derived from `sub`, while preserving simple admin sign-in. The user is asked to choose self-registration, operator-provisioned customer accounts, or deferring customer accounts. No M04 implementation begins before this is resolved.

## Design review

Initial internal consistency review completed 2026-10-24: domain ownership, M05 boundary, stale price/stock behavior, cart idempotency/revision, no owner ID in APIs, personal-data handling, failure UI and manual database verification are explicit. Review surfaced the identity/audience conflict above; it remains an implementation blocker pending the user’s policy choice. This is not an independent peer-review receipt. Re-review the resolved design and token boundary before coding.

## Verification record

Not run; design-only checkpoint. Automated and manual verification will be recorded after implementation.
