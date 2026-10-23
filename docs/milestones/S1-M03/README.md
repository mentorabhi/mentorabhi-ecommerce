# S1-M03 — Catalog, pricing, inventory and fixtures

Revision 1 · 2026-10-23 · Status: design reviewed; implementation ready to start.

Design: [S1-M03 catalog and inventory contract](../../../design/S1-M03/catalog-inventory.md). Editable diagram: [Excalidraw source](../../../design/S1-M03/catalog-inventory.excalidraw); preview: [SVG](../../../design/S1-M03/catalog-inventory.svg).
Decisions: [ADR 0002](../../decisions/0002-merchandising-stock-ownership.md). Origin requirements: R01, R02, R04, R07, R09, R16–R19 in [accepted requirements](../../../requirements/accepted-requirements.md).

## Scope checkpoint

S1-M03 adds merchandising administration and deterministic data; it does not deliver the customer storefront or checkout. Catalog, Pricing and Inventory own separate service databases and talk through APIs. The existing M02 Configuration currency descriptor is not a second runtime currency authority; Pricing owns active currency. INR/USD books must both be complete for every active SKU before activation. Coupon definitions are maintained here, while usage holds/redemption and inventory reservations remain S1-M05 work.

The admin browser in `apps/storefront` covers Catalog, Prices & Coupons, and Inventory with local Keycloak PKCE login. Product illustrations and brand artwork are local SVGs. M03 does not add Redis, Kafka, object storage, remote assets, cloud services or Ollama runtime dependencies.

## Design review — 2026-10-23

Compound Engineering `ce-doc-review` reviewed the implementation design in two passes. No external model CLI was used because the project working agreement prohibits it without explicit direction. The Compound Pack resolver found no declared packs or errors.

| Lens | Result |
|---|---|
| Coherence | No findings in either pass |
| Feasibility | Round 1 found a race between product activation and currency switching; round 2 found competing currency owners in Pricing and Configuration |
| Security | Round 1 asked for explicit Catalog/Pricing write roles; round 2 asked for stale-revision protection/audit on Catalog mutations |
| Scope | Round 1 challenged a replaceable asset abstraction with no second consumer; round 2 found no further issue |
| Adversarial | No findings in either pass |
| UI-oriented review | Round 1 asked for loading/empty/error/success/401/403 states, usable mobile table/form layouts, and a reviewable fixture-import preview. Those requirements were added. The dispatched design-lens prompt returned a `product-lens` reviewer label, so it is recorded as a label mismatch rather than a separate design-lens receipt. The round-2 UI-oriented response returned no findings. |

Applied design changes: require both INR/USD prices before product activation and prohibit deletion of required price entries; make Pricing the sole runtime currency owner and keep the M02 setting descriptive; define the role matrix; add Catalog optimistic revision checks/audit; remove the unused asset adapter abstraction; specify UI data states, import preview and mobile behavior. The review's manual currency-race concern was resolved through those implementation constraints without changing the accepted two-currency product behavior. No unresolved product decision blocks implementation.

The review is design evidence only. No S1-M03 code, test, runtime or memory acceptance has passed yet. Exact dependency/image pins, ARM64 manifests and resource measurements are required during implementation.

## Implementation evidence

Pending. Append commands, versions, fixtures, outcomes, failures/fixes, measured RSS and limitations as the milestone is implemented.
