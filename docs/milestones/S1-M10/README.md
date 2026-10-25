# S1-M10 — Local analytics dataset

Design: [synthetic commerce dataset](design.md). Review: [design review](design-review.md). Editable flow: [flow.mmd](flow.mmd). Manual checks: [manual acceptance](manual-acceptance.md).

Status: implementation, the full local dataset load, read-only source checks, analytics reconciliation and catalog Selenium journey are complete for the exercised synthetic scope. Owner manual acceptance remains pending. The dataset is 1,000 synthetic customer profiles, 100 variant SKUs with generated realistic product photographs, and 1–100 total items per customer divided into orders of 1–5 items across the prior year. These are synthetic confirmed reporting/history records; no payment ledger, shipment, email or real fulfillment is created. See [measured verification](verification.md).

Run after building core: `devops/scripts/seed-demo`. Rehearsal: `devops/scripts/seed-demo --users 2`. Full run extends the same seed safely. An ignored mode-0600 file `devops/.local/demo-commerce-20261024.json` retains the fixed anchor, settings and credentials; the sibling `-report.json` records actual counts and currency totals. Repeating the identical run preserves identities, SKU IDs, inventory movement keys, order references and events. State/report writes use mode-0600 atomic replacement so interruption leaves the prior resumable anchor intact. Changing `--max-items` requires a distinct seed. Rehearsal stock buffers remain in addition to the full run's buffer and are identifiable by movement keys.

UI: http://localhost:3000 and http://localhost:3000/admin (Analytics). Admin login is the existing local account. Generated customer usernames/passwords are in the ignored credential file; never copy that file into Git.

Image provenance: ten photorealistic product images generated for this local synthetic catalog, stored in `apps/storefront/public/products/synthetic/`. Product claims/prices are demonstration data. Each photo illustrates a model; the ten listed size/edition SKUs are distinct inventory items.
