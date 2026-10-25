# S1-M12 — Local request telemetry and logs

2026-10-25 · R28 / AE28 · Engineering and local automated acceptance complete; owner manual review remains separate.

The eleven Java services have a pinned OpenTelemetry agent, safe request filters and local OTLP pipeline to Collector, Prometheus, Tempo and Loki. Grafana at http://localhost:3001 uses admin/admin. The explicit profile preserves current images/History target and supports verified disable/re-enable. Python/browser instrumentation and arbitrary application/exception logs are outside this initial scope.

Read the [design](design.md), [editable flow](telemetry-flow.mmd), [dependency pins](dependencies.md), [measured verification](verification.md), [setup guide](../../setup/request-telemetry.md) and [manual checklist](manual-acceptance.md). Five live privacy/linkage/error/outage/restart cases, actual Grafana metric queries, browser acceptance and lifecycle checks passed. The finite 24-container/120-second resource observation peaked at 6,369.28 MiB; cold resource pressure and retention/endurance limits are documented.

## Historical intake and coding checkpoint

# S1-M12 — Local request telemetry and logs

2026-10-25 · Local engineering acceptance complete · R28 / AE28

The user's updated requirements/project_requirement.txt explicitly requests OpenTelemetry plus response-time/log visualization. ADR 0009's implemented Prometheus readiness dashboard does not satisfy this follow-up. Plan local instrumentation, a bounded OpenTelemetry pipeline and local metrics/trace/log storage with Grafana; verify official stable compatible versions and ARM64/resource support before implementation.

Required before implementation: reviewed design, editable data flow, dependency/retention/privacy/resource decisions, test plan and manual end-user checklist. Every operational UI uses the R23 local admin/admin login. No hosted telemetry service or model endpoint.

Coding checkpoint: [reviewed design](design.md), [editable flow](telemetry-flow.mmd), [dependency metadata](dependencies.md), [manual checklist](manual-acceptance.md) and [verification record](verification.md) now exist. Source adds pinned agent integration, safe Java request logging, Collector privacy pipelines, local Tempo/Loki, Grafana data sources/request dashboard and explicit image-preserving telemetry lifecycle. Unit/integration/Selenium cases are authored; no new test/build execution has occurred under the user's coding → data → testing order. Runtime compatibility, configuration parsing, cross-service signal linkage, privacy, restart and memory gates remain open.

Latest testing checkpoint: pinned images and agent are built/deployed, native config parsing passes, five live signal/privacy/cross-service/error/outage/restart cases pass, and Grafana Selenium passes. A 24-container/120-second commerce regression observation peaked at 6,369.28 MiB. Explicit telemetry disable preserved actual images/History target and left all eleven Java services ready. Actual image-preserving re-enable, final dashboard operations checks and closure documentation are recorded in the verification record and Stage 1 acceptance. The intake/source-only paragraphs above preserve the original planning history, not current pending work.
