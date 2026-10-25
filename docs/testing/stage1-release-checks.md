# Stage 1 owner verification

2026-10-26 · Manual checks, separate from automated evidence. Leave boxes unchecked until you perform them. Read [current status](../context/status.md) and the dated milestone verification records for measured results and limitations.

## Services and access

- [ ] Run `devops/scripts/supersports status`. Inspect Docker Desktop for stopped/unhealthy services, unexpected restarts and memory pressure. Core commerce and streaming must run together. Enable heavy analytics, graph and dashboard-studio profiles selectively.
- [ ] Open [Storefront](http://localhost:3000) and [Admin](http://localhost:3002/admin) side by side. Admin uses **admin/admin**; storefront uses your separate customer account or self-registration.
- [ ] Follow the [UI access guide](../setup/ui-access.md) for Keycloak, Kafka UI, Grafana, Prometheus, Trino, Neo4j and Superset. Every enabled operational UI uses **admin/admin**. A listed optional URL does not mean its profile is currently running.
- [ ] Open [Grafana](http://localhost:3001), select SuperSports request performance, browse the store and inspect traffic, response time, errors, traces and safe request logs. Follow the [telemetry setup guide](../setup/request-telemetry.md) to disable/re-enable it. Check service readiness again afterward.

## Shopping and administration

- [ ] Browse both sports, search and use pagination. Expect 103 Cricket models/1,030 SKUs and 113 Football models/1,130 SKUs at this release checkpoint, with locally served sourced photographs. New owner-created products can change these counts.
- [ ] Confirm the large storefront banner is absent and the small header logo remains. Search `bat`/`bats`, `ball`/`balls`, `pads` and `SG cricket bat`; verify equipment relevance, product links and portrait-photo containment above card text on desktop/mobile.
- [ ] Open a product beyond page one. Read its specifications/provenance, choose an exact option and confirm that SKU, price and stock in cart/checkout. Test INR and USD; restore INR afterward. Option ranges, prices, stock and delivery/payment are simulations.
- [ ] Compare rating/count across category, search, detail and Similar Products. Read the DEMO labels. Use arrows/keyboard on desktop and mobile; related cards must open the correct product.
- [ ] Register/sign in, update an Indian address, use cart/wishlist and place a simulated order. Check history/tracking. A second customer must not inherit your private data.
- [ ] Use dedicated test orders for cancellation before handoff, partial return after delivery, review submission and support. Publish/hide a review in Admin; inspect/refund/restock a return and check its audit. These actions change retained local test data.
- [ ] Apply REALCR10/REALFB10 to selected and unselected products; test REALCR10USD/REALFB10USD in USD. Confirm eligible-line-only discounts and historical order amounts remain unchanged.
- [ ] Start the analytics profile using the [operations guide](../../devops/README.md). Check Admin → Analytics period/currency filters, sales/orders/AOV/units, discounts/refunds, daily/product reports and the displayed metric definitions. Check the optional Trino/Superset interfaces separately.

## Database and retained data

Connect DBeaver through [host database access](../setup/database-access.md), using ignored local credentials. Query each owning database separately; do not join private tables across services. Never reset databases to make a check pass.

- [ ] In Catalog, run the query below. Confirm active models/SKUs meet each sport's minimum and retired test products stay out of active browsing.

```sql
SELECT c.slug, count(DISTINCT p.id) AS products, count(s.id) AS skus
FROM categories c
JOIN products p ON p.category_id = c.id AND p.status = 'active'
JOIN skus s ON s.product_id = p.id AND s.active
GROUP BY c.slug ORDER BY c.slug;
```

- [ ] In Pricing, inspect `sku_price` for both currencies and positive minor-unit values for the active Catalog SKU IDs. Historical/retired SKU prices may remain. Inspect coupon product allowlists in their owning database/API.
- [ ] In Inventory, check `inventory_balance` for nonnegative on-hand values and `stock_movement` for actor/reason/idempotency audits. Seed replay must not replenish previously consumed stock.
- [ ] In Reviews, inspect `product_review` DEMO origin, PUBLISHED state and 3–5 ratings. Compare selected product summaries with the UI; pending/hidden customer reviews must not affect public counts.
- [ ] In Orders and the active History database, inspect your own test order/timeline and compare identifiers, sequence and immutable currency/amount snapshots. In Kafka UI, inspect Debezium status, partitions, consumer lag and retained events.
- [ ] Inspect the 1,000 synthetic customer/prior-year order dataset using the [data guide](../milestones/S1-M10/manual-acceptance.md). Its historical products intentionally remain valid after active catalog replacement. Review the [replacement provenance and simulation record](../milestones/S1-M11/data-population.md).
- [ ] Follow the backup/restore guide using isolated restore databases. Inspect local telemetry volume usage separately; Tempo/Loki do not store request traces/logs in commerce PostgreSQL tables.

## Milestone checklists

Each milestone has its own service/UI/feature/database checks and space for your findings:

| Milestone | Owner checklist |
| --- | --- |
| M01 design | [Manual acceptance](../milestones/S1-M01/manual-acceptance.md) |
| M02 bootstrap | [Manual acceptance](../milestones/S1-M02/manual-acceptance.md) |
| M03 merchandising | [Manual acceptance](../milestones/S1-M03/manual-acceptance.md) |
| M04 customer storefront | [Manual acceptance](../milestones/S1-M04/manual-acceptance.md) |
| M05 checkout | [Manual acceptance](../milestones/S1-M05/manual-acceptance.md) |
| M06 CDC/history | [Manual acceptance](../milestones/S1-M06/manual-acceptance.md) |
| M07 post-purchase | [Manual acceptance](../milestones/S1-M07/manual-acceptance.md) |
| M08 analytics/graph | [Manual acceptance](../milestones/S1-M08/manual-acceptance.md) |
| M09 operations/recovery | [Manual acceptance](../milestones/S1-M09/manual-acceptance.md) |
| M10 synthetic history | [Manual acceptance](../milestones/S1-M10/manual-acceptance.md) |
| M11 sourced catalog/reviews/separate Admin | [Manual acceptance](../milestones/S1-M11/manual-acceptance.md) |
| M12 request telemetry | [Manual acceptance](../milestones/S1-M12/manual-acceptance.md) |

Tester/date, branch/commit, profiles, results and issue references: ____________________
