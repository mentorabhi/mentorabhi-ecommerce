# Soak and retention design review

Revision 1 · 2026-10-25 · Reviewed before implementation

- Scope: concrete 900-second windows resolve the previously unbounded wording; results must state the actual duration and offered rate.
- Commerce correctness: unique keys plus exact replay, owner reads, stock delta, money/line equality and final sequence/lag checks give independent oracles beyond HTTP acceptance.
- Retention correctness: use an inactive logical slot and durable idle group checkpoint; test deferred group consumption and full replay against the owned source table. A configuration value alone cannot pass retention.
- Resource protection: paced load, 60-order limit, 180-second drain, 256 MiB WAL guard, optional-profile suspension and finally cleanup bound impact on the 16 GB host.
- Isolation: UUID resource names; no production connector/group/policy mutation. Production topic growth is expected during the simultaneous soak.
- Evidence: private ignored reports survive failures, exclude secrets, and preserve outcomes. Cleanup failure makes the probe fail and identifies the disposable resource for recovery.

No design blocker identified. Implementation must preserve accepted order IDs when a later submission or assertion fails, refresh authentication during the full interval, and use monotonic timing rather than wall-clock arithmetic for latency.

## Implementation review and resolution

A separate session reviewer inspected the scripts read-only (receipt `/tmp/ce-code-review-soak-retention-4jgwa0ll/review.json`). Findings covered workload/drain deadline overruns, response-loss cleanup, main connector task health, complete lifecycle evidence, complete partition coverage, and stopped/disappeared-container accounting. The implementation now checks dispatch after authentication, checks terminal observation after polling, budgets connector startup within the recovery deadline, records resource ownership before creation attempts, reconciles all lifecycle facts, requires exact partition sets, and inspects the original container IDs even when stopped or missing. Fourteen focused tests cover these invariants; the final static follow-up reported no remaining actionable finding within that scope.

The 900-second runs had already loaded the earlier harness when guard fixes landed. Their recorded outcomes were therefore independently audited before acceptance: latest request plus acceptance at 887.662 seconds, latest terminal observation at 896.371 seconds, all three partitions covered, recovery 11.26 seconds, exact full reconciliation, all original images/containers created before the run still running without restart/OOM, and absence of disposable resources. Private audit report paths are recorded in verification. This is the evidence for accepting those finite runs; do not claim the guarded script revision itself was re-run for 900 seconds.
