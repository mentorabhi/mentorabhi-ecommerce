# Kafka UI on the host

Open **http://localhost:8091** after starting the streaming profile:

```sh
./devops/scripts/supersports streaming-up
./devops/scripts/supersports stream-status
```

Choose the `supersports` cluster. No login is required for this localhost-only development inspector. The cluster is configured read-only.

| Page | What to inspect |
|---|---|
| Brokers | Local broker ID 1, availability and configuration |
| Topics | `commerce.order.events.v1`, three partitions, offsets and retained size |
| Topic → Messages | Order event keys, payloads and partition/offset; choose earliest offsets to inspect retained events |
| Topic → Partitions | Leaders, replicas, in-sync replicas and offsets |
| Consumers | Current Order History consumer group and lag; rebuilds create a different active group |
| Kafka Connect → debezium | `supersports-orders-outbox` connector and RUNNING task |

`commerce.order.events.dlq.v1` contains diagnostic/poison test records, separate from the event topic. Read-only inspection does not publish corrections; use the documented audited replay workflow for that.

The UI container is `kafka-ui` on the existing Compose network, with a 512 MiB memory cap. `streaming-down` stops it along with streaming dependencies. Restart it with `./devops/scripts/supersports restart kafka-ui`. Existing storefront and database URLs are unchanged. Do not use `localhost:9092` as the UI container's bootstrap server; it correctly uses Docker DNS `kafka:9092`.

## Manual end-user acceptance

- [ ] Run status and confirm Kafka, Connect, Order History and Kafka UI are healthy.
- [ ] Open http://localhost:8091 from your Mac and select `supersports`.
- [ ] Inspect the broker, three event partitions, messages, active consumer lag and Debezium task.
- [ ] Open http://localhost:3000, place a synthetic order and confirm its event appears; its customer order history should load.
- [ ] In DBeaver inspect the Orders outbox and the active History projection using read-only queries; compare the synthetic order ID with the Kafka key. Find the active History database in ignored target configuration because rebuilds change its name.
- [ ] Restart only Kafka UI; confirm topics/messages remain and the storefront still works.
- [ ] Record date/result and any issue without copying secrets or raw connector configuration.

Human checks remain unchecked until performed. Runtime/API/browser results are recorded in the M06 Kafka UI verification document.
