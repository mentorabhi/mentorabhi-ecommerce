# Catalog, reviews and frontend separation design

Revision 1 · 2026-10-25 · Requirements/design before implementation

## User outcome

SuperSports has at least 100 genuine product models per sport, at least 1,000 sellable size/colour SKUs per sport, real product photographs, useful details, visible ratings/reviews and similar products. Admin is a separate application with a distinct theme. All operational UI access is documented and uses local demo admin/admin; storefront customers keep their accounts.

Reference: user-attached `/Users/abhijitkumarsingh/Documents/Screenshot 2026-10-25 at 10.03.03 AM.png`. Its horizontal similar-products row informs card photography, rating badges, prices and arrow navigation. Research: [Flipkart football listing](https://www.flipkart.com/mens-footwear/football-shoes~type/pr?sid=osp,cil,1cu), [Amazon India cricket search](https://www.amazon.in/s?k=cricket+kit). Amazon's page was not retrievable during initial research; do not claim a current visual inspection. The implementation uses familiar shopping structure rather than copying another store's identity or unverifiable discount claims.

## Product and SKU model

- A product is a branded model/style; a SKU is a sellable size/colour combination. At least 100 products and 1,000 active SKUs belong to each Cricket/Football sport. Distinct source colours may be grouped under one model where facts permit; do not count duplicate titles as different products just to inflate totals.
- Extend Catalog with structured product facts and photographic asset provenance: brand/model, equipment type, highlights, material/use/fit/care/package contents when known, source URL, capture date, gallery/alt text and source rights statement. Do not invent certification, manufacturer claims or genuine customer reviews.
- Gather real product facts/photos from accessible public manufacturer/retailer sources, retain source attribution and rights information, and store images locally. Runtime pages must not hotlink merchant assets or require an external/cloud service. Treat source blocks/rate limits as unavailable inputs, not permission to bypass them. Catalog intake must reject a missing/illustrated asset before activation.
- Prices, stock and extra educational variants are simulated commerce data; record their provenance independently of manufacturer facts. Do not present unsupported colours/sizes as confirmed manufacturer availability. Prefer products with sufficient genuine variants; documented demo variant ranges may extend a sourced model only with clear provenance.
- Retire the old fictional active fixtures after replacement data passes checks. Preserve old product/SKU identities, order snapshots, prices/audits and historical records. No destructive database reset is required.
- Ensure complete INR/USD prices and initial stock before activation. Idempotent imports use stable source/model/variant keys. Repeat import must not duplicate stock movements, products or reviews.

2026-10-25 U3 implementation refinement supersedes the activation ordering in the preceding original design bullet: Inventory requires an active SKU. Create both price books, activate at zero stock, then apply stable initial-stock adjustments. Require full replacement stock/price/assets before legacy retirement. See catalog-import-design.md and catalog-import-flow.mmd; no draft-stock bypass is introduced.

## APIs and ownership

- Catalog owns product facts, categories, variants, photographic asset keys, paginated browse/detail and bounded similar-product selection. Add direct detail lookup so products beyond the first page open from bookmarks. Similar selection excludes the current/retired model and ranks same equipment type/sport with useful brand/price-independent diversity.
- Pricing/Inventory keep live authority. Reuse bounded batch snapshots; paginate browsing instead of fetching every 2,000-SKU record for a single screen. Reviews offers a bounded summary batch for visible product IDs, avoiding one request per card.
- Reviews owns published review rows and rating aggregates. Add an explicit origin flag for seeded demo reviews; public responses expose that badge and omit private customer subject/order IDs. Real submissions continue to verify delivered purchase through Orders' owner API and enter moderation. Only PUBLISHED reviews enter aggregates.
- Seed 3 or 4 deterministic demo reviews/product rated 3–5. Demo rows never receive a verified-purchase badge. The seed operation belongs to Reviews and is authenticated/idempotent; it does not write another service's tables.
- No cross-service private-table reads. Similar products and summaries compose through public/bounded APIs in the frontend; deterministic checkout authority remains in existing services.

## Frontend applications

- `apps/storefront`: customer shopping only, port 3000. Bright neutral cards, navy SuperSports header, teal/blue accents, prominent search, sport navigation, clear price/rating/stock hierarchy, filters/sort/pagination and mobile drawer.
- `apps/admin`: independent React/TypeScript project, port 3002. Slate sidebar, compact operational tables/forms and a restrained teal accent. Reuse concepts and contracts through a small shared frontend package only where genuinely shared; do not bundle the Admin application into storefront.
- Separate Docker builds/configuration live under devops. Preserve existing host URLs for Kafka UI/Grafana/etc. Redirect the former storefront /admin entry point to the new origin and update identity redirect/logout callbacks, tests and documentation.
- Product detail: gallery, title/brand, rating summary, explicit variant controls, price/stock, cart/wishlist, highlights/specifications and care/package information, published reviews/histogram and a review action. Sign-in/eligible purchase messaging makes review requirements clear.
- Product cards in category, search and Similar Products show image, model/brand, price, rating average/count and detail link. The similar row scrolls using real buttons, supports keyboard focus and respects narrow screens. No fabricated bestseller or huge-discount badges.

## Operational UI credentials

Inventory the Admin frontend, Keycloak console, Kafka UI, Grafana, Prometheus, Trino, Neo4j Browser and optional Superset. Use each service's native login where practical; otherwise use a local reverse proxy with HTTP Basic authentication. Provision admin/admin idempotently on existing volumes, including first-login/password-policy handling where supported. Keep every UI loopback-bound. Storefront's customer realm and internal service/CDC/database credentials are distinct and unchanged by this UI-access request. The access guide reports only verified URLs/logins, clearly marking optional profiles.

## Exit evidence

U2 implementation refinement: keep browse page items separate from the public product cache. Resolve saved cart/wishlist SKU identities through Catalog's bounded lookup so pagination cannot make saved items disappear. Cache prices by currency and ignore superseded route loads; direct product routes fetch their own model and similar candidates. Reviews are a separate component keyed by model and customer identity, with explicit demo badges and an owned-order picker; submission stays pending until moderation. The editable request flow is [shopping-flow.mmd](shopping-flow.mmd). Reviewed against ownership, bounded requests and account-switch isolation before frontend implementation; no new dependency or material scope choice is required.

Unit/contract tests cover pagination bounds, details, similar exclusion, rating aggregation/moderation/privacy, demo seed identity and variant import validation. Live tests prove per-sport counts, local images, complete prices/stock, repeat-safe import, review visibility/submission and old-order continuity. Selenium covers all shopping/admin routes, separate origins and callbacks, ratings on browse/search/detail, similar navigation, variant-to-cart/checkout identity and each operational login. Measure API request counts/page size and memory on the 16 GB profile. Maintain a separate owner manual checklist and commit/push every unit after verification.
