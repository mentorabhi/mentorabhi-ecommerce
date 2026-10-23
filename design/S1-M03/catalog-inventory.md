# S1-M03 — Catalog, pricing, inventory and fixtures

Revision 1 · 2026-10-23 · Design for review before implementation.
Origin: `requirements/accepted-requirements.md` R01, R02, R04, R07, R09, R16–R19; accepted domain ownership in `design/S1-M01/architecture.md`; historical S1-M03 proposal in `architecture/stage-1/S1-M03.excalidraw`. Decisions: `docs/decisions/0002-merchandising-stock-ownership.md`.
Product Contract unchanged. This design details implementation boundaries for already accepted behavior.

## Goal and scope

Deliver the first working merchandising and stock-management slice for SuperSports: maintain an extensible sports taxonomy and product/SKU catalog; maintain complete INR and USD price books and eligible coupon definitions; record auditable stock movements; and load a reproducible cricket/football fixture dataset. Provide a role-protected local admin UI for those tasks, with original product illustrations and SuperSports brand artwork. Keep the system useful as a teaching environment on the 16 GB Mac.

In scope: independently buildable Catalog, Pricing and Inventory services; their owned PostgreSQL databases and migrations; public API contracts; PKCE-authenticated local merchandising UI; stable fixture IDs and quantities; local product-asset references; Docker profile integration; unit, contract, integration and browser regression evidence.

Out of scope: customer storefront and public browse UX (S1-M04), cart/quote/checkout and coupon redemption holds (S1-M05), reservations and order allocation (S1-M05), Kafka/outbox/search/analytics (S1-M06+), file upload or object-store deployment, production merchandising workflows, real payments/fulfillment, tax advice, cloud resources, Nova, and changing the read-only configuration registry into a general-purpose settings editor.

## Domain boundaries

| Project | Owns | References only |
|---|---|---|
| `services/catalog` | Sports, hierarchical categories, category attribute definitions, product descriptions/status, purchasable SKU and variant attributes, public asset keys | Price and stock by opaque SKU ID |
| `services/pricing` | Currency precision registry, explicit currency price books, active store currency, coupon definitions and eligibility rules | Catalog product/SKU/category IDs through public contracts |
| `services/inventory` | Warehouse definitions, append-only stock adjustments/movements, current on-hand projection, adjustment actor/reason/idempotency key | Catalog SKU IDs through public contracts |
| `apps/storefront` | Browser admin experience, PKCE session, form and table state | APIs only; no direct database access or browser-only authorization |
| `data/pipelines/catalog-fixtures` | Versioned synthetic fixture source and deterministic IDs/values; authenticated import orchestration | Public service APIs only |

Each service has an independent Maven project, DB/user, migration stream, tests, image and API contract. The local deployment may keep using the one PostgreSQL host from S1-M02, but each service owns a distinct database. Cross-service data uses IDs and HTTP contracts; no foreign key, SQL join, or read of another service's tables. Seed operations are repeatable by stable natural keys and fixture IDs.

## Product and money model

- Sports and categories are data, not Java/TypeScript enums. A category has a stable slug, optional parent, active state and category-owned attribute definitions. Attribute definitions describe key, label, scalar type, required flag, units/options and validation bounds. A new sport/category such as Tennis can be added without a code or image rebuild.
- A product belongs to a category and has a stable slug, brand, title, description, lifecycle state and one or more SKUs. A SKU is the purchasable unit with stable SKU code, variant attribute values and its own asset key. Active products require at least one active SKU and active SKUs need a primary asset key. The API validates values against the selected category schema and rejects unknown required/typed attributes.
- Category tree edits reject cycles. A category schema revision cannot make an active product invalid: incompatible required-field/type/key changes are rejected unless affected active product records are migrated in the same Catalog transaction.
- Asset keys are relative, allowlisted paths to locally packaged SVG artwork in the storefront asset bundle. Do not accept arbitrary URLs, filesystem paths or HTML/SVG uploads. Public API responses include alt text. Direct local asset-key resolution is sufficient; an asset adapter and object storage wait until another asset source is in scope.
- Pricing is the sole runtime authority for active store currency. The S1-M02 Configuration registry's `store.currency=INR` row remains a bootstrap/default descriptor and does not drive runtime prices; there is no second mutable currency setting. INR and USD start enabled at two decimals. Prices, thresholds and coupon caps are integer minor units in their declared currency; no floating point, implicit FX conversion or mixed-currency arithmetic.
- Every SKU must have a valid positive price in both initial books (INR and USD) before its product becomes active. A store-wide currency change switches between these complete books. Product activation is the only way to add active SKUs and is gated by a Pricing completeness read; active price entries cannot be deleted, only revised. Therefore an active SKU always has both supported prices, even if product activation and currency switching happen concurrently. Adding currencies beyond INR/USD requires a later backfill-and-activate workflow. Historical quotes/orders (S1-M05) will snapshot currency and amounts; this milestone creates no orders.
- Coupons are normalized unique codes with active interval (UTC), currency, fixed or percentage discount, category/SKU include/exclude rules, minimum eligible subtotal, maximum discount and global/per-customer limits. M03 validates and stores definitions and seeds examples; atomic usage holds, redemption counters, quote calculations and checkout consumption belong to S1-M05. No coupon in M03 can charge a customer or reserve inventory.

