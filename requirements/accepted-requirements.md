# Accepted requirements
Revision 2 · 2026-10-23. User decisions override the original planning baseline. IDs are stable; append or supersede rather than silently renumber.

| ID | Requirement | Delivery / acceptance |
|---|---|---|
| R01 | SuperSports is a single-retailer store initially covering Cricket and Football; add sports/categories without source-code enums. | S1-M03; AE01 |
| R02 | Realistic synthetic products, variants, descriptions, images, prices, customers and reconciled stock. Deterministic seed/reset. | S1-M03; AE01 |
| R03 | English; default country IN and Indian address validation; configurable supported countries later. | S1-M04; AE02 |
| R04 | INR default; configurable currencies including USD, explicit supported precision, currency-consistent totals and immutable historical amounts. | S1-M03/M05; AE03 |
| R05 | Browse, product pages, filters, search, wishlist, isolated customer carts/profile with customer self-registration. | S1-M04; AE04, AE21 |
| R06 | Idempotent checkout; stock reservation; simulated authorization, capture, fulfillment, tax and shipping. | S1-M05; AE05–AE08 |
| R07 | Coupons with product/category eligibility, dates, minimum spend, currency rules, usage limits and deterministic rounding. | S1-M03/M05; AE09 |
| R08 | Tracking, cancellation, return/refund simulations, verified-purchase reviews, moderation and support. | S1-M07; AE10 |
| R09 | Catalog, pricing and inventory administration with simple local sign-in; all authenticated local accounts can administer. Role enforcement superseded by ADR 0003 at the user's request. | S1-M03; AE11 |
| R10 | Categorized configuration administration: commerce/localization, simulations, storage, search/cache, messaging/workflows, identity, observability, Nova. | S1-M02 foundation; S1-M04 UI; AE12 |
| R11 | Monorepo with independent microservice projects and devops as the sole infrastructure project. | S1-M02; AE13 |
| R12 | Dockerized application/dependencies except existing host Ollama, ARM64-compatible local profiles on a 16 GB Mac and larger-machine deployment path; Kubernetes, Helm, Terraform and repeatable scripts. | S1-M02/M09; AE13 |
| R13 | Local services only; no cloud services or hosted AI. Provisioning must not contact a cloud provider. Downloads needed for setup are distinct from runtime dependencies. | S1-M02 onward; AE13/AE16 |
| R14 | PostgreSQL transactional authority, service ownership, Saga, outbox/CDC/Kafka and CQRS; Redis, search, graph, lakehouse and reporting each need explicit ownership and purpose. | S1-M05/M06/M08; AE08/AE14/AE15 |
| R15 | Nova uses the existing host-installed Ollama only (no Ollama container) and local lightweight open-source models; includes prompting, LangChain, orchestration, RAG, MCP, semantics, memory, context/loop engineering, guardrails, human approval, evaluation, caching and observability. | S2 design; S3 implementation; AE16–AE19 |
| R16 | Unit tests for every feature; integration, contract, regression, E2E and risk-specific tests; CI/CD, reproducible evidence and Git checkpoints. | Every implementation milestone |
| R17 | Design documents and editable diagrams reviewed before implementation; context, ADRs, revisions, lessons and guided execution maintained. | Every milestone |
| R18 | Logo, modern responsive pages and original product imagery; realistic synthetic prices/descriptions, accessibility and mobile verification. | S1-M03 assets; S1-M04 UI; AE20 |
| R19 | Latest stable compatible technology versions verified when implemented; exact pins and license/ARM64/resource checks recorded. | S1-M02 and each dependency addition |
| R20 | Progress through commerce, Nova design, and gap-led integration in that order. | Stage gates |
| R21 | Customer self-registration uses a local customer identity realm/API audience isolated from unrestricted merchandising administration. | S1-M04; AE21 |

## Actors and initial journeys
Customer: browse → compare → cart → quote → approve purchase → track → review/return.
Catalog administrator: maintain sports/categories/SKUs/assets and price books; import validated records.
Inventory operator: stock adjustment with reason and audit; inspect returned goods.
Support: investigate authorized orders and support tickets; no unrestricted customer impersonation.
Platform administrator: view/edit permitted configuration; validate and activate changes.
Nova: delegated caller scoped to a signed-in actor, never a privileged bypass.

## Acceptance examples
- AE01: Add Tennis using category/attribute data; existing Cricket/Football SKUs remain valid; identical seed produces identical fixture IDs and quantities.
- AE02: IN defaults in address entry. Missing PIN/state fails validation; customer A cannot read customer B's address.
- AE03: INR quote uses an INR price book; switching store currency to USD requires complete active SKU pricing. An existing INR order still displays/refunds INR. Mixed-currency totals are rejected.
- AE04: Customer B cannot mutate A's cart; search lag does not bypass live checkout validation.
- AE05: Two buyers request the final unit; exactly one reservation succeeds, available stock never becomes negative.
- AE06: Retrying a checkout key with identical payload returns its original result; changed payload conflicts.
- AE07: Payment declines after reservation; release stock, record explicit failed outcome, permit safe retry with a new key.
- AE08: Worker restart resumes persisted Saga; retries do not duplicate capture/shipments. Failed compensation becomes visible manual resolution.
- AE09: An expired, ineligible, wrong-currency or exhausted coupon fails; competing requests for the last redemption cannot both consume it.
- AE10: Owned delivered line supports a partial return; refund never exceeds captured amount less previous refunds; inspection governs restock independently.
- AE11: Anonymous callers cannot update catalog, prices or stock. Every authenticated local account can administer without role assignments. Stock changes retain actor/reason. Customer ownership and Nova approval rules remain required (ADR 0003).
- AE12: Platform admin changes tax simulation rate; new quotes use the activated revision and old orders retain their snapshot. Invalid adapter settings cannot activate; passwords are never returned to the browser.
- AE13: Clean checkout starts a documented core Docker profile without cloud credentials; local Kubernetes is a separate deployment exercise, not simultaneous duplicate infrastructure.
- AE14: Duplicate/late events and a restarted consumer do not inflate sales; search/order projections rebuild and reconcile.
- AE15: Graph compatibility queries return curated relationships; lakehouse sales/refund totals reconcile after replay.
- AE16: Nova uses only configured local endpoints; unsupported/unavailable models produce an explicit degraded state, no hosted fallback.
- AE17: Nova cites product/policy evidence and checks live price/stock; malicious review content cannot grant tools.
- AE18: Checkout requires approval bound to user, line items, price/currency, address, quote revision and expiry. Changed terms require new approval; replay cannot duplicate purchase.
- AE19: Preference correction/deletion applies across memory and applicable caches; another user's data cannot be retrieved.
- AE20: Keyboard and mobile navigation work across home, category/search, product, cart, checkout, account/order and admin screens. Assets have alt text and provenance.
- AE21: A self-registered customer can sign in and access only their profile/cart/wishlist; their token cannot read or mutate Catalog, Pricing, Inventory or Configuration. The operator token cannot read customer-owned data. Both isolation directions hold after restart and direct API calls; the owner is always taken from the verified token subject.

## Non-goals and deferred choices
No real money, carrier integration, live exchange-rate feeds, marketplace sellers or cloud deployment. Multi-tenancy and multi-agent delegation are later design topics, not baseline runtime requirements. Nova's detailed autonomy, memory retention, models and numeric quality gates belong to S2.
