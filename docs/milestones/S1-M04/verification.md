# S1-M04 verification record

Revision 2 · 2026-10-24 · Final full CI completed; owner manual acceptance remains open.

This record reports automated and runtime evidence. End-user manual checks remain in [manual acceptance](manual-acceptance.md) and are pending owner execution.

## Verification matrix

| Check | Command / method | Outcome |
|---|---|---|
| Python operations unit tests | `./devops/scripts/ci` | Passed: 22 tests |
| Java service tests | Maven `verify` for Catalog, Configuration, Pricing, Inventory and Customer (inside full CI) | Passed: 9 + 8 + 7 + 8 + 4 = 36 tests |
| Compose, Helm and Terraform | `./devops/scripts/ci` | Passed; no cloud provisioning |
| Live integration and contract/security regressions | `./devops/scripts/ci`, 17 integration cases (including recovery rerun) | Passed twice: 17 before and 17 after recovery |
| Service/DB recovery | `./devops/scripts/ci` recovery profile | Passed: application restart, DB outage readiness/liveness, DB reconnection, identity token recovery |
| Selenium browser flows | `./devops/scripts/ci` | Passed: five journeys, including customer self-registration and data isolation |
| Playwright browser flows | `cd apps/storefront && npm run test:e2e`, three tests | Passed on final source |
| Frontend production build | `cd apps/storefront && npm run build` | Passed |
| Storefront container image | `./devops/scripts/supersports up` | Built and ran locally |
| Customer DB migration and aggregate ownership counts | Read-only SQL in the manual acceptance guide | Passed: migration 1 succeeded; 12 profiles, 6 cart owners / 6 items, 7 wishlist owners / 7 items at query time |

## Browser regressions added from review

- Direct Football category deep link resolves the `football-equipment` slug, displays the category, and returns its three products.
- Searching from Account switches the view back to shop results.
- Adding the same SKU twice increments cart quantity to two.

## Environment and limits

The local environment reported Docker 29.8.0, `aarch64`, 7.75 GiB Docker RAM allocation, and Python 3.14.7 with the repository `.venv`. The frontend image uses pinned Node 24.22.1 and Nginx 1.29 Alpine. Service base images and application versions are pinned in the devops manifests. One post-test `docker stats` sample measured 2,112.6 MiB combined RSS across eight containers. This single sample is not a peak or load test; full 16 GB machine capacity and production-like throughput remain unverified. Maven printed non-blocking warnings while checking optional metadata on private repositories; dependencies resolved and every build passed. No real payment, shipping, cloud service, or hosted model was used. Ollama is not required for this commerce milestone.

## Remaining manual acceptance

The owner must run the separate checklist in a browser and record results, including the user-facing flows, service health, and read-only database checks. The aggregate query above was run for implementation verification; it does not mark the owner's manual checks complete.
