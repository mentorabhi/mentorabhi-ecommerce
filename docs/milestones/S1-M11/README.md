# S1-M11 — Catalog scale, reviews and separate frontend experiences

2026-10-25 · User-requested Stage 1 scope · U1/U2 are deployed/tested within their recorded scope. U3 sourced data is deployed and its focused integration gates passed. U4 consolidated browser/restart/regression verification remains in progress.

Requirements R23–R27 / AE23–AE27. Start with [design](design.md), [editable architecture](flow.mmd), [design review](design-review.md), [implementation units](implementation-units.md), and [manual acceptance](manual-acceptance.md). The user reference image is recorded in the design; preserve the original attached file.

The [data population record](data-population.md) now documents the deployed 216-model/2,160-SKU sourced replacement, DSC manufacturer PDF intake, photo exclusions/provenance, simulated commerce data and historical preservation. U3 data is populated; U4 consolidated verification is in progress. Use the latest verification section rather than earlier source-only status for current evidence.

Storefront target: http://localhost:3000. Separate Admin: http://localhost:3002/admin. Every operational UI must use local admin/admin; storefront customer accounts stay separate. Keep execution on stage1 and commit/push each verified unit.

Measured incremental results and limitations: [verification](verification.md). U1 and U2 have separate verified checkpoints; genuine catalog replacement and expanded-dataset regression remain pending.
