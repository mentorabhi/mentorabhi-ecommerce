---
title: SuperSports Stage 1 — High-level Knowledge Transfer
date: 2026-10-26
input_shape: concept
subject: Implemented services, APIs, infrastructure, access and end-to-end flows at the Stage 1 release
---

# SuperSports Stage 1 — Knowledge Transfer

This is the starting document for someone taking over development or operating the local learning environment. It describes the Stage 1 system after M13, including the 54-family Cricket catalog expansion, image/search corrections and separate Admin UI. Nova is the future shopping assistant; it is not deployed. Payments, shipping, stock and DEMO reviews are simulated. Product models/photos are sourced, with provenance retained.

The runtime inventory was checked on **26 October 2026**: **34 Compose service definitions, 25 running containers**, six stopped optional application/infrastructure containers, one completed initialization container, and two job/drill definitions without retained containers. Availability is a dated snapshot, not a promise that optional profiles are always running. The [sanitized inventory](supersports-stage1-inventory.json) records exact ports, memory limits, profiles and named volumes without secrets. This guide is a high-level map; linked contracts/source and milestone records contain payloads, detailed rules and failure-injection evidence.

## 1. Architecture in one page

SuperSports has two React/TypeScript applications, served independently by Nginx. Their `/api/...` routes proxy to independently running services. Eleven Java/Spring Boot services own business state in separate PostgreSQL databases on one local PostgreSQL instance. Keycloak handles customer/operator/service identity. Durable Orders state drives a retryable checkout Saga; the same transaction writes lifecycle facts into an outbox. Debezium captures that outbox through PostgreSQL WAL into Kafka. History, graph and batch analytics build separate read models from those events.

Services call other services' APIs; they do not join each other's private database tables. A shared PostgreSQL process is infrastructure sharing, not shared ownership of business tables. Derived History/Neo4j/Iceberg data does not authorize a purchase or change stock/money. Internal service names resolve through Docker DNS, for example `http://catalog:8080`; `localhost:8081` is the host-side publication of that service.

```mermaid
flowchart TB
  Buyer[Customer browser] --> Store[Storefront / Nginx :3000]
  Operator[Operator browser] --> Admin[Admin / Nginx :3002]
  Store --> Identity[Keycloak :8180]
  Admin --> Identity
  Store --> Commerce[Catalog, Pricing, Inventory, Customer, Orders, Reviews, Support]
  Admin --> Commerce
  Admin --> Fulfill[Fulfillment simulator]
  Commerce --> PG[(PostgreSQL: owned databases)]
  Commerce --> Payment[Payment simulator]
  Commerce --> Fulfill
  Commerce --> Config[Configuration]
  Config --> PG
  Payment --> PG
  Fulfill --> PG
  PG --> CDC[Debezium / Kafka Connect]
  CDC --> Kafka[Kafka lifecycle events]
  Kafka --> History[Order History]
  History --> PG
  Store --> History
  Kafka --> Graph[Relationship graph API]
  Graph --> Neo4j[(Neo4j)]
  Kafka --> Spark[Spark batch job]
  Spark --> Iceberg[(Iceberg / local warehouse)]
  Iceberg --> Trino[Trino]
  Trino --> Reports[Analytics API]
  Reports --> Admin
  Trino --> Superset[Superset]
  Commerce -. OTLP .-> Collector[OpenTelemetry Collector]
  Collector --> Signals[Prometheus / Tempo / Loki]
  Signals --> Grafana[Grafana :3001]
```

[Editable overview](diagrams/kt-overview.mmd). Telemetry is cross-cutting; the diagram abbreviates its eleven instrumented Java producers rather than listing an edge for each. The optional graph and analytics paths are independent consumers, not dependencies of checkout.

## 2. Human interfaces and credentials

Use `localhost` in browsers because Keycloak callback URLs are configured for it. Published ports bind to host loopback. All operational **human** interfaces below use the requested local demo **admin / admin**. API Bearer tokens, database passwords and service client secrets are separate; `admin/admin` is not a universal database/API credential.

| Interface | Host URL | Credentials / purpose | Observed state |
| --- | --- | --- | --- |
| Storefront | http://localhost:3000 | Register/use a separate customer account; no shared operator password | Running |
| SuperSports Admin | http://localhost:3002/admin | `admin` / `admin`; merchandising, settings, post-purchase operations, reviews/support and reports | Running |
| Keycloak console | http://localhost:8180/admin/master/console/ | `admin` / `admin`; manage master/realms/clients/users | Running |
| Kafka UI / Kafbat | http://localhost:8091 | `admin` / `admin`; read-only inspection of topics/messages/partitions/groups/Connect | Running |
| Grafana | http://localhost:3001 | `admin` / `admin`; health/request dashboards, traces/logs in Explore; Skip an offered first-login password prompt | Running |
| Prometheus | http://localhost:9090 | Browser Basic auth `admin` / `admin`; PromQL via Nginx proxy | Running |
| Neo4j Browser | http://localhost:7474/browser/ | `admin` / `admin`; database `neo4j`, Bolt `bolt://localhost:7687` | Stopped; graph profile |
| Trino UI | http://localhost:8096/ui/ | Browser Basic auth `admin` / `admin`, then upstream username `admin` if prompted | Stopped; analytics profile |
| Superset | http://localhost:8095 | `admin` / `admin`; build SQL datasets/charts/dashboards over Trino | Stopped; dashboards profile |

The historical storefront `/admin` URL redirects to the separate Admin app. These logins are local learning defaults, not production credentials. Provisioning/restart/account details are in the [UI access guide](../setup/ui-access.md).

### Database and machine access

| Connection | Address / identity | Credential source and boundary |
| --- | --- | --- |
| Host PostgreSQL / DBeaver | `127.0.0.1:15432`, database `postgres`, user `postgres` | `POSTGRES_PASSWORD` in ignored `devops/.local/bootstrap.env`. Enable Show all databases. Port is opt-in and currently enabled; [DBeaver guide](../setup/database-access.md). |
| Application PostgreSQL | `postgres:5432`, owned database/user in the service table below | Corresponding `*_DB_PASSWORD` in the same ignored file; application containers receive their own secret. |
| Neo4j service identity | `bolt://neo4j:7687`, user `neo4j` | `GRAPH_DB_PASSWORD`; distinct from the human `admin/admin` account. |
| Kafka broker | Internal `kafka:9092`; published `127.0.0.1:9092` | Local PLAINTEXT demo broker, no broker login configured. It advertises `kafka:9092`, so host clients also need that advertised hostname resolvable/routable. Prefer Kafka UI or container-network tools; a published port alone does not configure a host Kafka client. |
| Kafka Connect REST | http://localhost:8090/connectors | No separate REST login configured; local operational endpoint, not a customer API. |
| Internal business APIs | Service HTTP base plus routes below | Keycloak Bearer JWT, with the route's customer/operator/worker audience rules. Never substitute Basic auth. |
| Host Ollama | Normally http://localhost:11434 | Host-installed prerequisite for future Nova; not a Compose service and not required by commerce. Current running/model state was not probed for this KT task. |

