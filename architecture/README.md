# MentorAbhi architecture diagrams

23 separate editable Excalidraw diagrams: 3 stage overviews and all 20 milestones from the three-stage plan.

## Open and edit
Open https://excalidraw.com and use Open to select an .excalidraw file. Every node, label and connector is editable; no flattened screenshots are used. SVG files are preview companions. Open index.html for the offline gallery.

## Interpretation
These are proposed logical architectures, not as-built infrastructure. Stage 2 describes design activities and target concepts; stage 3 introduces the corresponding extensions. Technology selections remain subject to the project ADRs. A diagram shows the primary flow; response traffic, telemetry, credentials and detailed failure branches may be omitted for clarity and are explained in the notes. Service-owned stores may share local infrastructure without sharing table access. No cloud account or application was deployed.

## Teaching use
Start with a stage overview, open its milestone diagram, explain the problem and boundaries, then demonstrate code, tests and failure behavior at the associated future Git checkpoint. The milestones match the Google Doc created on 23 October 2026. Keep diagrams in Git and revise them when the implementation changes.

## Contents
- S1-00: Stage 1 — Working commerce platform
- S1-M01: Domain boundaries and ownership
- S1-M02: Infrastructure and delivery bootstrap
- S1-M03: Catalog, stock and synthetic fixtures
- S1-M04: Storefront, search and cart
- S1-M05: Checkout Saga and compensation
- S1-M06: Outbox, Kafka and CQRS
- S1-M07: Post-purchase workflows
- S1-M08: Graph, lakehouse and reporting
- S1-M09: Reliability, scaling and recovery
- S2-00: Stage 2 — Rufus requirements and design
- S2-M01: Journeys, permissions and autonomy
- S2-M02: Knowledge, semantic layer and memory
- S2-M03: Bounded agent runtime and MCP tools
- S2-M04: Quality, guardrails and caching design
- S2-M05: Design review and gap traceability
- S3-00: Stage 3 — Extend and integrate the assistant
- S3-M01: Safe commerce extensions
- S3-M02: Read-only shopping assistant
- S3-M03: Approval and durable action execution
- S3-M04: Memory, context and cache correctness
- S3-M05: Enterprise roles and specialist capabilities
- S3-M06: Integrated quality and release gates