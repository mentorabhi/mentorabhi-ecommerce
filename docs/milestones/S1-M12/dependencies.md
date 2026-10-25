# Dependency selection — 2026-10-25

Metadata checks performed during coding; no image has been built/run as an acceptance test in this phase.

| Component | Selected stable version | Registry index digest | ARM64 |
| --- | --- | --- | --- |
| Collector contrib | 0.163.2 | `7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849` | linux/arm64 advertised |
| Tempo | 3.1.1 | `64e2fbd56d9c2b3412a4b430a58ea59e91a670b1e75f920a0c702213ad145044` | linux/arm64 advertised |
| Loki | 3.7.9 | `0db216b630ae1f348a1584c67f3cead8b4c1fc839169a39501db664744158e28` | linux/arm64 advertised |
| Java agent | 2.33.0 | JAR SHA-256 `5f9d1f10056ed2b246fbb19543519b8066cda23d6aff19022dbdb84402d6c3ab` | architecture-independent Java; Java 27 runtime gate pending |

Selection uses the official GitHub `/releases/latest` metadata for open-telemetry/opentelemetry-collector-releases, grafana/tempo, grafana/loki and open-telemetry/opentelemetry-java-instrumentation. Published respectively 2026-10-21, 2026-10-21, 2026-10-20 and 2026-10-23. Registry `docker buildx imagetools inspect IMAGE --raw` showed platform descriptors; `--format '{{json .Manifest}}'` confirmed index digests. Agent digest comes from the official GitHub release asset. Exact image references are in devops/images.lock.json.

Licensing: Collector/agent Apache-2.0, Tempo/Loki AGPL-3.0. Source references and configuration documentation are linked from the design. Existing Java/Spring/Prometheus/Grafana versions are retained to avoid unrelated upgrades. Compatibility, config parsing, signal linkage, resources and privacy are unverified until the final test phase. Collector processors have upstream stability levels distinct from stable release packaging: transform is beta and filter alpha in current upstream docs; record this implementation limitation rather than claiming every component API is stable.

Source review caught Tempo 3's incompatible removal of ingester/compactor blocks. The authored configuration now uses the monolithic live-store and backend-scheduler compaction provider, without adding another Kafka dependency. See the official [migration guide](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/) and [configuration](https://grafana.com/docs/tempo/latest/configuration/). This is a documentation-based compatibility correction, not a runtime config-validation pass.

Runtime follow-up: the pinned ARM64 images were pulled and native config validators passed. Java 27 started all eleven instrumented service images successfully, and live HTTP/JDBC/cross-service spans, metrics/log linkage and privacy tests passed. Collector distrib 0.163.2 uses contrib component code 0.163.0; its typed-slice nil setter contract resolved the runtime event/link clearing error. See verification.md for actual tests and finite resource evidence; earlier pending language above is retained as metadata-checkpoint history.
