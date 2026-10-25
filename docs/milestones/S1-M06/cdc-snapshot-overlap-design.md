# Debezium consistent snapshot and WAL overlap probe

Revision 1 · 2026-10-25 · Design before implementation

## Goal

Exercise Debezium PostgreSQL `snapshot.mode=initial` with concurrent inserts and updates while the consistent snapshot is being emitted. Verify the final Kafka change stream represents every source primary key exactly once after folding `READ` and subsequent `CREATE`/`UPDATE` records, including changes that overlap the connector's snapshot/WAL handoff.

## Isolation and safety

- Use a UUID-scoped disposable PostgreSQL database, publication, replication slot, connector, Kafka topic prefix, consumer group and table. Never stop, alter, or reset the production-like Orders connector, its `orders` database, slot, publication, or `commerce.order.events.v1` topic.
- Create and remove all probe resources in `try/finally`; cleanup must not run broad volume, topic, or database deletion commands. If cleanup fails, print only the UUID resource names.
- Create a bounded synthetic relation with stable integer primary keys and a deterministic expected final state. Use a compact fixed-width payload and an explicit maximum row count so the 16 GB host and 7.75 GiB Docker allocation remain viable.
- Register a second Debezium Postgres connector with a new slot and publication, `snapshot.mode=initial`, and a unique topic prefix. Do not apply the Commerce outbox SMT to this plain table probe.
- Wait for the probe topic to begin receiving snapshot records before issuing concurrent updates and inserts. If the initial snapshot completes before the concurrent mutation starts, fail the probe as non-exercising rather than calling it a pass.
- Collect records from the probe topic from offset zero. Fold each keyed record in offset order: snapshot `r` establishes the row, later `u` replaces it, and `c` adds it. Require the folded state to match the authoritative table exactly, with no missing keys, unexpected keys, duplicate primary-key state, or stale final row versions.

## Bounded procedure

1. Confirm the regular Orders connector is RUNNING and the three production event partitions are caught up. Capture its connector configuration, slot and publication identity for post-test comparison.
2. Create the isolated database/table and seed a bounded initial set (target 100,000 compact rows). Grant only the CDC role's required database/table reads; create a publication for only the probe table.
3. Start the isolated connector and poll its task plus probe-topic high-water mark. Once at least one but fewer than all initial snapshot rows have been emitted, update a deterministic subset of existing keys and insert another deterministic subset. Record the snapshot high-water point and mutation counts.
4. Wait for the connector to return RUNNING and for the topic to remain quiescent across repeated high-water reads. Consume the complete topic and fold by primary key.
5. Compare the fold with an ordered query of the disposable source table. Assert source key count, final version distribution and payload hashes match. Require both snapshot-read and WAL-change operations for overlapped keys in the stream.
6. In `finally`, stop/delete only the probe connector; wait for its task removal; drop its replication slot, publication and disposable database; confirm the production connector config/status and production topic high-water marks are unchanged.

## Pass criteria

- The runtime confirms that mutations were submitted after snapshot emission began and before the initial snapshot finished.
- Snapshot records and WAL records are both observed for at least one key changed during the overlap interval.
- Folding the complete ordered topic yields exactly the final disposable source table state, including concurrently inserted keys and final versions for updated keys.
- The probe connector, slot, publication, database and topic data are removed or their exact remaining UUID-scoped names are reported for cleanup; the normal Commerce connector and topic remain unchanged and healthy.

## Failure and limits

Any connector failure, missing overlap window, consumer truncation, unexpected record operation, source mismatch, timeout, or production connector/topic change fails the test. Cleanup runs regardless, and accepted production commerce data is not modified. A single local run proves only this Debezium/PostgreSQL/Kafka version and dataset. It does not establish prolonged WAL retention, sustained throughput, broker HA, or production capacity.

## Review checklist

- Confirm no reset or delete path can target production Commerce resources.
- Bound row count, payload size, timeouts, and memory/CPU; reject unsafe project/resource names.
- Ensure record folding follows Kafka partition offset order and validates key/value identity.
- Verify cleanup is narrow and idempotent, including a connector task that fails during snapshot.
- Keep this probe opt-in under the explicit local integration test gate.
