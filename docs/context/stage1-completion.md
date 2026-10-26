# Stage 1 engineering acceptance

2026-10-26 · Branch `stage1` · Local engineering release gate complete. This record does not imply owner manual sign-off.

SuperSports includes separate customer/Admin applications, service-owned commerce and configuration, simulated checkout/post-purchase, outbox/Debezium/Kafka history, local analytics/graph/reporting, recovery tooling, sourced catalog data and local request telemetry. Nova remains the next stage, using host-installed Ollama.

## Delivered scope and evidence

| Scope | Evidence |
| --- | --- |
| M01 architecture/ownership/design | [Design index](../../design/README.md), accepted requirements and ADRs; no runtime pass is claimed for a design-only milestone. |
| M02–M05 bootstrap, merchandising, storefront and checkout | [Milestone records](../milestones/README.md), unit/integration/contract/browser and recovery evidence. Money, stock, coupon limits and ownership remain deterministic service rules. |
| M06 CDC/history and recovery | [Acceptance matrix](../milestones/S1-M06/acceptance-matrix.md): crash/DLQ/replay/rebuild/cutover, snapshot/WAL and transaction rollback, 900-second soak and retained-WAL/group recovery. |
| M07 post-purchase | [Verification](../milestones/S1-M07/verification.md), plus current 3/3 post-purchase rerun and fixture-backed browser actions in M11. |
| M08 analytics/graph | [Verification](../milestones/S1-M08/verification.md): reconciled Iceberg replay, currency-specific reports and graph projection; explicit batch freshness and metric definitions. |
| M09 local operations/recovery | [Verification](../milestones/S1-M09/verification.md): isolated database restore, ingress limits and local observability; alternate deployment artifacts are distinct from actual cluster provisioning. |
| M10 synthetic history | [Verification](../milestones/S1-M10/verification.md): 1,000 seeded synthetic profiles and prior-year orders; retained historical items remain valid after active replacement. |
| M11 current shopping/Admin/data requirements | [Verification](../milestones/S1-M11/verification.md), [data provenance](../milestones/S1-M11/data-population.md): 103 Cricket/113 Football products, 1,030/1,130 SKUs, both currencies, 751 DEMO reviews, product-scoped coupons, photographic assets, reviews/similar products and separate Admin. |
| M12 request metrics/traces/logs | [Verification](../milestones/S1-M12/verification.md): five live privacy/linkage/error/outage/restart cases, Grafana browser, actual image-preserving disable/re-enable and measured resources. |

## Final release gate — measured results

- Core commerce **25/25** (115.961-second runner); live request telemetry **5/5** (123.512s), post-purchase **3/3** (96.426s), plus separately recorded streaming/recovery/fixture-backed acceptance in M06/M07/M11.
- Final Devops discovery **148 discovered /103 executed passes /45 explicit live skips** (0.688s). Skips are opt-in live suites with separate executed records, not successful runtime assertions. Normal builds/Java/data/frontend unit and real database evidence are linked from milestone records.
- Final retained-history reconciliation: **ok=true, errorCount=0, 36,537 events, 18,077 orders**, 32 poison records and 52 replay audits. It retained database/group `order_history_r_3ca8f0ec3312` / `order-history-r-3ca8f0ec3312`; totals across all order states are not sales. Receipt: `devops/.local/verification/s1-release-history-reconcile-final.log`. The earlier concurrent operator-aborted attempt was not counted.
- Admin post-identity-restart mobile/login **1/1** (31.590s), Keycloak master login **1/1** (9.482s), native Kafka UI API **2/2** (30.083s before temporary selective shutdown), plus recorded operations-browser checks for Kafka UI, Prometheus, Trino, Neo4j and Superset. Heavy profile UIs were tested selectively; optional services need their profile to run.
- Support create/reply Selenium **1/1** (28.989s), retaining enabled-button synchronization and a unique ticket subject. The broad storefront run had seven executed passes, one Grafana error and six explicit fixture/profile skips. Its failed result is retained. Separately executed fixture journeys and the focused final Grafana test close those acceptance paths; no single all-profile clean browser run is claimed.
- Grafana's authenticated dashboard API stall was diagnosed separately from native login. Supported SQLite WAL on the same retained volume replaced DELETE journal mode; health/request dashboard and Explore Selenium passed **1/1** (9.278s), then **1/1** (16.293s) after telemetry/Kafka UI restoration. All original dashboard assertions/deadlines remain.
- User UI corrections: [R29 card/banner](../milestones/S1-M11/card-layout-refinement.md), pushed `9304c08`; [R30 search](../milestones/S1-M11/search-relevance.md), pushed `a933ed2`. The final search Catalog verify passed **26/26 with real PostgreSQL**, including three query units/eight database boundary tests. Docker test-enabled build/readiness passed and catalog Selenium **4/4** (13.571s), including actual search submission, product navigation and desktop/mobile layout. Live results: **13 bats, 25 balls, 24 pads**, with working plurals and brand/sport terms. Earlier wildcard/stale-element regressions are preserved with their fixes.

