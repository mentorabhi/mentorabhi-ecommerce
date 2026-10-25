# Sourced catalog population — 2026-10-25

| Sport | Active models | Sellable SKUs | Price books |
| --- | ---: | ---: | --- |
| Cricket | 103 | 1,030 | INR and USD |
| Football | 113 | 1,130 | INR and USD |
| Total | 216 | 2,160 | 4,320 SKU/currency entries |

Counts were observed through deployed Catalog APIs after import. Accepted manifest: data/pipelines/real-catalog/manifest.json, SHA-256 `dd3dbec2bcb8cc857b44677c33d695f9eaf3c1cc9043384a7d7d371ac9735f96`. Owner APIs initialized stock, seeded 751 labelled DEMO reviews, created four selected-product coupons and retired 17 old active fictional/test models. Existing identities/audits/order snapshots were not deleted. Private import receipts and exact image IDs stay under ignored devops/.local.

## Sources and photo review

Cricket combines retailer sources with the user-supplied DSC PDF: 78 pages, filename 2022, cover range 2023, SHA-256 `6f70a08f07b2ad46158817cb83d7774db3ff204139bf60b2bb6515d308e6afcc`. dsc-catalog-records.json records page/model/image-object mappings. Restore reconstructs original photo pixels/soft masks and losslessly encodes PNG; no generated or retouched art. Missing manufacturer prices remain unknown, independent from explicit simulated fixture prices.

Football research reached 114 candidates from Soccer90, with brand evidence from product content. Bounded downloads recorded decoded dimensions/formats/hashes. Visual data review inspected manufacturer page layouts and eight local browser-rendered sheets covering 219 prepared models. It excluded a black-silhouette PDF extraction, a Versant-labelled record showing an MRF photograph, and a page heading misparsed as a model. source-review.json records these exclusions. The accepted 216 records have unique photograph hashes. This source-data review is separate from later storefront Selenium acceptance.

All runtime images are local; no retailer hotlinks. Source owners retain image/trademark rights; attribution/local educational use does not assert an open licence. PDF/images are ignored, while metadata, hashes and restoration instructions are tracked. Pillow 13.0.0 and pypdf 6.21.2 are pinned in venv requirements.

## Simulations and history

Options, stock, prices and DEMO reviews are labelled simulation. Explicit price books use fixture conversion 85.00 INR/USD, never a live rate. Ten options per model use equipment-appropriate sizes/hands/packs; goalkeeper gloves are pairs and bags use bundles rather than apparel sizes. Photos depict the sourced option and do not establish manufacturer availability of simulated colours.

REALCR10/REALFB10 apply in INR and REALCR10USD/REALFB10USD in USD. Each selects ten models within its sport; Pricing enforces product eligibility, deterministic discounts/caps/dates and limits. Existing historical coupons remain. M10 customer/order data keeps original item snapshots; do not rerun the older generated-art catalog seed after replacement.

## Deployment and evidence

Data loading required the new Pricing product eligibility rule. Its preparation image explicitly skipped tests; default builds remain test-enabled. In the subsequent testing phase, all thirteen application images built successfully with normal test-enabled builds and were deployed. Storefront compilation includes TypeScript/Vite and is not a substitute for acceptance tests.

The first deployed-asset test caught HTTP 403: temporary photos were 0600 and copied root-owned into non-root Nginx. Creation/restoration now uses public-photo mode 0644. The new focused regression passed, the storefront was rebuilt, and the four-case real-catalog integration rerun passed in 58.112 seconds. It checked every served image hash, options/price books/stock, DEMO provenance/summaries, eligible-only coupon allocation, and replay with unchanged seed-movement digest, Catalog revisions and the selected customer's owned order-list snapshot. This does not claim an exhaustive before/after snapshot of every historical order; the importer never calls Orders mutation APIs.

Further API/browser/restart/telemetry results are recorded in verification.md. Owner checklists remain unchecked.
