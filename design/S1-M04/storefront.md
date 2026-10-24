# S1-M04 — Customer storefront and browsing

Revision 1 · 2026-10-24 · Status: proposed design; customer identity boundary needs a user decision before implementation.

## Objective and scope

Deliver the customer-facing SuperSports shopping experience on top of S1-M03 Catalog, Pricing and Inventory. Customers can discover Cricket and Football products, inspect variants and current price/availability, filter and sort results, maintain a wishlist and cart, and manage a profile/address. The catalog remains extensible through M03 data, and all customer-owned data must be isolated by authenticated subject. Checkout, order creation, stock reservation, coupon redemption, payment and fulfillment remain S1-M05.

## Requirements and acceptance

Trace to R03, R05, R10, R16–R19; AE02, AE03, AE04, AE12, AE13, AE20; and the S1-M04 source baseline. The storefront is English-only, uses INR by default with the configured store currency, and defaults customer addresses to India. Currency selection changes the active price book for new views/carts; it never converts using a live rate. Historical checkout amounts are outside this milestone.

Acceptance scenarios:

1. An unauthenticated visitor can browse active products, categories, search, filter, sort, and open a detail page. Unavailable/stale search results cannot imply checkout eligibility.
2. Product pages show active currency price and a clearly labeled availability snapshot, variant attributes, description and local image with useful alt text. Inactive products and variants are not discoverable.
3. A signed-in customer can add/change/remove their own cart lines and wishlist entries. Invalid SKU/variant combinations and non-positive/excessive quantities fail safely. Repeated requests are idempotent where a stable request key is supplied.
4. Customer A cannot read or mutate B's cart, wishlist, profile or address by changing a URL, body identifier, token or browser storage. Customer identity is derived from the verified token, never from a caller-supplied owner ID.
5. Cart display uses Pricing's current amount and currency and Inventory's availability snapshot; it is explicitly a planning view, not a quote/reservation. Checkout in M05 revalidates both authorities.
6. Profile/address UI defaults country to IN; required Indian state and PIN validation have field-level accessible errors. No payment credentials are collected.
7. Responsive keyboard and screen-reader paths cover home, search/category, product, wishlist, cart, sign-in/out and profile. Browser tests verify every navigation/control and error/empty/loading state.

## Service/data ownership

- Catalog remains the authority for product/category/SKU descriptions, attributes, images and active state; storefront calls its public read contract.
- Pricing remains the authority for active currency and price book; storefront reads its contract and does not calculate promotions or persist copied prices as authority.
- Inventory remains the authority for on-hand balance; this UI may display a snapshot only. No reservation is made.
- Add an independent `customer` service project under `services/customer/` to own customer profile and Indian address records, plus wishlist and cart aggregates in its own database. The signed identity subject is the aggregate owner key. Service APIs never read other services' private tables.
- The storefront is a customer route group alongside the existing admin workspace. Customer browsing is public; personal endpoints require customer identity. Existing admin routes remain usable with the configured local admin account.
- Search starts with Catalog's existing local relational read API and indexed PostgreSQL text search for the bounded synthetic catalog. Do not introduce Redis/OpenSearch before a measured need or dedicated workload profile. Preserve a versioned search contract so a future projection can replace the implementation without changing the UI.

## Identity boundary — unresolved decision

ADR 0003 intentionally lets every authenticated local account administer merchandising. Enabling open customer registration in that same unrestricted API audience would expose catalog, pricing and inventory writes. That conflicts with customer self-service and AE04 ownership.

Recommended design: retain the local operator login for admin; add a customer-facing local identity client/flow and make service tokens distinguish the customer API audience from merchandising APIs without realm-role policy. The Customer service accepts only customer-capability tokens and derives ownership from `sub`; merchandising services continue accepting the trusted local admin audience. This is a capability boundary, not a role taxonomy. It must be proven with a negative cross-audience contract test before exposing registration. Public browsing remains anonymous.

Before implementation, decide whether (A) customer self-registration is allowed with this separate token audience (recommended), (B) customer accounts are provisioned locally by an operator, or (C) M04 is browse-only and profile/cart/wishlist remain deferred until account policy is settled. A customer token must never administer the M03 services. No implementation begins until this question is resolved.

## Interaction and failure behavior