## Inventory invariants

- One seeded local warehouse. Current on-hand is derived from the append-only movement ledger; movements carry SKU ID, signed delta, actor subject, reason, idempotency key, timestamp and source.
- Every mutation is authenticated as `inventory-operator` or `platform-admin`. Adjustment reason and idempotency key are mandatory. Repeating a key with identical request returns the original movement; reusing it with a different payload conflicts. A transaction locks the SKU/warehouse projection, rejects a result below zero, inserts the movement and updates/rebuilds the summary atomically.
- S1-M03 has no reservation state. Later reservation/ship/return commands will extend the ledger with explicit movement types and idempotent owner transitions; admin adjustment endpoints cannot impersonate those operations.

## API outline and authorization

All APIs use the existing realm and API audience. Existing test-only CLI direct-grant client remains for automated synthetic tests/fixture setup; browser login uses Authorization Code + PKCE (`S256`) with the local Keycloak public client and exact local redirect allowlist. Add the `inventory-operator` role and synthetic fixture user. Never add passwords to realm JSON. Services enforce roles and ownership at every request.

- Role matrix: `catalog-admin` and `platform-admin` may maintain taxonomy, products/SKUs, prices and coupon definitions; `inventory-operator` and `platform-admin` may adjust/inspect stock. `customer` may read public-safe active catalog/pricing data but cannot perform admin mutations. Each service enforces these roles at its own endpoints.
- Catalog read: sports/categories/attribute schemas, product pages, filters and active SKU summaries. Inventory operators can validate a SKU through a scoped Catalog read endpoint that returns only SKU ID/status; no catalog-private fields are shared.
- Catalog admin: create/update/retire sport/category/schema/product/SKU, validate category values, and preview/apply a batch import. Import applies each submitted batch atomically and returns field-level errors without partial writes. Updates require the revision read with the record; stale revisions return conflict rather than overwriting a newer edit. Each committed mutation records actor, action, entity, revision transition and timestamp in a Catalog-owned audit table. The UI shows proposed import changes and field errors before confirmation and preserves submitted values when the operator returns to edit.
- Pricing admin: list/set SKU currency prices; reject negative/malformed amounts, unsupported currencies, duplicate entries, and deletion of required SKU prices. Create/edit/activate/retire coupon definitions with overlap/range validation. Admin price changes are revisioned and audited. Catalog activation forwards the authenticated admin bearer to Pricing's completeness read; Pricing independently checks the same audience and `catalog-admin`/`platform-admin` role. Unavailable/denied checks fail product activation closed. Public read contracts expose active currency/prices/coupon presentation data needed by S1-M04; sensitive/admin fields are excluded.
- Inventory admin: list warehouses and per-SKU on-hand; append an adjustment with delta/reason/idempotency key; inspect ledger history. Before adjustment, Inventory forwards the authenticated operator bearer to Catalog's scoped SKU read and rejects an unknown/inactive SKU. No endpoint allows arbitrary absolute quantity overwrite.
- Admin browser: Catalog, Prices & Coupons, and Inventory sections. Read/write controls reflect role claims for usability, while server-side checks remain authoritative. Keep price code/currency visible together, show validation before save, display idempotent retry results, and confirm stock adjustments with prior/new quantity.
- Interaction states are explicit: initial fetch shows a labeled loading state; empty collections explain what belongs there and offer the allowed create/import action; read/write failures show a plain-language cause category, preserve unsaved form values and offer retry; successful writes show the saved identity/revision and refresh the authoritative row; 401 returns to sign-in and 403 explains missing access without retrying the forbidden action. No blank list or silent optimistic success.
- Information architecture: section navigation keeps the three operator tasks distinct; the landing view prioritizes stock warnings and pending validation before generic totals. At narrow widths (<=640 px), dense tables become labeled product/movement cards with row actions visible without horizontal scrolling, navigation collapses to an accessible menu, and forms stack to one column with touch-sized controls. From 641–1024 px, tables retain key identity/quantity/currency columns and horizontal scrolling is limited to the data region. Keyboard users can reach every action in the same logical order and screen readers receive field errors and save status.

