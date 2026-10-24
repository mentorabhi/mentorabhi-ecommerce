# Revision history
Append dated entries with reason, changed artifacts, evidence and remaining work.

## 2026-10-24 — Stage branch and milestone push policy

The user specified that every milestone checkpoint must be committed and pushed, and that every stage starts on a branch named for the stage. Recorded this in AGENTS.md and project context. Added `origin` for `https://github.com/mentorabhi/mentorabhi-ecommerce.git`; pushed `feat/s1-m05-checkout-orders` at `21dac40`, then created and pushed `stage1` at the same commit. Future milestone commits must push the active stage branch; do not force-push or overwrite remote history.

## 2026-10-23 — Revision 1, S1-M01 draft
Captured the original requirements and Google planning baseline plus all subsequent user decisions.
Added accepted requirements, actor/acceptance examples, baseline architecture, local-first ADR, testing strategy and traceability.
Preserved original architecture proposals; new S1-M01 design overrides cloud/hosted-model suggestions and introduces currency/coupon/configuration policies.
Design review and structural validation pending. No application implementation or runtime verification yet.

## 2026-10-23 — Revision 2, reviewed design and Python environment
Seven session review lenses completed. Corrected the checkout sequence so unknown payment outcomes reconcile before releasing reservations/coupon holds.
Created .venv, verified Python 3.14.7 and pip 26.2.1; all subsequent Python execution uses .venv/bin/python. The initial system-default 3.9 environment was recreated with the installed modern interpreter.
Added persistent AGENTS.md, root entry point, devops ownership guide and .gitignore. Initialized local Git on docs/s1-m01.
Added editable S1-M01 ownership Excalidraw and SVG companions; preserved all 23 original diagram pairs.
Runtime service/test implementation remains S1-M02 onward. Final structural checks pending.

## 2026-10-23 — Verification checkpoint
Documentation links, requirements/acceptance traceability, diagram JSON/SVG, payment-reconciliation wording and ignore patterns checked successfully. Reproduction commands and limitations are recorded in S1-M01.
Design baseline is reviewed; rendered diagram inspection and tagged Git checkpoint are not claimed complete. No runnable service or application test exists yet. Next milestone is S1-M02 bootstrap.

## 2026-10-23 — Host-only Ollama clarification
User explicitly requires the existing host-installed Ollama, with no Ollama container. This supersedes the portable container fallback proposed earlier. Updated active requirements, context, working guidance and design. Bootstrap starts only PostgreSQL, identity and commerce foundations; Nova remains later-stage work.

## 2026-10-23 — S1-M02 implementation and verification
Added independently buildable Catalog and Configuration services, pinned ARM64 Docker core, local Keycloak/PostgreSQL, private generated credentials, operational/recovery/release scripts, Helm/Terraform/kind teaching artifacts and the Nova-native-Ollama prerequisite. Measured the running core at 1,180.28 MiB combined container RSS in one snapshot; this is not a peak or future full-commerce benchmark.
The full `devops/scripts/ci` run passed; follow-up review-driven coverage passed with 16 Python unit tests and 12 real-stack integration tests (18 Java tests also passed in each service image build). Recovery, exact-image rollback, scoped reset, Helm/Terraform checks passed. No Kubernetes cluster, cloud provisioning, security scan or SBOM was run.
Eight code-review lenses returned; reliability and adversarial lenses hit the session usage limit. Recorded findings were fixed and retested. Signed expired/wrong-issuer JWT negative tests remain a follow-up gap; review completion is partial, not represented as a full review receipt.
Checkpointed locally as `s1-m02-bootstrap` (`cf50e8e`); next milestone is S1-M03 catalog/inventory.

## 2026-10-23 — S1-M03 design reviewed
Added the Catalog/Pricing/Inventory implementation contract, editable Excalidraw architecture and preview, milestone evidence page, and ADR 0002. Two design-review passes resolved price-completeness concurrency, currency ownership, admin role/revision/audit rules, asset scope and admin interaction-state findings. Cross-model review was skipped under the repository rule against external model CLIs. No S1-M03 implementation or runtime test is claimed yet.

