# Genuine catalog import and asset restoration

2026-10-25 · U3 design before implementation · Coding/data/testing sequence follows the latest user direction.

## Input and local assets

Research produces candidate source facts: canonical product URL, real brand/model/title, equipment type, sport, photograph URL, observed source price/currency and capture date. Reject unavailable sources, duplicated models, missing brands and illustrations. Candidate research is not accepted catalog data. Public sources retain image rights; never assert an open licence without evidence.

The data-phase builder selects at least 100 distinct models per sport, downloads their public photographs once, decodes/verifies them, checks minimum dimensions, rejects duplicate photo/model mappings and records SHA-256, format and dimensions. Local files live under ignored `apps/storefront/public/catalog-real`; the committed manifest retains source URLs/hashes/provenance. A restore command recreates that exact asset bundle for a clean checkout before frontend builds. Runtime pages never hotlink retailer images. Unavailable or changed sources fail explicitly instead of being replaced with generated art.

The initial dataset contains at least 1,000 sellable SKUs for each sport. Variant ranges, stock and prices are educational simulations, independently labelled from sourced model facts. Use size/hand/colour/pack combinations appropriate to equipment; additional ranges do not claim manufacturer availability. INR/USD price books are explicit. A fixed documented demo conversion produces fixture amounts only; no live exchange-rate dependency is introduced. Source price observations remain separate metadata. Reviews are the existing deterministic 3–4-row DEMO seed, with no verified-purchase claim.

## Owner APIs and replay

Import creates/reconciles sports/categories, then each source model's draft, exact SKU codes/attributes/assets, both price books and sourced details. It activates after owner-side pricing completeness and source/local-asset preflight, then initializes stock through Inventory's existing active-SKU gate. The short zero-stock interval cannot be purchased. Each stock adjustment uses a stable per-SKU operation key; rerunning never replenishes stock consumed by orders. Existing active records must match the manifest's stable identities; divergence is reported rather than silently overwriting operator changes. Facts/retirement use Catalog revisions and operation receipts. Review seeding preserves moderation on replay.

Independent models may import with four bounded workers on the baseline host. The importer never queries private service tables. Before retiring legacy active models, require all replacement models/SKUs, prices and local assets to be present. Retire other active fictional fixtures through the owner API and preserve product/SKU identities, old prices/audits, reviews and immutable order snapshots. Do not reset databases or delete history. Failures retain an ignored receipt with manifest hash and partial progress for diagnosis/replay; no JWT/password is written.

## Review and final verification plan

Reviewed ownership, stable operation keys, currency/variant identity, asset provenance, partial-run recovery and preservation of historical facts. Input validation is part of importing data; acceptance tests execute only after the coding and data phases. Unit cases cover source/model uniqueness, target counts, integer pricing, variant identity and photo validation. Final integration compares per-sport active counts and complete INR/USD/stock, repeats import for zero new mutations, checks historical orders and review provenance, and exercises local image/variant/cart/coupon/review/related flows in Selenium. Record actual duration/resources/request counts separately from this design.

Dated source-intake refinement: the original proposal to initialize stock before activation conflicts with Inventory's enforced active-SKU validation. Retain that owner rule and use activation → initial stock rather than introducing a draft-stock bypass. The final replacement gate still requires complete stock/price/assets before retiring legacy models. This changes implementation ordering, not checkout authority or the required final dataset.

Coupon refinement reviewed before source changes: existing Pricing eligibility only matches category slugs, while the accepted requirement includes product-eligible coupons. Add an optional productIds allowlist in the owning Pricing rule; when both productIds and categorySlugs exist, a line must match both. Missing lists are unrestricted; malformed/empty lists are ineligible. Retain deterministic eligible-subtotal allocation and all existing limits/rounding. The real-catalog import seeds INR/USD demo codes for ten selected models per sport, with stable selection/dates and replay by existing code. Author unit/integration cases now and execute in the final testing phase.
