# Verification — S1-M12

2026-10-25 coding phase. Design and editable flow reviewed; dependency selection is sourced metadata, not runtime evidence. Implementation and tests are being authored. No new tests/builds are executed until remaining code and real catalog data are ready, following the user's explicit sequence. No telemetry acceptance criterion is marked passed.

Source checkpoint includes agent build checksum, independent Java safe request filters and unit cases, Collector allowlists and local stores, Grafana data sources/performance dashboard, project-local image-preserving lifecycle and unit cases, real signal/privacy integration source and Selenium dashboard extension. Official registry metadata advertises ARM64 for all three new images; exact digests and release metadata are recorded in dependencies.md. Host source review corrected Tempo 3 configuration blocks using the official migration/configuration guide. Actual collector parsing, Java 27 agent behavior, metrics naming, span/log linkage, resource use, restart and disable/outage behavior remain pending.

The formal review attempt 01a1723f-4c87-76c3-b393-f008ac899c2d returned failed/unavailable because its worker lacked nested native dispatch required by the skill; no clean review receipt exists. **Code review: skipped (ce-code-review unavailable)**. Host manual diff scan covered default-disabled SDK behavior, local-only exports/ports, scope/body filtering and attribute allowlists, current-image preservation, project-scoped state, stop ordering and independent service builds. Simplification retained intentional per-service filter duplication and extracted deterministic coupon fixture preparation. No tests were removed or executed. Source-only checkpoint; not a deployment/acceptance sign-off.


## Final testing phase started — 2026-10-25

After the real catalog population, normal test-enabled builds completed for all thirteen app images, including the pinned Java agent download/checksum. Consolidated unit results are recorded in S1-M11 verification; the eleven request-filter unit cases and Devops lifecycle cases passed. Collector 0.163.2 `validate --config=...`, Tempo 3.1.1 `-config.verify=true` and Loki 3.7.9 `-verify-config=true` all exited zero with their actual pinned images/configurations. Collector validation also passed after clearing incoming tracestate. These are build/config parsing observations, not live signal acceptance.

Started explicit telemetry-up with current image IDs and persisted History database/group. Heavy analytics/graph/dashboard-studio profiles remain stopped; Kafka UI was stopped after its passing browser test to release memory. Live signal/privacy, cross-service linkage, fault/restart/disable and resource checks are still in progress.


### Live signals, privacy and fault checks

Initial real-request test failed after 61.547 seconds because Collector rejected `set(events, [])` at runtime despite native config validation passing. A direct internal OTLP probe with nonempty event/link/trace-state sentinels also failed. The pinned contrib v0.163.0 typed pdata setter accepts nil as an empty typed slice; changed events/links to `set(..., nil)`, retaining propagate-on-error. The first immediate restart probe arrived before the Collector receiver was ready; the subsequent direct probe passed 1/1 in 3.310 seconds. No unsafe fallback/export relaxation was introduced. Source inspection: [typed slice setter](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.163.0/pkg/ottl/contexts/internal/ctxutil/slice.go).

Clean combined command: `SUPERSPORTS_TELEMETRY=1 SUPERSPORTS_TELEMETRY_FAULTS=1 .venv/bin/python -m unittest discover -s devops/tests -p test_request_telemetry_integration.py -v` passed **5/5 in 64.176 seconds**. Real local pipeline covered:

- Real Catalog HTTP request → Prometheus request-duration count, sanitized server/JDBC spans in Tempo and matching safe trace-ID log in Loki. Query/header/tracestate sentinel, SQL text and exception text absent.
- Direct internal OTLP fixture with nonempty events, links, status message, private resource/span fields and incoming tracestate → stored span with none of the sentinels/events/links/tracestate. This separately proves runtime transformation rather than config parsing.
- Owned Orders tracking → Fulfillment server span with parent matching an Orders client span; raw order ID absent from stored trace.
- Pricing outage → deterministic Catalog 502, corresponding server-error metric, sanitized failed trace and unchanged Catalog status/revision; Pricing recovered.
- Collector outage → five successful Catalog reads plus readiness; export resumed after recovery. Stored trace remained queryable after Tempo/Loki restart. This does not promise lossless telemetry during outages.

