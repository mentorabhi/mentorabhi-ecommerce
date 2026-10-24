# S1-M03 manual acceptance — Catalog, pricing and inventory

Revision 2 · 2026-10-24 · Local end-user checks; separate from automated test evidence.

## Start and check services

From the repository root:

```sh
./devops/scripts/supersports up
./devops/scripts/supersports status
curl -fsS http://localhost:3000/healthz
```

Confirm PostgreSQL, Keycloak, Catalog, Configuration, Pricing, Inventory and Storefront are healthy. The status output should show the application ports bound to `127.0.0.1`; PostgreSQL should have no published host port. Health endpoints:

```text
http://localhost:8081/actuator/health/readiness  Catalog
http://localhost:8082/actuator/health/readiness  Configuration
http://localhost:8083/actuator/health/readiness  Pricing
http://localhost:8084/actuator/health/readiness  Inventory
http://localhost:8180/health/ready               Keycloak
http://localhost:3000/healthz                    Storefront
```

## Sign in and inspect the UI

Open **http://localhost:3000/admin**. The customer storefront is now at the root URL. If a prior failed login left the page in a stale state, reload it before starting.

Sign in with username `admin` and password `admin`. These are local demo credentials stored in the ignored `devops/.local/admin-login.env` file. Confirm the Catalog workspace renders and remains visible after the redirect. All signed-in local accounts can use every admin section; role assignments are unnecessary (ADR 0003).

- **Catalog:** confirm Cricket and Football products appear with their product art, descriptions and SKU codes. Click each category filter and confirm the product cards change to that category; click **All sports** to restore the full list. The Selenium run also creates `Selenium UI Regression Item`; confirm it appears with LIVE status and a working local illustration.
- **Prices & coupons:** confirm fixture and Selenium product SKUs each have an INR and USD amount and that `WELCOME10`, `CRICKET250` and (after Selenium runs) `SELENIUMUI` appear. Switch the active currency to USD, confirm success, then switch it back to INR.
- **Inventory:** use the same signed-in account. Confirm the Inventory section lists the six fixture SKUs and on-hand quantities.
- **Stock adjustment:** record an adjustment of `+1` for one fixture SKU with a reason and a unique key (for example, `manual-check-YYYYMMDD-unique`). Confirm the quantity increases. Submit the identical adjustment again with the same key and confirm the quantity does not increase a second time. Reverse the first `+1` using `-1`, a correction reason, and a different unique key so the fixture balance returns to its original value.
- **Responsive view:** narrow the browser to a phone-sized viewport. Confirm navigation, product cards and pricing/inventory rows remain readable and controls are reachable.
- **Sign out:** use the top-bar sign-out control at both desktop and phone widths and confirm the login screen returns.
- **Authentication:** reload after sign-out and confirm the workspace requires sign-in. An incorrect password must not open the workspace. `curl -i http://localhost:8084/api/v1/inventory/balances` without a token must return HTTP 401.

All local changes are stored in the development databases. Restore currency to INR and reverse any manual stock adjustments after inspection. The stable Selenium product and coupon are intentionally retained because this milestone has no delete/retire controls for those records; do not add extra manual products/coupons unless you intend to keep them.

## Database checks

These are read-only inspection queries. Run them from the repository root; the commands use the local PostgreSQL container's generated password without displaying it.

```sh
docker compose --project-directory . --project-name supersports --env-file devops/.local/bootstrap.env -f devops/compose/core.yaml exec -T postgres sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d catalog -c "SELECT version, success FROM flyway_schema_history WHERE success ORDER BY installed_rank; SELECT slug, name FROM sports ORDER BY slug; SELECT status, count(*) FROM products GROUP BY status ORDER BY status; SELECT count(*) AS sku_count FROM skus;"'
```

Expect Catalog schema version 2, Cricket and Football, six active fixture products plus the active Selenium product, and seven SKUs after the Selenium suite has run.

```sh
docker compose --project-directory . --project-name supersports --env-file devops/.local/bootstrap.env -f devops/compose/core.yaml exec -T postgres sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d pricing -c "SELECT version, success FROM flyway_schema_history WHERE success ORDER BY installed_rank; SELECT code, revision FROM store_currency WHERE id=1; SELECT currency, count(*) FROM sku_price GROUP BY currency ORDER BY currency; SELECT code, active FROM coupon ORDER BY code;"'
```

Expect INR as the active currency after the UI check, seven prices per currency, and two fixture coupons plus `SELENIUMUI` after the Selenium suite has run.

```sh
docker compose --project-directory . --project-name supersports --env-file devops/.local/bootstrap.env -f devops/compose/core.yaml exec -T postgres sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d inventory -c "SELECT version, success FROM flyway_schema_history WHERE success ORDER BY installed_rank; SELECT count(*) AS balances, sum(on_hand) AS total_on_hand FROM inventory_balance; SELECT source, count(*) AS movements FROM stock_movement GROUP BY source ORDER BY source; SELECT actor, reason, delta FROM stock_movement ORDER BY occurred_at DESC LIMIT 8;"'
```

Expect six fixture balances. Each Selenium or manual adjustment and reversal appears as two `admin-adjustment` movements while the original balances are restored.

## Manual result

| Check | Result / notes |
|---|---|
| Services healthy | Pending user check |
| Catalog and pricing UI | Pending user check |
| Inventory and idempotent adjustment UI | Pending user check |
| Phone-sized layout | Pending user check |
| Catalog/Pricing/Inventory database checks | Pending user check |
| Checked by / date |  |
