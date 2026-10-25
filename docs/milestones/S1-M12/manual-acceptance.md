# End-user manual acceptance — request telemetry

These checks are separate from automated tests. Leave unchecked until a person performs them. Runtime setup/instructions and exact measured scope will be added with implementation evidence.

- [ ] Start the documented telemetry profile. Inspect Docker service state and restarts for Collector, Tempo, Loki, Prometheus, Grafana and commerce. Confirm optional graph/analytics are not required.
- [ ] Open http://localhost:3001 and sign in with admin/admin. Open the SuperSports request dashboard and select a Java service/time range.
- [ ] Browse http://localhost:3000, open a product and use search. Confirm dashboard request rate, error count and response-time panels update.
- [ ] Perform a simulated quote/checkout with your own customer account. Find its server/client/database spans in Grafana Explore. Confirm spans cross service boundaries where that journey makes HTTP calls.
- [ ] Open a related safe request log and follow its trace link. Check method, templated route, status and elapsed time; verify submitted query/body/address and credentials are absent.
- [ ] Generate a controlled invalid request and inspect the error metric/log without exposing personal data. Confirm unmatched paths are labelled UNMATCHED.
- [ ] Check the relevant order in the owning Orders database using DBeaver and compare its normal authoritative state. Telemetry adds no commerce rows or cross-service table reads. Inspect local Tempo/Loki volume sizes as telemetry storage rather than expecting telemetry tables in PostgreSQL.
- [ ] Restart telemetry, repeat Grafana login and inspect retained data. Disable telemetry and confirm storefront/checkout still work. Re-enable using the documented command.
- [ ] Record actual memory/storage observations and any failure below. A 24-hour retention setting does not prove a completed 24-hour endurance test.

Tester/date, app revision, profiles, result, evidence and follow-up: pending.
