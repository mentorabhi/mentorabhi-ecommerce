# ADR 0002 — Merchandising currency and stock ownership

Date: 2026-10-23 · Status: accepted for S1-M03 implementation.

## Context

S1-M03 needs extensible sports products, currency prices and coupons, operator stock adjustments, and deterministic demo fixtures. These are connected in the user workflow but have separate correctness and data ownership rules. The M02 bootstrap also has a static `store.currency=INR` configuration registry row; active pricing must have one runtime authority.

## Decisions

1. Catalog, Pricing and Inventory are independent service projects with separate databases, roles and migrations. Cross-service references use IDs and service APIs; services never query another service's tables.
2. Catalog owns sport/category taxonomy, attribute schemas, products and SKUs. Category attributes are schema data, not source-code sport enums. Product/SKU updates use optimistic revisions and append audit records with actor and revision transition.
3. Pricing is the only runtime authority for active store currency. M02's `store.currency` row remains a bootstrap descriptor, not a competing mutable setting. INR and USD start enabled; every SKU needs a price in both books before product activation. Required price rows cannot be deleted. Later currency additions require an explicit price backfill before enablement.
4. Pricing owns coupon definitions and eligibility policy. M03 stores and validates definitions; M05 owns atomic usage holds, redemption and checkout consumption.
5. Inventory owns warehouse quantities through an append-only movement ledger. Adjustments require role, reason and idempotency key and cannot make on-hand negative. M03 does not implement reservations; M05 adds explicit allocation transitions.
6. `catalog-admin`/`platform-admin` maintain catalog, prices and coupons; `inventory-operator`/`platform-admin` maintain stock. Browser login uses the local PKCE client; fixture direct grants are test-only.
7. Product art is locally packaged SVG referenced by allowlisted asset keys. No upload, cloud object store or replaceable storage abstraction is added until another asset source is in scope.

## Rationale and consequences

Separating the services preserves the ownership contract while keeping this milestone focused on operator-maintained data. Requiring both initial price books before activation makes currency switching safe without a distributed write transaction; additions beyond those two currencies need a backfill protocol. The ledger makes on-hand quantities explainable and adjustment retries safe. Locally packaged art is deterministic, works offline at runtime and avoids another container on the 16 GB profile. Each service and browser API remains independently testable and deployable.

The admin UI shows revision conflicts rather than overwriting another administrator's changes. Import batches are validated and previewed before atomic apply. Coupon and inventory guarantees stop at the explicit M03/M05 boundary; the M03 UI must not imply checkout redemption or reservation behavior that does not yet exist.

## Supersession

Any later change to runtime currency ownership, service data ownership, stock ledger semantics, or cross-currency completeness must supersede this ADR and update accepted requirements/design/traceability before implementation.