Store APIs remain loopback-published. CORS allows only the configured local storefront origin. The browser token is never written to persistent browser storage; use the PKCE client library's memory-backed session and short-lived access token. All product/catalog read fields are public-safe; no customer PII is in this milestone.

## Fixture and visual design

`data/pipelines/catalog-fixtures` holds a small human-readable fixture manifest and a deterministic Python generator/importer. It generates stable IDs from explicit fixture keys, fixed product descriptions/attributes, integer INR/USD prices, fixed coupon rules, and fixed initial stock values. It creates the accepted demo seed: Cricket and Football taxonomies, a compact set of bats, balls, pads, gloves, footwear and training goods, both-currency pricing for every active SKU, and product/category-specific coupon examples. Re-running import updates only records marked as fixture-owned and reconciles fixture stock by the stable movement key; it does not overwrite hand-created records or multiply inventory. The UI shows additions/updates, field errors and the all-or-nothing outcome before confirmation; a failed preview retains submitted values for correction.

Create the SuperSports logo as an original local SVG and a distinct original SVG illustration for each seeded product. Use a shared palette and visual scale so illustrations read as a consistent catalog, with useful non-empty alt text. No hotlinked/stock images or remote font/CDN dependency. The admin UI uses a clear merchandising visual system; table/forms follow the responsive behavior above, are keyboard-operable and announce validation errors and save status.

## Deployment and technology

Extend the Docker Compose core with Pricing, Inventory and the admin UI, their DB roles/databases and health/readiness checks. Keep per-service resource limits and JVM heaps; set a dedicated Node build stage and small static runtime. Bind browser/API/identity ports to loopback, keep PostgreSQL private, and preserve a lighter bootstrap profile only if measurements show the added admin and services materially pressure the 16 GB host. No Redis/Kafka in this milestone.

Service implementation follows the S1-M02 Spring Boot 4.1.2 / Java 27 Maven pattern and verified image lock. For the browser, use React 19.3 and Vite 8.1 with Node 24.22.1 LTS as build runtime, exact npm lockfile and pinned ARM64-compatible image digests. React's official versions page lists 19.3 as latest; Vite's official blog lists 8.1; Node's official release page identifies 24.22.1 as latest LTS while 26.12.1 is Current (checked 2026-10-23). Recheck versions, ARM64 manifests and licenses immediately before pinning implementation images/dependencies. Sources: https://react.dev/versions, https://vite.dev/blog, https://nodejs.org/en/blog/release.

## Implementation units and verification

### U1 — Catalog domain and APIs
Files: `services/catalog/**`, `contracts/catalog/**`, catalog portions of `devops/identity/**`, `devops/compose/**` and `devops/scripts/**`.
Build taxonomy, flexible category schema, product/SKU lifecycle, read/admin APIs, product-activation check against Pricing, inventory SKU lookup, optimistic revision checks and mutation audit, import validation and migrations. Keep requests/repositories scoped to Catalog DB. Add unit tests for category tree/cycle constraints and schema evolution against active products, slug constraints, typed attributes, variant uniqueness, state transitions, stale-revision conflicts, audit actor/revision fields, import all-or-nothing behavior, roles, and API mapping. Contract tests validate request/response examples and reject unknown fields/types. Live tests prove customer/admin role boundaries and that new sports/categories need no deployment.

