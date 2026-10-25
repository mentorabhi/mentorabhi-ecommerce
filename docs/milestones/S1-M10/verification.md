# S1-M10 runtime verification

2026-10-24 · Local ARM64 Mac, 16 GB host; Docker allocation 8,319,770,624 bytes. Python commands use `.venv/bin/python`.

## Measured import

- `devops/scripts/seed-demo --users 2`: passed; 100 variant SKUs across 10 new product models, 2 profiles, 17 orders, 46 items. Generation/import phase 8.72 seconds, excluding the Docker build and temporary route enable/disable lifecycle.
- `devops/scripts/seed-demo`: passed; 1,000 customer identities and profiles, 17,730 orders, 51,725 items. Created 17,713 orders in this run and replayed the 17 rehearsal orders. Generation/import phase 141.06 seconds, excluding Docker lifecycle.
- Order dates: 2025-10-25T18:26:26.764902Z through 2026-10-24T16:49:23.764902Z.
- Currency-specific order totals: INR 16,462,627,672 minor units; USD 23,078,898 minor units. These include tax/shipping and are not GMV.
- `.venv/bin/python devops/scripts/verify_demo.py`: passed. Read-only owner/admin diagnostics confirmed 10 active new models, 100 active new SKUs, 1,000 identities with `.invalid` emails, 1,000 Indian profiles, 1,000 order owners, 17,730 orders, 51,725 items, exactly 35,460 outbox lifecycle events, 1–100 items/customer, 1–5 lines/order, and zero orders outside the preceding year. Two generated customer API tokens confirmed cross-owner order detail returns 404.
- Inventory: 100 nonnegative balances, available on-hand 100–107 after historical supply/sales adjustments. This includes the separately keyed rehearsal safety buffer plus the full run buffer. Rehearsal buffers remain intentionally persistent.
- Credentials and seed report are ignored mode-0600 local files; no credential or raw profile file is tracked.

## Automated checks

- `devops.tests.test_demo_commerce`: deterministic 1,000-customer generation/count/date/currency/money bounds passed; public envelope privacy/validation check passed.
- Catalog photo regression failed against SVG-only validation before the extension change; the rebuilt catalog test suite passed with local JPEG and traversal/URL checks.
- Orders Maven verification passed, including dated import validation and disabled/self-registered seeder access cases.
- All 321 pre-seed Orders lifecycle envelopes passed the shared analytics contract validator.

## Follow-up reliability and browser evidence

- Repeated the identical full import: passed with `createdThisRun: 0`, retaining 1,000 identities/profiles, 100 new SKUs, 17,730 orders and 51,725 items. No new order or stock movement was created.
- `.venv/bin/python -m unittest devops.tests.test_demo_commerce -v`: 3 passed, including atomic/private state replacement and deterministic 1,000-customer generation properties.
- `SE_OFFLINE=true .venv/bin/python -m unittest discover -s apps/storefront/tests -p 'test_demo_catalog_ui.py' -v`: 1 passed. Selenium loaded every visible local catalog image, confirmed prices were available, observed exactly two batched Pricing and two batched Inventory requests for the 106 active SKUs, opened a demo product, and found all 10 variant options.
- Full core images were rebuilt and the local core profile returned healthy before this browser pass.

Analytics-side demo-subset reconciliation and remaining regressions are recorded after execution below; a UI/API health check alone does not prove the Iceberg totals match the Orders owner records.

## Consolidated seed and storefront status — 2026-10-25

The final read-only `verify_demo.py` run confirmed 10 synthetic catalog models, 100 distinct variant SKUs, 1,000 synthetic Indian customer profiles/identities using `.invalid` email addresses, 17,730 seeded orders, 51,725 order items and 35,460 seed lifecycle events. Every customer had 1–100 items, every order 1–5 lines, all order timestamps fell within the preceding year, all 1,000 orders owners were unique as expected, and no seeded inventory balance was negative. At the time of this later check, on-hand balances were 100–169 because post-purchase browser/integration fixtures recorded additional safe stock buffers; this differs from the immediate post-import 100–107 snapshot above.

The full catalog Selenium journey passed: all local product images loaded, prices rendered, 106 active SKUs were fetched via bounded pricing/inventory batches, and all variants were selectable. Seed rerun idempotency, `.invalid` privacy, ownership, and analytics subset reconciliation are documented above and in M08. Manual operator/database checks remain unchecked.
