# S1-M11 U2 — Reviews backend API

2026-10-25 · R08/R24, AE24, ADR 0010 · Bounded backend handoff; integration and canonical commits belong to host.

Paths below are service-relative, under `/api/v1`. No frontend, Catalog, gateway, contracts or deployment changes accompany this unit. Existing dependency/image pins are reused; no dependencies added.

## Public rating summary batch

`GET /api/v1/reviews/products/summaries?productIds=11111111-1111-1111-1111-111111111111,22222222-2222-2222-2222-222222222222`

Anonymous access. Supply 1–100 **unique** product UUIDs as a comma-separated query parameter (repeated `productIds` parameters also bind to the list). Empty, duplicate, null or oversized lists are invalid. Missing/malformed query parameters return 400; a parsed list violating bounds/uniqueness returns 422. Match results by `productId`; response order is canonical UUID order, independent of input order.

200 JSON response (array, no envelope):

```json
[
  {
    "productId": "11111111-1111-1111-1111-111111111111",
    "mean": 3.67,
    "count": 3,
    "histogram": {"1": 0, "2": 0, "3": 2, "4": 0, "5": 1}
  },
  {
    "productId": "22222222-2222-2222-2222-222222222222",
    "mean": null,
    "count": 0,
    "histogram": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
  }
]
```

`mean` is a JSON number rounded half-up to two decimal places, or null when there are no published reviews. `count` and all five histogram values are integers. Both CUSTOMER and DEMO origins contribute; only `PUBLISHED` rows count. PENDING, REJECTED and HIDDEN rows are excluded. There is one grouped, parameterized query per batch; aggregates cover all published reviews, independently of the public list's 100-row display limit. There is no stored aggregate/cache to invalidate on moderation. Unknown product IDs return an empty summary; Reviews does not validate Catalog existence or read Catalog tables. Use Catalog's active product IDs.

## Public reviews

`GET /api/v1/reviews/products/{productId}` remains anonymous and returns up to 100 published rows, newest first. Existing fields remain and provenance fields are additive:

```json
[
  {
    "reviewId": "33333333-3333-3333-3333-333333333333",
    "rating": 3,
    "title": "Demo: practice use",
    "body": "Synthetic demonstration review for practice sessions.",
    "createdAt": "2026-10-25T00:00:00Z",
    "origin": "DEMO",
    "verifiedDelivered": false
  }
]
```

Exact row fields: `reviewId` UUID string, `rating` integer 1–5, `title` string, `body` string, `createdAt` timestamp, `origin` enum CUSTOMER/DEMO, `verifiedDelivered` boolean. Display **Demo review** when origin is DEMO, and **Verified delivered purchase** when origin is CUSTOMER and verifiedDelivered is true. Demo rows always have verifiedDelivered false and ratings 3–5. Public SQL selects neither customer subjects nor order/SKU IDs. Do not use the private customer/operator APIs to populate public review cards.

## Operator demo seed

`POST /api/v1/operator/reviews/demo-seed`

Requires an authenticated operator bearer token with the existing operator issuer/audience (`supersports-api`); no role assignment is added. Anonymous requests return 401; customer-audience tokens return 403. Content-Type: application/json.

```json
{
  "operationId": "44444444-4444-4444-4444-444444444444",
  "productIds": ["11111111-1111-1111-1111-111111111111"],
  "reviewsPerProduct": 3
}
```

`operationId` is a required UUID. `productIds` follows the same 1–100 unique UUID bound. `reviewsPerProduct` must be 3 or 4; no caller-supplied ratings, review text, customer identity, order identity or purchase proof is used. Bad JSON/types return 400; invalid parsed fields return 422. The caller should validate active Catalog IDs before seeding.

200 JSON response:

```json
{
  "operationId": "44444444-4444-4444-4444-444444444444",
  "productCount": 1,
  "reviewsPerProduct": 3,
  "createdCount": 3,
  "replayed": false
}
```

