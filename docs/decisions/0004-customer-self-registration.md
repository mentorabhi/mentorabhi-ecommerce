# ADR 0004 — Customer self-registration identity boundary

Date: 2026-10-24 · Status: accepted by user.

## Context

The user selected customer self-registration for S1-M04. ADR 0003 permits every authenticated local account to administer Catalog, Pricing, Inventory and Configuration. Putting public registrations in the same identity realm/client audience could grant a customer token the existing `supersports-api` audience and therefore operator API access.

## Decision

Add a dedicated `supersports-customers` Keycloak realm with public PKCE client registration. Keep operator login in the existing `supersports` realm and preserve its `supersports-api` audience. The Customer service accepts only signed tokens with the exact customer-realm issuer and `supersports-customer-api` audience, validates token time/signature, and derives the owner from `sub`. It rejects operator-realm tokens. M03 services continue to validate only the operator realm issuer and `supersports-api` audience, so customer tokens cannot administer them. Customer endpoints never accept a caller-supplied subject/customer ID.

The frontend contains separate customer and operator OIDC configurations. Customer profile data does not contain identity passwords or tokens. Self-registration is local only; it sends no identity data to a cloud/hosted service.

## Alternatives

- Same realm with audience separation: rejected because shared realm/client scopes create an avoidable audience-mapping escalation path.
- Customer accounts provisioned by operators: rejected by the user, who selected self-registration.
- Anonymous browser-local cart: rejected because wishlist/cart/profile must be persistent and customer-owned.

## Verification consequences

Before enabling registration, integration tests must prove customer registration and customer-realm token issuance. The customer token must be rejected by Catalog, Pricing, Inventory and Configuration; the operator token must be rejected by Customer. Verify access/refresh token lifecycle in the browser, subject isolation across two accounts, migration/restart behavior and logout. The customer token/audience must never be added to `supersports-api` through shared default client scopes.
