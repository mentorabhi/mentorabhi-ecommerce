# ADR 0001 — Local-first monorepo and explicit ownership
Date: 2026-10-23 · Status: accepted constraints; proposed technology families.

## Context
The original plan allowed cloud and hosted inference. The user requires local services, a 16 GB Mac, all infrastructure under devops, independent microservice projects and existing local Ollama.

## Decision
Use a monorepo with explicit service ownership and no cross-service table access. Share a PostgreSQL host locally, with isolated databases/users.
Keep all infrastructure/build/deployment/operational automation in devops. Use Compose for daily work and local Kubernetes as a separate teaching/deployment target.
Support selective workload profiles and a larger self-hosted machine. Use local adapters for replaceable storage/messaging/search/model implementations.
Use the existing host-installed Ollama only. The user's later instruction explicitly excludes an Ollama container. No hosted inference fallback.
Keep exact dependency choices open until current stable compatibility is verified. Pin tested versions and immutable image references; do not use floating latest tags.

## Alternatives
A modular monolith reduces memory overhead but conflicts with the requested independent microservice learning structure. Retain small meaningful services and measure the complete commerce profile.
An always-on full stack makes demos simple but is not credible on 16 GB. Use explicit profile prerequisites and stop incompatible heavy workloads.
Cloud managed services reduce local operations but are outside the user's scope.
A configuration dropdown cannot safely migrate transactional storage. Separate desired configuration from reviewed migration/deployment.

## Consequences
More explicit contracts, idempotency and memory budgeting are required. Infrastructure is portable by configuration but adapters require compatibility and migration tests. No remote hosting/CI account is assumed.

## Provenance and revisions
User-directed constraints: monorepo/devops/local-only/Ollama/16 GB. Currency price books, single-retailer model, service list and workload budget are documented provisional defaults; they can be revised with evidence.
Revision 1: supersedes cloud and hosted-model proposals in original planning baseline without deleting it.