## 2026-10-23 — S1-M03 implementation started

Created independently buildable Catalog, Pricing and Inventory Spring projects with separate PostgreSQL migrations, role-protected APIs and published OpenAPI contracts. Added the initial React admin workspace, local image assets, a deterministic Cricket/Football fixture manifest/importer, and Compose integration including the local Keycloak inventory role upgrade and safe existing-database provisioning. Updated local credential extension and release tracking to include S1-M03 applications. Build and runtime verification is in progress; no S1-M03 end-to-end acceptance is claimed.

The live Keycloak 26.8.1 profile initially omitted JWT `sub` on existing CLI clients because their configured default scopes excluded `basic`; this caused null audit actors. Updated fresh realm defaults and idempotent upgrade provisioning to attach `basic` to the two CLI clients and browser client. The fix follows the Keycloak upgrade guide's Subject mapper/client-scope behavior.

## 2026-10-23 — S1-M03 implementation verification

Built and ran the full local Compose profile, then imported the deterministic six-product/two-coupon dataset twice to verify idempotent fixture behavior. Updated the live integration suite for the four APIs, Catalog schema v2, service database isolation, new auth boundaries, fixtures and stock idempotency. All 15 integration tests, 17 Python operations tests and 21 Java tests passed. The complete `devops/scripts/ci` run passed, including Helm lint/render, Terraform validation/native tests, application recovery and PostgreSQL outage/reconnection. The Dockerized Node 24 storefront build and local HTTP health checks passed. A single RSS snapshot measured 1,816.4 MiB across seven containers with 7.75 GiB allocated; it is not a peak benchmark. Visual browser review could not run because browser automation was unavailable. Updated M03 milestone evidence, project status and traceability accordingly.

## 2026-10-23 — Post-login blank page and milestone manual checklists

Headless Chromium reproduced React minified error #310 after successful PKCE login. The app conditionally returned before reaching a later `useEffect`, so signing in changed the component's hook count and React unmounted the workspace before API calls. Moved the screen-selection hook above conditional returns and guarded its empty-role state. The new Playwright test failed before the fix with error #310 and passed afterward, with Catalog fixture data visible and no browser errors. Added a milestone evidence convention requiring a separate end-user manual acceptance document for every milestone, and backfilled manual guides for S1-M01, S1-M02 and S1-M03.

## 2026-10-23 — Selenium UI coverage and clickable admin controls

Added a Python Selenium 4.51.0 suite using host Chrome/Selenium Manager and a `ui-test` operations command. Three authenticated journeys exercise Catalog assets/filtering/product activation, currency switching/coupon creation, and stock adjustment replay/reversal. Wired the suite into `devops/scripts/ci`; documented local setup, stable synthetic records and manual DB expectations. Browser testing exposed an omitted Pricing `expectedRevision`, an interrupted draft recovery path, and decorative category filters/inert card menu controls. Added revision-aware price upserts, functional data-driven category filters, removed inert controls, and anchored the brand link. Role-aware browser checks found Nginx had not forwarded the bearer header to service proxies; explicit forwarding restored Pricing reads/writes and the combined workspace refresh. Added safe error dispatch handling so Pricing failures retain their original HTTP status. Full CI passed (including recovery, live integration and Selenium); the Playwright login regression passed separately after the proxy fix.

## 2026-10-23 — Simple local authentication and milestone Git policy

The user removed the requirement for administrative authorization roles. Recorded ADR 0003, updated R09/AE11 and the M03 design before implementation, and added an editable authentication flow. All signed-in local accounts now access every admin section and the Configuration read API. Signature/issuer/audience/expiry validation and actor audit remain; customer ownership and Nova approvals remain later-stage requirements. Replaced obsolete role converters with 20 security filter-chain tests across the four services and updated live/Selenium checks for ordinary customer access. Verification: 29 Java tests, 17 Python operations tests, 15 live integration checks and recovery passed. CI caught an old Selenium helper argument list; corrected it and reran all three Selenium journeys successfully. The final code-review attempt was skipped because the local review agent hit its usage limit; this limitation is recorded explicitly in M03 evidence. User manual checks are documented separately.