`createdCount` counts rows inserted by the original operation. An identical retry returns the same receipt with `replayed: true`, retaining the **original** createdCount. Operation identity is global; its normalized payload consists of sorted product IDs, reviewsPerProduct and authenticated actor subject. Reusing the operation ID with different products, count or actor returns 409. List order alone does not conflict. Clients should branch on status codes; error message bodies are not an API contract.

Demo IDs use Java `UUID.nameUUIDFromBytes`, UTF-8 bytes of `supersports:demo-review:v1:<product UUID>:<zero-based slot>`. Slots 0–3 have ratings 3,4,5,3 and fixed, explicitly synthetic text. Rows are inserted PUBLISHED with origin DEMO, no customer/order/SKU identities, and no verified-purchase claim. A new operation on the same products inserts only missing slots: 3→4 can add slot 3; 4→3 retains all four. A new operation cannot overwrite text/ratings or reset moderation. Existing matching slots are left unchanged even when HIDDEN. Conflicting row identity/content returns 409 and rolls back the entire operation. An exact operation replay reads the original receipt without rechecking/recreating rows, preserving later moderation.

Transaction-scoped advisory locking serializes identical operation IDs; sorted products and stable slot IDs plus insert-on-conflict handle overlapping operations. Review insertion and receipt insertion share one transaction. Existing moderation endpoints can hide a published demo row with an audited reason. Seed retry never republishes that row.

## Customer purchase and moderation contract

`POST /api/v1/customer/reviews` remains customer-authenticated. Input:

```json
{
  "orderId": "55555555-5555-5555-5555-555555555555",
  "productId": "11111111-1111-1111-1111-111111111111",
  "skuId": "66666666-6666-6666-6666-666666666666",
  "rating": 5,
  "title": "Good for training",
  "body": "Used for local practice."
}
```

The verified JWT subject determines ownership; the token is forwarded to Orders' owned delivered-purchase API and the product ID must match its proof. A successful submission returns 201 `{"reviewId":"<UUID>","state":"PENDING"}`. Real ratings remain 1–5; trimmed title/body are required, maximum 120/2000 characters. Missing purchase identifiers or unverified/mismatched delivery return 422; unavailable verification returns 503; an owned purchase not found returns 404; a duplicate owner/order/SKU review returns 409. CUSTOMER is the database default; demo seeding bypasses neither this customer route nor its ownership check.

Existing `/customer/reviews`, `/operator/reviews/pending`, and `/operator/reviews/{id}/moderation` remain private and retain their existing payloads. Moderation input is `{ "state": "PUBLISHED", "reason": "Meets guidelines", "operationId": "<UUID>" }`. Existing pending-only publish/reject, audited hide, revision increments and moderation replay/conflict rules remain unchanged. Pending customer reviews enter public lists/summaries only after publication.

## Safe migration and integration gates

Flyway V1 is unchanged. V2 adds origin with NOT NULL default CUSTOMER, preserving every existing ID, ownership field, review text/rating, state, timestamp, revision, unique owner/order/SKU key and moderation audit. Ownership columns become nullable for DEMO only: a database check requires all three identities for CUSTOMER and forbids them for DEMO; it also constrains DEMO ratings to 3–5. The existing 1–5/state checks remain. A separate operation ledger stores normalized input, operator subject and receipt count. No data reset/backfill to fake orders or cross-service database reads occur.

Apply V2 through the normal host-controlled Flyway startup before using the new APIs. V1-era customer inserts remain compatible because origin defaults to CUSTOMER. After demo rows exist, rolling back to the old application would omit demo badges, so retain this application version or hide DEMO rows before an application rollback. Do not undo V2 by deleting historical customer data.

