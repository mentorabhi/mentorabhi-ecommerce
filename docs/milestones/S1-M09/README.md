# S1-M09 — Reliability, scaling and recovery

Status: Implementation complete; consolidated Stage 1 verification is underway. M09-specific build, tests, and runtime acceptance remain open.

Inputs: [architecture proposal](../../../architecture/stage-1/S1-M09.excalidraw), [design](design.md), [editable flow](flow.mmd), [review](design-review.md), [manual acceptance](manual-acceptance.md), and [ADR 0009](../../decisions/0009-local-restore-and-telemetry.md).

Scope: local Docker recovery, permission-restricted database backups (not cryptographic encryption), isolated restore drills, Nginx request limits, local health telemetry, and scale-out configuration for a future larger host. This milestone does not make single-node PostgreSQL/Kafka highly available.

The development source now includes per-database SHA-256 dumps, bounded operations and isolated restore checks, loopback Prometheus/Grafana health reporting, Nginx API limits and configurable stateless Helm replicas. Prometheus/Grafana/Python and M08 data-service image indexes are pinned in `devops/images.lock.json`; registry manifests include ARM64. Local image pulls/builds, automated checks and runtime acceptance remain pending the consolidated Stage 1 test pass.
