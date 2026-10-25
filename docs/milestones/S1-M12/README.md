# S1-M12 — Local request telemetry and logs

2026-10-25 · Requirement intake · R28 / AE28

The user's updated requirements/project_requirement.txt explicitly requests OpenTelemetry plus response-time/log visualization. ADR 0009's implemented Prometheus readiness dashboard does not satisfy this follow-up. Plan local instrumentation, a bounded OpenTelemetry pipeline and local metrics/trace/log storage with Grafana; verify official stable compatible versions and ARM64/resource support before implementation.

Required before implementation: reviewed design, editable data flow, dependency/retention/privacy/resource decisions, test plan and manual end-user checklist. Every operational UI uses the R23 local admin/admin login. No hosted telemetry service or model endpoint.
