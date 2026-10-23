# devops — infrastructure and operations project

This is the sole home for SuperSports/Nova infrastructure, build/deployment configuration and operational automation. S1-M01 establishes the boundary; S1-M02 adds runnable infrastructure.

Planned areas:
- docker/: service Dockerfiles and explicit repository build contexts.
- compose/: core, streaming/search, analytics and Nova profile definitions.
- kubernetes/ and helm/: alternate local/larger-machine deployment.
- terraform/: local/self-hosted provisioning with explicit teardown.
- observability/: local collectors, metrics/log/trace backends and dashboards.
- scripts/: bootstrap, seed/reset, validation, backups, restore and local CI.
- tests/: cross-service integration/regression/E2E orchestration.

No executable bootstrap command exists yet. No cloud provider/account/credentials is required.
Services keep build descriptors, source, unit/integration tests and migrations in their own project directories; devops consumes those projects without merging their ownership.
Secrets, volumes and local state must be ignored. Configuration UI records typed desired settings; it does not execute shell commands or hot-swap a database.