Grafana Selenium: `SUPERSPORTS_M09_LIVE_ACCEPTANCE=true SUPERSPORTS_TELEMETRY=1 .venv/bin/python -m unittest discover -s apps/storefront/tests -p test_ops_ui.py -v` passed **1/1 in 11.839 seconds**: admin/admin login, health dashboard, all four request-panel titles and Explore navigation. Panel existence is separate from the actual signal/API assertions above. Logs: `s1-m12-five-signals-final.log`, `s1-m12-grafana-browser.log` under ignored verification storage. Devops final unit discovery passed **147 discovered /102 executed /45 explicit live skips in 1.500 seconds**.

### Resource observation with full commerce and telemetry

Measured 24 containers during the 25-case commerce integration, including its intentional Orders stop/start. The initial run passed 24 and failed the old service-inventory check because it did not recognize the three new private telemetry services (84.763 seconds). Added the services and required no host publication for Collector/Tempo/Loki; focused rerun passed 1/1 in 1.507 seconds. Other currency, stock, refund, idempotency, ownership and worker-restart cases passed with SDK enabled.

Seventeen samples over a 120-second window peaked at **6,369.28 MiB** aggregate Docker usage; all measured containers remained present/running at the end, no OOM or automatic restart-counter increase. The workload includes the explicitly exercised Orders stop/start; do not call that an uninterrupted run. Snapshot: Collector 81.99/192 MiB, Tempo 100.4/384 MiB, Loki 87.13/256 MiB, Grafana 277.5/512 MiB; History 694.7/768 MiB. Heavy analytics/graph/dashboard-studio and Kafka UI were stopped. This is bounded functional/regression evidence, not a throughput or 24-hour endurance claim.

Read-only local volume snapshot: Tempo 7,488 KiB, Loki 860 KiB, Prometheus 4,552 KiB. Trace/log retention remains configured for 24 hours; observed sizes are not disk quotas. Private machine-readable evidence: `s1-m12-resources.json`, `s1-m12-container-memory.txt`, `s1-m12-volume-sizes.json`. Disable/re-enable and remaining operations checks continue.


### Disable lifecycle

`telemetry.switch(..., enable=False)` passed on the real profile: all thirteen running application image identities remained identical, the persisted History database/group stayed identical, SDK selection became disabled, all eleven Java readiness endpoints returned 200 and public Catalog stayed available after telemetry backends stopped. Evidence: `s1-m12-disable.log` and private `s1-m12-disable-receipt.json`. This checks actual runtime/image selection rather than mocks. Re-enable is recorded separately once complete.

The follow-up five simplification reviewers terminated at the session usage limit without findings/coverage receipts. Host inline passes used their loaded reuse, quality, efficiency, test-value and comment rubrics: no further behavior-preserving changes were justified, and proof tests remained intact. Formal review remains **Code review: skipped (ce-code-review unavailable)** for the documented terminal native-dispatch failure; host manual diff scan covers exact pinned typed-slice semantics, strict privacy/error propagation, private ports, real trace parent linkage, fault cleanup and owner state preservation. Do not present these scans as completed independent code reviews.


### Re-enable startup correction and live lifecycle result

The first re-enable attempt failed before changing SDK selection because Grafana was merely started, not HTTP-ready, when /api/user verification ran. Added a Grafana container-local wget /api/health check so Compose's existing --wait gates account provisioning. The binary was verified in the pinned image. This is a pure readiness configuration fix; existing lifecycle unit coverage is retained and the actual stopped-service reproduction provides the regression evidence.

