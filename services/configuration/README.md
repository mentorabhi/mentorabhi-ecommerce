# Configuration foundation — S1-M02 U1

Independent Spring Boot 4.1.2 Maven project, Java 27. Dependency versions come from the pinned Boot parent; no root aggregator or shared persistence library is required. [Bootstrap contract](../../design/S1-M02/bootstrap.md) governs this unit; R10–R13, R16/R17/R19 and initial AE12/AE13 apply.

## Ownership and API

Owns only database `configuration`, accessed as non-superuser `supersports_configuration`. No other service's tables are queried. Infrastructure creates the isolated database/user and revokes cross-database access; this project does not provision roles or databases. All infrastructure and Dockerfiles belong to host-owned `devops/`.

`GET /api/v1/configuration` requires a valid local JWT, without a role requirement (ADR 0003). Returns a revisioned `{categories,settings}` snapshot from JDBC in a read-only repeatable-read transaction. `PUT /api/v1/configuration/checkout/{key}` updates allow-listed checkout simulation values; `PUT /api/v1/configuration/returns/window-days` updates the local return window. Both use optimistic per-setting revisions, append actor/old/new values and revisions to `configuration_setting_audit`, and increment the global revision. Stale updates return 409; invalid values return 422. Accepted orders and return requests retain their setting revision and calculated snapshot.

The registry includes `returns-policy` with operator-editable `returns.window-days=30`, constrained to 1–90 days. Other defaults include `store.currency=INR`, `store.country=IN`, `store.language=en`, supported currencies INR/USD, simulated payment/shipping/tax, local storage, local Keycloak and local-only Nova endpoints. Checkout simulation settings include tax basis points, per-currency shipping minor units, reservation duration and payment authorization mode. Editable settings appear in the Configuration section of the operator UI; remaining categories stay visible as reviewed migration-managed defaults. No credentials are returned.

The operator routes require the operator API audience. The checkout internal settings read requires the exact worker client, internal audience and `checkout:configuration.read` scope. Only GET `/actuator/health/liveness` and GET `/actuator/health/readiness` are public. Readiness includes `readinessState,db`; liveness includes only `livenessState`. Components/details are never shown. Only health is exposed through Actuator; all other routes/methods are denied. This bearer-token API is stateless, with CSRF disabled and no form/basic login.

## Runtime configuration

Supply `SPRING_DATASOURCE_URL=jdbc:postgresql://<private-postgres-host>:5432/configuration`, `SPRING_DATASOURCE_USERNAME=supersports_configuration`, and `SPRING_DATASOURCE_PASSWORD` through the host's secret environment. The username defaults to the owning role; URL and password are not committed. Hikari uses at most five connections and a 3-second connection acquisition timeout. Application port is Boot's 8080 inside its container; the host owns loopback mappings.

Standard Boot environment variables bind directly:

- `SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_ISSUER_URI` (default `http://localhost:8180/realms/supersports`).
- `SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_JWK_SET_URI` (default internal `http://identity:8080/realms/supersports/protocol/openid-connect/certs`).
- `SPRING_SECURITY_OAUTH2_RESOURCESERVER_JWT_AUDIENCES` (default `supersports-api`).

Boot configures the decoder, signature/time checks, issuer validation even with an explicit JWK URI, and configured-audience validation. An additional Boot-discovered validator always requires `supersports-api`; changing the configured audience list cannot remove that requirement. All authenticated local accounts can read the registry. Application role claims do not control access (ADR 0003).

The Boot 4 modular starters include MVC, JDBC, Actuator, security resource server and **Flyway auto-configuration**. Flyway's PostgreSQL module and the PostgreSQL driver are runtime dependencies. JDBC supplies DB health auto-configuration. Do not substitute raw Flyway core alone for the starter.

## Build and focused unit check

From the repository root, with Docker running (no host Java/Maven required):

```sh
docker run --rm \
  --mount type=bind,src="$PWD/services/configuration",dst=/workspace \
  --mount type=volume,src=supersports-u1-maven-configuration,dst=/root/.m2 \
  -w /workspace maven:3.10.0-eclipse-temurin-27@sha256:095c056353550ea93605f9cbd200a7cbbc489a1989eeec8b8600749a157a0096 \
  mvn -B -q -Dtest=SecurityPolicyTest,RequiredAudienceTest,ConfigurationRepositoryTest test
```

The cache is private to this service's U1 checks. Reports/build output stay in ignored `target/`. For an independent executable jar build, the same container invocation can run `mvn -B verify`; the worker did not execute that broader build. The Boot Maven plugin repackages `target/configuration-0.1.0-SNAPSHOT.jar`. Host deployment/verification is separate.

## Migrations and limits

`V1__bootstrap.sql` creates the categorized registry. V2 adds checkout simulation defaults, V3 enables optimistic operator updates with an audit table, and V4 adds the revisioned local return-window setting. Flyway records migration history and checksums; subsequent starts do not reseed or overwrite records. No destructive rollback/down-migration is supplied. A prior compatible app image may reuse the schema; operational rollback belongs to the host.

Configuration management covers local settings only; it does not connect cloud services or execute provider adapters. Real payments, model calls, hosted fallback and cross-service data access are not implemented. Live migration and integration outcomes are recorded in the milestone verification document.
