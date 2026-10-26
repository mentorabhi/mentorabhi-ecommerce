# Sourced photographic catalog

Coding checkpoint, 2026-10-25. Implementation is unverified until the user's final testing phase. Research candidates are not accepted data and the requested active counts have not yet been populated.

The curated input is a JSON array with sport, brand, model, title, equipmentType, sourceUrl, imageUrl, capturedOn, sourcePriceMinor and sourceCurrency. Group colour/size listings under the same actual manufacturer model before building. A person must inspect that the source photograph depicts that model; decoding a JPEG does not establish authenticity. No generated product images are accepted.

Run from the repository root, during the data phase:

```sh
.venv/bin/python -m pip install -r data/pipelines/real-catalog/requirements.txt
.venv/bin/python data/pipelines/real-catalog/build_manifest.py devops/.local/catalog-research/curated.json data/pipelines/real-catalog/manifest.json
.venv/bin/python data/pipelines/real-catalog/import_catalog.py data/pipelines/real-catalog/manifest.json
```

The public manifest is the reproducible source record, with image URLs, SHA-256 hashes and dimensions. Photographs retain the source owners' rights; attribution does not assert an open licence or permission for redistribution. Binary photographs are ignored. Restore the exact accepted files before a clean frontend image build:

```sh
.venv/bin/python data/pipelines/real-catalog/assets.py data/pipelines/real-catalog/manifest.json
```

A changed/unavailable source fails explicitly. Do not substitute generated art. Runtime pages serve local files and make no retailer image requests. Pillow 13.0.0 is pinned for image verification only, without resizing or modifying source bytes. Official PyPI metadata was checked on 2026-10-25: Python >=3.11, MIT-CMU licence, macOS ARM64 and Linux aarch64 wheels advertised. Source: https://pypi.org/project/pillow/13.0.0/. Installation/runtime compatibility is pending final verification.

The user-supplied DSC UK PDF is an additional source: filename UK-CATALOG-2022.pdf, cover range 2023, 78 pages, SHA-256 6f70a08f07b2ad46158817cb83d7774db3ff204139bf60b2bb6515d308e6afcc. Curated page/model/XObject records are in dsc-catalog-records.json. PDF model identities include an explicit recordId. `pdf_assets.py` restores the exact reviewed PDF and reconstructs original photograph pixels with the original soft masks, then losslessly encodes PNG for browsers. No crop, retouch, generated replacement or fabricated missing source price is used. pypdf 6.21.2 (BSD-3-Clause, Python >=3.9, pure Python) is pinned after official PyPI metadata inspection. Manufacturer catalog prices remain unknown; separate fixtureBaseMinor/fixtureCurrency generate clearly simulated prices. Original PDF and extracted photos remain ignored local assets. Do not count bat grade names with only a shared range photo as distinct accepted models.

Ten simulated options per model produce at least 1,000 SKUs for each sport when 100 distinct models are accepted. Options do not claim manufacturer availability. Source price observations are separate from simulated INR/USD price books; fixture conversion is 85.00 INR/USD and never a live rate. Stock is simulated. Reviews use the existing deterministic DEMO seed and never assert verified purchases.

The import adds REALCR10/REALFB10 in INR and REALCR10USD/REALFB10USD in USD for ten selected models per sport. Pricing's optional productIds rule combines with category restrictions when both exist; absent lists are unrestricted, empty/malformed lists are ineligible. Dates and selection are deterministic from the accepted manifest. Do not rerun the older M10 catalog seeder after replacement: its generated-image models are retained historical fixtures. On a clean teaching setup, create the historical customer/order dataset before importing/retiring the sourced replacement; existing historical snapshots remain unchanged.

Importer authentication uses the ignored local Admin login; no token/password is written into receipts. It uses Catalog, Pricing, Inventory and Reviews owner APIs, preserves identities and historical orders, reports changed operator data, and retains partial progress under ignored devops/.local/catalog-import. Replay submits identical initial-stock operation keys rather than topping up consumed stock. Activation precedes stock because Inventory validates active SKU status. Only older unsourced active fixtures retire after replacement completeness; other sourced operator products remain.

In the testing phase, run the pipeline tests through `devops/scripts/supersports unit` or `.venv/bin/python -m unittest discover -s data/pipelines/real-catalog/tests -v`, followed by owner API, replay, history, INR/USD, stock, coupon and Selenium acceptance in the milestone guide. Unit source is not evidence of an executed pass.

## M13 equipment-family expansion — 2026-10-26

The current manifest extends the immutable 216-model release baseline with 96 source models for the user's 50 primary Cricket equipment families plus four maintenance families. Curated new source metadata is in `cricket-equipment-sources.json`; source-key bindings and explicit usage evidence are in `cricket-equipment-coverage.json`; photo/interpretation limitations are in `cricket-equipment-source-review.json`. A row counts distinct models, not size/colour SKU options. New sources can specify explicit `fixtureOptions` for sensible configurations rather than clothing sizes on rollers/grounds equipment. Their curated `equipmentType` takes precedence over broad title inference. Existing accepted product/SKU/price/stock identities are retained.

Before import, restore every exact local photo from the full manifest. The strict host allowlist includes the specifically reviewed public supplier photo hosts; an unavailable/changed source fails rather than substituting artwork. Model/photo attribution is not an open licence. Reproducible audit:

```sh
.venv/bin/python data/pipelines/real-catalog/equipment_coverage.py data/pipelines/real-catalog/manifest.json data/pipelines/real-catalog/cricket-equipment-coverage.json --require-complete
.venv/bin/python -m unittest discover -s data/pipelines/real-catalog/tests -v
```

Current prepared scale is Cricket 199 models/1,126 SKUs and Football 113/1,130. New ground/maintenance products have one explicitly simulated source configuration rather than invented XS–6XL sizes. Some sourced packs retain their supplier-listed multi-item contents within one SKU; `pack=1` means one listed package, not a claim that its contents are sold individually. Where a source price is unavailable it remains unknown; fixture INR is a separate field. New GBP observations can use a fixed **110 INR/GBP fixture conversion**, followed by the existing **85 INR/USD fixture conversion**. Neither is a live rate. Initial stock and reviews remain simulations. Existing coupons are not rewritten by expansion imports.

The importer still uses owner APIs, idempotent stock receipts and stable DEMO-review operations. Re-running it must not replenish consumed stock, overwrite operator price changes, modify old order snapshots or treat a kit component as its own product. Review the [M13 design](../../../docs/milestones/S1-M13/design.md), [human-readable coverage table](../../../docs/milestones/S1-M13/coverage.md), [executed evidence](../../../docs/milestones/S1-M13/verification.md) and [manual checks](../../../docs/milestones/S1-M13/manual-acceptance.md) for deployed results versus proposals. Earlier source-only/pending paragraphs in this README preserve the original intake history; current execution results are in the dated milestone records.
