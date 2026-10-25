# S1-M11 manual end-user checks

2026-10-25 · Planned checklist; leave unchecked until performed by the owner after deployment.

- [ ] Use the UI access guide to start required profiles and verify service health. Open Storefront on port 3000 and separate Admin on port 3002; confirm different themes and correct logo assets.
- [ ] Sign into each operational UI with admin/admin; verify sign-out and restart login. Use a separate storefront customer account and confirm private cart/profile/order ownership.
- [ ] Browse Cricket and Football; verify at least 100 models in each sport, useful pagination/filter/search and genuine product photographs. Confirm fictional/illustrated legacy fixtures no longer appear in active results.
- [ ] Open a direct product link beyond page one. Read model details, inspect the gallery, select size/colour, and confirm exact SKU/price/stock in cart and checkout. Verify INR and USD views.
- [ ] Compare rating/count on category, search, product and Similar Products cards. Read the 3–4 demo-labelled reviews and confirm ratings are 3–5. Submit a review from an owned delivered purchase and confirm it awaits moderation before affecting public counts.
- [ ] Publish/hide a review in Admin and verify the public count/average changes consistently. Customer B must not submit a review for customer A's order.
- [ ] Use similar-product arrows and keyboard focus on desktop/mobile; cards exclude the current/retired product and open working details.
- [ ] Perform owner-side Catalog database checks for active product/SKU counts by sport and uniqueness; Pricing/Inventory/Reviews checks for complete currencies, nonnegative stock and published demo provenance. Do not use cross-service private-table joins.
- [ ] Reopen an older order created before catalog replacement; historical items, currency and money remain unchanged.

Date/operator: __________  Outcome: __________  Issues: __________

## U1 operations checkpoint

- [ ] Open http://localhost:3000 and http://localhost:3002/admin side by side. Verify storefront/Admin themes differ and an old http://localhost:3000/admin bookmark redirects.
- [ ] Follow [UI access](../../setup/ui-access.md); use admin/admin for enabled operations interfaces and a separate customer account for shopping. Start heavy graph/dashboard-studio profiles selectively.
- [ ] In the identity database, inspect the master admin account and operator client callback configuration using DBeaver or the Keycloak console. Confirm both new and legacy callbacks exist and customer-realm accounts remain separate. Do not copy service passwords into tracked files.
- [ ] Restart a selected profile and repeat login. Confirm Prometheus/Trino reject anonymous/wrong-password requests and backend containers have no host publication bypass.