Final restored runtime: **25 containers running**, a single memory snapshot of **6,453.52 MiB**, all configured healthchecks healthy, no container currently marked OOM-killed. Kafka UI restore/readiness completed and native integration passed **2/2 in 8.384s** (`s1-release-kafka-ui-restored.log`). Telemetry stores and Grafana are running; analytics/graph/Superset remain selective. This snapshot is separate from the earlier 120-second memory observation and does not imply that all historical restart counts are zero. Receipts: `s1-release-final-runtime.json`, `s1-release-final-stats.txt`.

Runtime receipts and exact commands/outcomes are in milestone records; ignored local raw receipts are under `devops/.local/verification/`. Recorded results are finite local functional acceptance, not a throughput/endurance or independent-review claim.

 A previous cold-start run had two five-second client timeouts under Docker VM pressure; the unchanged warm commerce rerun passed all 25 checks. This does not establish a cold-start latency SLO.

## Reproducibility and limits

Use `.venv/bin/python` for host Python. Normal application builds run tests; images/dependencies are pinned under `devops/`. Restore the accepted photo manifest before frontend builds on a fresh checkout. Catalog import uses owning APIs, preserves consumed stock on replay and retires old active fixtures without deleting historical orders or audits. See the milestone data/development/testing guides for commands and source/simulation boundaries.

The measured host is a 16 GB ARM64 Mac, Docker Engine 29.8.0/aarch64 with 8,319,770,624 bytes allocated to Docker. A 24-container/120-second functional regression window peaked at 6,369.28 MiB. It included an intentional Orders stop/start and had no observed OOM or automatic restart-counter increase. This is finite local evidence, not peak production capacity, 24-hour endurance, a disk quota or multi-broker HA. Run heavy analytics, graph and dashboard-studio jobs selectively; cold resource pressure can exceed short client timeouts.

Tracing initially covers eleven Java services. Python/browser instrumentation and arbitrary exception/application-message logs are outside this implementation; Loki exports the dedicated safe HTTP request stream. Configured trace/log retention is 24 hours, with bounded queues and possible telemetry loss during outages. Commerce databases remain authoritative.

Code review: skipped (ce-code-review unavailable). The terminal review attempt could not perform required nested native dispatch; later simplification reviewers hit the usage limit. The evidence records distinguish host source scans, successful earlier simplification lenses, actual tests and unavailable independent review. No clean independent review is claimed.

## Owner review and next stage

The [Stage 1 owner verification guide](../testing/stage1-release-checks.md) links separate service/UI/feature/database checklists for every milestone. They remain unchecked until the owner performs them; automated results do not substitute for owner sign-off.

Storefront: http://localhost:3000, separate customer account/self-registration. Admin: http://localhost:3002/admin. Grafana: http://localhost:3001. Kafka UI: http://localhost:8091. Enabled operational UIs use **admin/admin**; [access/profile guide](../setup/ui-access.md).

The next stage is Nova requirements/design, tools, evaluation and commerce gap assessment. Start new stage work on a published `stage2` branch. No Nova implementation or owner sign-off is claimed here.

## M13 follow-up acceptance — 2026-10-26

A subsequent user request expanded Stage 1 to 50 Cricket equipment families plus four maintenance families. [M13 coverage](../milestones/S1-M13/coverage.md) and [executed evidence](../milestones/S1-M13/verification.md) establish **54/54** supported families, **96 added source models** and current totals of **312 products/2,256 SKUs**, Cricket **199/1,126**, Football unchanged **113/1,130**, **1,088 published DEMO reviews**. The earlier release counts and test receipts above are historical, not overwritten measurements.

Pipeline units 24/24; Catalog real-PostgreSQL verify 28/28; new owner/photo/replay/quote integration 3/3; full 312-model source regression 4/4; new equipment Selenium 3/3; catalog Selenium 4/4; product-experience three executed passes/one explicit delivered-review-fixture skip. Both frontends were rebuilt to package new photos, with hash checks at each origin. Admin login, restored runtime and exact timing/limitations are in M13 verification. No accepted source baseline model/history was deleted or replaced; stock/price/coupon replay and owned history preservation passed. The cloth/maintenance-kit/carrier interpretations and source availability/rights limits remain explicit. Owner manual checklists remain unchecked; Nova remains next-stage scope.

The M13 Grafana restoration rerun is a separate recorded exception: authenticated access to the provisioned service-health dashboard API returned HTTP 200 after a designed CPU-ceiling increase, but Selenium dashboard checks timed out amid measured host memory reclaim/CPU throttling. This is not counted as an M13 browser pass; see its retained logs and limits in the M13 verification file. Earlier Grafana browser receipts above remain historical Stage 1 evidence.
