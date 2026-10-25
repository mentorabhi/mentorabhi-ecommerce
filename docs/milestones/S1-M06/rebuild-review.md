# M06 rebuild implementation review

2026-10-24 · Scope: isolated projection rebuild, retained-history reconciliation, saved database/group target and operational test coverage.

Code review: skipped (ce-code-review unavailable). The dedicated multi-agent review cannot dispatch reviewers in this turn, and the project prohibits external model CLI reviews without user direction. An implementation-owner manual diff scan covered the paths below; no independent receipt is claimed.

## Findings resolved in this implementation

- Equal row counts were insufficient evidence. Reconciliation now compares exact event sets, canonical hashes (or proven legacy raw bytes), timeline fields/time, per-order state/owner/currency/amount/lines, pending gaps, replay provenance and copied audit/delivery records. Unit tests keep counts constant while corrupting these facts.
- Candidate-looking database names could also name the current active target after an earlier cutover. The CLI refuses rebuild against that target and the runner requires an explicit candidate flag before applying the mismatch probe.
- A replay could race audit copy. Mutating operator CLI commands share an exclusive local file lock; source audit and delivery rows are copied through owner-scoped operational `pg_dump`/`psql`, not an application cross-database read.
- Publishing a saved target before readiness could persist a failed deployment. Cutover now launches the pair through an explicit Compose override, waits for readiness, then atomically saves it. Startup failure recreates the previous pair; the unit test verifies both overrides and retained target state.
- A newly created database initially grants PUBLIC connection privilege. Candidate creation disables connections, revokes PUBLIC privileges, then enables owner access before migrations/replay.
- Polling can return records beyond a captured mark. The first-pass consumer seeks back to its captured marks before taking/reading the second marks, then commits exactly the second marks for the new group. Later events remain available to the normal consumer.
- Unresolved poison or identity conflicts must not disappear from reconciliation. The scan retains quarantine coordinates/hashes, verifies DLQ/source agreement, excludes quarantined variants from applied event evidence, and requires an audited published correction matching retained authoritative content.
- A stable distributed snapshot cannot be assumed during arbitrary writes. Before/after owner snapshots must agree; bounded retries fail safely if a stable comparison window cannot be obtained. This is an explicitly local operation and does not claim a distributed transaction.

## Observed verification and scope limits

The targeted streaming run passed three journeys in 256.815 seconds: consumer crash recovery, audited replay recovery/idempotency, and rebuild dry-run → injected candidate mismatch → successful cutover → new checkout delivery. The mismatch left the saved target unchanged and Order History healthy. Rebuild carried forward audit/delivery records and reconciled retained state before activation.

Thirteen Order History Java tests and the Python target/lock/reconciliation/control-path tests pass. Full CI subsequently exited 0, including both rebuild journeys and seven Selenium tests; measured results and sampled memory are recorded in `verification.md`. The complete M06 acceptance matrix remains authoritative for unclosed failure, freshness, load and human-check evidence.

## Tombstone follow-up

A later manual edge-case scan found that diagnostic hashing assumed a non-null Kafka value. A new regression failed with `NullPointerException` before the fix. Tombstones now receive a deterministic fingerprint distinct from every UTF-8 string value and are classified as quarantined records by the index. Existing non-null fingerprints are unchanged. This avoids a generic diagnostic abort; an unresolved tombstone still fails reconciliation explicitly and is not silently accepted or assigned an invented commerce event identity.

The same scan found that textual identity comparison rejected integer-equivalent sequence representations even though the schema and canonical hashing accept them. Identity fields now compare their canonical values; different IDs/owners/sequences still conflict. Its new test failed before the change, then all 15 module tests passed. A live numeric correction/retry and subsequent reconciliation/UI check also passed; the full repository CI was not rerun for these leaf changes.

## Full demo dataset resource review — 2026-10-25

The generated 1,000-customer dataset raised retained source history to 35,830 events and 17,855 orders. The first live `stream-reconcile` attempt terminated its short-lived Order History operator with exit 137 at the existing 512 MiB container / 384 MiB heap. This is a measured failure, not a passed rebuild. The owner snapshot also used one PostgreSQL `json_agg` over all events; PostgreSQL restarted when that query exceeded the 384 MiB database container budget.

The owner snapshot now emits one JSON record per event and order, avoiding whole-history aggregation inside PostgreSQL. The Order History Compose limit and heap are raised to 768 MiB and 512 MiB respectively so the existing complete in-memory Kafka comparison and JSON receipt can handle the reviewed demo scale with native-memory headroom. This adds 256 MiB to the selective streaming profile; verify actual Docker allocation before enabling it on the 16 GiB baseline. A post-change runtime peak and full rebuild/cutover still require a green live run before claiming acceptance.