Stopped Grafana, then reran telemetry enable from the SDK-disabled state. The full operation **passed** with the HTTP health gate: all thirteen actual application image identities and the persisted History database/group were preserved, all eleven actual container OTEL_SDK_DISABLED values became false, every Java readiness endpoint returned 200 and Grafana's Docker HTTP health status was healthy. No secret environment values were stored in evidence. `s1-m12-reenable-final.log` and `s1-m12-reenable-receipt.json` record the result. Final Collector native config validation also exited zero after the nil-clearing fix.


Final cold-start gate observation: after identity restart with Kafka UI plus telemetry (25 containers), the first full commerce run passed 23/25 and hit the unchanged five-second host client timeout for one checkout and one full Catalog admin read (177.745 seconds). No assertion/deadline was relaxed. Docker VM pressure at diagnosis showed memory full-stall avg60 12.49% and CPU some-stall avg60 37.09%; no OOM was observed. Three subsequent admin reads returned 200 in 1.025/0.332/0.338 seconds, public reads in 0.377/0.270/0.043 seconds. This records a cold/resource-pressure limitation, not an authorization failure or a verified cold-start response-time SLO. Logs/data: `s1-release-core-cold.log`, `s1-release-latency-diagnostic.json`, `s1-release-slow-memory.txt`. A clean rerun retains the same request timeout and assertions; its outcome is recorded separately below.


Final warm commerce rerun passed **25/25** with unchanged timeouts/assertions (runner 115.961 seconds). The following telemetry run passed four checks and exposed a shared probe defect during backend restart: Grafana returned a non-JSON HTTP error and JSON decoding inside the HTTPError handler escaped its sibling exception guard (five cases/one error, 102.829 seconds). Added a unit regression with plain text, HTML and invalid-encoding error bodies; it first failed in all three subcases. The helper now preserves the actual HTTP error status with an empty body, closes the response and never returns raw error text. Valid JSON error responses remain unchanged. The full management unit suite passed **33/33 in 0.122 seconds**. The final live gate reruns after this fix; no wait/transport timeout or functional assertion was relaxed. Evidence: `s1-m12-http-error-red.log`, `s1-m12-manage-final.log`, `s1-release-telemetry-before-http-fix.log`.


### Final M12 acceptance

After the HTTP helper fix, a follow-up live run passed three and failed two asynchronous assumptions (121.662 seconds): a partial trace had both service names before its required parent edge, and one request issued immediately after Collector start was legitimately lost during exporter recovery. A direct diagnostic recorded Orders-only batches from 3.808 seconds until the linked Fulfillment edge at 10.813 seconds. Changed only the observation predicates/workload: wait for the actual parent edge, and issue successful safe reads through recovery until a trace arrives, preserving the original 60-second bounds and all relationship/privacy/availability assertions. Bounded-loss telemetry remains explicitly allowed; no lossless claim is added.

The final clean **5/5 live suite passed in 123.512 seconds**, with all privacy, error metrics, cross-service parent linkage, Collector-outage commerce availability and retained-trace backend restart checks executed. Log: `s1-release-telemetry-clean.log`. The final Devops unit rerun passed **148 discovered /103 executed /45 explicit live skips in 0.662 seconds**. Normal application test-enabled builds and real PostgreSQL gates remain recorded in M11.

Queried each actual provisioned Grafana dashboard expression through its Prometheus datasource proxy using Catalog and a five-minute interval. All four returned nonnegative finite values: requests/sec 0.25960, server errors/sec 0.003508, p95 0.315 seconds and mean 0.10504 seconds. This synthetic observation includes probes and the deliberate 502 case; it is not a production latency SLO. Evidence: `s1-m12-dashboard-values.json`. Grafana browser login/panel/Explore and actual datasource values are independently verified.

M12's engineering/runtime gates are complete within this documented local scope. Owner manual acceptance remains unchecked. Later final Stage 1 browser/history checks are recorded in the stage completion record, without changing these finite measurements.