Recorded the user's Git policy: commit each milestone on the active branch; create a new branch after each stage; continue without routine approval. No remote publication was requested.

## 2026-10-24 — Requested local login, supplied artwork and mobile access

The user set the demo username/password to `admin`/`admin` and supplied the final icon and banner. Added the local account via Keycloak provisioning using an ignored mode-0600 password file, and used the two source JPEGs directly for branding and sign-in. Selenium exposed that mobile CSS hid the only sign-out control; moved it into the top bar and added mobile navigation/logout coverage. Mobile table labels now come from each cell's data, so inventory cards identify warehouse, on-hand, revision and health correctly. The independent review agent stopped at its session usage limit; code review status remains incomplete until fallback review is recorded.

The final full-stack run found that `docker compose up --build` rebuilt the same image tags but left existing containers on their previous image IDs. `supersports up` now requests `--force-recreate`, and its operations unit suite asserts this behavior. A fresh token then received HTTP 200 from direct and proxied Pricing endpoints. The final `devops/scripts/ci` run passed: 20 Python operations tests, 29 Java tests, 15 live integration tests, Helm/Terraform checks, service/DB outage recovery and four Selenium journeys. Playwright login passed separately. The full banner was visually checked in Chromium at desktop size. The independent review agent stopped at the session usage limit; recorded code review state: `Code review: skipped (ce-code-review unavailable)`. Owner manual acceptance and peak/load memory checks remain pending.

## 2026-10-24 — S1-M05 checkout admission and storefront

Implemented internal Catalog SKU facts, Configuration checkout reads, Pricing quote/coupon holds, and Inventory reservation APIs using the narrow checkout-worker identity. Orders now claims idempotency before mutable reads, validates and snapshots the customer's Indian address, catalog provenance, quote and simulation settings, and creates order lines, initial Saga and outbox atomically. Added owner-scoped order listing/detail API and checkout/order-detail UI. Selenium surfaced and fixed an Orders root-route proxy redirect; API and Selenium regressions cover it. Added price/currency revision checks and customer-bound coupon hold replay. Configuration V3 adds revision-checked edits and actor audit; the categorized operator UI supports checkout tax/shipping/reservation/payment simulation settings. Verification: 23 Python unit tests, 71 Java unit tests, 20 real-stack integration tests and six Selenium journeys passed. One current nine-container RSS snapshot was 2,494 MiB with 7.75 GiB Docker allocation; this is not peak evidence. Orders remain `PENDING_PAYMENT`. Payment/Fulfillment simulators, Saga worker, recovery/failure tests and owner manual acceptance remain open. See `docs/milestones/S1-M05/verification.md`.
## 2026-10-24 — S1-M04 initial design checkpoint

- Created customer storefront design and editable Mermaid architecture; separated browse/cart informational values from M05 checkout authority.
- Added M04 manual acceptance draft, including service health, UI flows, cross-customer isolation and read-only database checks.
- Branch `feat/s1-m04-customer-storefront` starts from the committed M03 checkpoint.
- Implementation was intentionally held pending customer identity policy because ADR 0003 allows all authenticated local accounts to administer M03 APIs.

## 2026-10-24 — S1-M04 design checkpoint

Created the customer storefront design and editable Mermaid architecture; separated browse/cart informational values from M05 checkout authority. Added the M04 manual acceptance draft and updated requirement traceability and current project context. Branch `feat/s1-m04-customer-storefront` starts from the committed M03 checkpoint. Implementation was held for customer identity policy.

## 2026-10-24 — S1-M04 self-registration decision

The user selected customer self-registration. Design review found that same-realm audience mapping could expose M03 administration; tightened the design to a dedicated `supersports-customers` realm, exact issuer and customer-only API audience. Added ADR 0004, R21/AE21, bidirectional token-isolation checks and the manual acceptance path. Design revision 2 is ready for implementation.

## 2026-10-24 — S1-M04 implementation and verification

