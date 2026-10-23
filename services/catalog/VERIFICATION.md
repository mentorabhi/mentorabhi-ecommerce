# U1 verification — 2026-10-23

Baseline HEAD verified before editing: `fe7b7d98322a70728f9e15a30454a9d18b37b344`; unchanged at the final pre-documentation check. Native inline execution in the shared workspace; no external model CLI, override, Git index mutation, commit, Compose operation, host Java/Maven, or global install.

## Behavior and proof

New independent catalog application: protected read API, realm-role conversion, mandatory API audience, Flyway bootstrap data and public DB-aware readiness. There were no existing service tests or sources to inspect at baseline (`services/` was absent).

Tests were authored before production sources. Observed initial red: the focused Maven command exited 1 at test compilation because `RealmRolesConverter`, `CatalogController`, and `CatalogRepository` did not exist. After implementation the original eight tests passed.

Added tests:

- `RealmRolesConverterTest`: six cases; only realm roles, deduplication, missing/malformed claim, missing/non-list roles, mixed/null/blank role list, empty roles.
- `RequiredAudienceTest`: one case covering missing, wrong-only and required-plus-other audiences.
- `CatalogControllerTest`: two cases; exact JSON and migrated schema lookup, plus DB failure propagation.

## Final measured command

```sh
docker run --rm --mount type=bind,src=/Users/abhijitkumarsingh/ChatGPT/mentorabhi-ecommerce/services/catalog,dst=/workspace --mount type=volume,src=supersports-u1-maven-catalog,dst=/root/.m2 -w /workspace maven:3.10.0-eclipse-temurin-27@sha256:095c056353550ea93605f9cbd200a7cbbc489a1989eeec8b8600749a157a0096 mvn -B -q -Dtest=RealmRolesConverterTest,RequiredAudienceTest,CatalogControllerTest test
```

Exit 0. Surefire XML inspected: **9 tests, 0 failures, 0 errors, 0 skipped**. JDBC unit tests use Mockito result sets and templates; this is not real PostgreSQL persistence/auth acceptance. Mockito emitted its dynamic agent-loading warning; tests passed. No model or application runtime was started.

The pinned container reports Maven `3.10.0` (`c43a36b8d67be7e0805a411bc0898af1a51f5472`), Temurin `27+35` (`openjdk 27`, 2026-09-15), Linux `aarch64`. Compiler plugin `3.15.0`, Surefire `3.5.6`; all supplied by the pinned parent. Image ID matches its supplied digest. Artifact inspection confirmed JDBC health auto-configuration and the resource server's additional-validator support. Boot starter metadata was checked against Maven Central; [official build documentation](https://docs.spring.io/spring-boot/reference/using/build-systems.html) and [JWT documentation](https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html) were consulted. Spring/Maven are Apache-2.0; Temurin is GPLv2 with Classpath Exception; PostgreSQL uses its PostgreSQL license. Full transitive notices/SBOM and security scans were not generated.

## Exceptions, pending verification and omitted work

No behavior-unit-test exception. README/configuration wiring and SQL are not claimed runtime-verified by these unit tests. Host must run actual Flyway/PostgreSQL acceptance, endpoint authorization/signature/issuer checks, wrong-audience HTTP checks, outage/recovery readiness, restart persistence, isolation and resource measurements. No full suite, Compose stack, package/verify build or authoritative integration checks were run by this worker.

Considered and not built: a shared security library (the design explicitly keeps both projects independent); custom JWT decoder/key retry/fallback (Boot already supplies required decoder behavior); configuration write/activation or adapter-selection mechanisms (later milestones, not this read-only registry). The extra audience validator is required by the explicit API security contract. No migration rewrite/reset facility was added.

All authored paths are under `services/catalog/`: `pom.xml`, `README.md`, `VERIFICATION.md`, `src/main/java/com/supersports/catalog/*.java`, `src/main/resources/application.properties`, `src/main/resources/db/migration/V1__bootstrap.sql`, and `src/test/java/com/supersports/catalog/*Test.java`. Generated `target/` artifacts are ignored and excluded from delivery. No changes outside the two owned service directories are attributable to U1.
