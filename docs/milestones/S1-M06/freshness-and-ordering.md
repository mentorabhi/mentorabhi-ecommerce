# M06 freshness and ordering acceptance design

2026-10-24 · Implementation-owner review completed before coding; supplements the approved M06 design.

## Customer behavior

The History list response adds `freshness` with `state`, `checkedAt`, and owner-scoped pending-event information. States are `CURRENT`, `DELAYED`, `BLOCKED`, and `UNAVAILABLE`. Current means the consumer is active and caught up to its latest successful broker observation; it does not assert zero CDC latency from Orders. Idle event timestamps do not imply staleness.

An independent scheduled broker probe reads topic high-water marks and committed group offsets. The consumer records recent poll progress. Failed/expired broker observation or expired consumer progress is unavailable; positive lag or a new owner gap is delayed; an owner gap older than the configured timeout is blocked. Broker/consumer unavailability takes precedence. Defaults: probe every three seconds, observation/consumer timeout ten seconds, gap timeout thirty seconds. Probe-only tests may shorten the gap timeout.

The storefront shows plain-English status and last checked time. During delay, blocked state or unavailable streaming, it reads the signed-in customer's Orders API for current store records. History status is still displayed when its API is available; an unavailable API gets an explicit notice. Customer ownership remains token-derived in both services. No group IDs, other customers' gaps or private tables are exposed.

## Isolated ordering and browser probe

Use retained synthetic events from two existing customer-owned orders. Create a disposable History-owned database, one-partition probe topic/DLQ and separate consumer group. Stop the ordinary History container, run the probe under its local port/network alias, and reload the storefront proxy; the core store remains available. This deliberately exercises the real consumer, database, authenticated API and existing browser origin without adding another full stack.

Send order A sequence 3 before 1/2 and all of order B. Verify A parks, B completes on the same partition, owner A sees the timed gap, another owner does not, and the UI shows the blocked notice while authoritative owned records remain accessible. Send A sequences 1/2, observe drain to 3, then redeliver duplicates and conflicting identities to verify no inflation/regression. Broker outage/recovery verifies unavailable/current status through Selenium. Cleanup always restores Kafka, ordinary History and proxy routing, then removes only validated probe resources. Main outbox/topic/projection facts are never edited by the ordering probe.

## Review findings resolved

- Source event age is not a valid idle-health signal; use fresh broker observation plus consumer progress.
- Consumer `poll` alone does not prove broker availability; probe broker offsets independently with bounded timeouts.
- A store-wide gap count would reveal another owner's state; query only the verified owner's pending payloads.
- A generic asynchronous banner hides failure; use explicit states and current Orders fallback.
- Injecting fake events in the authoritative topic would pollute reconciliation; isolate topic/database/group and restore routing in `finally` cleanup.
- Parallel operator mutations could disrupt the demonstration; use the existing local operator lock and reject overlapping probes.

Unit checks cover status precedence/timeouts. Live tests cover gap parking/drain, same-partition progress, duplicates/conflicts and ownership; Selenium covers desktop/mobile status, outage/recovery and current-order fallback. Record actual results separately; no gate is passed by this design document.