```mermaid
sequenceDiagram
    actor C as Customer
    participant UI as Storefront
    participant ID as Local Identity
    participant CAT as Catalog
    participant PRI as Pricing
    participant INV as Inventory
    participant CS as Customer Service
    C->>UI: Browse / search
    UI->>CAT: Active product query
    CAT-->>UI: Product page (catalog revision)
    UI->>PRI: Current price + currency
    PRI-->>UI: Price book revision
    UI->>INV: Availability snapshot
    INV-->>UI: Available quantity snapshot
    C->>UI: Sign in and save cart/wishlist
    UI->>ID: Customer login
    ID-->>UI: Customer-scoped token
    UI->>CS: Mutate own aggregate (token, request key)
    CS->>CS: Verify audience; derive owner from sub
    CS-->>UI: Persisted cart/wishlist/profile revision
    Note over UI,INV: Cart values are informational; M05 checkout revalidates and reserves.
```

On Catalog/Pricing/Inventory unavailability, browsing reports a recoverable service error and avoids fabricated values. Existing cart lines remain stored; stale amounts are marked and checkout is unavailable until M05 revalidation. Customer-service mutations use optimistic aggregate revisions and deterministic idempotency keys; an ownership failure does not disclose whether another subject's identifier exists.

## UI and API shape

Customer pages: home; category/search results with filters/sort; product detail/variant selection; wishlist; cart; profile/addresses; sign-in. Preserve admin workspace routes and existing operational UI. Use shared SuperSports brand assets. Provide loading, empty, validation, service unavailable and success states. Use responsive semantic links/buttons and visible focus.

Proposed public contracts: `GET /api/v1/catalog/products`, `GET /api/v1/catalog/products/{slug}`, `GET /api/v1/pricing/active`, `GET /api/v1/pricing/products/{sku}`, `GET /api/v1/inventory/availability?sku=...`; customer-owned `GET/PUT /api/v1/customer/profile`, `GET/POST/DELETE /api/v1/customer/wishlist/items`, and `GET/PUT/DELETE /api/v1/customer/cart`. Exact paths and payloads are finalized in OpenAPI before implementation. No cart endpoint accepts an owner/customer ID. Price and quantity validation that governs purchases stays server-side in M05.

## Data and security constraints

Customer database tables: customer profile, address, cart and cart line, wishlist item. Store only subject references (not identity passwords); addresses are personal data. Normalize and bound text; validate country/state/PIN; avoid logging address or token values. Enforce ownership in every query predicate and mutation transaction. Keep cart line uniqueness per aggregate/SKU/variant; reject inactive SKU on write. Cart mutations do not touch stock or coupon usage. Do not return password/token/identity provider secrets to the UI.

## Verification plan

- Unit: search/filter/sort input validation; variant selection; address normalization/IN PIN-state validation; cart quantity/line rules; optimistic revision; idempotent mutation; subject/audience parsing and authorization; error states.
- Contract: Catalog/Pricing/Inventory response compatibility; Customer OpenAPI schema and audience/issuer requirements; no owner ID in customer mutation input.
- Integration: user A/B isolation for every aggregate; inactive/missing SKU rejection; partial dependency outage; currency switch reads matching explicit price book; DB migration and restart persistence.
- Regression: M01/M02/M03 full CI and store/admin sign-in, currency, coupon, catalog, stock behavior unchanged.
- Browser/Selenium: home/category/search/filter/sort/detail/variant, wishlist/cart/profile/address, validation and empty/error states, keyboard/mobile viewport, logout, direct-link/reload behavior; operator/admin journeys remain available.
- Manual end-user checks and read-only database queries are in `docs/milestones/S1-M04/manual-acceptance.md` before milestone review.
- Baseline search latency and memory on the 16 GB Mac; report dataset, commands, versions and limits separately from proposals.

## Rollout and constraints

All added service code remains independently deployable, with Dockerfiles/Compose/healthchecks/build pins under `devops/`. Reuse the local PostgreSQL host but create a separate Customer database/user/schema ownership. No cloud, remote search, external identity, real payment, shipping or Ollama dependency. Add any new dependency only after checking official stable release, license, ARM64 support and resource impact. Rollback disables customer routes/service while preserving M03 admin operations and database data.

## Design review checklist

- [x] Scope is separated from M05 checkout and from M03 operator maintenance.
- [x] Catalog/Pricing/Inventory remain authorities; search/cart/availability are not checkout authority.
- [x] Customer-owned data has a single service and token-subject owner key.
- [x] Failure, stale data, responsive accessibility and manual database checks are called out.
- [ ] Resolve customer account provisioning/registration and validate the capability-token boundary before implementation.
- [ ] Independent design-review receipt after user decision and diagram update.

## Change history

- Rev 1 — 2026-10-24: initial scope and design; raised the identity-collision decision before implementation.
