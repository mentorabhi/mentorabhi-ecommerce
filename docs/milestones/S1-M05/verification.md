# S1-M05 verification record

Revision 3 · 2026-10-24 · Checkout Saga and simulator implementation evidence. Manual owner acceptance and deeper fault-boundary coverage remain open.

## Automated and live checks completed

| Check | Command / evidence | Result |
|---|---|---|
| Python and Java unit tests | `./devops/scripts/supersports unit` | 23 Python tests passed. Java suites passed: Catalog 10, Configuration 12, Pricing 13, Inventory 13, Customer 4, Orders 8, Payment Simulator 4, Fulfillment Simulator 2 (66 total). |
| Full profile rebuild | `./devops/scripts/supersports up` | Rebuilt all nine application images and started the 11-container profile; all containers reached healthy status. Images use pinned base image digests. |
| Core integration | `./devops/scripts/supersports test` | 22 tests passed. Includes customer checkout and owner isolation, quote and configuration revision checks, simulated decline compensation, separate service databases, API audience boundaries, and Orders restart/resume. |
| Storefront browser journeys | `./devops/scripts/supersports ui-test` | All six Selenium journeys passed, covering customer registration/profile/cart, checkout/order detail and fulfillment status, admin configuration/audit, inventory, pricing, catalog and mobile navigation. |
| Runtime migrations and readiness | Healthy Compose profile and integration assertions | Orders, Pricing, Inventory, Configuration, Payment Simulator and Fulfillment Simulator migrations applied successfully; readiness probes passed. |
| Storefront health | `curl -fsS http://localhost:3000/healthz` | `ok`; storefront URL is http://localhost:3000 and operator UI is http://localhost:3000/admin. |
| Checkout persistence | Read-only SQL against local service-owned databases | Orders: 10 `FULFILLMENT_SCHEDULED`, 13 `FAILED`, no nonterminal orders after recovery. Payment ledger: 10 `AUTHORIZED`, 10 `CAPTURED`, 4 `DECLINED`. Fulfillment ledger: 10 `SCHEDULED`. The failed rows include simulated declines and expired test quotes; expired legacy quotes fail before stock reservation. |
| Source whitespace | `git diff --check` | Passed after implementation changes. |

## Resource snapshot

The prior full-CI `docker stats --no-stream` sample recorded approximately 3,195 MiB across 11 containers with Docker allocated 7.75 GiB on `aarch64`; this is a single idle/short-run snapshot, not peak or concurrency evidence. Application container memory limits are documented in Compose. Startup, peak load and concurrency resource measurements remain open.

## Remaining verification gates

- Manual end-user acceptance remains pending; all checkboxes in [manual-acceptance.md](manual-acceptance.md) are intentionally unchecked.
- Exercise additional failure boundaries, especially stale worker fencing across each external step and failure/retry while payment capture or inventory commit is in flight.
- Define and verify the audited operator resolution path for any Saga requiring manual review.
- Measure concurrent checkout and full-profile peak memory on the 16 GB baseline, then validate deployment sizing on a larger host.

Automated evidence does not imply completion of these manual and operational gates.
