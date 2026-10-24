# Local development prerequisites
Revision 1 · 2026-10-23.

## Stage 1 commerce/bootstrap
- 16 GB Mac (ARM64 baseline) or a larger self-hosted machine.
- Docker Desktop/Engine running, with Compose and at least 4 GiB allocated for this bootstrap; this Mac has about 7.75 GiB allocated. Full future commerce/data/model workloads require separate measurements.
- A compatible Python interpreter and repository-local .venv for operational scripts. This checkout uses Python 3.14.7. Do not install project packages globally.
- Git and initial internet access for pinned image/dependency downloads. Runtime uses local services and does not require cloud accounts.
- Google Chrome installed on the host for the Selenium UI suite. Selenium Manager downloads the matching ChromeDriver on first test run; runtime services do not need Chrome.
Java/Maven and all app/dependency workloads for this milestone run in Docker. Host Java, Maven, PostgreSQL, Keycloak, Redis or Kafka installations are unnecessary.

From the repository root:
```sh
python3 -m venv .venv
.venv/bin/python --version
devops/scripts/supersports doctor
devops/scripts/supersports configure
devops/scripts/supersports validate
```
Choose a supported installed interpreter explicitly if system python3 is old; for example python3.14 -m venv .venv. Do not recreate an existing working environment just to run these commands.

Set the local application account to the requested demo login before first startup:

```sh
printf 'ADMIN_PASSWORD=admin\n' > devops/.local/admin-login.env
chmod 600 devops/.local/admin-login.env
```

Customer storefront: `http://localhost:3000`. Admin workspace: `http://localhost:3000/admin`, username `admin`, password `admin`. The ignored file is local-only; the identity provisioning step synchronizes it on each `supersports up`. Infrastructure/database credentials stay in the separate generated bootstrap file.

Install the pinned UI test dependency in the repository environment:

```sh
.venv/bin/python -m pip install -r apps/storefront/tests/requirements.txt
```

After starting the full commerce profile, run `devops/scripts/supersports ui-test`. Selenium covers admin merchandising and a self-registering customer flow, including separate customer accounts, profile/cart/wishlist, public search/product detail and token-audience isolation. It retains one stable Selenium admin product/coupon, appends an inventory adjustment/reversal pair per successful run, and creates uniquely named local customer test accounts. Retain these records in the local development databases so UI-to-database results remain inspectable. Browser driver acquisition is managed by Selenium Manager.

## Nova prerequisite: native host Ollama
Use the Ollama installation already present on the host. Do not install, create or start an Ollama Docker container. This is the explicit exception to the Dockerized application/dependency stack. Stage 1 commerce must work while Ollama is stopped.

Before Nova retrieval/model experiments and runtime work:
1. Verify the native CLI and server.
2. Start the existing native application/server if it is stopped.
3. Have the selected lightweight, open-source models available locally. Stage 2 selects and checks exact model versions/digests, licenses, memory use, generation/tool capabilities, embeddings and optional reranking. Do not choose an arbitrary model merely to make a prerequisite check green.
4. Verify connectivity from the Dockerized Nova API to the native host server before declaring integration ready. No hosted/cloud-model fallback is allowed.

Host checks:
```sh
command -v ollama
ollama --version
curl --fail http://127.0.0.1:11434/api/version
ollama list
curl --fail http://127.0.0.1:11434/api/tags
```

If no native server is running, start the existing Ollama application or run this in its own terminal:
```sh
OLLAMA_NO_CLOUD=1 ollama serve
```
Do not start a second server if the native application is already listening. The local-only setting disables cloud features; see the [official Ollama FAQ](https://docs.ollama.com/faq). Existing native app environment configuration must be applied to that app's startup, rather than assuming a terminal export changes an already-running process.

Nova's host endpoint defaults to http://127.0.0.1:11434 for host-side tooling. Its future Docker Desktop client uses http://host.docker.internal:11434. A container's localhost refers to itself. Check host binding/firewall reachability for the Docker bridge; do not broadly expose the unauthenticated model server to the LAN. Linux host-gateway mapping is a deployment-specific configuration to validate when that target is used.
Model discovery is documented in the [official local model-list API](https://docs.ollama.com/api/tags). API availability does not establish model license, size, tool quality or readiness.

## Observed setup on this machine
Checked 2026-10-23: native CLI exists at /usr/local/bin/ollama, reporting client version 0.33.3. No server answered on 127.0.0.1:11434 at that check. No installation was changed, model downloaded, inference run or Ollama container started. Starting the native server and selecting models remain Nova-stage prerequisites, not blockers for this bootstrap.

## Alternate deployment exercises
Helm, Terraform and kind are separate deployment lessons. Helm/Terraform validation can run in pinned tool containers; kind and kubectl are only needed for actual Kubernetes execution. Follow docs/lessons/S1-M02.md and record whether a check rendered configuration or actually deployed it. No cloud provisioning is required.
