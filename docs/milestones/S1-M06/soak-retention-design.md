# Stage 1 sustained checkout and retention acceptance

Revision 1 · 2026-10-25 · Design before implementation

## Acceptance windows

Stage 1 uses a 900-second continuous checkout workload and a concurrent, isolated 900-second stopped-connector/idle-consumer interval. Previous evidence covered a 20-order burst and roughly two-minute recovery. No numeric sustained-load or retention target was previously accepted; these explicit local windows close that ambiguity and retain their measured duration in the result.

## Checkout workload

- Keep Commerce, Kafka, Connect and Order History running. Stop optional Analytics, graph, Kafka UI and observability profiles while measuring; restore their previous running state afterwards.
- Submit one synthetic one-unit football checkout every 15 seconds for 15 minutes (60 orders). Retry each idempotency key once with identical content and require the same order ID. This rate is below the previously observed single Saga worker's burst-drain rate.
- Refresh local customer credentials during the run, poll owner-visible order state and freshness, sample memory/stock/consumer lag, and record per-request and per-order latency with monotonic clocks.
- Require 60 unique accepted orders, all reaching FULFILLMENT_SCHEDULED within the window plus a 180-second drain; exact net stock decrease of 60, no negative samples, three lifecycle sequences per projected order, identical money/lines, cross-owner 404, and final zero lag. Report all intermediate lag/freshness states rather than assuming uninterrupted freshness.
- Preserve a private ignored report on success or failure, including accepted IDs and pending work. No credentials, customer profiles or connector secrets enter the report.

## Retention workload

- Create UUID-named database/table/publication/slot, Debezium connector, single-partition Kafka topic and consumer group. Reuse existing local images and CDC role; change no production connector, group or topic policy.
- Snapshot 20 fixture rows, checkpoint the isolated consumer group at offset 20, gracefully stop the isolated connector and wait until its slot is inactive. Record restart/confirmed LSNs, retained WAL bytes, topic bounds and group offset.
- For 900 seconds, commit one update and one insert every 15 seconds (60 transactions). Require the stopped connector to remain stopped, the confirmed LSN and group checkpoint to remain unchanged, initial Kafka records to remain readable, and retained WAL to grow without exceeding a 256 MiB guard. Record PostgreSQL WAL and broker/topic retention configuration.
- Resume the connector and require the 120 deferred changes within 180 seconds. Read the group from its saved offset and verify the deferred records; replay the complete 140-record topic and compare the exact folded rows to the fixture database. Verify no record truncation and clean up every owned connector/slot/database/topic/group in a finally block.
- Main Commerce remains active during retention; the soak intentionally advances its topics. Compare the main connector configuration and health, not unchanged production high-water marks.

## Interpretation and limits

Passes establish a 15-minute local steady workload and retained-WAL/consumer-checkpoint recovery interval on the pinned one-broker ARM64 profile. They do not establish day-scale disk capacity or multi-broker HA. The one-broker learning topology is an explicit Stage 1 design constraint, not an unimplemented HA acceptance test. Record elapsed durations, source/event counts, latency, memory, lag, WAL bytes, cleanup and runtime versions separately from these planned criteria.

## Verification

Add focused tests for schedule bounds, terminal accounting, source-fold validation and retention-coordinate checks. Run both live probes, retained-history reconciliation, and the existing affected operational tests. Maintain the manual end-user guide, verification, matrix, context and revision history; commit and push the checkpoint on stage1.
