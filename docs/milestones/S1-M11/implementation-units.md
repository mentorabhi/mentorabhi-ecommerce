# Implementation units

2026-10-25 · Dependency order · Stage 1 branch remains stage1

Latest user sequencing: finish all remaining Stage 1 coding first (M11 and M12), populate catalog/demo data second, then execute the consolidated tests last. Author test cases and maintain design/context with implementation, but do not run further tests during the coding/data phases. Earlier measured results remain historical evidence; new changes are unverified until the final test phase.

1. **U1 — Separate applications and access:** create apps/admin and its container/origin/theme, update callbacks/proxies/legacy redirect, inventory operational UIs, provision and verify admin/admin, and share the access guide. Verify both application builds, login isolation, direct routes and operations logins.
2. **U2 — Product and review experience:** Catalog structured details, direct paginated browse/detail and similar lookup; Reviews summary batches, demo provenance/seed and public privacy; storefront ratings/reviews/detail/similar components and responsive theme. Test deterministic rules, moderation/ownership and browser journeys.
3. **U3 — Genuine catalog expansion:** source and validate photographic model data, import at least 100 products/1,000 SKUs per sport with prices/stock and 3–4 demo reviews per product, retire legacy fictional active fixtures, prove rerun idempotency and preserve historical orders. Source availability/rights must be recorded rather than inferred.
4. **U4 — Consolidated regression and documentation:** update fixtures/tests for the expanded catalog and separate Admin, run full affected unit/integration/contract/Selenium regressions and bounded request/resource checks, maintain manual guides, context, ADRs/revisions/evidence and push checkpoint commits.

S1-M06's active soak/retention probes complete before deploying any changes that could alter their workload. Design/source intake may proceed while those tests run.
