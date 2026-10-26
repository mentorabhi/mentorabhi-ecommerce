# Accepted requirements
Revision 6 · 2026-10-26. User decisions override the original planning baseline. IDs are stable; append or supersede rather than silently renumber.

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
| R22 | User-requested DBeaver inspection from the host uses explicit localhost-only PostgreSQL access; private default and service database ownership remain. Existing local admin credentials may be shared directly with the user, never committed. | 2026-10-24 revision; ADR 0007; AE22 |
| R23 | Every operational UI has a documented URL and local demo login `admin` / `admin`. Storefront customer sign-in/self-registration is the exception. Internal service/database identities retain their separate credentials. | 2026-10-25 user revision; S1-M11; AE23 |
| R24 | Product pages, category cards and search results display published rating averages/counts; product pages display reviews and allow eligible customers to submit ratings/reviews. Keep existing verified-purchase ownership and moderation. Seed 3–4 explicitly labelled demo reviews per product, with integer ratings 3–5. | S1-M11; AE24 |
| R25 | Replace active fictional products and generated/illustrated product art with real branded product models, sourced photographic assets and fuller product details. Cricket and Football each have at least 100 active products and 1,000 active sellable SKUs. Product colour/size variants are distinct SKUs. Historical order snapshots remain valid. This supersedes R02/R18's generated/original product-art preference and the earlier 100-SKU fixture scale. | S1-M11; AE25 |
| R26 | Product pages include a responsive Similar Products section with clickable cards, photographs, prices, rating summaries and working keyboard/arrow navigation, informed by the user's supplied reference. | S1-M11; AE26 |
| R27 | Storefront and Admin run as separate frontend projects, containers and host URLs with different UX themes. Use Amazon India/Flipkart shopping patterns as inspiration while retaining SuperSports branding. | S1-M11; AE27 |
| R28 | Add local OpenTelemetry integration with request response-time/error metrics, distributed trace visualization and searchable application logs through open-source tooling. The user's updated requirement file reaffirms this earlier request; it supersedes ADR 0009's health-only scope for the follow-up implementation. | S1-M12; AE28 |
| R29 | Keep all storefront card photographs, especially tall pads, contained above card text on desktop/mobile. Remove the large promotional banner from storefront pages while retaining the header logo. | 2026-10-25 user revision; S1-M11 follow-up; AE29 |
| R30 | Storefront search must return relevant equipment: bat/bats excludes kits and batting accessories; ball/balls excludes football apparel. Support whole-word brand/model/sport terms and deterministic relevance before pagination. | 2026-10-25 user revision; S1-M11; AE30 |
| R31 | Audit all 50 supplied Cricket equipment families plus four maintenance families; add at least two distinct sourced equipment models for every missing family, preserve existing source/history identities, and document exact coverage. | 2026-10-26 user follow-up; S1-M13; AE31 |

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

- AE22: Explicit enablement binds only `127.0.0.1:15432` to PostgreSQL, survives ordinary profile restarts, authenticates from the native host, and can be disabled back to the private default. Credentials stay in ignored local state and the user's client/conversation.
- AE23: The access guide lists each enabled UI and its tested login. Every operational UI accepts admin/admin after restart; storefront customer credentials still work and preserve ownership isolation.
- AE24: Every active product starts with 3–4 demo-labelled published reviews, each rated 3–5. A verified delivered customer can submit a review; pending/hidden reviews do not affect public counts. Product, category and search summaries agree.
- AE25: Owner-side catalog checks show at least 100 active products/1,000 active SKUs for each sport, complete INR/USD prices, valid stock and locally served photographic assets. Variant selection changes the exact SKU in cart/checkout. Old synthetic products are absent from storefront browsing and remain usable as immutable historical order facts.
- AE26: Similar cards exclude the current/retired product, link to valid detail pages, and render consistent prices/ratings on desktop and mobile.
- AE27: Storefront localhost:3000 and Admin localhost:3002 serve separate applications/themes. Legacy /admin links redirect to the Admin origin. Direct links, customer/operator callbacks and API proxying work independently.
- AE28: A local service request produces queryable response-time/error metrics, linked trace spans and searchable structured logs. Grafana visualizes the locally stored data; credentials follow R23. Exporters do not require a hosted endpoint, and telemetry excludes credentials and personal order/address payloads. Record actual memory and retention bounds.

- AE29: Real portrait-shaped pad photos fit within their image frames without intersecting card text at desktop and 390px mobile widths. Home/category/search have no promotional banner; the header logo and product navigation remain.

- AE30: Bat/ball/pad queries return matching equipment, plurals and brand/sport combinations work, title/model hits rank ahead of description-only matches, and pagination/counts reflect the same filters.

- AE31: The 54-row curated coverage registry has supported distinct Cricket source-model identities, with at least two models per completed family, genuine reviewed local photos, realistic simulated SKU options/INR-USD prices/stock and labelled DEMO reviews. Existing catalog/history and bat/accessory search distinction remain valid.

## Non-goals and deferred choices

No real money, carrier integration, live exchange-rate feeds, marketplace sellers or cloud deployment. Multi-tenancy and multi-agent delegation are later design topics, not baseline runtime requirements. Nova's detailed autonomy, memory retention, models and numeric quality gates belong to S2.
