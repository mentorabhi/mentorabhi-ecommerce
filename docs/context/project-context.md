# SuperSports and Nova — project context

Revision 3 · 2026-10-24 · Source of truth for continuing work.

## Read order
Read this file, repository AGENTS.md when present, the current milestone, its design review, and the decision log before changing the project. Read requirements/accepted-requirements.md for product constraints. Update context, milestone evidence, and revision history at every meaningful checkpoint.

## Objective and sources
Build a realistic local ecommerce platform (SuperSports), then design and implement an Ollama-powered shopping assistant (Nova), for self-learning and teaching intermediate students. Concepts, alternatives, deployment, execution, and failure behavior matter as much as code.
Original input: requirements/project_requirement.txt (preserve unchanged).
Planning baseline: docs/context/original-planning-baseline.txt, fetched from the Google Doc on 2026-10-23. Source URL: https://docs.google.com/document/d/1Udo6YdV0xtdBJbNNWtFgOxYqFi6GIM7n3BdjMHbtzlM/edit?tab=t.0
Existing architecture/ diagrams are proposals from that baseline, not implemented capabilities. New requirements below override conflicting baseline proposals. Do not rewrite the shared Google Doc without an explicit editing instruction.

## Confirmed user decisions
- Cricket and Football initially; extensible sports, categories, attributes and variants.
- English. Indian addresses and INR default. Currency configurable, including USD.
- Simulate payments, refunds, fulfillment, taxes, shipping and product-eligible coupon codes.
- 16 GB Mac baseline; all application and dependency workloads containerized, deployable to larger machines.
- No cloud services. Use local adapters; keep replaceable infrastructure interfaces. Categorized administration UI for configurations.
- Use the existing host-installed Ollama only. Do not create or run an Ollama container. Generation and other models must remain open-source, lightweight and locally deployable. This is the explicit exception to Dockerizing application/dependency workloads.
- Propose technology versions; verify latest stable compatible releases at implementation time, pin exact tested versions, record compatibility and licensing.
- Monorepo; every microservice is its own project; all infrastructure and operational automation under devops/.
- Design document and editable diagram first, review second, implementation third. Maintain context and revision history throughout.
- Unit tests for every feature; documented and executed integration, regression and relevant end-to-end tests after major features/milestones.
- Maintain .gitignore. Modern responsive storefront, logo, original product imagery, useful descriptions and plausible synthetic prices.
- Work autonomously on this repository, Git and service lifecycles. Ask about material ambiguity; respect environment-enforced approvals.
- At each milestone checkpoint, commit with a relevant message on the active stage branch and push it to the configured remote. At each new stage, create and publish a branch named for that stage (for example, `stage1`). Do not force-push or overwrite remote history. Continue subsequent milestones without routine approval.

## Python execution
Use the repository-local .venv for all Python execution and package management: .venv/bin/python and .venv/bin/python -m pip. Never install project dependencies globally. Bootstrap the environment with python3 -m venv .venv. Current verified local interpreter is Python 3.14.7, recorded in verification evidence; dependency/version selection remains S1-M02 work.

## Current state
S1-M01 is checkpointed as s1-m01-design-v1 (7ef04c4). S1-M02 is locally verified and checkpointed as `s1-m02-bootstrap` (cf50e8e), with the review limitation recorded in its milestone evidence. S1-M03 catalog, pricing, inventory, fixtures and admin UI are committed as `6617e40` on `feat/s1-m03-catalog-inventory`; automated checks passed, while owner manual review and peak/load memory checks remain pending. S1-M04 customer storefront is implemented and verified on `feat/s1-m04-customer-storefront`; the user selected self-registration with a separate customer identity realm. Nova remains later. The configured remote is `https://github.com/mentorabhi/mentorabhi-ecommerce.git`; `stage1` tracks `origin/stage1`.
Scope now: S1-M04 is committed as `cf8de79`; owner manual acceptance remains open. S1-M05 is committed as `af6f7d6`, with simulated checkout through `FULFILLMENT_SCHEDULED`; deeper failure injection, audited manual-review resolution and concurrent-load acceptance remain open. S1-M06 on `stage1` includes CDC/Kafka, versioned outbox, owner-scoped History API/UI, commit/offset crash recovery, audited poison replay, canonical fingerprints and isolated rebuild/reconciliation/cutover. Its recent DLQ transaction boundaries, broker/Connect restart, sequence-gap, freshness ownership and browser fallback probes passed; the subsequent broader replay/rebuild run exposed six retained poison coordinates requiring correction. Snapshot/WAL overlap, sustained/concurrent load and owner manual results remain open. S1-M07 Payment bounds and tracking/handoff source are implemented; tracking changes remain unverified. M07 units 3–8 and M08/M09 development remain. The configured remote is `https://github.com/mentorabhi/mentorabhi-ecommerce.git`; active branch `stage1` tracks `origin/stage1`. Current details are in `status.md` and milestone evidence.
Application code must follow the corresponding reviewed design. Do not interpret the full roadmap as implemented or claim S1-M01 runtime tests passed.

After rebuild checkpoint `3d84ca5`, focused fixes cover null Kafka tombstone diagnostics and canonical replay identity for integer-equivalent sequence representations. Both new tests failed before the fixes; the rebuilt Order History module now passes 15 tests plus live numeric replay/retry/reconciliation and customer history Selenium. The full CI recorded above predates these leaf fixes. M06 remaining gates are unchanged.

