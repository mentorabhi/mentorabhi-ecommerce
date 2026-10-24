# SuperSports and Nova — project context

Revision 2 · 2026-10-23 · Source of truth for continuing work.

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
Scope now: S1-M04 is committed as `cf8de79`; owner manual acceptance remains open. S1-M05 is committed as `af6f7d6` on `feat/s1-m05-checkout-orders`, with simulated checkout and customer-visible order progression through `FULFILLMENT_SCHEDULED`; its manual acceptance, deeper failure injection, audited manual-review resolution and peak/concurrency measurements remain open. S1-M06 design is reviewed. Implementation on `stage1` includes local Debezium/Kafka CDC, versioned outbox events, durable consumer inbox, owner-scoped Order History projection/API and UI, plus tested crash-after-database-commit recovery. Operator-audited poison correction/replay, isolated projection rebuild/reconciliation/cutover and peak/load measurements remain incomplete. Full CI passed before the latest recovery slice; targeted integration/Java/operations verification passed afterward. Owner manual acceptance remains open. User-selected customer self-registration uses a separate Keycloak realm and customer-only API audience, per ADR 0004. S1-M02 implements bootstrap; S1-M03 merchandising administration; S1-M04 customer browsing and customer-owned cart/profile; S1-M05 checkout; S1-M06 streaming and projections.
Application code must follow the corresponding reviewed design. Do not interpret the full roadmap as implemented or claim S1-M01 runtime tests passed.

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
Native host Ollama setup/server/model/connectivity is a Nova prerequisite, documented in docs/setup/prerequisites.md. Commerce bootstrap must not require Ollama to be running.