Implemented the customer-owned profile, Indian address, cart and wishlist service with a dedicated self-registration realm; public storefront discovery uses Catalog/Pricing/Inventory snapshots. Added responsive React storefront and supplied brand assets, category/search/product flows, Playwright and Selenium coverage, Customer database provisioning, contracts and Nginx API routing. Browser review fixes cover category slug deep links, search from non-shop pages, and additive cart quantity (maximum 99).

Final verification: 22 Python tests, 36 Java tests across five services, Helm/Terraform/Compose validation, 17 live integration tests both before and after recovery, four recovery assertions and five Selenium journeys passed. Three Playwright tests and frontend build passed separately. A read-only Customer DB aggregate reported migration 1 successful, 12 profiles, six cart owners/six items and seven wishlist owners/seven items. One eight-container RSS sample was 2,112.6 MiB with 7.75 GiB Docker allocation; this is not peak/load evidence. Owner manual acceptance remains pending. Storefront is available at `http://localhost:3000`; operator UI at `http://localhost:3000/admin`. No Nova behavior is claimed. Next milestone is S1-M05 after the M04 Git checkpoint.

## 2026-10-24 — S1-M05 checkout design reviewed

Created M05 checkout design, editable Mermaid flow, manual end-user checklist and ADR 0005 on `feat/s1-m05-checkout-orders`, branched from the clean M04 checkpoint `cf8de79`. Independent session reviewers identified missing inventory/coupon finalization, stale-worker fencing, internal route/audience separation, address availability after restart, quote revision binding, Catalog provenance for category coupons, early idempotency claims and payment status reconciliation. Resolved all findings, updated the diagram, and obtained final reviewer confirmation that no design blocker remains. The design uses an Orders-owned persisted Saga, service-owned resource holds and simulator ledgers, a synchronous customer address snapshot before asynchronous work, and a dedicated checkout-worker identity. Temporal is deferred pending workload evidence; official PostgreSQL persistence docs and the maintained sample were reviewed. Resource acceptance requires future startup/concurrency/peak measurement against Docker's 7.75 GiB allocation.

## 2026-10-24 — S1-M05 implementation in progress

Added deterministic Inventory reservation arithmetic tests and Pricing coupon arithmetic tests; Pricing coupon percentage rounding is half-up and allocation uses largest remainder with SKU UUID tie-breaking. Added Inventory V2 reservation tables, service-scoped checkout reservation routes and transactional reserve/protect/commit/release operations with deterministic SKU lock ordering and order-key advisory locking. Dockerized Java verification passed for Inventory (12 tests) and Pricing (11 tests); no live M05 service/migration or checkout integration is yet verified. The checkout Saga, coupon persistence/holds, payment/fulfillment simulators, configuration UI, customer checkout UI, deployment wiring and milestone acceptance remain to implement.

Added the initial Orders Spring service, customer-realm protected owner-scoped endpoints, V1 schema for checkout idempotency/order snapshots/Saga/outbox, canonical cart normalization and SHA-256 request fingerprinting. Dockerized Orders verification passed (3 unit tests). The claim endpoint currently records/replays the validating request; quote validation, address snapshotting, saga execution and service deployment wiring remain outstanding.

Extended the local Compose profile, PostgreSQL provisioning and storefront proxy for Orders. Added a dedicated local test-only customer client and two synthetic users so integration tests use the customer issuer and can verify cross-customer 404 isolation without enabling password grants on the storefront client. Added Catalog's internal checkout SKU facts endpoint with exact worker audience/client/scope enforcement. Full current profile startup succeeded with 9 healthy containers; Orders Flyway V1 succeeded. The 23 Python operations tests, 63 Java tests and 18 real-stack integration tests passed. A read-only aggregate found five idempotency claims (five distinct keys), all intentionally `VALIDATING`; one RSS snapshot was 2,386.9 MiB of the 7.75 GiB Docker allocation. Checkout quoting, reservations integrated with Orders, Saga worker, payment/fulfillment, settings UI, customer checkout UI, Selenium, recovery, and peak/load measurements remain incomplete. Evidence: `docs/milestones/S1-M05/verification.md`.

## 2026-10-24 — S1-M05 checkout Saga and simulators verified