No generated secret values are copied into this tracked document. Read the named entry locally when connecting; do not commit the bootstrap file or a DBeaver connection export. The current History database is a rebuild target, not necessarily the original `order_history`: use `devops/scripts/supersports stream-status` and the persisted target rather than assuming its name. At this checkpoint it is `order_history_r_3ca8f0ec3312`, group `order-history-r-3ca8f0ec3312`.

## 3. Application service catalog and design

All Java rows below are independent Java 27 / Spring Boot 4.1.2 projects, JDBC/Flyway backed, exposing HTTP on container port 8080. Each has a **512 MiB** configured container limit except **Order History 768 MiB**. Every row is running except the two explicitly optional Python APIs. Frontends have **128 MiB** limits. Limits are configuration, not measured consumption.

| Service / source | Responsibility and design | Data ownership | Main touchpoints |
| --- | --- | --- | --- |
| [Storefront](../../apps/storefront) | React 19.3 / TypeScript / Vite build, Nginx static app and API proxy; browse/search, variant cart/wishlist, profile, checkout, history, reviews/support | Browser session/UI state; business state remains server-owned | Customer Keycloak realm; Catalog, Pricing, Inventory, Customer, Orders, History, Reviews, Support |
| [Admin](../../apps/admin) | Separate React/TypeScript app/theme and Nginx proxy; merchandising, configuration, fulfillment, moderation, support, reports | No separate business database | Operator Keycloak realm; owning APIs; Analytics API for optional reports |
| [Catalog](../../services/catalog) | Sports/categories, products and sellable SKUs, photographic details/provenance, activation/revision/retirement. Search is PostgreSQL whole-word/equipment-aware relevance; Similar Products uses metadata/sport ranking | `catalog`, user `supersports_catalog`, `CATALOG_DB_PASSWORD` | Storefront/Admin and Customer/Orders/Inventory callers; Pricing completeness check before activation |
| [Configuration](../../services/configuration) | Categorized adapter/config registry; revisioned checkout/return settings. Some infrastructure adapters are migration/configuration choices, not hot-swappable runtime services | `configuration`, `supersports_configuration`, `CONFIGURATION_DB_PASSWORD` | Admin; Orders settings/policy reads |
| [Pricing](../../services/pricing) | INR/USD price books, active currency, quote calculation, product-eligible coupons and coupon holds/commit/release. Amounts use integer minor units | `pricing`, `supersports_pricing`, `PRICING_DB_PASSWORD` | Storefront/Admin; Catalog completeness; Orders checkout worker |
| [Inventory](../../services/inventory) | Stock balances/movement ledger, revisions/idempotent adjustments, reservation/protection/commit/release, cancellation reversals, inspected-return restock | `inventory`, `supersports_inventory`, `INVENTORY_DB_PASSWORD` | Storefront/Admin; Catalog validates active SKU for adjustments; Orders worker receives/returns stock |
| [Customer](../../services/customer) | Customer-owned Indian address/profile, cart and wishlist; checks SKU facts via Catalog | `customer`, `supersports_customer`, `CUSTOMER_DB_PASSWORD` | Storefront/customer realm; Catalog; Orders reads the owned profile |
| [Orders](../../services/orders) | Checkout idempotency, immutable price/address/settings snapshots, durable fenced Saga and post-purchase state, transactional outbox; authenticated synthetic-order import for fixtures | `orders`, `supersports_orders`, `ORDERS_DB_PASSWORD` | Customer, Catalog, Pricing, Configuration, Inventory, Payment, Fulfillment, Keycloak; Reviews/Support ownership validation; Debezium reads outbox |
| [Payment simulator](../../services/payment-simulator) | Deterministic authorization/capture/void/refund ledger, bounded refund totals, operation-key replay/conflict and fencing; no payment gateway | `payment`, `supersports_payment`, `PAYMENT_DB_PASSWORD` | Orders worker only for payment mutations |
| [Fulfillment simulator](../../services/fulfillment-simulator) | Schedule simulated shipments, operator tracking transitions, delivery facts and cancellation claim/finalization race boundary; no carrier | `fulfillment`, `supersports_fulfillment`, `FULFILLMENT_DB_PASSWORD` | Orders worker/tracking/eligibility; Admin operator transitions |
| [Order History](../../services/order-history) | Kafka-derived customer order timeline/read model; inbox deduplication, aggregate sequencing, gap/DLQ handling, freshness, replay/rebuild support | Current History target database, `supersports_order_history`, `ORDER_HISTORY_DB_PASSWORD` | Kafka; Storefront/customer JWT; local owner/operator reconciliation and rebuild tooling |
| [Reviews](../../services/reviews) | Customer verified-purchase reviews, operator moderation, public summary batches, labelled DEMO review seed/replay; only published reviews affect public summaries | `reviews`, `supersports_reviews`, `REVIEWS_DB_PASSWORD` | Orders verifies owned delivered purchase; Storefront/Admin; Keycloak |
| [Support](../../services/support) | Owned support tickets/messages, operator queue/status transitions/audit | `support`, `supersports_support`, `SUPPORT_DB_PASSWORD` | Orders verifies order ownership when linked; Storefront/Admin; Keycloak |
| [Analytics API](../../services/analytics-api) | Python/FastAPI read-only allowlisted Trino queries; period/currency reports. Readiness route is process readiness; report requests test Trino/tables | No business DB; reads Iceberg projections through Trino | Admin `/api/reports/...`; Trino. **Stopped**, analytics profile, **256 MiB** |
| [Relationship graph](../../services/relationship-graph) | Python/FastAPI Kafka consumer projects `OrderAccepted` into Neo4j: Product–SKU–Order and SKU `BOUGHT_WITH`; bounded one/two-hop relationships | Neo4j projection, not order authority | Kafka, Neo4j, explicit graph API clients. **Stopped**, graph profile, **384 MiB** |
| [Health exporter](../../services/health-exporter) | Small Python HTTP service probes configured HTTP/TCP targets and exposes health metrics | No persistent business data | Readiness targets and Prometheus; **128 MiB**, running observability profile |

**Important:** the relationship graph is not used by storefront search or the current Similar Products rail. It is a separate learning/relationship API and a possible future Nova input. Redis, a vector database, a separate search cluster and a Nova service are not deployed in Stage 1.

### Main API entry points

