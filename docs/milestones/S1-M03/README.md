# S1-M03 — Catalog, pricing, inventory and fixtures

Revision 5 · 2026-10-24 · Status: implementation verified; code review was skipped due to the session usage limit; checkpoint pending.

Design: [S1-M03 catalog and inventory contract](../../../design/S1-M03/catalog-inventory.md). Editable diagram: [Excalidraw source](../../../design/S1-M03/catalog-inventory.excalidraw); preview: [SVG](../../../design/S1-M03/catalog-inventory.svg).
Manual end-user checks: [S1-M03 manual acceptance](manual-acceptance.md).
Decisions: [ADR 0002](../../decisions/0002-merchandising-stock-ownership.md). Origin requirements: R01, R02, R04, R07, R09, R16–R19 in [accepted requirements](../../../requirements/accepted-requirements.md).

## Scope checkpoint

S1-M03 adds merchandising administration and deterministic data; it does not deliver the customer storefront or checkout. Catalog, Pricing and Inventory own separate service databases and talk through APIs. The existing M02 Configuration currency descriptor is not a second runtime currency authority; Pricing owns active currency. INR/USD books must both be complete for every active SKU before activation. Coupon definitions are maintained here, while usage holds/redemption and inventory reservations remain S1-M05 work.

The admin browser in `apps/storefront` covers Catalog, Prices & Coupons, and Inventory with local Keycloak PKCE login. Product illustrations and brand artwork are local SVGs. M03 does not add Redis, Kafka, object storage, remote assets, cloud services or Ollama runtime dependencies.

## Design review — 2026-10-23

Compound Engineering `ce-doc-review` reviewed the implementation design in two passes. No external model CLI was used because the project working agreement prohibits it without explicit direction. The Compound Pack resolver found no declared packs or errors.

| Lens | Result |
|---|---|
| Coherence | No findings in either pass |
| Feasibility | Round 1 found a race between product activation and currency switching; round 2 found competing currency owners in Pricing and Configuration |
| Security | Round 1 asked for explicit Catalog/Pricing write roles; round 2 asked for stale-revision protection/audit on Catalog mutations |
| Scope | Round 1 challenged a replaceable asset abstraction with no second consumer; round 2 found no further issue |
| Adversarial | No findings in either pass |
| UI-oriented review | Round 1 asked for loading/empty/error/success/401/403 states, usable mobile table/form layouts, and a reviewable fixture-import preview. Those requirements were added. The dispatched design-lens prompt returned a `product-lens` reviewer label, so it is recorded as a label mismatch rather than a separate design-lens receipt. The round-2 UI-oriented response returned no findings. |

Applied design changes: require both INR/USD prices before product activation and prohibit deletion of required price entries; make Pricing the sole runtime currency owner and keep the M02 setting descriptive; define the role matrix; add Catalog optimistic revision checks/audit; remove the unused asset adapter abstraction; specify UI data states, import preview and mobile behavior. The review's manual currency-race concern was resolved through those implementation constraints without changing the accepted two-currency product behavior. No unresolved product decision blocks implementation.

The review is design evidence only. Runtime evidence below is recorded separately from design approval.

## Implementation evidence

Implementation includes separate Catalog, Pricing and Inventory services, migrations and OpenAPI contracts; React admin UI; local SVG brand/product art; synthetic Cricket/Football products; both currency price books and coupons; and Compose integration. Runtime configuration defaults to INR. Ollama stays host-installed and is not in the Compose profile.

### Verification evidence — 2026-10-23

| Check | Result |
|---|---|
| `devops/scripts/manage.py validate` | PASS; Compose configuration resolves |
| `devops/scripts/manage.py unit` | PASS; 17 Python operations tests; Catalog 9, Configuration 9, Pricing 1, Inventory 2 Java tests (21 total) |
| `devops/scripts/manage.py test` | PASS; 15 real-stack integration tests across auth, role boundaries, fixtures, currency/coupons, stock idempotency, migrations/database isolation and loopback-only ports |
| Fixture import | PASS twice; 6 products and 2 coupons; repeated import preserves initial stock movements |
| `devops/scripts/manage.py test --recovery` | PASS; 15 integration tests plus service restart, database outage/readiness, liveness, reconnection and identity recovery |
| Container build | PASS for all five application images using pinned ARM64-compatible Node 24.22.1 and Nginx 1.29.8; Java images run `mvn verify` in build stages |
| Storefront runtime | PASS; `http://localhost:3000/` returned 200 and `/healthz` returned `ok`; Docker healthcheck healthy |
| Container RSS | 1,816.4 MiB in a single snapshot across seven containers (including an existing Configuration container); Docker allocated 7.75 GiB. This is not peak or load-test evidence. |
| UI dependency audit | 0 vulnerabilities in the implementation-time npm audit; host Node 26 is incompatible with the pinned TypeScript package, so build runs in pinned Node 24 container |
| `devops/scripts/ci` | PASS end to end, including Python/Java unit checks, Helm lint/render, Terraform validation/native tests, full container rebuild, 15 live integration checks, recovery and all three Selenium journeys |
| Browser login regression | PASS after the React hook and Nginx proxy fixes; Playwright completes local PKCE login and confirms Catalog fixture data renders without browser errors |
| Selenium admin UI suite | PASS; three Chrome journeys cover Catalog sign-in/art/category filters/product activation, currency switching/coupon creation, and inventory adjustment idempotency/reversal; persisted database state checked (7 active products, 7 INR/USD prices, 3 coupons, INR active currency, 6 balances) |
| UI controls and API proxy fixes | PASS; category filters are functional buttons, inert card/menu controls were removed, and the brand link returns to the workspace start. Product price writes read current revisions so an interrupted draft can resume. Nginx explicitly forwards the bearer header for Catalog, Pricing and Inventory; Pricing previously saw browser requests as anonymous and the shared refresh left Inventory blank. Pricing error dispatch preserves original responses. |
| Selenium command and CI | PASS; `devops/scripts/supersports ui-test` checks Storefront health then runs the Python Selenium suite; `devops/scripts/ci` installs the pinned test dependency and runs it after stack recovery/integration checks |
| Visual browser review | Pending user review; UI is available at http://localhost:3000 |

