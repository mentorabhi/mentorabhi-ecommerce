# Project working agreement

## Start here
Read docs/context/project-context.md, docs/context/status.md, requirements/accepted-requirements.md, the active milestone and relevant ADRs before changes.
Original requirements and architecture are historical inputs; accepted requirements and dated decisions capture subsequent user changes.

## Structure and execution
Use a monorepo with each microservice as an independent project under services/. Frontend belongs in apps/storefront; data projects in data/pipelines; public schemas in contracts.
All Dockerfiles, Compose/Kubernetes/Helm/Terraform configuration, CI implementation and operational scripts belong under devops/. Keep tests near owning code; cross-service orchestration belongs under devops.
Use .venv/bin/python for Python commands, including pip via -m pip. Do not install project dependencies globally. .venv is ignored; documented interpreter/dependencies must be reproducible.
No cloud services, hosted model fallback, real payments or real fulfillment. Use existing host-installed Ollama only; do not create or run an Ollama container.

## Design before implementation
For each milestone or major feature: save requirements/design and editable diagrams, review, resolve blockers, then implement.
Use Compound Engineering skills when appropriate. Do not invoke additional external model CLIs for automatic reviews without explicit user direction; session reviewers are sufficient.
Maintain context, ADRs, revision history, milestone evidence, lessons and traceability. Record measured results separately from proposals. Keep originals rather than overwriting their historical meaning.

## Correctness and tests
Every feature needs unit tests. Run/document integration, contract, regression, E2E and risk-specific tests after major features/milestones.
Stock, money, coupon limits, idempotency, ownership and approval rules belong in deterministic services. Never query another service's private tables.
Record commands, versions, datasets, outcomes and limitations. Do not claim a runtime acceptance criterion passed based on documentation checks.

## Dependencies and local resources
Verify current stable compatible versions from official sources at implementation time; pin tested versions and images. Check licenses, ARM64 support and resource feasibility.
The baseline machine has 16 GB RAM. Run explicit profiles, measure actual memory and preserve a full commerce integration mode. Heavy data/model jobs may run selectively.

## Autonomy
The user authorizes work in this repository, Git operations and starting/stopping its services. Proceed without routine permission questions; ask for material requirement ambiguity. Environment-enforced approval requirements still apply.
At each milestone checkpoint, create a relevant commit on the active stage branch and push that branch to the configured Git remote. At the start of each new stage, create and publish a branch named for the stage (for example, `stage1`). Do not force-push or overwrite remote history.
Never publish or send messages externally without authorization. Never commit credentials, local state or generated build output.
