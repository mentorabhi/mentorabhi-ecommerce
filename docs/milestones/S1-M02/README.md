# S1-M02 — Local platform bootstrap
Revision 2 · 2026-10-23 · Status: implemented and locally verified; independent review partially unavailable.

Design and implementation contract: [bootstrap design](../../../design/S1-M02/bootstrap.md).
Origin: [accepted requirements](../../../requirements/accepted-requirements.md).
Baseline checkpoint: s1-m01-design-v1 (7ef04c4). Implementation checkpoint: s1-m02-bootstrap (cf50e8e).

The milestone delivers independently buildable Catalog/Configuration foundations, private PostgreSQL, local identity, Docker operational scripts, real-stack verification and alternate-deployment scaffolding. Storefront/catalog business features retain their later milestone owners.

## Implementation and runtime evidence — 2026-10-23

- `devops/scripts/ci` completed successfully on the freshly reset local Compose profile: Docker doctor, Compose validation, unit suites, Helm/Terraform checks, image builds, startup, integration suite, and recovery drill. It used Python 3.14.7, Docker 29.8.0, Compose 5.5.1, ARM64, Docker allocation 7.75 GiB. This full run preceded the final review-driven test additions below.
- Follow-up `.venv/bin/python -m unittest discover -s devops/tests -p test_manage.py -v`: **16 passed**. Follow-up `SUPERSPORTS_INTEGRATION=1 .venv/bin/python -m unittest discover -s devops/tests -p test_core_integration.py -v`: **12 passed**, including authenticated POST/PUT/PATCH/DELETE attempts with unchanged configuration snapshots.
- Service image builds ran `mvn -B -ntp verify` in the pinned Maven/Temurin build image: **9 JUnit tests per service (18 total)**. Docker image builds succeeded for Catalog and Configuration.
- Live recovery evidence: application restart preserved configuration/migration state; PostgreSQL outage removed readiness while liveness remained available; restarting PostgreSQL restored readiness and identity token issuance; the full integration suite passed after recovery.
- Release/rollback exercise: two local releases were recorded with immutable image IDs; rollback to the first release passed integration checks and the running image IDs matched the recorded release. Scoped reset removed only the synthetic `supersports` runtime volumes and preserved local credentials/build cache; the full CI bootstrap then passed.
- Deployment checks: Helm lint/render and negative schema checks passed; Terraform fmt/init/validate and three native tests passed. No Kubernetes cluster was deployed and Terraform is a providerless desired-state scaffold, not provisioning.
- Latest point-in-time `docker stats --no-stream` after the follow-up tests: Catalog 331.9 MiB, Configuration 280 MiB, Keycloak 526.3 MiB, PostgreSQL 42.08 MiB; combined **1,180.28 MiB**. These are observed container RSS snapshots under this workload, not a peak or whole-platform benchmark. Configured limits are 512/512/768/384 MiB respectively.
- Host-native Ollama was not started and no models were downloaded. Its installation, local-only server setup, model selection and Docker-to-host connectivity are documented as Nova prerequisites.

Reproduction entry point: `devops/scripts/ci`. Follow-up commands are listed above. The CI run's 13 Python unit tests and 11 integration tests were extended by the later passing 16/12 targeted runs; do not interpret the initial CI transcript as having run the later-added cases.

## Code review — 2026-10-23

Compound Engineering `ce-code-review` was started against base `fe7b7d98322a70728f9e15a30454a9d18b37b344`, covering the 68-file implementation diff. Eight session lenses returned results: correctness, standards, testing, maintainability, agent-native, security, API contract, and data migration. Reliability and adversarial reviewers could not complete because the session reported its usage limit. No external model CLI was used, per project instructions; therefore this is **not a complete independent review receipt**.

Applied findings: moved the local token helper into `devops/scripts/manage.py` to remove the recovery-to-test-module dependency; added release failure/rollback orchestration unit cases; added real-stack mutation-method regressions. All affected tests passed (16 unit, 12 integration). Remaining explicit testing gap: no correctly signed expired-token or wrong-issuer-token negative case was added; existing live authentication tests cover anonymous, wrong-role, wrong-audience and tampered tokens. The reviewer-set interruption and this gap remain recorded for follow-up hardening.

The implementation received a direct final diff and secret/whitespace scan; `git diff --check` passed. No automated security scan or SBOM generation is claimed.

## Design review — 2026-10-23
Compound Engineering ce-doc-review, non-interactive. Coherence, feasibility, security, scope and adversarial reviewers each completed in separate session contexts and returned no findings. No packs configured. Cross-model pass disabled by active project instructions; no external model CLI invoked. peer.outcome: in-process-fallback.
Applied fixes: none. Proposed fixes/decisions: none. Runtime feasibility remains subject to measured execution.
Review complete.

```json
[
  {
    "reviewer": "scope-guardian",
    "findings": [],
    "residual_risks": [],
    "deferred_questions": []
  },
  {
    "reviewer": "adversarial",
    "findings": [],
    "residual_risks": [],
    "deferred_questions": []
  },
  {
    "reviewer": "security-lens",
    "findings": [],
    "residual_risks": [],
    "deferred_questions": []
  },
  {
    "reviewer": "feasibility",
    "findings": [],
    "residual_risks": [],
    "deferred_questions": []
  },
  {
    "reviewer": "coherence",
    "findings": [],
    "residual_risks": [],
    "deferred_questions": []
  }
]
```