Remaining limits: no user visual review, load/peak memory benchmark, real payment/fulfillment, or coupon redemption/usage reservation (later milestone). The M03 browser app is a local admin workspace, not the customer shopping experience. Selenium retains one synthetic product/coupon and appends two inventory ledger movements per successful run; the manual acceptance guide documents their expected database state.

The live Keycloak 26.8.1 upgrade test exposed missing `sub` claims for the existing direct-grant test clients because their explicit default-scope list excluded Keycloak's `basic` scope. Added idempotent local provisioning to attach `basic` to the CLI, negative-audience CLI and browser clients. This supplies the subject used in audit records. The role checks in this historical entry were superseded by the user's later authentication revision in ADR 0003; JWT audience validation remains required.

### User revision — simple local authentication

[ADR 0003](../../decisions/0003-simple-local-authentication.md) and its editable Mermaid flow were written and reviewed before implementation. It supersedes the historical role checks above: all authenticated local accounts can use Catalog, Pricing, Inventory and read Configuration. The browser keeps the existing username/password login, PKCE session and logout; the APIs still validate the token and audit the subject. Old role-converter code/tests were replaced by filter-chain policy tests using a valid identity without role claims.

Verification after this revision: 20 Python operations tests, 29 Java tests (Catalog 8, Configuration 8, Pricing 6, Inventory 7), 15 live integration tests, Helm/Terraform validation and recovery checks passed. Two full CI attempts caught an outdated Selenium helper call and stale same-tag containers, respectively; both were fixed and CI is rerunning with forced container recreation. After the helper fix, all four Selenium journeys passed, including the requested `admin` login, mobile navigation/sign-out, and an inventory adjustment/replay/reversal. Playwright login regression also passed. The manual checklist uses one ordinary local account across all admin sections.

### User credentials and supplied brand assets — 2026-10-24

The local login is `admin` / `admin`; the password is held in ignored `devops/.local/admin-login.env` and synchronized into Keycloak during `supersports up`. The owner-provided icon and banner are copied unchanged under `apps/storefront/public/brand/`, with source recorded in its README. Sign-out stays visible in the top bar on mobile and desktop, and mobile table labels are data-driven. Targeted operations and browser checks pass. The latest full CI result is recorded after completion below.

Code review: skipped (ce-code-review unavailable). The local review agent exited at the session usage limit before returning its receipt; no external peer review was used. This is a review coverage limit, not a passed review.

### Final milestone verification — 2026-10-24

The final `./devops/scripts/ci` run passed end to end after `supersports up` was changed to force-recreate containers when rebuilding an unchanged tag. Evidence: 20 Python operations tests, 29 Java unit tests, 15 live service/database integration tests, Helm/Terraform validators, restart/database-outage recovery, identity reconnection, and four Selenium journeys. A separate `npm run test:e2e` passed its Playwright PKCE login regression. Selenium verifies `admin`/`admin`, supplied icon/banner loads, catalog filtering/product activation, currency/coupon administration, inventory idempotency/reversal and phone-width navigation/sign-out. Direct and Nginx-proxied Pricing requests both return 200 for the role-free local account after recreation. `git diff --check` passes.

An owner-provided asset screenshot was inspected at 1440 × 1000; the full banner is visible without cropping. End-user manual checks remain pending in [manual acceptance](manual-acceptance.md). Code review remains explicitly skipped as recorded above. Resource measurement remains the earlier single RSS snapshot, not peak/load evidence. Checkout, real money/fulfillment and coupon redemption remain later milestone scope.