Host integration gates still required: migrate a populated V1 database and compare customer rows/audits; enforce CUSTOMER/DEMO constraints with invalid inserts; exercise real PostgreSQL rollback/concurrent seed replay and overlap; seed 3→4 and retry after audited hide; publish/hide a delivered customer review and compare list/summary counts; verify real Keycloak realm isolation and frontend/gateway composition. These are not claimed as passed by unit tests.

## Local verification evidence

Used the existing Java/Maven test path with the pinned build image and existing cache, without global dependency installation or application service lifecycle operations:

```sh
docker run --rm \
  --mount type=bind,source="$PWD/services/reviews",target=/workspace \
  --mount type=volume,source=supersports-maven-cache,target=/root/.m2 \
  --workdir /workspace \
  maven:3.10.0-eclipse-temurin-27@sha256:095c056353550ea93605f9cbd200a7cbbc489a1989eeec8b8600749a157a0096 \
  mvn -B -ntp verify
```

JUnit/Mockito repository tests use grouped-row fixtures with ratings 3×2 and 5×1 plus an unrated UUID; inspect published-only SQL, public projection, batch bounds, deterministic seed fields, operation replay/conflict, product-order normalization, no-overwrite retries and occupied identity conflicts. MockMvc uses the real Reviews security filter and controller with a test authentication resolver/repository to check public routes, serialized badges/privacy, malformed UUIDs, operator-only seed and conflict status. Local in-process HTTP Orders fixtures cover delivered product matching and successful owner forwarding; the existing mismatch regression remains unchanged. Existing ReviewRulesTest remains unchanged.

The first run exposed `List.of(...).contains(null)` throwing NullPointerException in batch validation; changed validation to a null predicate and reran. PostgreSQL itself, Flyway application, actual JWT signature verification and cross-service/runtime acceptance are outside this unit's measured evidence. Build output includes existing Mockito agent/deprecation warnings and nonfatal 401 metadata warnings for optional Flyway repositories.

Final result: **BUILD SUCCESS**, 17 tests, 0 failures, 0 errors, 0 skipped; Maven verify completed in 25.146 s at 2026-10-25T05:38:47Z. Breakdown: ReviewsSummarySeedTest 10, ReviewsApiTest 4, existing VerifiedReviewProductTest 1, existing ReviewRulesTest 2. Maven 3.10.0, Java release 27, Spring Boot parent 4.1.2, Surefire 3.5.6. Surefire XML/text reports are under ignored `services/reviews/target/surefire-reports/`; no generated output is part of this change.

## Operator state browser and host follow-up

`GET /api/v1/operator/reviews?state=PUBLISHED&productId=<optional UUID>` is operator-only and returns at most 200 rows, newest first. Allowed states are PENDING (default), PUBLISHED, HIDDEN and REJECTED; an unknown state returns 422 and malformed UUID returns 400. Rows include product/SKU/order identities for operator context and an origin badge, but no customer subject. Admin uses the state selector and optional product filter to find any model; published rows offer **Hide review**, while pending rows retain Publish/Reject. Hidden rows cannot be republished through the existing pending-only state machine. The original `/operator/reviews/pending` route stays compatible.

The new operator route returned 404 in the focused test before implementation. Host Maven verify with real PostgreSQL then passed **22/22**, including four database boundary cases and five HTTP/security cases. The migration case first created a populated V1 schema, migrated V2, and compared all historical customer fields. The database checks proved concurrent same-key receipt identity, no reseed of a hidden demo, filtered moderation queries, origin/ownership constraints and rollback of earlier inserts when a later slot conflicts. Random schemas were removed.

Signed-JWT host integration and JSON Schema contract checks passed 4/4 in 0.729 seconds. Actual customer tokens are rejected by Catalog's operator-issuer authentication with 401; Reviews accepts the customer issuer but rejects operator routes with 403. Public response schemas reject private fields and fake demo verified badges. Storefront Selenium passed review submission as PENDING, Admin publication, visible verified-delivered badge, Admin hide and exact public count changes. Detailed combined evidence is in verification.md.