These are principal operations, not a replacement for the linked OpenAPI contracts. Direct bases below are loopback developer endpoints. All Java services also expose `/actuator/health/readiness` and `/actuator/health/liveness`; frontends expose `/healthz`. A healthy process does not prove all business dependencies/optional reports are available.

For browser APIs, Nginx rewrites `/api/catalog/...` to `/api/v1/catalog/...`, and similarly for pricing/inventory/customer/orders/history/configuration. Reviews/support/fulfillment use a different rewrite: `/api/reviews/...`, `/api/support/...`, `/api/fulfillment/...` become `/api/v1/...`. For example, public reviews are `/api/reviews/reviews/products/{id}` through the frontend. Reports keep `/api/reports/...` unchanged. See [Storefront proxy](../../devops/nginx/storefront.conf) and [Admin proxy](../../devops/nginx/admin.conf).

| Service base on host | Principal routes relative to base | Access / contract |
| --- | --- | --- |
| Catalog http://localhost:8081 | `GET /api/v1/catalog/public/products?q=bat&page=1&pageSize=24`; `GET .../public/products/{slug}` and `/{slug}/similar`; sports/categories; admin product/SKU create/update/activate/retire | Public browse/detail; operator mutations; worker `GET /api/v1/internal/checkout/catalog/skus/{skuId}`. [Contracts](../../contracts/catalog) |
| Configuration http://localhost:8082 | `GET /api/v1/configuration`; `PUT /api/v1/configuration/checkout/{key}` and `/returns/{key}`; `GET /api/v1/internal/checkout/configuration` and `/returns-policy` | Operator configuration; worker settings/policy. [Contracts](../../contracts/configuration) |
| Pricing http://localhost:8083 | `/api/v1/pricing/currency`, `/public/skus`, `/prices`, `/coupons`; internal `POST /api/v1/internal/checkout/pricing/quotes`, `/coupon-holds` and order hold transitions | Public price snapshots, operator management, worker quote/holds. [Contracts](../../contracts/pricing) |
| Inventory http://localhost:8084 | `/api/v1/inventory/availability`, `/balances`, `/movements`, `/adjustments`, `/returns/pending`, `/returns/{returnId}/inspection`; internal `/api/v1/internal/checkout/inventory/reservations` and `/returns/{returnId}/receive` | Public availability; operator adjustment/inspection; worker reservation/restock. [Contract](../../contracts/inventory/openapi.yaml) |
| Customer http://localhost:8085 | `GET/PUT /api/v1/customer/profile`; `GET /cart`, `PUT/DELETE /cart/items/{skuId}`; `GET /wishlist`, `POST/DELETE /wishlist/items/{skuId}` under `/api/v1/customer` | Customer JWT and subject ownership. [Contract](../../contracts/customer/openapi.yaml) |
| Orders http://localhost:8086 | `POST /api/v1/orders/checkout`; `GET /checkout-requests/{requestId}`; order list/detail/tracking; `POST /{orderId}/cancellations`, `POST /{orderId}/returns` and eligibility/status reads under `/api/v1/orders` | Customer JWT; `Idempotency-Key` for checkout/cancel/return. Worker-specific ownership/purchase checks support other services. [Contract](../../contracts/orders/openapi.yaml) |
| Payment http://localhost:8087 | `POST /api/v1/internal/checkout/payments/{operation}` (`authorize`, `capture`, `void`, `refund`); `GET /{orderId}/status` | Internal worker JWT; no human payment UI. [Contract](../../contracts/payment-simulator/openapi.yaml) |
| Fulfillment http://localhost:8088 | `POST /api/v1/internal/checkout/fulfillment`; `GET /{orderId}`, `POST /{orderId}/cancel-claim`, `/cancel-finalize`; `POST /api/v1/operator/shipments/{orderId}/transitions` | Worker schedule/cancel; operator shipment transitions. [Contract](../../contracts/fulfillment-simulator/openapi.yaml) |
| History http://localhost:8089 | `GET /api/v1/order-history`; `GET /api/v1/order-history/{orderId}` | Customer JWT/owner-key projection filtering; freshness metadata. [Contract](../../contracts/order-history/openapi.yaml) |
| Reviews http://localhost:8092 | `GET /api/v1/reviews/products/{productId}`, `/products/summaries`; `GET/POST /api/v1/customer/reviews`; operator `/api/v1/operator/reviews`, `/pending`, `/{id}/moderation`, `/demo-seed` | Public summaries/published reviews; customer submit; operator moderation/seed. [Contract](../../contracts/reviews/openapi.yaml) |
| Support http://localhost:8093 | `/api/v1/customer/support/tickets` and `/api/v1/operator/support/tickets`; detail/messages; operator `PUT /{id}/status` | Customer-owned ticket access or operator token. [Contract](../../contracts/support/openapi.yaml) |
| Graph http://localhost:8094 | `GET /api/relationships/products/{product_id}?depth=1&limit=12`; `/health/ready` | Optional loopback graph API; no auth layer in its current FastAPI handler. Do not mistake this for a public customer endpoint. [Source](../../services/relationship-graph/app.py) |
| Analytics, internal `http://analytics-api:8080` | `GET /api/reports/summary`, `/daily-sales`, `/top-products`, `/refunds` with `currency`, `days` and bounded `limit` where supported | No direct host port; reachable through frontend `/api/reports/...` when enabled. Current API has allowlisted read queries but no JWT enforcement in its Python handler. [Source](../../services/analytics-api/app.py) |
| Health exporter, internal `http://health-exporter:9108` | `GET /metrics`, `/healthz` | Internal monitoring, no human credentials. [Source](../../services/health-exporter/app.py) |

The Admin/frontends do not turn an unauthenticated Python reporting handler into a service-level authorization boundary. Current local exposure/handler limits are explicit rather than assumed enterprise security.

## 4. Identity and configuration boundaries

Keycloak runs as `identity`, backed by database `identity`, user `supersports_identity`, secret `IDENTITY_DB_PASSWORD`. There are three distinct uses: **master** for console administration, **supersports** for operator/service clients, and **supersports-customers** for customer registration/login. The SPAs use browser OIDC; business services validate JWT issuer/audience. The Orders worker obtains a service token using client credentials so it can recover work after the customer's browser closes. Customer ownership remains enforced despite the deliberately simple operator login.

The configuration UI manages supported settings with revisions/audit. It does not create a managed Redis/Kafka/cloud account on demand, migrate databases, or switch every adapter without a deployment. Image/version/ports/resource/profile choices live under `devops/`; generated local secrets/state live under ignored `devops/.local/`. See [configuration contract](../../contracts/configuration/openapi.yaml), [identity decision](../decisions/0003-simple-local-authentication.md), and [ADRs](../decisions).

## 5. Infrastructure and other deployed components

