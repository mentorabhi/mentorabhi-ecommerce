# Acceptance probes need their own failure checks

2026-10-25 · Verified during the S1-M06 soak/retention work

The system under test can be correct while the test harness reports a false pass. The session review found deadline checks made before authentication/polling, zero-lag checks accepting partial partition sets, cleanup flags recorded only after successful create responses, and final memory checks that omitted stopped containers. Keep deadlines around actual dispatch/observation, enforce complete coordinate sets, own UUID resources before attempting creation, and inspect the original container IDs after execution.

Kafka 4.3's console consumer prints a deprecation warning to stdout for `--consumer-property`. Strict JSON consumers then fail on the warning before reading real events. Use the pinned CLI's `--command-property`; do not silently drop arbitrary non-JSON lines, which could hide malformed event data.

When a long probe has already loaded code before review improvements land, preserve that report's code/evidence scope. Audit actual recorded windows, resources and complete event reconciliation explicitly; do not imply that edits changed the already-running process. Keep policy configuration (for example seven-day offset retention) distinct from a measured 15-minute idle checkpoint.
