# Revision history
Append dated entries with reason, changed artifacts, evidence and remaining work.

## 2026-10-23 — Revision 1, S1-M01 draft
Captured the original requirements and Google planning baseline plus all subsequent user decisions.
Added accepted requirements, actor/acceptance examples, baseline architecture, local-first ADR, testing strategy and traceability.
Preserved original architecture proposals; new S1-M01 design overrides cloud/hosted-model suggestions and introduces currency/coupon/configuration policies.
Design review and structural validation pending. No application implementation or runtime verification yet.

## 2026-10-23 — Revision 2, reviewed design and Python environment
Seven session review lenses completed. Corrected the checkout sequence so unknown payment outcomes reconcile before releasing reservations/coupon holds.
Created .venv, verified Python 3.14.7 and pip 26.2.1; all subsequent Python execution uses .venv/bin/python. The initial system-default 3.9 environment was recreated with the installed modern interpreter.
Added persistent AGENTS.md, root entry point, devops ownership guide and .gitignore. Initialized local Git on docs/s1-m01.
Added editable S1-M01 ownership Excalidraw and SVG companions; preserved all 23 original diagram pairs.
Runtime service/test implementation remains S1-M02 onward. Final structural checks pending.

## 2026-10-23 — Verification checkpoint
Documentation links, requirements/acceptance traceability, diagram JSON/SVG, payment-reconciliation wording and ignore patterns checked successfully. Reproduction commands and limitations are recorded in S1-M01.
Design baseline is reviewed; rendered diagram inspection and tagged Git checkpoint are not claimed complete. No runnable service or application test exists yet. Next milestone is S1-M02 bootstrap.

## 2026-10-23 — Host-only Ollama clarification
User explicitly requires the existing host-installed Ollama, with no Ollama container. This supersedes the portable container fallback proposed earlier. Updated active requirements, context, working guidance and design. Bootstrap starts only PostgreSQL, identity and commerce foundations; Nova remains later-stage work.

## 2026-10-23 — S1-M02 implementation and verification
Added independently buildable Catalog and Configuration services, pinned ARM64 Docker core, local Keycloak/PostgreSQL, private generated credentials, operational/recovery/release scripts, Helm/Terraform/kind teaching artifacts and the Nova-native-Ollama prerequisite. Measured the running core at 1,180.28 MiB combined container RSS in one snapshot; this is not a peak or future full-commerce benchmark.
The full `devops/scripts/ci` run passed; follow-up review-driven coverage passed with 16 Python unit tests and 12 real-stack integration tests (18 Java tests also passed in each service image build). Recovery, exact-image rollback, scoped reset, Helm/Terraform checks passed. No Kubernetes cluster, cloud provisioning, security scan or SBOM was run.
Eight code-review lenses returned; reliability and adversarial lenses hit the session usage limit. Recorded findings were fixed and retested. Signed expired/wrong-issuer JWT negative tests remain a follow-up gap; review completion is partial, not represented as a full review receipt.
Checkpointed locally as `s1-m02-bootstrap` (`cf50e8e`); next milestone is S1-M03 catalog/inventory.

## 2026-10-23 — S1-M03 design reviewed
Added the Catalog/Pricing/Inventory implementation contract, editable Excalidraw architecture and preview, milestone evidence page, and ADR 0002. Two design-review passes resolved price-completeness concurrency, currency ownership, admin role/revision/audit rules, asset scope and admin interaction-state findings. Cross-model review was skipped under the repository rule against external model CLIs. No S1-M03 implementation or runtime test is claimed yet.
