# S1-M06 completion audit

2026-10-24 · This matrix preserves the full approved design scope. Implemented features do not by themselves prove every failure/load acceptance gate.

| Design gate | Authoritative evidence | Current disposition |
|---|---|---|
| Transactional state/outbox writes and legacy sequence backfill | Orders transaction paths, migrations/backfill, event writer/contract checks, live outbox validation | Implemented; explicit rollback-boundary and snapshot-overlap runtime probes still required |
| CDC snapshot/WAL handoff and connector/broker restart | RUNNING connector, durable volumes, owner-scoped live CDC journey | Normal runtime passes; deliberate publication/offset restart-window evidence remains open |
| Inbox deduplication and per-order sequencing | Projector uniqueness/hash/sequence code; commit-before-offset crash journey; canonical hash tests | Deduplication/crash passes; explicit delayed/gapped interleaving and visible timed-gap acceptance remains open |
| Transactional DLQ and immutable audited replay | Kafka transactional DLQ code; operator replay integration with pre/post-publication failures and audit immutability | Replay passes; DLQ pre/post-transaction-commit crash probes remain open |
| Customer ownership and projection UI | Customer/operator audience checks, owner derivation, direct API isolation, customer history Selenium | Existing journeys pass; freshness/staleness under broker outage requires explicit acceptance |
| Isolated rebuild, two marks, reconciliation, failure retention and cutover | Candidate/group code, content-corruption unit checks, live dry-run/mismatch/success/new-checkout journey | Targeted run and both full-CI integration passes passed |
| Full historical reconciliation within retained dataset | `stream-reconcile`: outbox ↔ Kafka ↔ inbox IDs/hashes, timeline, order state/owner/lines/money, audit copy | Targeted runtime passes for retained synthetic dataset; command prints retention limitation |
| Stable compatible ARM64 local profile | Pinned tested images, version/license record, live Docker profile, Compose/Helm/Terraform validation | Full CI passed on the 16 GiB ARM64 host with 7.75 GiB Docker allocation |
| Peak/resource/throughput/concurrent-checkout feasibility | Actual sampled workload and reported memory/lag/throughput, with dataset and limits | 210 CI samples: application maximum 5,237.09 MiB, all-container maximum 5,331.09 MiB; sustained/concurrent capacity and lag remain open |
| Separate manual acceptance and milestone checkpoint | `manual-acceptance.md`, verification/revisions/context, Git push | Guide and checkpoints maintained; human results remain pending |

Next implementation work must close these remaining gates without relabeling them as passed. Later Stage 1 milestones and final reliability work may share test orchestration, but this matrix remains the M06 traceability record.
