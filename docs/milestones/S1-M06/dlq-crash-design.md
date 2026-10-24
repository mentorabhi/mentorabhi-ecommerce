# M06 transactional DLQ crash probes

2026-10-24 · Reviewed before implementation · Completes the previously open transactional DLQ crash boundary gate.

The poison consumer begins a Kafka transaction, writes a DLQ record, stages the original partition offset in that transaction, then commits. Add two one-shot local-only fault points: after the staged write/offset but before commit, and immediately after commit. The probe must use an actual invalid v1 event, retained source/DLQ Kafka topics, the real Order History container and transactional consumer group.

Before commit, a killed process must leave the source offset uncommitted and the transactional DLQ write invisible; after restart, the poison source is retried and exactly one committed DLQ record is visible. After commit, the process may die before observing success, but the transaction must contain both a single DLQ record and the advanced source offset; restart must not redeliver it. Preserve source coordinate/key/error headers and verify the event is not projected as a valid order.

Fault controls are one-shot marker files under the existing local fault directory. Require `--once`; allow only named transaction boundaries; atomically move armed markers to fired markers. Never accept shell fragments, source coordinates or payloads through this control. Injection is disabled unless a marker is explicitly created by the local management command.

Review resolved transaction ordering, restart timing and aborted transactional visibility, marker replay protection, actual end-to-end poison generation, source-offset comparison and DLQ key uniqueness. Use a stable transactional ID per consumer group to fence the crashed producer immediately, with a bounded five-second transaction timeout. Exactly one Order History consumer instance may run per group; candidate rebuilds use distinct groups. Set the local group session timeout to 15 seconds to make process recovery observable without waiting for the Kafka default 45-second member expiry. The DLQ inspector/test reads with `read_committed` so an aborted pre-commit write is invisible. Integration tests run serially under the existing operator lock and wait for zero lag. The docs record that this tests Kafka's transactional commit boundary in the local single-broker profile; it does not establish multi-broker durability.

Diagram: `dlq-crash-flow.mmd`. Verification uses real broker source/DLQ offsets, actual container restart count, and exact DLQ coordinate count before/after restart.