Versions below are the repository's tested pins, not a new claim that they are today's newest releases. Exact immutable digests are in [images.lock.json](../../devops/images.lock.json). Services run on a Docker Compose network with independent containers/restart policies/limits; this local runtime is not Kubernetes pods or a multi-node HA deployment.

| Compose component | What it does / touchpoints | Endpoint / access | Profile, limit, observed state |
| --- | --- | --- | --- |
| `postgres` — PostgreSQL 18.6 | Owned transactional DBs plus Keycloak and Iceberg JDBC metadata; WAL logical replication for Orders CDC | Internal `postgres:5432`; optional host 15432, credentials above | Base, 384 MiB, running |
| `identity` — Keycloak 26.8.1 | Customer/operator/service tokens and console; PostgreSQL identity DB | Internal `identity:8080`, host 8180 | Base, 768 MiB, running |
| `kafka` — Kafka 4.3.1 | Single KRaft broker/controller; durable lifecycle/DLQ/replay and Connect internal topics | Internal `kafka:9092`; host-port caveat above | streaming, 1,024 MiB, running |
| `kafka-connect` — Debezium 3.7.0.Final | PostgreSQL CDC connector, replication slot/publication, outbox routing to lifecycle topic; Connect offsets/config/status in Kafka | Internal `kafka-connect:8083`, host http://localhost:8090 | streaming, 1,024 MiB, running |
| `kafka-ui` — Kafbat 1.5.0 | Inspects broker/topics/records/groups/connector state; read-only cluster configuration is not broker ACL enforcement | Host 8091, admin/admin | streaming, 512 MiB, running |
| `neo4j` — 2026.10.1 Community | Graph storage for relationship service; persistent product/SKU/order/co-purchase nodes/edges | Browser 7474 / Bolt 7687; logins above | graph, 1,536 MiB, stopped |
| `trino` — 484 | SQL engine over Iceberg JDBC catalog/warehouse; consumed by reporting API/Superset | Internal `trino:8080`; no direct host publication | analytics, 1,024 MiB, stopped |
| `trino-ui` — pinned Nginx | Host Basic-auth gate in front of Trino UI/HTTP | Host 8096, admin/admin | analytics, 64 MiB, stopped |
| `superset` — 6.1.0 local image | Optional authoring/report visualization; SQLite metadata under persistent Superset home and Trino data connection | Host 8095, admin/admin | dashboards, 1,536 MiB, stopped |
| `prometheus` — 3.15.1 | Scrapes exporter availability and Collector request metrics; local time-series store | Internal `prometheus:9090`; Grafana datasource | observability, 384 MiB, running |
| `prometheus-ui` — pinned Nginx | Host Basic-auth gate; avoids direct unauthenticated backend publication | Host 9090, admin/admin | observability, 64 MiB, running |
| `grafana` — 13.2.2 | Provisioned health/request dashboards, Prometheus/Tempo/Loki datasources and Explore links; SQLite WAL enabled for local dashboard concurrency | Internal port 3000, host 3001, admin/admin | observability, 512 MiB, running |
| `otel-collector` — 0.163.2 contrib | Receives Java OTLP, sanitizes/batches/routes traces/logs/metrics; allowlists rather than exporting arbitrary payloads | Internal OTLP HTTP 4318; metrics `otel-collector:9464` scrape endpoint; no host ports | observability, 192 MiB, running |
| `tempo` — 3.1.1 | Local trace storage/query backend used by Grafana | Internal HTTP query `tempo:3200`, OTLP ingest; no host ports | observability, 384 MiB, running |
| `loki` — 3.7.9 | Local dedicated safe HTTP-request logs, trace correlation | Internal `loki:3100`, no host ports | observability, 256 MiB, running |

The application table includes the remaining runtime containers: eleven Java services, two SPAs, two optional Python business APIs and the health exporter. The [complete 34-definition inventory](supersports-stage1-inventory.json) is the coverage checklist across both tables and the three execution-only definitions below.

### Jobs, initialization and recovery services

| Definition / project | Function and data touchpoints | Runtime behavior |
| --- | --- | --- |
| `lakehouse-init` | Initializes permissions/directories for the shared local warehouse/Ivy volumes | analytics-job profile; 64 MiB; completed/exited initialization container, no UI/API |
| `spark-ingest` / [lakehouse pipeline](../../data/pipelines/lakehouse) | Spark 4.1.3 batch reads retained Kafka lifecycle facts, validates/quarantines/deduplicates and builds Iceberg reporting tables; PostgreSQL JDBC catalog metadata, `/warehouse` files | analytics-job profile; 1,536 MiB; one-shot run, no retained container/host UI in current snapshot |
| `restore-postgres` | Isolated PostgreSQL restore target for backup/restore drills; separate volume, not a replacement for live PostgreSQL | restore-drill profile; 384 MiB; created for drills, absent now, no host port |
| [Real-catalog pipeline](../../data/pipelines/real-catalog) | Reviewed source manifest/photo restore, import through owning APIs, both price books/stock/DEMO review fixture orchestration; retires superseded active fixtures | Host `.venv/bin/python` tools; no permanent service/API |
| [Demo-commerce pipeline](../../data/pipelines/demo-commerce) | Reproducible synthetic customer/order history via intended fixtures/import boundary | Host tool; not a separate running container |

### Persistence, networking and deployment

| Persistent storage | Contents / owner |
| --- | --- |
| `supersports_postgres-data` | All owned SQL databases and logical WAL; preserve during normal restart |
| `supersports_kafka-data` | Broker topic logs and single-node KRaft state |
| `supersports_graph-data` | Neo4j projection |
| `supersports_lakehouse-data` | Local Iceberg warehouse files, shared by Spark and Trino; catalog metadata is in PostgreSQL `lakehouse` |
| `supersports_analytics-ivy` | Spark dependency cache, not business authority |
| `supersports_superset-home` | Superset local metadata/state |
| `supersports_prometheus-data`, `supersports_grafana-data`, `supersports_tempo-data`, `supersports_loki-data` | Local telemetry/dashboard stores |
| `restore-drill-data` under the drill project/configuration | Disposable isolated restored database, separate from live data |

Frontend photos are locally restored source assets packaged into the Storefront image; they are not hosted cloud storage. The reviewed manifest/provenance is tracked, while restored binaries/local state are ignored and reproducible. Backups and generated credentials belong to local ignored storage, not Git. Migrations are Flyway-owned; application rollback does not automatically reverse schemas/data.

The baseline host is a 16 GB ARM64 Mac with roughly 7.75 GiB allocated to Docker in the release measurement. The 25-container final snapshot used 6,453.52 MiB; a separate 24-container/120-second functional observation peaked at 6,369.28 MiB. These are finite observations, not capacity promises. Run Spark, graph, Trino and Superset selectively; enabling every profile together is not the default baseline workload. Alternate Kubernetes/Helm/Terraform artifacts are maintained under [devops](../../devops), but no Kubernetes cluster/cloud deployment is claimed.