## Stage gates
1. S1: working commerce, reproducible local profiles, streaming, relationship and analytics demonstrations, recovery evidence.
2. S2: Nova requirements/design/evaluations grounded in working S1 APIs; identify gaps.
3. S3: implement gaps, grounded read-only Nova, then approval-bound actions, memory, caching and enterprise roles.

## Milestone manual acceptance
Every milestone has a separate `docs/milestones/<milestone>/manual-acceptance.md` for end-user checks outside automation. Cover local service health, UI journeys and feature actions, relevant database state, and a manual result record. See [milestone evidence convention](../milestones/README.md).

## Provisional defaults (change through a recorded decision)
Single retailer, one store, one initial warehouse; no marketplace or cross-border tax compliance.
Store-wide currency selection at first, not per-customer currency switching. Explicit currency-specific price books; no implicit live exchange-rate service. Currency changes affect new quotes, not historical orders.
No public exposure by default. Simple local sign-in is required; administrative role distinctions are removed by the user's revision in ADR 0003. Customer ownership and Nova approval rules remain required.
All numeric capacity targets remain proposed until measured. No cloud or hosted model fallback.

## Setup prerequisite

Host database inspection is now explicitly authorized (R22/ADR 0007). The optional Compose override binds PostgreSQL only to `127.0.0.1:15432`, persists the choice in ignored local state, and uses existing generated credentials. See `docs/setup/database-access.md`; never copy credentials into tracked documentation. M06 now exposes observed freshness and falls back to owned Orders records when streaming is delayed/unavailable; its planned isolated runtime gap/outage acceptance remains open.

Kafbat UI is available at `http://localhost:8091` when the streaming profile is active. It is pinned in images.lock, read-only in its cluster configuration, and connected to the existing broker and Debezium Kafka Connect. See `docs/setup/kafka-ui.md` and the M06 design/verification; local UI read-only is not broker ACL enforcement.

M07 Unit 1 payment-ledger bounds was implemented and verified before the development-first sequencing change. Units 2–4 and the v2 event compatibility foundation are implemented in source, unverified. Cancellation emits `OrderCancelled` v2 only after shipment claim, simulated refund and inventory reversal complete. Returns verify delivery/window in Fulfillment/Configuration, reserve immutable unit refund allocations in Orders, and emit v2 request/refund events around idempotent Payment work; Inventory stays unchanged pending Unit 5 inspection. M06 acceptance remains open; no scoped M07 work implies Stage 1 completion.

User sequencing update: complete Stage 1 development across M07–M09 before resuming the consolidated testing pass. New implementation checkpoints still include test source and dated documentation, but do not run tests/builds until the user-defined development phase is complete. Units 2 and 3 are expressly unverified.

Current development pass (2026-10-24): M07 Units 2–8 are authored and pushed, unverified. M08 design and implementation are authored on `stage1`, also unverified. It adds a bounded Neo4j graph API; Spark/Iceberg Kafka projections; Trino; a read-only reports API; Admin → Analytics reports/dashboard; and optional Superset at localhost:8095. The dashboard supports 7/30/90/365-day reports in INR/USD with defined GMV, order value/count, AOV, item volume, discounts/refunds and rates, net cash sales, cancellations/returns, daily trend, product performance and refund detail. Traffic funnel, coupon attribution, customer retention and inventory metrics require additional reviewed event sources/owner APIs. Keep resource-heavy graph, reporting and batch work opt-in. Metrics and limits are in `docs/milestones/S1-M08/dashboard-and-metrics.md`; manual runtime/service/UI/database/reconciliation steps are in the milestone guide. M09 recovery, ingress, telemetry and scale configuration is authored but unverified; exact image index digests are pinned and registry manifests include ARM64. Consolidated testing resumes at M06 only after remaining Stage 1 development is finished.

Native host Ollama setup/server/model/connectivity is a Nova prerequisite, documented in docs/setup/prerequisites.md. Commerce bootstrap must not require Ollama to be running.

## Current consolidated checkpoint — 2026-10-25

The state above is a dated development snapshot and has been superseded by the consolidated acceptance record in [status.md](status.md). On active branch `stage1`, S1-M01–M10 implementation is present. The latest automated local acceptance run covers core service unit/build checks, recovery and streaming integration, post-purchase tests, browser workflows, the synthetic dataset, lakehouse reconciliation, graph projection, deployment validation, backup/restore, ingress limits, and operations UI. Per-milestone dated results and explicit limits are recorded in each `docs/milestones/S1-Mxx/verification.md`.

Stage 1 is not owner-signed off. Manual acceptance checklists remain for the user to execute. M06 now has dedicated snapshot/WAL-overlap, actual state/outbox rollback, concurrent burst, 900-second paced checkout and 900-second inactive-slot/idle-group retention evidence, followed by exact full reconciliation. Results are finite local measurements, with higher rates/day-scale disk capacity and multi-broker HA outside the measured scope. The user's subsequent catalog/review/separate-Admin/credential changes expand Stage 1; the updated requirements file also reaffirms OpenTelemetry response-time metrics and logs beyond M09's existing readiness dashboard. Nova remains later and Ollama is host-installed only.
