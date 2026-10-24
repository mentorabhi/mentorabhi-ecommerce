# M07 Units 6–7 design review

Revision 1 · 2026-10-24

Review covered accepted AE10/AE11/AE21, existing customer/operator realms, Orders ownership APIs, migration-per-service conventions and v2 event privacy allowlists.

- **Purchase proof:** resolved by an owner-scoped Orders endpoint; Reviews/Support do not join or query Orders storage.
- **Cross-customer access:** customer subject comes from the verified customer token and participates in every read/update predicate. Operator routes require the operator audience and expose no impersonation mechanism.
- **Untrusted content:** lengths and states are bounded; output remains escaped text. Reviews/tickets/messages do not enter Kafka events or model/tool contexts.
- **Duplicate/replay:** review uniqueness is enforced in the Reviews DB. Support message operation UUID plus payload hash makes retries safe and changed replays conflict.
- **Privacy minimization:** Orders returns only the order/SKU/delivery verification fact. Support stores no bearer token and exposes only necessary order references.
- **Failure handling:** dependency outage rejects linked submissions without creating orphan state. This means clients may retry after restoring Orders.
- **Decision:** design is ready for source implementation. No test/build is authorized by this design checkpoint; execution remains deferred until all Stage 1 development is complete.
