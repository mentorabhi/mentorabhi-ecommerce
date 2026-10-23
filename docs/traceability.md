# Traceability register
Revision 2 · 2026-10-23. S1-M02 bootstrap scope is implemented; future product milestones remain planned.

| Requirement | Journey / owner | Contract / data | Design | Milestone | Verification / target | Release |
|---|---|---|---|---|---|---|
| R01/R02/R09 | Catalog/admin; Catalog, Pricing, Inventory | Catalog/price/stock APIs | design/S1-M01/architecture.md | S1-M03 | AE01/AE11; deterministic fixtures, access checks | Pending |
| R03/R05/R18 | Customer discovery; Storefront, Cart | Browse/cart/profile APIs | design/S1-M01/architecture.md | S1-M04 | AE02/AE04/AE20; isolation, responsive E2E | Pending |
| R04/R06/R07 | Purchase; Pricing, Orders, Inventory, Payments | Quote/checkout/Saga | design/S1-M01/architecture.md | S1-M03/M05 | AE03/AE05–AE09; unit, real DB concurrency, recovery | Pending |
| R08 | Post-purchase; Orders, Engagement | Return/refund/review contracts | architecture/stage-1/S1-M07.excalidraw | S1-M07 | AE10; original-value refund and ownership | Pending |
| R10 (bootstrap foundation) | Configuration; Configuration, Platform admin | Read-only migration registry/API; runtime activation and UI later | design/S1-M02/bootstrap.md | S1-M02; activation S1-M04 | 12 live integration checks include roles, redaction, non-mutating methods; activation pending | S1-M02 verified |
| R11/R12/R13 (bootstrap profile) | Bootstrap/operator; devops | Local Docker Compose profile; alternate deployment artifacts | design/S1-M02/bootstrap.md | S1-M02; expanded profiles S1-M09 | `devops/scripts/ci`, measured RSS snapshot, local-only services; no cluster provisioning | S1-M02 verified |
| R14 | Streaming/data; service owners, pipelines | Outbox/events/projections | architecture/stage-1/S1-M06.excalidraw | S1-M06/M08 | AE08/AE14/AE15; replay and reconciliation | Pending |
| R15 | Shopping assistance; Nova | Typed tools/RAG/memory | architecture/stage-2/S2-00.excalidraw | S2/S3 | AE16–AE19; local inference/evaluation, approval | Pending |
| R16/R17 (S1-M02 artifacts) | Developer/student; service and devops projects | Unit/integration suites, milestone evidence, ADR/lesson | docs/testing/strategy.md | Every milestone | 16 Python unit, 18 Java unit, 12 live integration tests; review partial due two usage-limit failures | S1-M02 verified with review limitation |
| R19 (S1-M02 pins) | Dependency selection; devops and service owners | Compatibility/version/image digest record | docs/decisions/0001-local-first-monorepo.md | S1-M02 onward | Official source/version and ARM64 checks documented; no SBOM/security scanner claimed | S1-M02 verified |
| R20 | Stage gates; project owner | Stage acceptance | docs/context/project-context.md | S1 → S2 → S3 | Baseline plan stage exit gates | Pending |

Detailed endpoint/event names, automated test paths and numeric targets will be added at each implementation milestone, not fabricated before contracts exist.
