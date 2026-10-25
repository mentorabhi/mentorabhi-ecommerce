# Request metrics, traces and logs

Verified local signals include request metrics, server/client/JDBC traces, linked safe logs, privacy sentinels, dependency/Collector outages, backend restart and Grafana browser navigation. See [measured evidence](../milestones/S1-M12/verification.md) for commands, resource observations and limits. Enable this profile separately from heavy analytics/graph jobs.

Rebuild/deploy the Java apps with the pinned OpenTelemetry agent before enabling it. Agent download is checksum-verified during setup/build, never a hosted runtime dependency. Services are SDK-disabled by default. The lifecycle command rejects older running images without an agent entrypoint.

```sh
devops/scripts/supersports telemetry-up
devops/scripts/supersports status
devops/scripts/supersports telemetry-down
```

`telemetry-up` starts local Collector, Tempo, Loki, Prometheus and Grafana, then recreates only the currently running Java commerce/history apps using their actual image IDs and current History database/group selection. It does not launch the optional data/graph profiles. The SDK selection is project-specific ignored local state and persists across normal restarts. `telemetry-down` disables exporters and recreates apps before stopping telemetry backends. If a recreation fails, inspect state and repeat the same operation; do not delete volumes or guess release image tags. The existing `observability-up` remains the health-dashboard lifecycle and does not enable agent exporters.

Grafana: http://localhost:3001, username **admin**, password **admin**. Open **SuperSports request performance** for traffic, server errors, mean/p95 response time. Select service/time range. Use Explore → Tempo for distributed spans and Explore → Loki with `{service_name="catalog"}` for safe request logs. Trace-to-log and log-to-trace links are provisioned. Request instrumentation initially covers eleven Java services; browser and Python analytics/graph instrumentation are not included. Safe Loki logs deliberately exclude arbitrary application exception/message logs; console diagnostics remain available locally.

No Collector/Tempo/Loki host port is exposed. Grafana queries them internally. Request logs contain templated route, method, status, elapsed time and trace ID, without submitted bodies, URLs/queries, credentials, addresses or exception text. Collector allowlists and fail-closed transform errors enforce the exported scope. The explicit live sentinel suite verifies actual stored output; see the evidence record. See [design](../milestones/S1-M12/design.md) for scope, versions and proposed resource/retention bounds, and [manual checks](../milestones/S1-M12/manual-acceptance.md) for human service/UI/database acceptance.

Tempo/Loki retain 24 hours by configuration on local named volumes; this is not a disk quota or measured 24-hour endurance claim. Collector queues are bounded and may lose telemetry during outages. Commerce databases remain authoritative. A 120-second regression window with 24 containers peaked at 6,369.28 MiB; this is not a long-duration capacity guarantee. Keep analytics/graph/dashboard studio selective, and avoid simultaneous profile startup bursts on the 16 GB host.
