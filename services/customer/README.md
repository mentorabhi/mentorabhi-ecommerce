# Customer service

Independent Spring Boot service and database for customer profiles, Indian addresses, carts and wishlists. The verified JWT subject is the sole owner key. This service accepts only the `supersports-customers` realm issuer and `supersports-customer-api` audience; it rejects the operator realm. Application code never reads Catalog, Pricing or Inventory tables.

Customer cart/wishlist writes validate SKU activity through Catalog's public SKU endpoint. Cart lines store SKU and quantity only; the UI obtains current price and informational stock snapshots from Pricing and Inventory. No reservation, coupon redemption or checkout occurs here; those are S1-M05 responsibilities.

## Endpoints

- `GET/PUT /api/v1/customer/profile` — profile/address; country is `IN`; profile updates use an optimistic revision.
- `GET /api/v1/customer/cart`; `PUT/DELETE /api/v1/customer/cart/items/{skuId}` — set quantity or remove a line. Quantity is 1–99.
- `GET /api/v1/customer/wishlist`; `POST/DELETE /api/v1/customer/wishlist/items/{skuId}` — idempotently add or remove an active SKU.
- Public health probes are `/actuator/health/liveness` and `/actuator/health/readiness`.

The owner is derived from the validated token subject. Request bodies and routes contain no customer/owner ID. SQL reads and writes include that subject in every predicate. Never log bearer tokens or address values.

## Verification

Run the service tests via `./devops/scripts/supersports unit`. Real migrations, Keycloak registration, API cross-realm denial, ownership isolation and persistence are covered by `./devops/scripts/supersports test` and `ui-test` against the local Docker profile.
