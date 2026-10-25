# S1-M06 completion audit

2026-10-24 · This matrix preserves the full approved design scope. Implemented features do not by themselves prove every failure/load acceptance gate.

| Design gate | Authoritative evidence | Current disposition |
|---|---|---|
| Transactional state/outbox writes and legacy sequence backfill | Orders transaction paths, migrations/backfill, event writer/contract checks, live outbox validation | Implemented; explicit rollback-boundary and snapshot-overlap runtime probes still required |
| CDC snapshot/WAL handoff and connector/broker restart | RUNNING connector, durable volumes, owner-scoped live CDC journey; `test_cdc_resumes_outbox_after_connect_and_broker_restart`; `test_initial_snapshot_overlaps_concurrent_wal_changes` | Broker+Connect resume passed. Isolated 100,000-row initial snapshot overlapped 500 updates and 500 inserts; 101,000 Kafka records folded exactly to source state and production connector/topic positions remained unchanged. Extended WAL-retention windows remain open |
| Inbox deduplication and per-order sequencing | Projector uniqueness/hash/sequence code; commit-before-offset crash journey; `test_isolated_gap_parking_owner_freshness_and_browser_fallback` | Live isolated one-partition probe passed: A sequence 3 parked, B progressed, owner A moved DELAYED→BLOCKED while B stayed CURRENT, A sequences 1/2 drained the gap, duplicate delivery did not inflate inbox, and changed content under the same event ID did not change projected state |
| Transactional DLQ and immutable audited replay | Kafka transactional DLQ code; operator replay integration with pre/post-publication failures and audit immutability; `test_dlq_and_source_offset_commit_atomically_across_both_crash_boundaries` | Replay passes. Both DLQ pre/post-transaction-commit forced-crash boundaries pass on the live broker: each leaves one read-committed DLQ record and advances its source offset. Broader CDC/broker restart and snapshot/WAL overlap remain open |
| Customer ownership and projection UI | Customer/operator audience checks, owner derivation, direct API isolation, customer history Selenium; isolated gap journey above | Blocked and unavailable states passed in real storefront Selenium with owned Orders fallback; cross-owner gap counts remained zero. Human manual acceptance remains open |
| Isolated rebuild, two marks, reconciliation, failure retention and cutover | Candidate/group code, content-corruption unit checks, live dry-run/mismatch/success/new-checkout journey | Targeted run and both full-CI integration passes passed |
| Full historical reconciliation within retained dataset | `stream-reconcile`: outbox ↔ Kafka ↔ inbox IDs/hashes, timeline, order state/owner/lines/money, audit copy | Targeted runtime passes for retained synthetic dataset; command prints retention limitation |
| Stable compatible ARM64 local profile | Pinned tested images, version/license record, live Docker profile, Compose/Helm/Terraform validation | Full CI passed on the 16 GiB ARM64 host with 7.75 GiB Docker allocation |
| Peak/resource/throughput/concurrent-checkout feasibility | Actual sampled workload and reported memory/lag/throughput, with dataset and limits | Bounded 20-checkout/8-worker run passed: acceptance p95 857.20 ms, end-to-end p95 167.86 s, 20/20 scheduled, zero lag, stock 113→93, sampled container peak 5,694.8 MiB. 210 CI samples previously peaked at 5,237.09 MiB application / 5,331.09 MiB all containers. Sustained/soak throughput, full host memory peak and long retention remain unmeasured |
| Separate manual acceptance and milestone checkpoint | `manual-acceptance.md`, verification/revisions/context, Git push | Guide and checkpoints maintained; human results remain pending |

Next implementation work must close these remaining gates without relabeling them as passed. Later Stage 1 milestones and final reliability work may share test orchestration, but this matrix remains the M06 traceability record.

## Consolidated disposition — 2026-10-25

Final retained-source reconciliation passed with 35,973 events, 17,896 Orders, 29 quarantined poison coordinates, 48 replay audits and zero reconciliation errors; three History partitions were caught up. The full two-pass recovery integration also passed (25 core + 6 streaming checks per pass). These results close the earlier pending reconciliation/recovery entries above.

Still open by design: sustained/soak throughput and lag, extended retention, broker HA, and the owner-run manual checklist. Current one-broker runtime does not establish broker HA. See [verification](verification.md) for the dated evidence and limits.

The dedicated snapshot/WAL overlap gate is now closed for the pinned local version by the isolated 100,000-row probe in [verification](verification.md): 500 concurrent updates, 500 inserts, 101,000 ordered Kafka records, exact final source-state fold, unchanged production connector/topic positions, and UUID-scoped cleanup. A bounded concurrent checkout gate is also measured in [verification](verification.md). Extended WAL/offset retention, sustained/soak checkout throughput, and owner manual acceptance remain open.