Completed the persisted Orders Saga through simulated payment authorization/capture and local fulfillment scheduling; added separate Payment and Fulfillment projects/databases, worker fencing and restart recovery, decline compensation, customer order status polling, and payment simulation controls in categorized Configuration. Expanded Compose to 11 healthy containers. Verification passed 23 Python tests, 66 Java tests, 22 live integration tests and six Selenium journeys. Full-stack checks recovered persisted orders; a newly identified legacy case with expired quote snapshots now fails before inventory reservation and writes its terminal Saga/outbox outcome. Post-run read-only database state: 10 fulfilled orders, 13 failed test orders (declines and expired quotes), zero pending orders. Measured prior short-run idle RSS was about 3,195 MiB; not peak evidence. Owner manual acceptance, deeper fault injection, audited manual-review resolution and concurrency/resource measurement remain open. See `docs/milestones/S1-M05/verification.md` and [manual checks](../milestones/S1-M05/manual-acceptance.md).

## 2026-10-24 — S1-M06 design reviewed

Started M06 design after committing M05 as `af6f7d6`. Added an editable event-flow diagram, separate manual acceptance guide and design review record. Two local reviewer passes identified and resolved legacy outbox backfill/sequence seeding, snapshot/WAL overlap, consumer/DLQ crash boundaries, per-order gap handling, replay audit, projection rebuild cutover, customer ownership privacy, explicit core/streaming resource budgets and manual test procedure details. Design uses Debezium CDC, local KRaft Kafka, versioned JSON Schema contracts checked in CI, a separate Order History service/database, durable inbox/gap buffer, audited replay CLI and rebuildable CQRS projection. Product search, graph and lakehouse remain deferred. Design is approved for implementation; M06 code and runtime feasibility have not yet been verified. Evidence: `docs/milestones/S1-M06/`.

## 2026-10-24 — S1-M06 streaming projection implementation slice

Implemented local Debezium CDC to Kafka, schema-validated versioned order lifecycle events, Orders outbox backfill/enrichment, a separate Order History service/database with durable inbox and customer-owned CQRS reads, and storefront order-history refresh. Added API/event contracts, Python contract/streaming integration coverage, Selenium history journeys, and executable manual acceptance steps. Full offline CI passed; a follow-up streaming integration run passed the added Orders-database isolation assertion. Runtime evidence records 14 healthy containers, zero consumer lag, matching 104-row outbox/inbox totals, and a 4,719 MiB RSS snapshot against 7.75 GiB Docker allocation. These are bounded test observations, not peak/load capacity results. Manual owner acceptance is pending. Audited poison-event correction replay, candidate projection rebuild/reconciliation/cutover, and deterministic crash injection are not implemented; the reviewed M06 objective remains open. Work is being checkpointed on the existing `feat/s1-m05-checkout-orders` branch; no stage completion or branch transition is recorded.
## 2026-10-24 — S1-M06 deterministic consumer crash recovery

Added local one-shot fault injection after the Order History inbox/projection transaction commits and before the Kafka consumer offset commits. The streaming integration journey arms the next valid event after confirming zero lag, creates a checkout, confirms the container restarts, and checks that the projection sequence is not duplicated after redelivery. Targeted verification passed: six Order History Java unit tests, 25 operations tests, Compose validation and the full streaming integration journey. The run exposed two integration issues and resolved them: the consumer must use the validated event aggregate ID (Debezium wraps its Kafka key), and the next-event marker must be checked through the matching overload. Latest source/inbox counts are 122/122, projections 46 and consumer lag zero. Full CI has not been rerun after this feature. Poison correction replay and candidate projection rebuild/cutover remain open. Checkpointed to `stage1` and pushed as `11dd781`.

## 2026-10-24 — S1-M07 post-purchase design reviewed

Created the post-purchase design, review record, editable flow and separate manual acceptance guide before implementation. The review resolves immutable captured-amount refund arithmetic, distinct return-request and inspection ownership, cancellation/fulfillment handoff races, customer content privacy, prohibition on support impersonation, and clear simulator labeling. M07 is implementation-ready; no service capability is claimed yet. M06 replay and candidate projection rebuild remain ahead in the dependency sequence.
