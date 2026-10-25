# ADR 0011 — Local request telemetry

2026-10-25 · Accepted for S1-M12; local runtime acceptance verified within the finite scope in the milestone evidence.

R28 expands ADR 0009 beyond service health. Use the OpenTelemetry Java agent for eleven Java services, an internal Collector, Prometheus request metrics, Tempo traces and Loki safe request logs, visualized in existing Grafana with admin/admin. The profile is explicit on the 16 GB host. All telemetry storage/export remains local; no host ports for ingestion/backends. Default SDK-disabled app images keep normal commerce independent of telemetry.

Retain only bounded route/method/status and selected database operation metadata. Export only a dedicated safe request logger; drop raw exceptions/application messages, headers, query/body/SQL values, personal identifiers and other resource data. Preserve trace/span relationships. This intentionally limits centralized log scope. Unit/config source cannot prove actual privacy; sentinel and linked-signal runtime tests are required.

Pin release versions/digests and a checksum-verified agent artifact, with ARM64 metadata and licence records. Retention is configured at 24 hours for traces/logs with bounded queues/resources, not a fixed disk guarantee. Image-preserving lifecycle commands recreate only running Java apps and persist project-local selection. Python/browser instrumentation and multi-node telemetry availability remain outside this initial scope. See S1-M12 design, dependencies and manual guide for targets versus evidence.

Runtime follow-up, 2026-10-25: actual five-case privacy/linkage/error/outage/restart acceptance, Grafana/API signals, image-preserving disable/re-enable and finite resource observation passed. Collector uses the pinned typed-slice nil setter for event/link removal; Grafana has an HTTP readiness gate. See S1-M12 verification for cold-start pressure, asynchronous observation and unavailable-review limits. Owner manual acceptance is separate.

Post-restart dashboard correction, 2026-10-25: enable the supported SQLite WAL option for the single local Grafana instance. The retained volume used DELETE journal mode, authenticated dashboard APIs stalled during SQL permission/resource-lease work, and the focused browser gate passed after WAL recreation with unchanged assertions/deadlines. First-run login prompt synchronization is explicit. See M12 evidence for measured outcomes and retained failed attempts; this does not introduce another database service or change commerce data.
