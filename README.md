# SuperSports + Nova

A local ecommerce platform and, later, an Ollama-powered shopping assistant built as a reproducible learning project.

Start with [project context](docs/context/project-context.md), [accepted requirements](requirements/accepted-requirements.md), and the [S1-M01 milestone](docs/milestones/S1-M01/README.md).
See the [current architecture](design/S1-M01/architecture.md), [editable ownership diagram](design/S1-M01/ownership.excalidraw), [SVG preview](design/S1-M01/ownership.svg), [decision record](docs/decisions/0001-local-first-monorepo.md), [test strategy](docs/testing/strategy.md), and [traceability](docs/traceability.md).
The [original architecture gallery](architecture/index.html) is preserved as historical planning input; current decisions supersede its cloud and Rufus terminology.

## Current state
S1-M01 requirements/design baseline. No commerce services, storefront or Nova runtime exists yet.
The seven-lens design review and verification evidence are recorded in the milestone. Next is S1-M02 platform bootstrap.

## Python environment
Use the local virtual environment for every Python command. Activate with source .venv/bin/activate, or invoke .venv/bin/python directly; install dependencies through .venv/bin/python -m pip.
Current verified local interpreter: Python 3.14.7. A fresh checkout must create .venv with a compatible installed interpreter; it is intentionally ignored by Git.
No application dependencies have been installed. Runtime dependencies and exact compatible version pins are selected and verified in S1-M02; this documentation interpreter does not settle all future service runtime versions.

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
