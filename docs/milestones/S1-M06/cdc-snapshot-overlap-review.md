# Snapshot/WAL overlap design review

Revision 1 · 2026-10-25 · Reviewed before implementation

## Review findings

- **Isolation:** The existing Commerce connector and topic are sensitive durable state. The test uses a separate database, publication, replication slot, connector name, topic prefix and consumer group, all UUID-scoped. It must never alter the normal connector's config or source resources.
- **Overlap proof:** Connector RUNNING is insufficient evidence that snapshot scanning began. The test waits for a nonzero but incomplete snapshot topic high-water mark before writing. It also asserts `r` and subsequent `u`/`c` records for the changed keys and folds the entire partition against a source-table snapshot.
- **Deterministic oracle:** The primary key and final row values are deterministic. Kafka offset order is used for folding; source rows and final key/version hashes are compared after the connector is quiescent.
- **Bounds:** A 100,000-row compact fixture, strict deadlines, bounded console-consumer count and one disposable connector keep resource use limited. Failure to catch the overlap window is a failed/non-exercising test, never a pass.
- **Cleanup:** `finally` deletes only the UUID connector, slot, publication and database, then verifies normal connector and topic high-water values. No Docker volumes or production topics are deleted.
- **Compatibility:** The probe uses the repository's pinned Debezium PostgreSQL connector, Kafka broker and PostgreSQL runtime and adds no dependencies or cloud components.

## Review disposition

No design blocker identified. Implementation must be tested first against a tiny disposable fixture and then the bounded live run. If the connector's emitted key/value format differs from the assumed JSON representation, inspect only this disposable topic and adjust the parser before a full run. Do not weaken the overlap or source-state assertions to force a pass.
