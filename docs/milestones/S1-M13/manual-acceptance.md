# S1-M13 manual owner checks

2026-10-26 · Separate from automated engineering evidence; leave unchecked until performed.

- [ ] Inspect running Catalog/Pricing/Inventory/Reviews/Storefront/Admin and dependency health; preserve the current History target/data.
- [ ] Use the coverage registry/report to browse every requested Cricket equipment family. Confirm at least two distinct source models for every required added family, rather than colour/size variants or unrelated football products.
- [ ] Inspect photos, model details, provenance, appropriate option names, INR/USD prices and 3–4 labelled DEMO reviews. Check heavy/light equipment, separate ball colours and footwear types explicitly.
- [ ] Search representative accessories (`bat grip`, `bat oil`, `batting tee`) as well as `bat`; verify that a bat search still excludes accessories. Open detail/similar navigation on desktop/mobile and check photo containment.
- [ ] Add a new equipment SKU to cart/checkout in each currency using a dedicated simulated test order. Verify SKU/quantity/money and old orders remain intact.
- [ ] In the owning Catalog DB, inspect active Cricket model/SKU identities and equipment types. Separately inspect owning Pricing/Inventory/Reviews state for complete positive prices, nonnegative stock and published DEMO provenance; no cross-service private-table joins or manual data repair.
- [ ] Reconnect from DBeaver and inspect an older order snapshot. Compare active counts with this milestone's dated verification rather than the earlier 103-model release baseline.

Date/operator: ______ Outcome/issues: ______
