# Local health exporter

This optional service checks readiness URLs and TCP ports listed in `devops/observability/health-targets.json`, then serves Prometheus gauges on port 9108 inside the Compose network. It has no host port and exposes only service name, up/down, and probe duration. It does not read health response bodies, credentials, orders, or customer data.

Local unit, Prometheus profile, Grafana dashboard and service-failure manual checks are defined under `services/health-exporter/tests` and `docs/milestones/S1-M09/manual-acceptance.md`. No M09 test/build/profile has run yet.
