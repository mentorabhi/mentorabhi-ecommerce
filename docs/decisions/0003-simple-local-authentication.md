# ADR 0003 — Simple authentication for local administration

Date: 2026-10-23 · Status: accepted user revision; reviewed before implementation.

## Decision

The user requested basic authentication without role-based authorization. All signed-in local accounts may use Catalog, Pricing, Inventory and the Configuration registry. The UI exposes all three merchandising sections after sign-in. No realm-role assignment is required.

“Basic authentication” means a simple username/password sign-in experience. Retain the working local Keycloak login and PKCE session, including logout, token signature/issuer/audience/expiry validation and authenticated audit subjects. Changing to the HTTP Basic protocol is unnecessary for this requirement. Existing demo account names and credentials continue to work; their role labels have no effect on these APIs.

The local accounts are trusted operators. Anonymous requests still fail, health probes remain public, and unimplemented routes/methods remain denied. Customer-owned carts, addresses and orders in subsequent milestones still require ownership checks, as do Nova approval and deterministic stock/money rules. This decision removes administrative role distinctions, not business invariants or database service isolation.

## Supersession and review

Supersedes the application role requirements in R09/AE11, ADR 0002 decisions 5–6 and the M03 role matrix. Original design reviews and M02 verification results remain historical evidence. The new policy also applies to the existing Configuration read endpoint.

Review: the policy is consistent across frontend and all four APIs; server authentication prevents anonymous writes; keeping subject identity preserves audit attribution; only trusted local accounts use this workspace. No database migration or dependency change is needed. Customer ownership remains explicit to prevent this simplification from accidentally granting access to another customer's future data. No unresolved design blockers.

## Verification plan

Unit checks exercise each service's real security filter with an authenticated token containing no role claims, missing/invalid credentials, and unsupported methods. Live tests exercise ordinary customer credentials across all admin reads and mutations, and retain invalid-token/audience and service/database isolation checks. Selenium uses the ordinary customer account to traverse all screens and make/reverse a stock adjustment. Update the manual milestone guide and record measured results after execution.

Editable flow: [local authentication diagram](../../design/S1-M03/local-authentication.mmd).

## Follow-up user decisions — 2026-10-23

Provide a local account named `admin` using the password `admin`. Store its value only in ignored `devops/.local/admin-login.env` with mode 0600; provision/synchronize it through the local identity admin API. New local setups set this user-supplied demo value before first start. Do not weaken database or identity bootstrap credentials. The application account has no administrative role assignment requirement.

Use the two user-supplied JPEGs unchanged: icon in the site brand and favicon; banner in the sign-in page. Package both locally and record provenance. Expose sign-out in the top bar at mobile and desktop widths, and label mobile inventory cards with warehouse/quantity/revision rather than price-table labels. Review: these changes are local and reversible, require no service schema or dependency change, and fit the current admin UI. Selenium must exercise the new account, supplied assets, mobile navigation and logout before checkpointing.
