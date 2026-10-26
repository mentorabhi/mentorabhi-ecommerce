# Project status

Updated: 2026-10-26 · Active branch `stage1` · M13 implementation/data and required regression suites complete; Grafana browser stability caveat remains documented.

Stage 1 development, data and documentation are complete. M13's catalog, commerce, photo, Storefront/Admin browser and database acceptance gates passed. A final Grafana browser restoration check did not pass reliably under host memory/CPU pressure; its authenticated service-health dashboard API is responsive after the measured CPU-limit adjustment. This M13 limitation and failed Selenium receipts are not hidden or counted as passes. Owner manual review remains separate.

- Storefront: http://localhost:3000, separate customer account/self-registration.
- Admin: http://localhost:3002/admin, **admin/admin**.
- Grafana: http://localhost:3001, **admin/admin**.
- Kafka UI: http://localhost:8091, **admin/admin**.
- Optional operations interfaces and profile commands: [access guide](../setup/ui-access.md). Heavy analytics/graph/dashboard-studio remain selective on the 16 GB host.

The active sourced catalog contains **199 Cricket products/1,126 SKUs** and **113 Football products/1,130 SKUs**, INR/USD prices, local source photographs, stock and **1,088 published DEMO reviews**. Product-scoped coupon fixtures are present. Old/test products are retired; historical orders and the prior-year synthetic customer/order dataset remain intact. [Current M13 coverage/provenance](../milestones/S1-M13/verification.md); [original M11 baseline](../milestones/S1-M11/data-population.md).

Measured evidence includes normal test-enabled app builds; Java/DevOps/data/frontend units; real PostgreSQL Catalog checks; core commerce, streaming recovery/gap/fallback and post-purchase integration; sourced-data replay and photo hashes; separate Admin/customer browser journeys; operational logins; five live OpenTelemetry privacy/linkage/error/outage/restart cases; and prior Grafana Selenium passes. Actual telemetry disable/re-enable preserved images/History target, with all eleven Java services ready. M13's additional Grafana browser failures and API result are recorded separately in [M13 verification](../milestones/S1-M13/verification.md).

The 24-container, 120-second telemetry/commerce observation peaked at **6,369.28 MiB**. It includes intentional Orders stop/start and does not establish maximum throughput or 24-hour endurance. M06 separately records its finite 900-second soak and retained-WAL/idle-group recovery. Single-node local profiles are not multi-broker HA or a cloud deployment.

Owner manual checklists remain **unchecked**, separate from engineering/automated verification. Start with [Stage 1 owner verification](../testing/stage1-release-checks.md), which links every milestone's service/UI/feature/database guide. No owner sign-off is claimed.

Nova belongs to the next stage and is not implemented. Host-installed Ollama remains its prerequisite; no Ollama container or hosted AI fallback is used. A new stage must use a new branch, for example `stage2`.

Latest UI corrections are deployed: portrait pad photos stay above card text, promotional storefront banners are removed, and equipment search uses whole-word/type-aware relevance. The original search checkpoint returned 13 bats/25 balls/24 pads; M13 adds equipment and compound accessory intent with updated live evidence. Catalog verification passed 26/26 with real PostgreSQL and the affected catalog Selenium file passed 4/4. Checkpoints 9304c08 and a933ed2 are pushed to stage1.

Final restored runtime has 25 running containers, configured healthchecks healthy, with a single 6,453.52 MiB memory snapshot. Heavy analytics/graph/studio profiles remain selective.

Final retained-history reconciliation: 36,537 events /18,077 orders, ok=true and zero errors. Earlier Grafana SQL dashboard stalls improved with supported SQLite WAL and had passing native browser runs; the separate M13 post-restart rerun remains unstable under measured host pressure despite its authenticated dashboard API returning HTTP 200. Keycloak login passed after identity restart. Consolidated [release evidence and limitations](stage1-completion.md) distinguish explicit fixture/profile skips from separately executed live gates and retain failed diagnostics.

Earlier dated status is preserved in [the pre-closure history](status-before-stage1-close-2026-10-25.md). Original planning inputs and their historical meanings remain unchanged.

Knowledge-transfer handover: [service/API/infra/access and overall-flow guide](../explainers/supersports-stage1-kt.md), with the sanitized 34-definition/25-running inventory and editable diagrams (2026-10-26). It describes the release baseline; future catalog additions must update the dated counts/provenance separately.

## New follow-up scope — 2026-10-26

The user requested a further 54-family Cricket equipment audit/expansion (50 primary rows plus four maintenance rows), tracked as R31/S1-M13. This additional scope is implemented, populated and verified in its own M13 evidence after the completed release snapshot; earlier release evidence is retained separately. See [M13 design and evidence](../milestones/S1-M13/README.md). KT handover is pushed as 4338991. M13 adds 96 genuine source models with 54/54 supported equipment families; full 312-model import and replay, price/stock/review/photo checks, both frontend bundles, PostgreSQL/query and desktop/mobile/cart browser acceptance passed. Monitoring/streaming are restored; no owner manual sign-off is claimed.
