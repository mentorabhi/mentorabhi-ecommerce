# M06 replay implementation review

2026-10-24 · Scope: audited replay, canonical event hashes, operator CLI, additive migration, and consumer validation.

Code review: skipped (ce-code-review unavailable). The portable full review requires subagent dispatch; no dispatch capability is exposed in this turn. The project prohibits launching external model CLIs for automatic review. An explicit implementation-owner diff scan was performed instead; this is not an independent review receipt.

## Manual diff findings and resolutions

- **Raw JSON hashes rejected semantically identical formatting.** Added canonical fingerprints while preserving legacy raw hashes; retained Kafka payloads can prove a legacy fingerprint before upgrading it. Unit and live replay tests cover reordered objects and reformatted payloads. Arrays retain order; equivalent numbers normalize.
- **The consumer validated fewer fields than the checked-in schema.** Tightened envelope and type-specific payload checks, ownership-key shape, timestamps and integer sequences. Test-first checks failed against the previous implementation, then passed after the fix. Live Orders events continue to validate.
- **Replay could lose intent between its database and Kafka writes.** Audit and delivery intent commit together before publication. Delivery state remains separate from immutable audit. Live tests interrupt before publication and after publication/before receipt persistence, then retry the same operation.
- **A replay could change an already applied event.** Applied raw/canonical fingerprint checks refuse changes; the consumer independently enforces the same invariant. The live test attempts a changed timestamp and observes rejection.
- **Caller-supplied actor text would weaken audit.** The non-web runner verifies operator issuer, audience and signature, records the verified subject, and receives the token on stdin. A customer token is rejected in live testing. CLI tests ensure tokens are absent from command arguments and failure messages.
- **Partition/key changes could reorder corrections.** New DLQ messages retain the original record key; replay publishes to the original source partition, including legacy DLQ records without that header.

## Verification scope and residual work

Eleven Order History Java tests and 31 Python unit cases pass. Both live streaming journeys pass, including the existing commit/offset crash recovery and the new operator recovery/idempotency journey. The customer history Selenium journey passes. Compose validates and `git diff --check` is clean.

The last full repository CI predates this replay slice. Candidate rebuild/reconciliation/cutover, broader failure-boundary acceptance and load/resource measurements remain open. No human manual acceptance is claimed.
