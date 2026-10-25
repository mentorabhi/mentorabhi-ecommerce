# SuperSports + Nova

A local ecommerce platform and, later, an Ollama-powered shopping assistant built as a reproducible learning project.

Start with [project context](docs/context/project-context.md), [accepted requirements](requirements/accepted-requirements.md), and the [S1-M01 milestone](docs/milestones/S1-M01/README.md).
See the [design index for all Stage 1 milestones](design/README.md), [current architecture](design/S1-M01/architecture.md), [editable ownership diagram](design/S1-M01/ownership.excalidraw), [SVG preview](design/S1-M01/ownership.svg), [decision record](docs/decisions/0001-local-first-monorepo.md), [test strategy](docs/testing/strategy.md), and [traceability](docs/traceability.md).
The [original architecture gallery](architecture/index.html) is preserved as historical planning input; current decisions supersede its cloud and Rufus terminology.

## Current state
Stage 1 commerce, simulated checkout/post-purchase, CDC/history, reporting and recovery have recorded automated evidence through M10. M11 catalog/review enhancements and M12 OpenTelemetry are in progress; Nova remains later. See [current status](docs/context/status.md) for measured results and limitations.

Storefront: http://localhost:3000. Separate Admin: http://localhost:3002/admin, using the requested local demo login **admin / admin**. Customer accounts remain separate. Operational UI URLs, credentials and optional profiles are in the [access guide](docs/setup/ui-access.md).

Read [operations](devops/README.md), [setup prerequisites](docs/setup/prerequisites.md), and [original bootstrap evidence](docs/milestones/S1-M02/README.md).
Start with devops/scripts/supersports doctor, configure, validate and up; then run devops/scripts/supersports test. No host Java or cloud account is needed.
Existing host-installed Ollama is a Nova prerequisite only; no Ollama container is used.

## Python environment
Use the local virtual environment for every Python command. Activate with source .venv/bin/activate, or invoke .venv/bin/python directly; install dependencies through .venv/bin/python -m pip.
Current verified local interpreter: Python 3.14.7. A fresh checkout must create .venv with a compatible installed interpreter; it is intentionally ignored by Git.
Runtime dependencies and tested image pins are recorded in their owning projects and devops/images.lock.json. The host documentation/test interpreter is separate from container service runtimes.

## Delivery sequence
1. Stage 1: SuperSports commerce, customer/admin UI, simulations, events, data/reporting and operations.
2. Stage 2: Nova requirements/design, tools, evaluations and commerce gap assessment.
3. Stage 3: Nova integration, grounded chat, approved actions, memory and measured quality.

Initial sports: Cricket and Football. English, INR and Indian addresses by default. Local services only; no hosted model or cloud runtime.
All infrastructure and operational automation belongs to [devops](devops/README.md). Independent service projects will be added during bootstrap.

## Frontend delivery
S1-M03: catalog/inventory admin and product assets/content.
S1-M04: logo, responsive storefront, home/categories/search/product/cart/wishlist/account and categorized configuration administration.
S1-M05: checkout/payment simulation. S1-M07: tracking/returns/reviews/support.
S3-M02/M03: Nova chat, citations/product cards and approval/resume UI.
