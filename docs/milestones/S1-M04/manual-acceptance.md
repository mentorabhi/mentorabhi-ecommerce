# S1-M04 manual end-user acceptance

Revision 3 · 2026-10-24 · Local runtime is available; owner-run checks are pending.

These are manual checks outside automated tests. Do not mark a check complete based on the verification record alone. No password or token belongs in this document.

## Start and service health

- [ ] From the repository root, start the profile with `./devops/scripts/supersports up`.
- [ ] Run `./devops/scripts/supersports status`; confirm eight containers are running: PostgreSQL, Keycloak, Catalog, Configuration, Pricing, Inventory, Customer and Storefront. Record image tags.
- [ ] Confirm the Storefront returns `ok` at http://localhost:3000/healthz.
- [ ] Confirm readiness returns `{"status":"UP"}` at `http://localhost:8081/actuator/health/readiness` (Catalog), `8082` (Configuration), `8083` (Pricing), `8084` (Inventory), and `8085` (Customer).
- [ ] Confirm Keycloak readiness at `http://localhost:8180/health/ready` and the `supersports-customers` realm discovery document advertises `http://localhost:8180/realms/supersports-customers` as issuer.

## Public storefront and discovery

- [ ] Open http://localhost:3000. Confirm the supplied SuperSports icon and banner load and the six synthetic products show descriptions, images, prices and stock snapshots.
- [ ] Use Cricket and Football category navigation. Confirm each category shows the corresponding products.
- [ ] Search by a product name, by `football`, and by a term with no matches. Confirm `football` returns all three Football fixtures and no-result messaging is clear.
- [ ] Sort by name and both price directions. Open product details and confirm the displayed active-currency price and stock are labelled as snapshots.
- [ ] Confirm no checkout, payment or stock reservation is implied in the cart or product pages; those belong to S1-M05.
- [ ] Use keyboard-only navigation. Confirm visible focus, meaningful image alternative text and working product/category controls.
- [ ] Resize to a phone-sized viewport and repeat search, category navigation, product details and the primary product actions.
- [ ] In the operator workspace at http://localhost:3000/admin, switch active currency to USD, return to the storefront and confirm USD-specific fixture prices are shown. Switch back to INR and confirm prices return to the explicit INR book; no exchange-rate conversion is implied. Local admin sign-in is `admin` / `admin`.

## Self-registration, ownership and profile

- [ ] From the storefront's Account area, choose **Sign in or create account**, then **Register** in the customer realm. Complete local registration and confirm return to the storefront as a signed-in customer. This account is separate from the M03 operator account.
- [ ] Open a product. Add and remove it from the wishlist; refresh and confirm the saved state persists.
- [ ] Add products to the cart. Open Cart, change quantity, remove an item, refresh and confirm cart persistence. Confirm no reservation or order was made.
- [ ] In Account, save and edit a valid Indian address with state and six-digit PIN. Try missing state and invalid PIN and confirm validation prevents saving.
- [ ] Register a second customer in a separate browser session. Confirm the second customer's cart, wishlist and address are separate from the first customer's data, including after a page refresh.
- [ ] With a customer token, call M03 Catalog, Pricing, Inventory and Configuration protected routes; confirm they reject the customer-realm token. With an operator token, call the Customer profile route; confirm it rejects that token.
- [ ] Sign out. Confirm Account requires sign-in while public product browsing continues to work. Confirm customer credentials cannot sign in as the operator account.

## Database checks

Use the local PostgreSQL owner account for these read-only checks. The SQL returns migration state and counts only; it does not select addresses or authentication credentials. Run from the repository root:

```sh
docker compose --project-directory . --project-name supersports --env-file devops/.local/bootstrap.env -f devops/compose/core.yaml exec -T postgres sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -U postgres -d customer' <<'SQL'
SELECT version, description, success
FROM flyway_schema_history
ORDER BY installed_rank;

SELECT count(*) AS customer_profiles FROM customer_profile;
SELECT count(DISTINCT subject) AS cart_owners, count(*) AS cart_items FROM cart_item;
SELECT count(DISTINCT subject) AS wishlist_owners, count(*) AS wishlist_items FROM wishlist_item;
SQL
```

- [ ] Confirm Customer migration version `1` succeeded and profile/cart/wishlist counts reflect the test users.
- [ ] Confirm the two test accounts have separate cart and wishlist ownership. The `subject` is the verified Keycloak subject; no application service role accepts an owner supplied by the browser.
- [ ] Confirm the Customer database contains no password, bearer-token or payment-detail columns. Customer data is in database `customer`, owned by the Customer service role; do not inspect another service's private tables using an application service role.
- [ ] Record timestamp, Git revision, command and aggregate results here. Do not paste address values, email addresses, subject identifiers, passwords or tokens.
- [ ] Selenium creates two uniquely named customer-realm accounts during each full run and leaves their local identity records/data in the development profile. Keep or clean those accounts intentionally; `./devops/scripts/supersports reset --confirm-reset supersports` removes all local DB/identity volumes.

## Manual result

- Tester/date:
- Git revision:
- Profile and dataset:
- Outcome by section (pass/fail):
- Issues / evidence paths:
- Database aggregate results (no identifiers):
- Cleanup performed:
