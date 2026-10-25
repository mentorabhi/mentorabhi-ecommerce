# Actual application transaction rollback acceptance

2026-10-25 · Design and review before the targeted test

The remaining atomic-write matrix row requires an application transaction failure, beyond a database BEGIN/ROLLBACK demonstration. Create one synthetic checkout using the real Orders API. Before its confirmation step, add a UUID-named PostgreSQL BEFORE INSERT trigger restricted to that order ID and event_type=OrderConfirmed. The trigger raises an exception on that outbox insert only.

The actual Saga confirmation transaction updates the order, sequence and outbox. Require the worker to record a retry while the order remains PENDING_PAYMENT, only OrderAccepted exists, and the committed per-order sequence stays at 1. Require History to remain at the accepted sequence after Kafka catches up. Then remove the trigger/function in a finally block, wait for normal retry to reach FULFILLMENT_SCHEDULED, and require exactly the three expected source event sequences, one payment capture and one-unit stock use.

Isolation/review: the fault targets one newly generated synthetic order; other orders never match the trigger predicate. No payment/provider/fulfillment outside the local simulators is invoked. Cleanup uses only the generated trigger/function identifiers on the owner Orders database and always runs after arming. The one-order SQL fault is an explicitly opt-in operational acceptance test, not a production feature. Failure to remove the fault is a failed test requiring immediate owner-database cleanup. Keep credentials and personal snapshots out of output.

Editable flow: [outbox-rollback-flow](outbox-rollback-flow.mmd). Opt-in flag: SUPERSPORTS_OUTBOX_ROLLBACK=1, alongside the existing SUPERSPORTS_INTEGRATION=1 flag.
