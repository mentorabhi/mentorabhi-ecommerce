# Stage 1 handoff

2026-10-26 · Active branch stage1 · Stage 1 local engineering acceptance complete.

Read [project context](project-context.md), [current status](status.md), [Stage 1 acceptance](stage1-completion.md), [accepted requirements](../../requirements/accepted-requirements.md) and the milestone evidence before further changes. Earlier in-progress handoff is preserved in [the historical snapshot](resume-stage1-before-final-2026-10-25.md).

Current source/data: 216 genuine sourced products, 2,160 SKUs, INR/USD, 751 published DEMO reviews, separate storefront/Admin, simulated commerce, post-purchase, CDC/history, analytics/graph and local request telemetry. Image/banner revision is pushed as 9304c08; equipment search is pushed as a933ed2. Final closure commit records supporting test synchronization, Grafana WAL and documentation. No active test job or unresolved known Stage 1 release gate is carried forward.

Owner manual checklists remain unchecked. Independent code review was unavailable for the recorded native worker limitation; host diff review and executed tests are not described as an independent clean review. Resource/cold-start/retention and selective-heavy-profile limits remain explicit in acceptance.

Runtime: Storefront http://localhost:3000; Admin http://localhost:3002/admin; Grafana http://localhost:3001; Kafka UI http://localhost:8091. Operational logins admin/admin; customer identity is separate/self-registration. See [UI access](../setup/ui-access.md). Preserve current image identities and the persisted History target; never rerun obsolete generated active-art fixtures or reset data. Host Python must use .venv/bin/python.

Nova is next-stage scope. Begin its requirements/design/evaluation on a newly created and published stage2 branch when next-stage work is requested. Use existing host Ollama only, no Ollama container/hosted fallback. Stage 1 does not require owner input to finish engineering work.
