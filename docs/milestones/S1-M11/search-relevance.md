# Storefront search relevance revision

2026-10-25 · User reported searching `bat` returns cricket kits.

## Diagnosis and reviewed design

The public browse repository currently ORs substring matches across title, brand, description and category, then sorts alphabetically. `bat` therefore matches `batting gloves/pads`, while `ball` matches the substring in `football` even for apparel. Reproduced against the live catalog: bat returned 65 results, beginning with gloves/pads; ball returned 124 including jackets/jerseys. There is no relevance ranking.

Use deterministic local PostgreSQL full-text matching with the `simple` dictionary (whole lexemes rather than English stemming of bat/batting). Recognize singular/plural equipment queries (bat/bats, ball/balls, pad/pads, etc.) against existing `details.equipmentType`. A single unambiguous equipment intent restricts results to that type; legacy products without equipment metadata use whole-word title matching. Remaining words must all match across title/brand/model/description/category/sport. Ignore only conversational filler such as `a`, `the`, `show`, `me`, `find`, `for`. Punctuation-only input returns no matches. Queries containing literal `%`, `_` or `!` use bound literal substring matching rather than dropping those characters or interpreting them as wildcards. Match terms are bound SQL parameters, never SQL/query-string interpolation.

Rank title/brand/model matches ahead of description-only matches, with stable title/id ties before pagination. Empty search keeps the original browse order. Category/sport/visibility constraints and count/page consistency remain. No new hosted search service, model, dependency or data mutation. The current frontend already preserves the API result order in Featured mode; explicit user-selected sorting remains available.

Review: a bat query must exclude populated non-bat equipment even if its title mentions a bat. Plural queries and reversed brand/equipment order must work. Category/sport terms narrow the same query. Literal wildcard characters must never become SQL wildcards; punctuation-only queries must not return the entire catalog. Pagination must apply after filtering/ranking, not to a locally filtered first page.

## Verification plan

Add unit cases for query normalization/intent and real PostgreSQL API regressions with adversarial kits, batting accessories, football apparel, plural/brand/sport/multiword queries, visibility, literal punctuation, pagination and deterministic relevance. Reproduce the deployed failure in Selenium before rollout, then check real bat/ball/pad searches and product navigation after deployment. Retain the sourced data and all commerce history. See [editable flow](search-relevance.mmd).

## Executed regression evidence

The pre-deployment Selenium check failed for bat results containing other equipment and plural `balls` returning no results: one test, two failed subcases, 4.505s (`s1-m11-search-red.log`).

The first real-PostgreSQL regression run passed the new search scenarios but caught an existing literal `%25` boundary changing into the numeric term `25` (25/26 passing, one failure). Queries containing `%`, `_` or `!` now retain a bound literal substring constraint instead of dropping those characters. After correction and final alias consistency review, the complete Catalog Maven verify passed **26/26, zero skips**, in **30.705s** (`s1-m11-search-postgres-final.log`), including **8 real PostgreSQL boundary tests** and **3 query-interpretation unit tests**. Tests use fresh random schemas in the existing local PostgreSQL 18.6 instance and drop only those owned schemas. No live products/history were changed.

The deterministic matching deliberately does not add typo correction, embeddings or semantic/graph search. Existing Catalog metadata remains authoritative; unknown equipment words use ordinary whole-word matching. At this catalog size the query scans the local catalog; a larger dataset requires a measured indexing/search-capacity decision, not a production-throughput claim. The graph projection remains separate from storefront search.

The normal Docker Catalog build (tests enabled) and readiness deployment gate passed (`s1-m11-search-build.log`). Live sourced-catalog checks returned bat/bats **13**, ball/balls **25**, pads **24**, and `SG cricket bat` **2**; each returned item had the requested equipment type.

The first deployed Selenium run exposed a harness stale-element race while React replaced browse cards with search results. The wait now reads the entire card-ID array in a single browser JavaScript snapshot, retaining exact result-order assertions and the same deadline. The complete catalog Selenium file then passed **4/4 in 13.571s** (`s1-m11-search-browser-clean.log`): actual search input/button submission, API/UI result order, product navigation, real photographs/variants/bounded requests, portrait bounds at desktop/mobile, and banner-free routes. The failed stale-element run is retained separately in `s1-m11-search-browser-final.log`.

Host diff review covered bound SQL arguments, whole-word matching, metadata/legacy fallback, stable ordering before LIMIT/OFFSET and matching count filters. Code review: skipped (ce-code-review unavailable), per the recorded native reviewer limitation; no independent clean verdict is claimed. The owner manual checklist remains unchecked.

## Reproduce the PostgreSQL gate

After local setup/configuration and PostgreSQL startup, run from the repository root. The test uses fresh random schemas and requires the explicit owner/admin test credentials; do not point it at an unrelated database. No secret values are printed or committed.

```sh
.venv/bin/python - <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, 'devops/scripts')
import manage
root = Path.cwd()
env = manage.deployment_env(root)
env.update(CATALOG_TEST_JDBC_URL='jdbc:postgresql://postgres:5432/catalog',
           CATALOG_TEST_DB_USER='postgres', CATALOG_TEST_DB_PASSWORD=env['POSTGRES_PASSWORD'])
manage.run(['docker', 'run', '--rm', '--network', 'supersports_default', '--memory', '768m',
    '-e', 'MAVEN_OPTS=-Xmx256m', '-e', 'CATALOG_TEST_JDBC_URL', '-e', 'CATALOG_TEST_DB_USER',
    '-e', 'CATALOG_TEST_DB_PASSWORD', '-v', str(root / 'services/catalog') + ':/workspace',
    '-v', 'supersports-maven-cache:/root/.m2', '-w', '/workspace', env['BUILD_IMAGE'],
    'mvn', '-B', '-ntp', 'verify', '-DargLine=-Xmx256m'], environment=env)
PY
```

Run heavy test/build jobs sequentially on the baseline host; optional telemetry stores may be stopped temporarily while retaining their volumes, then restored. Customer commerce/history services and their data remain intact.
