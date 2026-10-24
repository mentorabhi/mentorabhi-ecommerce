# S1-M04 — Customer storefront and browsing

Revision 4 · 2026-10-24 · Implementation and automated verification complete; owner manual acceptance remains open.

Design: [storefront and customer boundary](../../../design/S1-M04/storefront.md). Editable architecture diagram: [storefront.mmd](../../../design/S1-M04/storefront.mmd).
Manual end-user checks: [manual acceptance](manual-acceptance.md).
Automated/runtime evidence: [verification record](verification.md).

## Scope delivered

Customer product discovery, category-aware search, category navigation, sorting, product details, currency-specific price snapshots, inventory snapshots, self-service account registration/sign-in, wishlist, cart and Indian profile/address. Catalog, Pricing and Inventory remain authoritative. Customer-owned records belong to a separate service and are isolated by authenticated subject. Checkout, stock reservation, payment and order fulfillment remain S1-M05 scope.

## Identity and ownership

The user chose self-registration. ADR 0004 uses the dedicated `supersports-customers` realm, `supersports-customer-web` public PKCE client and `supersports-customer-api` audience. Customer validates that exact issuer and audience. M03 APIs retain the operator realm and `supersports-api`. Customer records are keyed only from verified token subject; request bodies and paths cannot select an owner.

## Design review

The initial same-realm recommendation was replaced before implementation after review identified that customer registrations could inherit the broad M03 API audience. The separate realm, exact issuer/audience and bidirectional negative checks resolve that boundary. Domain ownership, the M05 boundary, stale price/stock labels, revisions, personal-data handling, failure UI and manual DB verification are covered in the design and ADR. No design blocker remains.

## Verification

See [verification record](verification.md) for exact commands and outcomes. The full local Docker profile, all service unit builds, live integration tests before and after recovery, recovery tests, Selenium journeys, Playwright checks and read-only DB aggregate query passed. The end-user checklist remains unchecked for the owner to perform in a normal browser. No production-scale load or peak-memory claim is made.
