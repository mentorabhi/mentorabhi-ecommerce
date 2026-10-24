# S1-M04 manual end-user acceptance

Revision 1 · 2026-10-24 · Draft checklist; refresh URLs and account setup after implementation.

These checks are manual and separate from automated tests. Record results after M04 runtime is available.

## Start and service health

- [ ] Start the documented S1-M04 profile with `./devops/scripts/supersports up`.
- [ ] Confirm storefront is reachable at http://localhost:3000 and its health endpoint returns healthy.
- [ ] Confirm identity, Catalog, Pricing, Inventory, Customer and PostgreSQL containers are running and healthy.
- [ ] Run `./devops/scripts/supersports status`; record profile and image versions.

## Customer browsing

- [ ] Open the home page and use Cricket and Football navigation.
- [ ] Search by product name and inspect no-result behavior.
- [ ] Apply category/attribute filters, sort by price/name, and clear filters.
- [ ] Open product details, choose each valid variant, inspect price/currency and availability labels.
- [ ] Verify product image alt text and keyboard-only navigation/focus.
- [ ] Change store currency in the existing admin configuration and confirm the product page displays the matching explicit price book. Confirm no exchange conversion is implied.
- [ ] Resize to mobile and confirm menus, cards, search and product actions remain usable.

## Account, wishlist, cart and address

- [ ] Sign in with the customer account flow documented for the selected local identity policy; never copy a password into this guide.
- [ ] Add/remove a wishlist item; refresh and confirm persistence.
- [ ] Add multiple variants to cart, change quantities, remove a line, refresh and confirm persistence.
- [ ] Confirm displayed cart values are informational and the UI does not claim stock reservation or checkout completion.
- [ ] Enter an Indian address with a valid state and PIN; save and edit it.
- [ ] Submit invalid/missing state and PIN values; confirm accessible field-level validation.
- [ ] With a second test customer, repeat cart/wishlist/profile flows. Confirm the second account cannot view or alter the first account’s records by editing paths or request data.
- [ ] Sign out and confirm personal pages require a customer session; public browsing remains available.
- [ ] Visit the M03 admin workspace and confirm the configured admin account still performs expected catalog operations. Confirm customer credentials cannot administer Catalog, Pricing or Inventory.

## Database checks

Use local owner/admin database access only. Customer data must be checked in the Customer database; do not query another service's private tables using an application service role. Replace placeholders with the actual local DB container/owner/database names documented by the implementation.

```sql
-- Migration state
SELECT installed_rank, version, description, success
FROM flyway_schema_history
ORDER BY installed_rank;

-- Verify only non-sensitive aggregate ownership and counts; do not print addresses.
SELECT customer_subject, count(*) AS cart_lines
FROM cart_line
GROUP BY customer_subject;

SELECT customer_subject, count(*) AS wishlist_items
FROM wishlist_item
GROUP BY customer_subject;
```

- [ ] Confirm records for the two test subjects remain separate after browser restart.
- [ ] Confirm no passwords, bearer tokens or payment details are persisted in Customer tables.
- [ ] Record database/container, command, timestamp, row counts and redacted result; do not paste address values into this file.

## Manual result

- Tester/date:
- Git revision:
- Profile and dataset:
- Outcome (pass/fail per section):
- Issues / evidence paths:
- Cleanup performed (test customer/cart data):
