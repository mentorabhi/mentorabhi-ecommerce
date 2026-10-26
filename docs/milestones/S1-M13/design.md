# S1-M13 — Cricket equipment breadth

2026-10-26 · User follow-up after the Stage 1 release; R31.

The supplied list contains 50 primary rows and four maintenance rows. Audit all 54 rows against actual active sourced Cricket models. Preserve a machine-readable coverage registry with stable requirement IDs, original labels, evidence and accepted model identities. Do not count football gloves, generic batting pads as wicketkeeping pads, a kit photo as an individual item, or colour/size SKUs as distinct models.

For any absent row, add at least two distinct sourced models. Target two models per row across the completed registry. Slash/combined labels describe the stated family; preserve meaningful subtypes (red/white/pink leather balls separately, spiked/rubber shoes separately, heavy/light rollers explicitly). Fielding/catching gloves are training products, not a claim that wearing them in a match is permitted. A multi-use helmet counts for wicketkeeping only with source support. Do not claim source availability, certification, medical protection or prices beyond sourced facts.

## Reviewed implementation

Use the existing Catalog/Pricing/Inventory/Reviews owning APIs and real-catalog importer. Extend its preparation only as required: explicit curated equipment types override broad title heuristics (bat oil/grip/tee must not become bats or shirts); optional explicit realistic fixture options allow ground/maintenance products without XS–6XL clothing sizes. Existing accepted model identities, source photos/prices, options, stock idempotency keys, coupons and historical orders remain stable. The original 216-model manifest is an append-only baseline for this expansion; no relabeling or retirement of sourced models without explicit reconciliation.

New original photographs must be downloaded from reviewed HTTPS source hosts, decoded/hashed/bounded, locally restored and visually reviewed against the specific model. Extend the strict image-host allowlist only for actually reviewed suppliers/CDNs; do not allow arbitrary network targets or substitute generated artwork. Record source URL/date, separate fixture prices/currencies/stock/options and DEMO reviews. Metadata/provenance must identify equipment usage and any source uncertainty.

Coverage maps refer to stable source keys, not free-text substring counts. Validate distinct source/model identities, Cricket sport, required source evidence and photo hashes. One model may cover closely related stated uses only with explicit evidence; it still counts once within each row. New synonyms/search behavior must retain the bat/accessory distinction and be tested if changed.

Sequence: finish implementation/test source first, then curate/populate data, then execute units/integration/replay/Selenium/coverage checks. Build/deploy local photo bundle before final browser acceptance. Run resource-heavy workloads selectively on the 16 GB host; preserve the main History target and all data. Keep the previous Stage 1 release evidence intact and report this new scope separately.

## Review

Reviewed before implementation: taxonomy is not a manufacturer claim; unknown source data remains unknown; synthetic prices/options/reviews remain labelled. No new service, database migration, model or cloud integration is needed. Main risks are false coverage from similarly named items, inappropriate options, duplicate/reused images, oversized assets and data replay changing prior operator state. Validation and owner API reconciliation must fail on those conditions rather than silently reset state.

See [editable flow](flow.mmd) and [manual checks](manual-acceptance.md). Actual coverage/sourcing/deployment/test results belong in verification, not this proposed design.

Source review refinement before ingestion: a maintenance kit can cover the maintenance family only when the listing and SKU remain explicitly labelled as the complete kit with documented contents. It must never represent a separately sold individual sheet or count its components as separate model identities. For CE54, use a genuine umpire ball towel plus a sourced soft cricket sports cloth; preserve that the latter supplier advertises sweat/hand drying, not approved ball polishing. Do not claim artificial shiner, match permission or manufacturer endorsement of a new use. The cloth alternative is a practice/kit-care curation, with this limitation retained in product details and coverage evidence.

Reviewed public image hosts added for this intake: www.ecbacoshop.co.uk (original ball towel/jacket/hat), www.cricket-hockey.com (specific padded shorts), kdsport.com.au (UMD905 light meter), media.newitts.com (crease marker). Other accepted source photos use the already-approved cdn.shopify.com. No arbitrary-host switch is introduced. Fixture GBP sources may use an explicitly fixed 110 INR/GBP simulation before the existing 85 INR/USD fixture conversion; this is not a live exchange rate. Missing source prices remain unknown while fixture prices are separate.

A CricHeroes coin source was investigated but its public photo redirect ended in HTTP 502. It is excluded; no unusable photo or replacement art is accepted. A different Vixen/Bhalla Sports model with its own original supplier photograph replaces it. No AWS resize host or unused CricHeroes image host remains in the downloader allowlist.

Search refinement from new source types: exact multiword accessory intent (bat grip, bat oil, bat toe guard, batting tee, bat care kit) must take precedence over the generic bat word. Bind the resulting canonical metadata type separately from title aliases, retain whole-word matching and count/pagination, and add real PostgreSQL/browser regression before deployment. Existing broad bat results must remain true bats.
# Final verification follow-up — 2026-10-26

The full catalog/browser suites were green, but Grafana's restored dashboard Selenium check stalled. Logs showed session creation and internal API timeouts rather than rejected credentials; host/container evidence recorded severe Linux memory reclaim and Grafana CPU throttling. A warm rerun reproduced the stall, so this is not counted as a pass. The bounded remediation hypothesis is Grafana CPU starvation under the 16 GB host profile: increase its container CPU ceiling from 0.75 to 1.5 while retaining the existing 512 MiB memory cap and SQLite WAL. No database concurrency or authentication changes. Re-run the same authenticated Grafana Selenium check and inspect cgroup throttle counters. If it still fails, retain the failure and report it rather than expanding resource use blindly.