### U2 — Pricing, currency and coupon definitions
Files: `services/pricing/**`, `contracts/pricing/**`, pricing resources in `devops/**`.
Add money/currency types, versioned price books, audited updates, an authenticated completeness read for Catalog product activation, and the single runtime active-currency setting. Seed both INR/USD for every active SKU. Unit tests cover integer precision, currency mismatch, negative/zero rules, required-price deletion rejection, switch/revision behavior, half-open UTC time windows, percentage/fixed caps, eligible category/SKU resolution and per-currency minimums. Tests explicitly prove M03 definitions do not consume coupon limits; redemption concurrency is deferred to M05. Contract/integration tests verify old revision reads remain stable and failed currency activation changes nothing.

### U3 — Inventory ledger and operator API
Files: `services/inventory/**`, `contracts/inventory/**`, inventory resources in `devops/**`.
Add warehouse/on-hand model, append-only movements, idempotent adjustment service and operator APIs. Unit tests cover negative stock rejection, exact replay vs changed payload conflict, concurrent last-units adjustments, actor/reason audit and aggregate reconciliation. Live tests use the real DB to prove concurrent writes never produce negative stock and catalog customers/platform roles without inventory role cannot adjust stock.

### U4 — Deterministic fixture pipeline and product artwork
Files: `data/pipelines/catalog-fixtures/**`, `apps/storefront/public/**`, devops seed orchestration.
Implement stable source manifest and API importer for taxonomy/product/SKU/prices/coupon definitions/stock. Verify generated manifest and IDs byte-identical on repeated runs, import idempotent, fixture stock reconciles, non-fixture products are untouched, every active SKU has INR/USD price and valid local artwork/alt text. Add fixture-specific unit and end-to-end smoke tests.

### U5 — Admin UI and local integration
Files: `apps/storefront/**`, `devops/docker/**`, `devops/compose/**`, realm/lock updates and cross-service `devops/tests/**`.
Build responsive PKCE login and Catalog / Prices & Coupons / Inventory screens, role-aware navigation, accessible forms/tables and local SVG logo/art. Implement the specified loading, empty, failure, success, 401 and 403 states. At <=640 px, verify labeled card layouts expose every row action without horizontal scrolling; verify keyboard/touch completion of each primary task. Verify build/lint/unit, accessibility semantics, Playwright browser flows at desktop/mobile widths, auth expiry/re-login, full-stack smoke and actual combined RSS under the 16 GB allocation. Preserve the app/profile's S1-M02 recovery and release gates.

### Dependencies, order and milestone exit
U1 public API/domain contract precedes U2/U3 integration. U4 can build its schema and fixed content in parallel but importer depends on all APIs. U5 uses completed contracts and fixture content. Implement in this order: U1, U2/U3, U4, U5, then full regressions. Keep all service DB migrations additive; reset integration fixtures only within the named local project. No cross-service database queries.

S1-M03 is done when a clean local setup starts all services, deterministically imports/updates seed data, demonstrates responsive authenticated admin maintenance, switches to USD only with a complete book and back to INR, records auditable safe inventory adjustments, displays product artwork, passes required test layers, and records actual memory/RSS and limitations. It does not claim customer shopping, reservation, checkout, coupon redemption or storefront acceptance.

## Risks and deferred decisions

- S1-M02 identity client roles/direct grants may need realm changes for the new inventory role and PKCE browser login; browser must not use fixture passwords in its grant. Configuration's existing `store.currency` registry row must not be mistaken for a second active-currency authority.
- Spring Boot 4/JDK 27 and newest React/Vite/Node combinations must be verified by builds, tests and multi-platform manifests. If a security patch or dependency fails compatibility, select the newest supported compatible release and record the deviation.
- Asset upload and object storage are deliberately deferred; local SVG bundle references satisfy repeatable demos without another daemon.
- The 16 GB physical Mac has a Docker allocation of about 7.75 GiB. Current M02 RSS is ~1.15 GiB; this is not a bound for added services/browser builds. Measure M03 with concurrent compile/load, set limits, and support larger self-hosted profiles without claiming capacity until measured.
- Coupon redemption/usage-limit concurrency and stock reservation are not M03 behaviors. M05 must consume these definitions atomically.
- Admin UI is a merchandising tool, not the customer-facing S1-M04 storefront. Design system and brand artwork can be reused, but customer journeys stay in their milestone.
