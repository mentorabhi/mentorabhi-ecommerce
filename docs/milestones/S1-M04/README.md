# S1-M04 — Customer storefront and browsing

Revision 2 · 2026-10-24 · Status: design reviewed; customer self-registration policy approved; implementation in progress.

Design: [storefront and customer boundary](../../../design/S1-M04/storefront.md). Editable architecture diagram: [storefront.mmd](../../../design/S1-M04/storefront.mmd).
Manual end-user checks: [manual acceptance](manual-acceptance.md).

## Scope

Customer product discovery, search, filters, sorting, product details, wishlist, cart and profile/address. Catalog, Pricing and Inventory remain authoritative. Customer-owned records belong to a separate service and are isolated by authenticated subject. Checkout, stock reservation, payment and order fulfillment are deferred to S1-M05.

## Identity decision

The user chose self-registration. ADR 0004 defines a dedicated `supersports-customers` realm and `supersports-customer-api` audience; the Customer service validates its exact issuer and audience. M03 endpoints retain the operator realm and `supersports-api`. Cross-audience tests are release gates.

## Design review

Internal review completed after the user’s decision: detected that a same-realm token mapper could grant customer registrations the broad M03 audience. Replaced that recommendation with a separate realm, exact issuer and audience validation. Added AE21 and bidirectional negative integration checks. Domain ownership, M05 boundary, stale price/stock behavior, idempotency/revisions, personal data, failure UI and manual DB verification are explicit. No unresolved design blocker remains.

## Verification record

Not run; design-only checkpoint. Automated and manual verification will be recorded after implementation.