## 6. Overall business and data flows

### A. Sign in, browse and manage products

A customer registers/signs in through the customer realm; anonymous browsing remains possible. Storefront requests paginated Catalog models plus batched Pricing/Inventory/Reviews snapshots. Product selection resolves a specific SKU; Customer owns the saved cart/wishlist/address. Search uses equipment metadata and whole words in PostgreSQL. Explicit sort controls can reorder the current page; they do not turn the system into semantic/graph search.

An operator uses the separate Admin/operator identity to create/edit models/SKUs and source details, set owning Pricing/Inventory records, then activate the model after required completeness/validity checks. Revision/idempotency conflicts prevent silent overwrites. Retiring a listing hides it from current shopping while preserving historical identity/order snapshots.

### B. Checkout and recovery

```mermaid
flowchart TB
  Buyer[Customer confirms exact SKU quantities]
  UI[Storefront]
  O[Orders accepts idempotent checkout request]
  Facts[Validate customer address, Catalog SKU, Pricing quote and Configuration]
  Persist[Persist order snapshot, Saga state and outbox]
  Reserve[Reserve stock and hold eligible coupon]
  Authorize[Authorize simulated payment]
  Protect[Protect stock and coupon holds]
  Capture[Capture simulated payment]
  Commit[Commit stock and coupon holds]
  Confirm[Confirm order and write lifecycle fact]
  Ship[Schedule simulated fulfillment]
  Tracking[Read order and tracking]
  Buyer --> UI --> O --> Facts --> Persist
  Persist -->|durable request ID; UI polls status| UI
  Persist --> Reserve --> Authorize --> Protect --> Capture --> Commit --> Confirm --> Ship
  Confirm --> Tracking
  Ship -->|fulfillment scheduled fact| O
  Tracking --> UI
```

[Editable checkout sequence](diagrams/kt-checkout.mmd). The durable worker performs these operations, not the browser. Each service commits only its own state. Idempotency keys, persisted operation results and fencing make retries controlled; this is a Saga with compensation/reconciliation, not one cross-database transaction. A decline releases holds; outages leave retryable work, while ambiguous/unsafe states can require explicit review. Historical quote/currency/address values are snapshots, so later Catalog/price/address edits do not rewrite an old order. See [Saga source](../../services/orders/src/main/java/com/supersports/orders/CheckoutSagaWorker.java) and [checkout design](../milestones/S1-M05).

### C. Tracking, cancellation, returns, reviews and support

Fulfillment owns shipment transitions/delivery facts; Orders exposes customer-owned tracking. Before handoff, a cancellation first claims the shipment boundary, then completes simulated refund, inventory reversal and shipment finalization through retryable idempotent steps. This avoids refunding and shipping the same order in a handoff race.

For a return, Orders verifies ownership, delivery/window and quantities, reserves immutable original-value refund allocations and completes bounded Payment work. Stock does **not** become sellable merely because a refund was issued: operator receipt/inspection in Inventory determines restock, including rejected/damaged outcomes. Published lifecycle facts feed the same projections.

Reviews checks the customer's delivered purchase with Orders, stores a pending review, then operator moderation controls publication/aggregate counts. Sourced demo fixtures remain visibly DEMO, never verified purchases. Support owns tickets/messages and checks linked-order ownership with Orders. See [post-purchase design/evidence](../milestones/S1-M07), [reviews contract](../../contracts/reviews/openapi.yaml) and [support contract](../../contracts/support/openapi.yaml).

### D. CDC, customer history, graph and analytics

```mermaid
flowchart LR
  Tx[Orders transaction] --> State[(Order state)]
  Tx --> Outbox[(Order outbox)]
  Outbox --> WAL[PostgreSQL logical WAL]
  WAL --> Connect[Debezium / Connect outbox routing]
  Connect --> Events[commerce.order.events.v1]
  Events --> History[History inbox / sequence / timeline]
  History --> HistoryDB[(History DB)]
  History --> Store[Customer Orders screen]
  History -. invalid records .-> DLQ[commerce.order.events.dlq.v1]
  DLQ --> Replay[Audited operator replay]
  Replay --> History
  Events --> Graph[Relationship consumer]
  Graph --> Neo[(Neo4j projection)]
  Events --> Batch[Spark batch / dedup / quarantine]
  Batch --> Ice[(Iceberg tables and JDBC metadata)]
  Ice --> Trino[Trino SQL]
  Trino --> Reports[Analytics API to Admin reports]
  Trino --> Superset[Superset dashboards]
```

[Editable data flow](diagrams/kt-data-flow.mmd). Lifecycle schemas are versioned; the topic name retaining `v1` does not mean every payload has eventVersion 1. [V1/V2 contracts](../../contracts/orders) and shared parsers define compatibility. Consumer groups/offsets are independent.

History deduplicates event IDs, applies aggregate sequence rules and exposes freshness. The Storefront can fall back to owned Orders records when the projection is delayed/blocked/unavailable. Poison records use transactional DLQ/audited replay; rebuilding creates a candidate DB/group, reconciles retained source/Kafka/projected facts, then switches the persisted target. This is why an operator should discover the current History DB rather than hardcode it.

Graph handles accepted-order co-purchase relationships only; it is not a current-inventory or net-sales view. Spark is an explicitly invoked batch job, not a claim of continuously up-to-date dashboards. Reports expose currency-specific order value/GMV, counts, units, discounts/refunds, trend/product/refund breakdowns with defined time windows. Mixed-currency sums and all-state order totals are not sales. [Metric definitions](../milestones/S1-M08/dashboard-and-metrics.md) explain inclusion/time/refund limits; Admin derives display metrics from the reports. Superset is a separate optional authoring interface, not the only dashboard path.

### E. Observability

```mermaid
flowchart LR
  Java[11 Java services: agent + safe HTTP logger] -->|OTLP HTTP 4318| Collector[Collector: privacy / batch / bounded export]
  Collector -->|request metrics scrape| Prom[Prometheus]
  Collector -->|traces| Tempo[Tempo]
  Collector -->|safe request logs| Loki[Loki]
  Exporter[Health exporter: configured HTTP/TCP probes] --> Prom
  Prom --> Grafana[Grafana health/request dashboards]
  Tempo --> Grafana
  Loki --> Grafana
```

[Editable telemetry flow](diagrams/kt-telemetry.mmd). The Java agent is packaged in app images but SDK-disabled by default; the explicit telemetry lifecycle enables the running Java services while preserving actual image identities/History target. Prometheus health-only observability and request telemetry are related but separate switches.

