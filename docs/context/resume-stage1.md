# Stage 1 handoff

2026-10-26 · Active branch stage1 · M13 development/data and affected regression suites complete; final Grafana browser stability limitation documented.

Read [project context](project-context.md), [current status](status.md), [Stage 1 acceptance](stage1-completion.md), [accepted requirements](../../requirements/accepted-requirements.md) and the milestone evidence before further changes. Earlier in-progress handoff is preserved in [the historical snapshot](resume-stage1-before-final-2026-10-25.md).

Current source/data: 312 genuine sourced products, 2,256 SKUs, INR/USD, 1,088 published DEMO reviews, separate storefront/Admin, simulated commerce, post-purchase, CDC/history, analytics/graph and local request telemetry. Image/banner revision is pushed as 9304c08; equipment search is pushed as a933ed2. The original closure commit e8a4868 records supporting test synchronization, Grafana WAL and documentation. KT is 4338991. M13 adds 96 real sourced Cricket equipment models and complete 54-family coverage, realistic single source configurations, compound accessory search, both frontend photo bundles and executed unit/PostgreSQL/API/replay/quote/Selenium evidence. One operational caveat remains: Grafana's provisioned health dashboard API responds after its CPU-limit adjustment, but the M13 Selenium dashboard run remains unstable under recorded host pressure; see exact failures and limits in M13 verification. No catalog/data implementation gate is pending.

Owner manual checklists remain unchecked. Independent code review was unavailable for the recorded native worker limitation; host diff review and executed tests are not described as an independent clean review. Resource/cold-start/retention and selective-heavy-profile limits remain explicit in acceptance.

Runtime: Storefront http://localhost:3000; Admin http://localhost:3002/admin; Grafana http://localhost:3001; Kafka UI http://localhost:8091. Operational logins admin/admin; customer identity is separate/self-registration. See [UI access](../setup/ui-access.md). Preserve current image identities and the persisted History target; never rerun obsolete generated active-art fixtures or reset data. Host Python must use .venv/bin/python.

Nova is next-stage scope. Begin its requirements/design/evaluation on a newly created and published stage2 branch when next-stage work is requested. Use existing host Ollama only, no Ollama container/hosted fallback. Stage 1 does not require owner input to finish engineering work.
