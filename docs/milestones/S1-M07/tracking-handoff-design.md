# M07 Unit 2 — shipment tracking and handoff design

Revision 1 · 2026-10-24 · Design before implementation

## Goal and ownership

Fulfillment Simulator remains the sole owner of a shipment's state, tracking code, revision and transition audit. It exposes deterministic local milestones; no carrier integration or delivery claim is made. Orders exposes tracking only within the authenticated customer's owned order. The operator workspace will advance the simulator in Unit 8.

## State model

`SCHEDULED → HANDED_OFF → IN_TRANSIT → DELIVERED`. Each accepted transition increments a monotonic shipment revision and inserts an append-only audit record containing operation UUID, previous/new state and revision, authenticated operator subject, reason and timestamp. The local simulator supplies a deterministic tracking ID and deterministic estimated milestone dates from the scheduled timestamp. Actual transition timestamps are recorded separately.

Every advance includes `expectedRevision`, `operationId`, target state and bounded reason. The shipment row is selected `FOR UPDATE`; matching operation ID and identical payload returns its original result; changed payload conflicts; stale revision conflicts; unsupported transition is rejected. Scheduling and transition operations share the shipment row/fence. The same lock and revision will arbitrate the cancellation claim added in Unit 3, so handoff and cancellation cannot both win.

## API and security

- Existing checkout worker contract continues to schedule one shipment idempotently.
- Internal tracking reads and operator transition writes have separate authorization checks. Operator calls use the local `supersports-api` audience and record verified JWT subject. No customer bearer token is forwarded to Fulfillment.
- The Orders customer tracking route first proves ownership from its own order database, then reads the simulator's narrow status contract with its service credential. Cross-customer lookup returns the same non-disclosing not-found response.
- Operator UI controls are added in Unit 8. Unit 2 supplies APIs and stable response fields.

## Data and events

Fulfillment adds an additive migration for shipment revision, simulated ETA fields and append-only transition audit. It does not write Orders tables or change checkout events. Orders stores a small shipment mirror and appends post-purchase lifecycle events only after an authoritative fulfillment read; publication is held for Unit 8's versioned event contract and dual-version History support so the existing v1 consumer is never sent an unsupported event.

## Failure boundaries

The transition transaction contains revision/state update and audit insertion. Operation replay is scoped to a stable UUID and request hash. A crash before commit leaves neither transition nor audit; after commit, retry returns the committed receipt. An Orders tracking read failure returns an explicit unavailable tracking state while preserving owned order details. No customer-visible data is inferred from an operator or another customer's shipment.

## Constraints and open facts

All milestones are synthetic and deterministic. ETA is illustrative only. Cancellation and handoff share a row lock; return/refund remains separate. This unit does not move order state to delivered until the simulator transition is observed and mirrored by Orders. Automated tests are authored with implementation but deferred, at the user's direction, until Stage 1 development is complete.
