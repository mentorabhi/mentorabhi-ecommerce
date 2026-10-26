# S1-M13 — Cricket equipment coverage expansion

2026-10-26 · New user scope after Stage 1 release; implementation, data, and affected catalog/commerce/browser gates verified. Grafana browser stability limitation is recorded in verification.

Start with [reviewed design](design.md), [editable flow](flow.mmd), [manual owner checks](manual-acceptance.md) and [verification](verification.md). Covers all 50 primary equipment rows and four maintenance rows. The previous Stage 1 release remains historical evidence, not proof that this expansion is complete.

The [54-family coverage table](coverage.md) links two supported source models per family. Current catalog: **199 Cricket products/1,126 SKUs**, **113 Football/1,130**; **312 models/2,256 SKUs**, **1,088 published DEMO reviews**. Adds 96 real sourced models without changing historical identities. See verification for exact tests, fixture skips and supplier/cloth/kit interpretations.

Storefront http://localhost:3000 (customer account); Admin http://localhost:3002/admin (**admin/admin**). Try `bat grip`, `bat oil`, `batting tee`, `wicketkeeping gloves`, `roller`, `sightscreen`, `padded shorts`, or `light meter`.
