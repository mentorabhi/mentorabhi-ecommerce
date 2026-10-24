# S1-M05 manual end-user acceptance

Revision 2 · 2026-10-24 · Updated for the local simulator projects; manual execution remains outstanding.

This checklist is separate from automated test evidence. Leave boxes unchecked until a person completes the action in the local UI or database. Do not use real payment, card, bank or carrier details.

## Start and service health

- [ ] From repository root, start the documented full local profile: `./devops/scripts/supersports up`.
- [ ] Run `./devops/scripts/supersports status`; confirm healthy PostgreSQL, Keycloak, Catalog, Configuration, Pricing, Inventory, Customer, Orders, Payment Simulator, Fulfillment Simulator and Storefront containers; record image tags.
- [ ] Confirm the Storefront is available at http://localhost:3000 and `/healthz` reports `ok`.
- [ ] Confirm readiness for Catalog (`8081`), Configuration (`8082`), Pricing (`8083`), Inventory (`8084`), Customer (`8085`), Orders (`8086`), Payment Simulator (`8087`) and Fulfillment Simulator (`8088`).
- [ ] Confirm Keycloak readiness at http://localhost:8180/health/ready and both customer/operator issuer documents.
- [ ] Confirm no cloud account, real payment provider or carrier is configured. Ollama is host-installed and not required for checkout.

## Operator simulation configuration

- [ ] Sign in at http://localhost:3000/admin using the local operator account. Open the categorized Configuration area and confirm checkout controls are grouped under commerce simulations.
- [ ] Record the current configuration revision, demo tax rate and explicit INR/USD shipping amounts. Confirm the UI labels them as simulations.
- [ ] Change a simulation value and confirm validation, actor audit and revision increment. Submit an order and confirm its configuration revision and calculated totals are snapshotted.
- [ ] Select the local authorization-decline mode for a test order, restore the normal approval mode afterward, and verify no real provider is contacted.

## Customer checkout UI

- [ ] Sign in or self-register as a customer at http://localhost:3000. Confirm the account stays in the customer realm.
- [ ] Add one or more products to Cart. Confirm shown prices/stock are described as snapshots until a quote is created.
- [ ] Open checkout, choose the Indian delivery address, and inspect the quote: line quantities, current active currency, per-line price, coupon discount if used, simulated tax/shipping, and total agree with the current local rules.
- [ ] Submit a valid checkout once. Confirm an order number/status appears and the order detail matches the values/address shown at confirmation.
- [ ] Refresh the page and reopen the order. Confirm it persists and the original currency, prices, discounts, tax, shipping and address remain unchanged.
- [ ] Change the store currency after creating an order. Confirm the historical order remains in its original currency and value.
- [ ] Try an expired, ineligible, wrong-currency, minimum-spend-failing or exhausted coupon. Confirm a clear rejection and that no stock/payment/order side effect was left behind.
- [ ] Try an invalid quantity, unavailable SKU and incomplete/invalid Indian address. Confirm checkout is blocked with a safe explanation.
- [ ] Register/sign in as a second customer. Confirm they cannot list, view, or infer the first customer's orders by changing a URL or order ID.
- [ ] Confirm the storefront collects no card/bank information and presents payment, tax, shipping and fulfillment as simulations.

## Failure and recovery UI

- [ ] Use the local Configuration setting for authorization decline. Confirm the checkout fails, no capture occurs, and reserved stock/coupon capacity are released.
- [ ] Stop Payment Simulator after its operation is accepted but before the response returns. Restart it and confirm retry/status reconciliation does not duplicate capture and the UI shows pending/reconciling state until outcome is known.
- [ ] Stop/restart the Orders worker during a pending checkout. Confirm it resumes without duplicate payment or reservation.
- [ ] Stop Fulfillment Simulator after order confirmation. Confirm the order remains confirmed and fulfillment is visibly pending, then recovers after service restart.
- [ ] Interrupt a simulator/service during a compensation so it cannot complete within the retry budget. Confirm the order is marked for manual review and the admin view displays the outstanding action and safe recovery instructions.
- [ ] Sign in with the local operator account at http://localhost:3000/admin. Find the test order in the operator/recovery view, review the audit trail and resolve only the documented simulated action.

## Database checks

Use the PostgreSQL owner account only for these read-only checks. Compare aggregate counts before and after each journey; do not paste personal addresses, email, customer subject identifiers, payment tokens or secrets into this document. Update table and database names if the reviewed migration contract changes.

```sh
docker compose --project-directory . --project-name supersports --env-file devops/.local/bootstrap.env -f devops/compose/core.yaml exec -T postgres sh -ec 'for database in orders pricing inventory payment fulfillment; do echo "--- $database ---"; PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -U postgres -d "$database" -c "SELECT version, description, success FROM flyway_schema_history ORDER BY installed_rank;"; done'
```

- [ ] Confirm migrations for Orders, Pricing, Inventory, Payment Simulator and Fulfillment Simulator succeeded.
- [ ] Confirm the successful order has one idempotency record, expected line count and `FULFILLMENT_SCHEDULED` state with matching order-owned Saga steps and outbox records.
- [ ] Confirm inventory has a single active/consumed reservation for the order and the stock movement ledger reconciles with on-hand stock.
- [ ] Confirm coupon usage has one committed redemption for the order; failed/declined orders leave no active hold.
- [ ] Confirm Payment Simulator has one authorization and one capture for the successful order; the decline case has no capture; a failed checkout's void/refund is represented once.
- [ ] Confirm Fulfillment Simulator has one shipment schedule for the confirmed order; replay did not add a second shipment.
- [ ] Confirm order-owned amount, currency, address snapshot, and configuration/pricing revisions are present, and no payment credentials/card data are stored.
- [ ] Confirm customer A's orders are not visible through customer B's API/UI. Operator identity cannot read customer profile data; customer identity cannot call admin APIs.
- [ ] Record date, Git revision, profile/dataset, aggregate outcomes and cleanup. Do not record customer identifiers or secrets.

## Manual result

- Tester/date:
- Git revision:
- Profile and dataset:
- Outcome by section (pass/fail):
- Issues / evidence paths:
- Database aggregate results (no identifiers):
- Cleanup performed:
