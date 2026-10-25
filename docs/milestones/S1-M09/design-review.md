# S1-M09 design review

Revision 2 · 2026-10-24 · Reviewed against the S1-M09 architecture, local-only requirement, 16 GB ARM64 development host, and existing Compose/Helm profiles.

- **Data safety:** restore uses a distinct project name/volume and explicit cleanup for that name only. Backup files stay ignored and mode 0600/0700. No destructive restore runs against the active project.
- **Recoverability:** PostgreSQL database dumps are independent and custom format; restore targets are provisioned from the repository's current SQL roles. Kafka topics and offsets are not included in database backups. Existing CDC WAL/outbox and Kafka retention remain separate recovery inputs.
- **Claims:** local single-node service has no HA. RPO/RTO are proposed drill targets, not observed. Service health dashboard does not claim traces, logs, application latency or Kafka lag.
- **Availability:** ingress limits are explicit and local. Health probes expose only readiness status, not component details or credentials.
- **Capacity:** Prometheus/Grafana/health exporter are opt-in and resource-capped. Backup/restore drills are selective and not concurrent with Spark analytics or peak load.
- **Scale path:** Helm replica/resource values support stateless services on larger hosts; stateful replication remains an architecture/deployment prerequisite.
- **Decision:** the reviewed design is ready and exact image index digests/platform manifests are pinned. Local image/build/runtime verification is still deferred.

## Implementation-owner source review

- Backup database names map to owner roles from one fixed allowlist. Output is local-only, mode-restricted, and includes no role password. Restore input must be a direct child of the ignored backup root; files are checked for symlinks, sizes and hashes before the disposable project is started.
- The restore project's name is generated independently of the active project. All `up`, `exec`, and `down --volumes` calls use that temporary project name. The restore service does not publish a port or join the active project network. Restore checks connected database identity and table count; a source database with zero application tables is valid and remains zero.
- Cleanup is in `finally` and a cleanup error is surfaced. No tests were run to prove these behaviors yet.
- Nginx bounds apply only to `/api/` request rate/connections; empty map keys exclude static files and health checks. Request body size is limited to 1 MiB.
- Health exporter reads only readiness/TCP outcomes and emits fixed service labels. Its dashboard is optional, local and coarse. It does not claim full telemetry.
- The former Grafana `13.3.0` selection had no corresponding Docker image tag. It is corrected to stable `13.2.2`; Prometheus, Grafana, Python, Neo4j, Trino, Spark and Superset image index digests are now pinned and their manifests include ARM64. Restore, cleanup-under-failure, Nginx status, and Grafana provisioning remain unexecuted runtime gates.
- Sequential per-database dumps do not represent one atomic cluster-wide point in time; manifest timestamps and post-restore owner reconciliation expose this boundary.

Consolidated acceptance correction (2026-10-24): restored table counts alone do not prove content. During the isolated drill, compare canonical COPY-row and sequence fingerprints from each verified custom dump with a fresh data-only dump of the restored database. Sort rows within tables, retain duplicates and sequence state, and ignore nondeterministic dump comments/restriction tokens. Only hashes leave process memory. This proves backed-up content without reading changing live services during the restore; it does not make the sequential source dumps a cross-database transaction.
