# S1-M11 Catalog API

2026-10-25 · R25–R27 · Existing dependencies and service ownership retained.

All paths below use `/api/v1/catalog` on the service, or `/api/catalog` through the storefront/Admin proxy. UUIDs serialize as strings. Public responses include only active products under active categories and sports.

## Customer queries

`GET /public/products?page=1&pageSize=24&q=bat&category=cricket-equipment&sport=cricket` returns `{items, page, pageSize, total, hasNext}`. Page is 1–10,000; page size is 1–48. Search is literal, case-insensitive text up to 100 characters; category and sport accept their UUID or slug, up to 64 characters. The deterministic order is product title then UUID. Pricing remains owned by Pricing; price sorting in the frontend applies to the visible page and is labelled accordingly.

Each item is `{id, categoryId, sportId, slug, brand, title, description, status, revision, details, skus}`. `skus` contains active variants `{id, code, attributes, assetKey, altText}`. A legacy product has `details: {}`. `GET /public/products/{slug}` returns the same item directly, independently of pagination; missing/retired/hidden-parent products return 404.

`GET /public/products/{slug}/similar?limit=8` returns an array, with a 1–12 limit. It excludes the source and all invisible products. Ranking prefers same equipment type and sport, then same sport, then matching equipment elsewhere, then other active products, with title/UUID tie-breakers. Sufficient same-sport inventory therefore fills the row before cross-sport fallback.

`GET /public/products/by-skus?skuIds=<UUID>,<UUID>` resolves 1–100 unique active SKU identities to distinct visible product records. Missing/inactive IDs are omitted; malformed, duplicate or oversized requests fail with 400. Cart/wishlist restoration must use this endpoint rather than assuming saved variants are on the current browse page. Batch prices/stock remain the existing owner APIs, each bounded to 100 SKU IDs.

The original `/products` array API and `/admin/products` remain available for existing integrations. The original public list retains its 100-product cap; new shopping pages use the paginated endpoint.

## Sourced details and mutations

`PUT /products/{id}` requires an operator JWT and JSON:

```json
{
  "expectedRevision": 1,
  "idempotencyKey": "source-model-update-v1",
  "brand": "Source brand",
  "title": "Source model",
  "description": "Original, factual description.",
  "details": {
    "model": "Source model",
    "equipmentType": "bat",
    "highlights": ["A factual source-backed highlight"],
    "material": "",
    "intendedUse": "Cricket",
    "fit": "",
    "care": "",
    "packageContents": [],
    "provenance": {
      "sourceUrl": "https://example.com/products/model",
      "capturedOn": "2026-10-25",
      "rightsStatement": "Source owner retains image rights; no open licence is asserted."
    },
    "gallery": [{"assetKey": "catalog-real/model.jpg", "altText": "Source model", "kind": "photograph"}],
    "commerceProvenance": "Prices, availability and educational variant ranges are simulated."
  }
}
```

Facts are plain text with bounded fields; gallery contains 1–8 relative local JPG/JPEG/PNG/WebP keys and meaningful alt text. Attribution accepts HTTP(S) URLs without credentials and an ISO capture date. An accepted URL is attribution only: Catalog never fetches it. The importer separately verifies photo bytes, model correspondence and complete prices/stock before activation. Unknown facts remain blank rather than invented.

`POST /products/{id}/retire` accepts `{expectedRevision, idempotencyKey, reason}` and returns `{id, status: "retired", revision}`. Retirement preserves product/SKU identities and excludes the product from public browse and checkout availability. It does not delete historical order snapshots or stock/audit records. Retired products cannot be changed. Active/retired fact changes cannot bypass revision checks through the legacy create/upsert route; identical fixture replay stays supported.

Both mutations serialize on their operation key and lock the product row. Identical actor/input/key replays return the original receipt without another audit/revision; changed input/actor/key reuse or stale revision conflicts. Audit, product revision and receipt commit in one transaction. Existing activation requires INR/USD completeness and, for sourced details, photographic SKU keys. Storage does not infer photo authenticity merely from an extension.

## Measured verification

Catalog unit verification passed 14 executed cases; six then seven optional PostgreSQL tests are separate. The final PostgreSQL boundary run passed **7/7 in 33.914 seconds**, using the existing owner role in isolated random schemas, with cleanup. It covers V1/V2/V3 migration, literal filters/pagination/direct detail, saved variants beyond page one, similar ordering/exclusion, authenticated revisioned mutation, concurrent retirement, replay/audit identity and historical SKU preservation. The saved-SKU lookup test returned 404 before implementation and passed afterward. Invalid harness credentials in the first database attempt were corrected without changing credentials or production data. Production deployment and signed-JWT/runtime composition are recorded in the milestone verification, not inferred from these tests.