Grafana dashboards show readiness and request rate/error/p95/mean response time; Explore joins traces/logs. Exported logs are the dedicated safe HTTP-request stream, not every application exception/stdout line. Privacy excludes credentials, bodies/query values, personal order/address fields and raw SQL values, with runtime sentinel evidence. Bounded queues may drop telemetry during outages; trace/log retention is configured at 24 hours, not a measured 24-hour endurance/disk quota. Python/frontend instrumentation is outside current request tracing. See [telemetry setup](../setup/request-telemetry.md) and [acceptance](../milestones/S1-M12/verification.md).

## 7. DevOps: fresh machine setup, startup and troubleshooting

This section is a reproducible local runbook for a new developer workstation. It distinguishes the default shared commerce set, either UI by itself, and optional infrastructure profiles. It does not claim that macOS, Windows and Linux runtime acceptance was separately executed; the measured release host was Apple Silicon Mac. All three operating systems need an internet connection for the initial clone, pinned dependency/image downloads and source-photo restoration. After those assets/images are present, service runtime is local; no cloud account is used.

### 7.1 Hardware and host prerequisites

- **Memory:** 16 GB RAM is the project baseline; more is suitable. Allocate about **8 GB** to Docker when available. The measured Mac Docker VM allocation was 7.75 GiB and the observed full runtime reached about 6.45 GiB. Do not start analytics, graph, dashboard-studio and heavy test jobs together on a 16 GB host.
- **Processor/architecture:** a supported 64-bit machine. The validated release machine is ARM64 Apple Silicon. Check the actual Docker architecture with `docker info`; image/dependency references are pinned in [`devops/images.lock.json`](../../devops/images.lock.json). An unsupported architecture or a pinned image lacking its platform build must be resolved before startup.
- **Disk/network:** leave room for the repository, Docker images/build cache, PostgreSQL/Kafka/history data and source photographs. First startup downloads pinned images and build dependencies. Docker must be able to reach the public registries and accepted product-photo sources during setup.
- **Docker:** Docker Desktop with Linux containers and Compose v2 on macOS/Windows; Docker Engine plus the Compose plugin on Linux. Docker must be using its local daemon/context. Use the official [macOS install guide](https://docs.docker.com/desktop/setup/install/mac-install/), [Windows install guide](https://docs.docker.com/desktop/setup/install/windows-install/) or [Linux Engine guide](https://docs.docker.com/engine/install/). Windows users should enable WSL 2 and preferably clone/run inside the Linux filesystem of their WSL distribution; see [Docker's WSL guidance](https://docs.docker.com/desktop/features/wsl/).
- **Python:** a supported Python 3 interpreter and a repository `.venv`; Python 3.14.7 was used for recorded checks. Do not install project packages globally. Host Java, Maven, PostgreSQL, Kafka, Redis, Keycloak, Node and Ollama are not needed for Stage 1 runtime; Java builds run in containers. Chrome is only needed for Selenium tests.
- **Ollama:** not part of any Stage 1 startup set. Nova will use the already-installed host Ollama; never start an Ollama container.

Open a terminal at the repository root. For a fresh clone:

```sh
git clone https://github.com/mentorabhi/mentorabhi-ecommerce.git
cd mentorabhi-ecommerce
docker version
docker compose version
docker info
```

On Windows, install/launch Docker Desktop, enable the WSL 2 engine, then open the repository from the WSL distribution for the commands below. Docker's Linux containers are required by this Compose project.

Create the virtual environment:

| OS | Command |
| --- | --- |
| macOS | `python3 -m venv .venv` |
| Linux | `python3 -m venv .venv` |
| Windows PowerShell | `py -3 -m venv .venv` |

Check the available interpreter first (`python3 --version` on macOS/Linux; `py -0p` on Windows). If it is not a supported version, install a current Python 3 release and select it explicitly. Confirm the venv (`.venv/bin/python --version` on macOS/Linux/WSL; `.\.venv\Scripts\python.exe --version` in PowerShell). The executable is the venv's Python, not the system Python.

Configure private infrastructure credentials once and retain them across normal restarts:

```sh
# macOS / Linux / WSL
devops/scripts/supersports doctor
devops/scripts/supersports configure
devops/scripts/supersports validate
```

```powershell
# Windows PowerShell
\.venv\Scripts\python.exe .\devops\scripts\manage.py doctor
\.venv\Scripts\python.exe .\devops\scripts\manage.py configure
\.venv\Scripts\python.exe .\devops\scripts\manage.py validate
```

The `devops/scripts/supersports` shell wrapper works on macOS/Linux/WSL. In **Windows PowerShell**, run the same actions as `\.venv\Scripts\python.exe .\devops\scripts\manage.py doctor`, then replace `doctor` with `configure` or `validate`. `doctor` checks Docker server architecture/memory and confirms the repository venv is active. `configure` creates private, ignored random database/service secrets in `devops/.local/bootstrap.env`; it never prints or rotates existing values. `validate` checks merged Compose configuration without starting containers.

Set the requested operational UI demo password before first startup. This is separate from generated database/service secrets:

```sh
# macOS / Linux / WSL
mkdir -p devops/.local
printf 'ADMIN_PASSWORD=admin\n' > devops/.local/admin-login.env
chmod 600 devops/.local/admin-login.env
```

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Force devops/.local | Out-Null
Set-Content -Encoding ascii -NoNewline -Path devops/.local/admin-login.env -Value 'ADMIN_PASSWORD=admin'
```

Never commit, share, print or rotate `devops/.local` casually; it contains service/database credentials and local operational state. See [credential boundaries](../setup/ui-access.md).

### 7.2 Startup sets and order

Compose waits for dependencies in order. The sequence is **1) PostgreSQL**, including the per-service database/user provisioning; **2) Keycloak**, which imports the operator/customer realms; **3) shared business services** against their owner databases (Catalog, Configuration, Pricing, Inventory, Customer, Orders, Payment simulator, Fulfillment simulator, Reviews and Support); **4) the selected frontend** after its required APIs are healthy. The `common-up`, `admin-up` and `storefront-up` actions preserve pinned images, apply database initialization and provision local identity. They can be called from the shell wrapper on macOS/Linux/WSL or as `\.venv\Scripts\python.exe .\devops\scripts\manage.py <action>` in Windows PowerShell.

**Services shared by both applications (default common set):** PostgreSQL, Keycloak, Catalog, Configuration, Pricing, Inventory, Customer, Orders, Payment simulator, Fulfillment simulator, Reviews and Support. Customer is in the shared set because the Orders checkout worker validates the customer's saved address. The shared set intentionally excludes both frontends, Kafka/CDC/Order History, OpenTelemetry stores, Trino/Spark, Neo4j and Superset.

| Use case | macOS / Linux / WSL | Windows PowerShell | UI |
| --- | --- | --- | --- |
| Shared APIs/infra only | `devops/scripts/supersports common-up` | `\.venv\Scripts\python.exe .\devops\scripts\manage.py common-up` | No frontend |
| **Admin only** (shared set starts first) | `devops/scripts/supersports admin-up` | `\.venv\Scripts\python.exe .\devops\scripts\manage.py admin-up` | http://localhost:3002/admin · `admin` / `admin` |
| **Storefront only** (shared set starts first) | `devops/scripts/supersports storefront-up` | `\.venv\Scripts\python.exe .\devops\scripts\manage.py storefront-up` | http://localhost:3000 · customer self-registration/login |
| Both applications, full default Stage 1 commerce | `devops/scripts/supersports up` | `\.venv\Scripts\python.exe .\devops\scripts\manage.py up` | Both URLs above |

If one app is already running and an isolated one-app experience is needed, stop the other app first using `admin-down` or `storefront-down`; `admin-up`/`storefront-up` do not stop an already-running sibling. `supersports up` is the existing full core command: it builds/starts all non-profile core services and both frontends. First startup builds images and may take several minutes.

**Fresh checkout data and photographs:** a clean database starts without the accepted retail catalog. If the local teaching environment should also contain the requested synthetic reporting/history workload, create it **before** importing the sourced catalog. This opt-in workload creates 1,000 synthetic Indian profiles and prior-year orders; its verified M10 run generated 17,730 orders/51,725 items and took about 141 seconds for the import phase. It uses reserved `.invalid` email addresses and creates no payment, email or real shipment. macOS/Linux/WSL:

```sh
# Run after common-up; omit only if synthetic profile/order history is not needed.
devops/scripts/seed-demo --users 1000
```

Windows PowerShell:

```powershell
\.venv\Scripts\python.exe .\devops\scripts\demo_operations.py --users 1000
```

Generated passwords and seed receipts stay in ignored `devops/.local/`. Do not rerun the old generated-art catalog seeder after importing the sourced catalog. The source importer retires obsolete active fixtures while retaining their historical order snapshots. See [M10 data evidence](../milestones/S1-M10/verification.md).

Source-photo binaries are intentionally not tracked. Before building either frontend image, restore the accepted source photos, then import the catalog through owning APIs:

| OS | Install the pinned data tools and restore photos |
| --- | --- |
| macOS/Linux/WSL | `.venv/bin/python -m pip install -r data/pipelines/real-catalog/requirements.txt` then `.venv/bin/python data/pipelines/real-catalog/assets.py data/pipelines/real-catalog/manifest.json` |
| Windows PowerShell | `\.venv\Scripts\python.exe -m pip install -r .\data\pipelines\real-catalog\requirements.txt` then `\.venv\Scripts\python.exe .\data\pipelines\real-catalog\assets.py .\data\pipelines\real-catalog\manifest.json` |

Start **only the common services** first (`common-up`), and then run the owner importer:

| OS | Import command |
| --- | --- |
| macOS/Linux/WSL | `.venv/bin/python data/pipelines/real-catalog/import_catalog.py data/pipelines/real-catalog/manifest.json` |
| Windows PowerShell | `\.venv\Scripts\python.exe .\data\pipelines\real-catalog\import_catalog.py .\data\pipelines\real-catalog\manifest.json` |

Now run `admin-up`, `storefront-up` or `up`. The importer is designed for first population and safe replay against the accepted manifest; keep its ignored local progress receipts. Image restoration needs the accepted public sources to remain available; failure is explicit, and generated replacement art is not an acceptable substitute. Details: [catalog provenance/setup](../../data/pipelines/real-catalog/README.md).

**Optional capabilities, started after the common set:**

| Capability | Start / stop command | Notes |
| --- | --- | --- |
| Kafka, Debezium Connect, Kafka UI and Order History | `streaming-up` / `streaming-down` | Provides CDC, customer timeline projection and http://localhost:8091 (`admin/admin`). Run `stream-status` after startup. Storefront checkout works without this profile; the order page has an owned Orders fallback. |
| Health dashboards | `observability-up` / `observability-down` | Starts exporter, Prometheus and Grafana; Grafana http://localhost:3001 (`admin/admin`). If request telemetry is enabled, first use `telemetry-down`. |
| Request metrics/traces/safe logs | `telemetry-up` / `telemetry-down` | Starts Collector, Prometheus, Tempo, Loki and Grafana and enables instrumented Java apps. See [telemetry guide](../setup/request-telemetry.md). Do not enable concurrently with heavy profiles on the baseline host. |
| Reports/query engine | `analytics-up` / `analytics-down` | Starts Trino, report API and Prometheus-auth proxy. Fresh data needs the explicit `analytics-run` batch job. |
| Relationship graph | `graph-up` / `graph-down` | Starts Kafka if needed, Neo4j and graph consumer; optional API, not Storefront search. |
| Dashboard authoring | `dashboard-studio-up` / `dashboard-studio-down` | Starts Trino and Superset; Trino is therefore common to this option and analytics. |

Command names above are `devops/scripts/supersports <action>` on macOS/Linux/WSL; in Windows PowerShell use `\.venv\Scripts\python.exe .\devops\scripts\manage.py <action>`. Optional profile teardown stops that profile while retaining named volumes.

### 7.3 Shutdown and inspect

| Goal | macOS/Linux/WSL shell wrapper command |
| --- | --- |
| Stop only Admin; leave Storefront and shared services running | `supersports admin-down` |
| Stop only Storefront; leave Admin and shared services running | `supersports storefront-down` |
| Stop the full Compose system; preserve database/Kafka/telemetry volumes | `supersports down` |
| See configured/running services | `supersports status` |
| Check Docker/Python allocation | `supersports doctor` |
| Validate Compose configuration | `supersports validate` |
| Inspect streaming/CDC | `supersports stream-status` |
| Verify/reconcile History | `supersports stream-reconcile` (expect JSON `ok=true`, `errorCount=0`) |
| Verify configured Admin/customer and database behavior | `supersports test` (test execution, not normal startup) |

The Docker CLI commands below are **Across all OS**. The `supersports` shell wrapper runs on macOS/Linux/WSL; in Windows PowerShell use `\.venv\Scripts\python.exe .\devops\scripts\manage.py <action>` for the table actions above.

The commands above use the shell wrapper; PowerShell equivalents are `\.venv\Scripts\python.exe .\devops\scripts\manage.py <action>`. `down` is the normal full shutdown and preserves named volumes. **Do not use `reset`, `docker compose down -v`, or Docker prune commands for routine stop/start**: they erase persisted application data/build cache. Stop optional profiles with their specific `*-down` actions before starting resource-intensive work.

To follow logs, use Docker's cross-platform CLI (service names are the Compose names):

**Across all OS:** the Docker CLI log and container commands below work in macOS/Linux terminals, WSL shells and Windows PowerShell.

```sh
docker ps --filter label=com.docker.compose.project=supersports
docker logs --tail 200 -f supersports-catalog-1
docker logs --tail 200 -f supersports-orders-1
docker logs --tail 200 -f supersports-identity-1
docker logs --tail 200 -f supersports-postgres-1
```

Press Ctrl+C to stop following a log (the service continues running). Replace the container name with `supersports-admin-1`, `supersports-storefront-1`, `supersports-kafka-1`, `supersports-kafka-connect-1`, `supersports-grafana-1`, etc. `docker logs --since 10m <container>` is useful for a bounded capture. Do not use `docker inspect` formats that print `.Config.Env`, `docker compose config` without secret redaction, or attach raw secret-bearing output to an issue.

### 7.4 Basic troubleshooting

1. Confirm the local daemon and resources: `docker info` and `supersports doctor`. Docker must report the intended architecture and sufficient memory; free disk space if image/build/database writes fail.
2. Check the intended profile: `supersports status`, `docker ps --filter label=com.docker.compose.project=supersports`; optional profile URLs are unavailable until that profile starts.
3. Follow the failed service logs using the cross-platform `docker logs` command above. Inspect PostgreSQL and Keycloak before application APIs; the Compose dependency graph requires their health first.
4. Check a direct readiness endpoint from the host, e.g. `http://localhost:8081/actuator/health/readiness` (Catalog), `http://localhost:8086/actuator/health/readiness` (Orders), `http://localhost:8180/health/ready` (Keycloak), or `http://localhost:3000/healthz` / `http://localhost:3002/healthz` (frontends). A healthy process does not prove optional reports/CDC are ready.
5. For authentication, use `localhost` rather than an IP because OIDC redirect/issuer URLs are configured for `localhost`; distinguish the customer realm from the operator realm. Operational UIs use `admin/admin`; customer accounts self-register.
6. For checkout, inspect Orders' durable Saga state and logs plus the readiness of Customer, Catalog, Pricing, Configuration, Inventory, Payment and Fulfillment. Do not submit repeated requests with new idempotency keys to work around a pending order.
7. For history delay, compare Orders authority to History freshness, then run `stream-status` and inspect Kafka UI topic/consumer/Connect task state. Checkout has an Orders fallback while the projection catches up.
8. For report/API 503 or stale data, start the analytics profile and verify Trino/Iceberg plus the last explicit Spark batch. For graph issues, inspect graph/Neo4j profiles; graph does not power product search.
9. For Grafana, use the manual UI checks in [M13 verification](../milestones/S1-M13/manual-acceptance.md) and retain the browser/API response separately; Grafana health alone does not prove dashboard panels render.

Never delete live volumes, rerun obsolete generated-art catalog seeders, or restore over active commerce to resolve an ordinary startup issue. The [DevOps README](../../devops/README.md), [database guide](../setup/database-access.md), [UI access](../setup/ui-access.md), [Kafka guide](../setup/kafka-ui.md) and milestone runbooks describe deeper checks.

| Symptom | First boundary to inspect |
| --- | --- |
| Cannot sign in | Correct localhost origin/realm; Keycloak readiness; callback/client configuration; customer vs operator account |
| Wrong search results | Catalog equipment metadata/title and whole-word query; actual `/public/products?q=...`; deployed Catalog image |
| Price/stock missing | Pricing/Inventory readiness and batch snapshots, active SKU/currency; Catalog alone does not prove checkout availability |
| Checkout stays pending | Owned request/order and persisted Saga step; dependency/worker token readiness; preserve idempotency key |
| Order History lags | Orders authority vs History freshness/sequence gap; Connect task/slot, Kafka partitions/groups, DLQ; use fallback/reconciliation |
| Reports return 503 or look stale | Optional analytics profile, Trino/Iceberg tables and last explicit Spark batch, currency/time-window definitions |
| Graph unavailable | Graph/Neo4j profiles, Neo4j service identity and consumer progress; Storefront search does not depend on graph |
| No trace/log | Java SDK enablement, Collector/store readiness, Grafana datasource/time range; exported logs intentionally have limited fields |

## 8. Data, evidence and where to work next

The original release baseline had **103 Cricket /113 Football products**, **1,030/1,130 SKUs**, INR/USD books and **751 published DEMO reviews**. The subsequent [M13 equipment follow-up](../milestones/S1-M13/verification.md) adds 96 source models: current catalog **199 Cricket /113 Football products**, **1,126/1,130 SKUs** (312 models/2,256 total SKUs) and **1,088 published DEMO reviews**, with [54-family coverage](../milestones/S1-M13/coverage.md). Service/API/infrastructure ownership stays the same; compound accessory search and both frontend photo bundles are updated. Product is the model; SKU is a sellable size/colour option. The historical synthetic workload includes 1,000 profiles and prior-year orders; verification creates additional fixtures, so do not assume the original seeded order count is today's total. The final retained reconciliation recorded 36,537 events/18,077 orders with zero errors; that is a checkpoint, not an immutable business metric. Subsequent user-requested catalog expansion will change counts; consult [current status](../context/status.md).

| Work area | Canonical location |
| --- | --- |
| Service implementation/unit tests/migrations | `services/<service>/`; Java public contracts under `contracts/` |
| Browser apps and Selenium | `apps/storefront`, `apps/admin` and their tests |
| Data manifests/import/batch transformations | `data/pipelines/`; photos/provenance instructions in real-catalog README |
| Docker/Compose/CI/ops/Kubernetes/Helm/Terraform | `devops/`; do not scatter infrastructure into service directories |
| Reviewed designs/ADRs | [Design index](../../design/README.md), [milestones](../milestones/README.md), [decisions](../decisions) |
| Current context/decisions and release limits | [Project context](../context/project-context.md), [accepted requirements](../../requirements/accepted-requirements.md), [Stage 1 acceptance](../context/stage1-completion.md) |
| Manual handover checks | [Stage 1 owner checks](../testing/stage1-release-checks.md), linking each milestone's service/UI/feature/database checklist |

The KT task inspected code/configuration and sanitized runtime inventory; it did not rerun the full commerce test suite, restart services, or perform the owner's manual sign-off. Existing release evidence records unit/real-DB/contract/integration/Selenium/recovery/resource results, explicit skips and cold-start limits. Independent review tooling was unavailable for the recorded release; passing runtime checks are not presented as a clean independent review. This handover adds no cloud service, changes no credentials/data, and does not implement Nova. Next-stage implementation requires its own reviewed design and a published stage branch.
