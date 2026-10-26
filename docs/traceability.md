# Current Stage 1 traceability

2026-10-25 · Stage 1 local engineering gate complete through M12 and R29/R30 corrections. Owner manual sign-off remains separate. Earlier tables are retained as historical snapshots.

| Requirements | Current delivery and evidence |
| --- | --- |
| R01/R02/R09/R18/R25 | Extensible Catalog/administration and sourced replacement: [M11 data](milestones/S1-M11/data-population.md), [verification](milestones/S1-M11/verification.md); 103/113 models, 1,030/1,130 SKUs, prices/stock/photo hashes and replay. R25 supersedes generated active artwork. |
| R03/R04/R05/R21 | English/India defaults, currencies, customer storefront and identity/ownership isolation: M04/M05 and current M11 unit/contracts/API/Selenium evidence. |
| R06/R07/R08 | Deterministic checkout/coupons/stock/payment/fulfillment and post-purchase: M05–M07, current core 25/25, post-purchase 3/3 and fixture-backed browser gates in [M11](milestones/S1-M11/verification.md). |
| R10 | Categorized configuration, validation/revisions and supported activation: M02–M05, current Admin UI/API audit checks. Migration-only adapter limits remain explicit. |
| R11/R12/R13 | Independent monorepo projects, devops ownership, local Docker/ARM64 profiles and alternate deployment artifacts: M02/M09 plus [M12 resource/lifecycle evidence](milestones/S1-M12/verification.md). No cloud runtime or Ollama container. |
| R14 | Owner databases, Saga/outbox/Debezium/Kafka, History, graph/lakehouse/reporting: [M06 matrix](milestones/S1-M06/acceptance-matrix.md), [M08 reconciliation](milestones/S1-M08/verification.md), final retained-history gate in Stage 1 acceptance. |
| R16/R17/R19 | Tests, reviewed designs/editable diagrams, exact compatible pins, context/ADRs/revisions and Git: [design index](../design/README.md) and each milestone's evidence. Independent review-tool limits are recorded. |
| R20 | Commerce → Nova design → Nova integration: [Stage 1 acceptance](context/stage1-completion.md); next-stage branch/design remains separate. |
| R22 | Host DBeaver/PostgreSQL access: [database guide](setup/database-access.md), live host-auth/loopback/owner-role checks. GUI owner review remains manual. |
| R23/R27 | admin/admin operational interfaces and separate frontend origins/themes: [access guide](setup/ui-access.md), M11 selective restart/API/Selenium evidence. Customer/service identities remain separate. |
| R24/R26 | Ratings/DEMO provenance/verified reviews/moderation/similar products: M11 real PostgreSQL, contract, unit and desktop/mobile browser evidence. |
| R28 | Local request latency/error metrics, linked traces and safe logs: [M12](milestones/S1-M12/verification.md), five live cases, dashboard values/browser, disable/re-enable and resources. |
| R29 | Banner removal and card photograph containment: [reviewed design and desktop/mobile red/green evidence](milestones/S1-M11/card-layout-refinement.md); deployed/pushed as 9304c08. |
| R30 | Search relevance: [reviewed design and unit/PostgreSQL/browser evidence](milestones/S1-M11/search-relevance.md); equipment intent, whole words and stable pagination. |
| R31 | All 54 requested Cricket equipment families: [M13 coverage](milestones/S1-M13/coverage.md), [source/owner-API/replay/quote/Selenium evidence](milestones/S1-M13/verification.md); 96 additions, current Cricket 199 models/1,126 SKUs, preserved baseline/history. |
| R15 | Nova inference/tools/RAG/approval/evaluations: next-stage scope; host Ollama prerequisite documented, no Nova runtime claimed. |

## Historical traceability snapshots

# Traceability register
Revision 6 · 2026-10-24. S1-M02 bootstrap and S1-M03 implementation/runtime checks are verified; S1-M03 code is committed. Owner manual acceptance and peak/load memory checks remain pending. S1-M04 has design traceability below; runtime is not implemented.

