# Project status

Updated: 2026-10-26 · Active branch `stage1` · Stage 1 engineering release complete.

Stage 1 development, data, automated verification and documentation are complete within the recorded local acceptance scope. The final post-restart commerce, telemetry, browser and retained-history gate passed. No user input is required to finish Stage 1 engineering work. Owner manual review remains separate.

- Storefront: http://localhost:3000, separate customer account/self-registration.
- Admin: http://localhost:3002/admin, **admin/admin**.
- Grafana: http://localhost:3001, **admin/admin**.
- Kafka UI: http://localhost:8091, **admin/admin**.
- Optional operations interfaces and profile commands: [access guide](../setup/ui-access.md). Heavy analytics/graph/dashboard-studio remain selective on the 16 GB host.

The active sourced catalog contains **103 Cricket products/1,030 SKUs** and **113 Football products/1,130 SKUs**, INR/USD prices, local source photographs, stock and **751 published DEMO reviews**. Product-scoped coupon fixtures are present. Old/test products are retired; historical orders and the prior-year synthetic customer/order dataset remain intact. [Data/provenance](../milestones/S1-M11/data-population.md).

Current measured evidence includes normal test-enabled app builds; Java/Devops/data/frontend units; real PostgreSQL Catalog/Reviews checks; core commerce, streaming recovery/gap/fallback and post-purchase integration; sourced-data replay and photo hashes; separate Admin/customer browser journeys; operational logins; five live OpenTelemetry privacy/linkage/error/outage/restart cases and Grafana Selenium. Actual telemetry disable/re-enable preserved images/History target, with all eleven Java services ready. See [M11 verification](../milestones/S1-M11/verification.md) and [M12 verification](../milestones/S1-M12/verification.md) for exact counts, commands, failures and passing reruns.

The 24-container, 120-second telemetry/commerce observation peaked at **6,369.28 MiB**. It includes intentional Orders stop/start and does not establish maximum throughput or 24-hour endurance. M06 separately records its finite 900-second soak and retained-WAL/idle-group recovery. Single-node local profiles are not multi-broker HA or a cloud deployment.

Owner manual checklists remain **unchecked**, separate from engineering/automated verification. Start with [Stage 1 owner verification](../testing/stage1-release-checks.md), which links every milestone's service/UI/feature/database guide. No owner sign-off is claimed.

Nova belongs to the next stage and is not implemented. Host-installed Ollama remains its prerequisite; no Ollama container or hosted AI fallback is used. A new stage must use a new branch, for example `stage2`.

Latest UI corrections are deployed: portrait pad photos stay above card text, promotional storefront banners are removed, and equipment search uses whole-word/type-aware relevance. Live bat/bats returns 13 bats, ball/balls 25 balls, pads 24 pads. Catalog verification passed 26/26 with real PostgreSQL and the affected catalog Selenium file passed 4/4. Checkpoints 9304c08 and a933ed2 are pushed to stage1.

Final restored runtime has 25 running containers, configured healthchecks healthy, with a single 6,453.52 MiB memory snapshot. Heavy analytics/graph/studio profiles remain selective.

Final retained-history reconciliation: 36,537 events /18,077 orders, ok=true and zero errors. Grafana's post-restart SQL dashboard stall was corrected with supported SQLite WAL storage; native login/dashboard/Explore Selenium passed. Keycloak login passed after identity restart. Consolidated [release evidence and limitations](stage1-completion.md) distinguish explicit fixture/profile skips from separately executed live gates and retain earlier failed diagnostics.

Earlier dated status is preserved in [the pre-closure history](status-before-stage1-close-2026-10-25.md). Original planning inputs and their historical meanings remain unchanged.