| Requirement | Journey / owner | Contract / data | Design | Milestone | Verification / target | Release |
|---|---|---|---|---|---|---|
| R01/R02/R09 | Catalog/admin; Catalog, Pricing, Inventory | Catalog/price/stock APIs | design/S1-M03/catalog-inventory.md; ADR 0003 | S1-M03 | Final CI: 20 Python, 29 Java, 15 live integration checks, recovery and 4 Selenium journeys; six-product fixtures, authenticated access without role claims and DB isolation | Committed as 6617e40; runtime verified; code-review skill skipped for usage limit; user manual review pending |
| R03/R05/R18/R21 | Customer discovery; Storefront, Customer | Browse/cart/profile APIs and isolated customer realm | design/S1-M04/storefront.md; ADR 0004 | S1-M04 | AE02/AE04/AE20/AE21; cross-realm isolation, responsive E2E | Implementation in progress |
| R04/R07 | Merchandising; Pricing | INR/USD price books, active currency, coupon definitions | design/S1-M03/catalog-inventory.md | S1-M03; checkout/redemption S1-M05 | Live integration confirms both currency books and two coupon definitions; unit rules and migration checks pass; redemption limits later | Local runtime verified; browser review pending |
| R06 | Purchase; Pricing, Orders, Inventory, Payments | Quote/checkout/Saga | design/S1-M01/architecture.md | S1-M05 | AE05–AE08; unit, real DB concurrency, recovery | Pending |
| R08 | Post-purchase; Orders, Engagement | Return/refund/review contracts | architecture/stage-1/S1-M07.excalidraw | S1-M07 | AE10; original-value refund and ownership | Pending |
| R10 (bootstrap foundation) | Configuration; Configuration, Platform admin | Read-only migration registry/API; runtime activation and UI later | design/S1-M02/bootstrap.md | S1-M02; activation S1-M04 | 12 live integration checks include roles, redaction, non-mutating methods; activation pending | S1-M02 verified |
| R11/R12/R13 (bootstrap profile) | Bootstrap/operator; devops | Local Docker Compose profile; alternate deployment artifacts | design/S1-M02/bootstrap.md | S1-M02; expanded profiles S1-M09 | `devops/scripts/ci`, measured RSS snapshot, local-only services; no cluster provisioning | S1-M02 verified |
| R14 | Streaming/data; service owners, pipelines | Outbox/events/projections | architecture/stage-1/S1-M06.excalidraw | S1-M06/M08 | AE08/AE14/AE15; replay and reconciliation | Pending |
| R15 | Shopping assistance; Nova | Typed tools/RAG/memory | architecture/stage-2/S2-00.excalidraw | S2/S3 | AE16–AE19; local inference/evaluation, approval | Pending |
| R16/R17 (S1-M02) | Developer/student; service and devops projects | Unit/integration suites, milestone evidence, ADR/lesson | docs/testing/strategy.md | Every milestone | 16 Python unit, 18 Java unit, 12 live integration tests; S1-M02 review limitation recorded | S1-M02 verified |
| R16/R17 (S1-M03) | Developer/student; service, data, frontend and devops projects | Unit/contract/integration/browser suites and reviewed design | design/S1-M03/catalog-inventory.md | S1-M03 | 20 Python, 29 Java, 15 live integration tests, Playwright local-login regression, 4 Selenium UI journeys and recovery; separate manual guide | Committed as 6617e40; local implementation verified; user manual review pending |
| R18 | Store visitors/admin; Storefront | Local logo and per-product artwork | design/S1-M03/catalog-inventory.md | M03 assets; M04 storefront | Local generated SVG brand and product art; visual/browser review pending | Assets created; verification pending |
| R19 | Dependency selection; devops and service owners | Compatibility/version/image digest record | docs/decisions/0001-local-first-monorepo.md | Each milestone | React/Vite/Node versions and ARM64 image digests pinned; compatibility builds underway | S1-M03 pending |
| R20 | Stage gates; project owner | Stage acceptance | docs/context/project-context.md | S1 → S2 → S3 | Baseline plan stage exit gates | Pending |

Detailed endpoint/event names, automated test paths and numeric targets will be added at each implementation milestone, not fabricated before contracts exist.
# S1-M04 design traceability (2026-10-24)

Current additions (2026-10-25): R23–R27 / AE23–AE27 map to docs/milestones/S1-M11/design.md, flow.mmd, implementation-units.md and manual-acceptance.md; U1 separate applications/access and U2 product/review APIs/UX have measured incremental evidence in M11 verification. U3 real catalog/scale and U4 expanded-data/restart/consolidated checks remain pending; AE23–AE27 are not closed solely by the U1/U2 passes. R28 / AE28 maps to S1-M12 intake and requires a reviewed local telemetry design before implementation. M06's final automated finite-window evidence is in its latest verification/matrix: 60-order/900-second soak, 900-second retained-WAL/idle-group recovery, actual state/outbox rollback and exact retained-history reconciliation. Earlier tables below retain their historical checkpoint meanings.

New unverified source: R07/R25 importer and product-scoped coupon rules map to S1-M11/catalog-import-design.md and data/pipelines/real-catalog; R28 maps to reviewed S1-M12/design.md, telemetry-flow.mmd, dependencies.md, ADR 0011, telemetry configuration/lifecycle and Java request filters. Authored tests are pending execution under coding → data → testing. No acceptance row closes from code or dependency metadata alone.

| Requirement / acceptance | Design coverage | Evidence target |
|---|---|---|
| R03 / AE02 | India-default address form and server-side state/PIN validation | `design/S1-M04/storefront.md`; Customer tests and manual checklist |
| R05 / AE04 | Browse, search, filter, sort, product details, wishlist, cart, profile; subject-derived owner isolation | `design/S1-M04/storefront.md`; Customer API contract, integration and Selenium tests |
| R04 / AE03 | Explicit active currency price book; no live conversion; M05 revalidates checkout | `design/S1-M04/storefront.md`; integration/browser checks |
| R10 / AE12 | Preserve M03 admin configuration workspace | M04 regression/Selenium and manual checks |
| R16–R19 / AE13, AE20 | Unit, contract, integration, regression, browser and manual UI checks; local Docker profile and accessibility | M04 CI evidence and manual acceptance |
