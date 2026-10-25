# Local operational UI access

S1-M11 U1 / R23 / AE23 · 2026-10-25

Every human operational UI uses **admin / admin**, as explicitly requested for this local demo. Customer storefront accounts are separate. Keep all published ports bound to `127.0.0.1`; use `localhost` in the browser for existing OIDC callbacks. No generated infrastructure password belongs in this guide or terminal output.

The separate Admin and the operational logins below have been checked locally. Optional profiles are started selectively on the 16 GB host; a listed URL does not imply its profile is running at every moment. Current browser checks cover Admin, Keycloak master, Kafka UI, Prometheus, Trino, Neo4j, Superset and Grafana after selective profile restarts. Wait for each complete lifecycle command, including account provisioning, before testing login; container startup alone is not sufficient. The final post-identity-restart gate is recorded in M11 verification. See [dated verification](../milestones/S1-M11/verification.md).

| UI | Browser URL | Login | Configuration/status |
| --- | --- | --- | --- |
| Customer storefront | http://localhost:3000 | Customer registration/account | Existing application; exception to operational defaults, `supersports-customers` realm. |
| SuperSports Admin | http://localhost:3002 | admin / admin | Deployed separate application; `supersports` realm. Legacy `/admin` redirects here; normal identity provisioning maintains callbacks. This helper does not provision this realm. |
| Keycloak console | http://localhost:8180/admin/master/console/ | admin / admin | Existing identity service; helper provisions a permanent **master** realm administrator using existing `bootstrap-admin`. |
| Kafka UI (Kafbat) | http://localhost:8091 | admin / admin | Optional `streaming` profile; native LOGIN_FORM is enabled and browser/API login is verified. |
| Grafana | http://localhost:3001 | admin / admin | Optional `observability`; existing initial defaults. Helper verifies, or resets the native initial admin on retained volumes. |
| Prometheus | http://localhost:9090 | admin / admin (browser Basic auth) | Optional `observability`; Basic-auth proxy is enabled; direct backend host publication removed. |
| Trino | http://localhost:8096/ui/ | admin / admin (browser Basic auth) | Optional `analytics`; Basic-auth proxy is enabled; direct backend host publication removed. Upstream also shows its username-only form: enter `admin`. Basic auth supplies the password gate. |
| Neo4j Browser | http://localhost:7474/browser/ | admin / admin | Optional `graph`; use `bolt://localhost:7687`, database `neo4j`. Helper creates a separate native UI account; the configured five-character demo minimum permits the requested password. |
| Superset | http://localhost:8095 | admin / admin | Optional `dashboards` (requires analytics/Trino); helper repairs/provisions the native Admin account after normal initialization. |

The graph API (8094), internal analytics API, Kafka Connect, service health endpoints and host database inspection are not additional human UIs. Their existing internal authentication/credentials are unchanged. See [database access](database-access.md) for host inspection.

## Reproducible helper

From the repository root, after the host has configured and started the desired profiles through its normal workflow:

```sh
.venv/bin/python devops/scripts/ui_access.py
```

The helper does not start, stop, recreate, initialize or upgrade services. It targets the existing `supersports` Compose project and fixed loopback endpoints. Docker must refer to the local daemon/context for this repository; remote Docker contexts are outside this helper's scope. It discovers only running containers by Compose labels. Stopped optional services are reported as unavailable, not verified. Missing Keycloak or a failed provision/verification returns nonzero; other services are still attempted. An explicitly selected unavailable service also returns nonzero.

Individual operations:

```sh
.venv/bin/python devops/scripts/ui_access.py --only basic-auth
.venv/bin/python devops/scripts/ui_access.py --only keycloak
.venv/bin/python devops/scripts/ui_access.py --only grafana
.venv/bin/python devops/scripts/ui_access.py --only neo4j
.venv/bin/python devops/scripts/ui_access.py --only superset
```

Only `basic-auth` works entirely offline. It creates ignored `devops/.local/ui.htpasswd` with mode 0600 in a 0700 directory. Nginx supports its salted `{SSHA}` format; Python's standard library generates it without OpenSSL, Apache tools, Python crypt or a new package. This format is sufficient for the explicitly public local demo default, not a production password-storage choice. Valid files retain their hash on rerun; stale credentials are replaced atomically. Symlinks, hardlinks and non-regular files are refused. When replacing this file after proxies are mounted, recreate/remount those proxies through the host workflow so bind mounts point at the new inode.

Keycloak reads only the existing `KEYCLOAK_ADMIN_PASSWORD` value from `devops/.local/bootstrap.env`, authenticates `bootstrap-admin` in master, finds/creates `admin`, fills its profile, clears required first-login actions, sets a non-temporary password and assigns the master `admin` role once. Verification obtains a new token as admin/admin and performs an authorized master API request. No customer/operator realm settings, accounts, password policies, bootstrap password or service client secrets are changed. A bootstrap account removed/rotated outside this workflow or a stricter master password policy causes an explicit failure; the helper does not weaken policy or rotate bootstrap secrets.

Grafana first verifies the native account and server-admin flag. Only HTTP 401 triggers its bundled `grafana cli admin reset-admin-password`, pointed at `/etc/grafana/grafana.ini`, `/usr/share/grafana` and `/var/lib/grafana`. This uses the existing initial administrator ID 1, which must still be named `admin`; renamed/deleted initial identities need host diagnosis. Network failures do not trigger password resets. Any first-login UI password-change prompt still needs browser acceptance; keep the requested demo password and use Skip if the installed UI offers it.

Neo4j reads the existing `GRAPH_DB_PASSWORD` to authenticate as `neo4j` over the loopback Query API against `system`. It verifies an already-correct admin first; otherwise it finds/creates or repairs only `admin`, clears password-change requirements, then verifies `SHOW CURRENT USER` as admin/admin. It preserves the service user and its password. This targets the pinned **Community** image, where all native users have database access and Enterprise role assignment is unavailable. It does not introduce Enterprise licensing or change image editions.

Superset runs a short Python program inside its existing container/app context using its native Flask-AppBuilder security manager. It creates only a missing admin, or repairs that account's password/active state/Admin membership; reruns do not duplicate users/roles or rehash an already correct password. The existing app configuration supplies its own metadata connection and signing secret; neither is changed. It then verifies the DB login through `/api/v1/security/login`. Normal `superset db upgrade`/`superset init` must already have finished; the helper does not run migrations or initialize roles.

HTTP provisioning disables environment proxy use and refuses redirects. Generated credentials and tokens remain in memory; subprocess output and HTTP error bodies are suppressed. A generic FAILED result intentionally requires local configuration/availability diagnosis without dumping secrets. The helper does not modify `admin-login.env`: the host owns the separate Admin realm's existing provisioner and must synchronize its demo login independently.

## Implemented wiring and reproduction

1. Keep the separate Admin origin at `127.0.0.1:3002`, its operator login admin/admin, and customer realm isolation. Integrate callbacks, redirect and tests in the host's existing U1 work.
2. In `neo4j.environment` in `devops/compose/analytics.yaml`, add exactly:

   ```yaml
   NEO4J_dbms_security_auth__minimum__password__length: "5"
   ```

   Neo4j's default minimum is eight; `admin` has five characters. Apply this configuration through the host's service workflow before provisioning. Keep `NEO4J_AUTH: neo4j/${GRAPH_DB_PASSWORD...}`, the graph API password and loopback 7474/7687 publications unchanged. Do not use `set-initial-password` or reset the volume.

3. In Kafka UI's existing environment, host adds:

   ```yaml
   AUTH_TYPE: LOGIN_FORM
   SPRING_SECURITY_USER_NAME: admin
   SPRING_SECURITY_USER_PASSWORD: admin
   ```

   Keep `127.0.0.1:8091:8080`, read-only cluster configuration and existing service identities. Native LOGIN_FORM is host-owned and is not provisioned/verified by this helper.

4. Replace Prometheus/Trino **host** publications with two Nginx proxy publications. Remove the old direct `ports` mappings from those upstream services, including any override publications; otherwise users can bypass the login or the proxy cannot bind the port. Keep upstream internal addresses `prometheus:9090` and `trino:8080` for Grafana, reports and jobs. Do not route internal service traffic through Basic auth.

   Service stanzas implemented in the Compose profiles (paths relative to the repository project directory):

   ```yaml
   prometheus-ui:
     profiles: [observability]
     image: "${STOREFRONT_NGINX_IMAGE:?Use the pinned lock value}"
     user: "${UI_PROXY_UID:?Set to host uid}:${UI_PROXY_GID:?Set to host gid}"
     entrypoint: [nginx]
     command: [-g, "daemon off;"]
     ports: ["127.0.0.1:9090:8080"]
     volumes:
       - ./devops/nginx/prometheus-ui.conf:/etc/nginx/nginx.conf:ro
       - ./devops/.local/ui.htpasswd:/etc/nginx/ui.htpasswd:ro
     tmpfs: [/tmp]
     read_only: true
     cap_drop: [ALL]
     security_opt: ["no-new-privileges:true"]
     mem_limit: 64m
     depends_on: {prometheus: {condition: service_started}}
   trino-ui:
     profiles: [analytics]
     image: "${STOREFRONT_NGINX_IMAGE:?Use the pinned lock value}"
     user: "${UI_PROXY_UID:?Set to host uid}:${UI_PROXY_GID:?Set to host gid}"
     entrypoint: [nginx]
     command: [-g, "daemon off;"]
     ports: ["127.0.0.1:8096:8080"]
     volumes:
       - ./devops/nginx/trino-ui.conf:/etc/nginx/nginx.conf:ro
       - ./devops/.local/ui.htpasswd:/etc/nginx/ui.htpasswd:ro
     tmpfs: [/tmp]
     read_only: true
     cap_drop: [ALL]
     security_opt: ["no-new-privileges:true"]
     mem_limit: 64m
     depends_on: {trino: {condition: service_started}}
   ```

   Supply `UI_PROXY_UID`/`UI_PROXY_GID` from the host credential-file owner's `id -u` / `id -g` in the host's Compose environment. Reuse the **digest-pinned** Nginx image from `devops/images.lock.json`. These are full main configs, not `conf.d` snippets. Running Nginx workers as that numeric owner lets them read the 0600 file without widening permissions. Entry point bypasses the image's default configuration-edit scripts. Both configs listen on container port 8080; Docker publication enforces host loopback. Docker DNS resolves upstreams dynamically. Every path requires Basic auth; Authorization is stripped before forwarding. `/tmp` contains all writable Nginx state. The two 64 MiB limits are proposed bounds, not measured memory evidence.

## Verification evidence and remaining acceptance

Focused author verification uses Python 3.14.7 in the existing `.venv` and deterministic in-memory account fakes/temporary directories; no packages/images were added or upgraded. Initial test discovery failed because the helper module was absent. The focused command below subsequently passed **17 tests** (2026-10-25):

```sh
.venv/bin/python -m unittest discover -s devops/tests -p test_ui_access.py -v
```

Coverage includes master creation/repair/rerun and realm isolation, native Neo4j creation/repair/rerun without changing its service password, Superset creation/repair/rerun including FAB's `None` success result, Grafana conditional reset, private modes/hash validity, stale-file repair, symlink/hardlink refusal, bootstrap preservation and secret-safe HTTP errors. The account fakes exercise the provisioning decisions, not installed server compatibility. Host follow-up verified Nginx UID/mount access, password rejection/acceptance, and the installed native/proxy browser flows. Profile availability is selective. Normal restart persistence remains a final acceptance gate; the dated verification records measured resources and limits.

The host should record AE23 only after wiring and running the helper against enabled profiles, logging into each listed operational UI as admin/admin, checking unauthenticated/wrong-password requests to **both** proxies return 401 and valid requests reach the UI, verifying no direct upstream host-port bypass remains, repeating provisioning and repeating logins after normal restart. Check that Neo4j's `neo4j` service identity still serves the graph API, Superset remains Admin, Keycloak master can administer realms, separate Admin works, and customer registration/login/ownership still works. Optional profiles that were not enabled remain untested; do not report them as passed. The helper-author unit run itself did not execute runtime commands; host follow-up evidence is recorded separately in the milestone verification.

## Official configuration/API references

Existing image versions were read from [images.lock.json](../../devops/images.lock.json): Keycloak 26.8.1, Grafana 13.2.2, Neo4j 2026.10.1 Community, Superset 6.1.0, Nginx 1.29 and Trino 484. No version selection or dependency upgrade is part of U1.

- [Keycloak 26.8.1 Admin REST API](https://www.keycloak.org/docs-api/26.8.1/rest-api/index.html): exact user search, profile update, reset-password and realm role mappings.
- [Nginx Basic auth module](https://nginx.org/en/docs/http/ngx_http_auth_basic_module.html): auth scope and RFC 2307 SSHA password files.
- [Grafana bundled admin CLI](https://grafana.com/docs/grafana/latest/administration/cli/): initial admin ID, home/config/data paths and password reset; [User API](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/user/): authenticated current-user verification.
- [Neo4j Docker settings mapping](https://neo4j.com/docs/operations-manual/current/docker/ref-settings/), [minimum password length](https://neo4j.com/docs/operations-manual/current/configuration/set-initial-password/), [native user management and Community restrictions](https://neo4j.com/docs/operations-manual/current/authentication-authorization/manage-users/), and [Query API](https://neo4j.com/docs/query-api/current/query/).
- [Superset 6.1.0 dependencies](https://github.com/apache/superset/blob/6.1.0/requirements/base.txt) pin Flask-AppBuilder 5.0.2; [that version's native security manager](https://github.com/dpgaspar/Flask-AppBuilder/blob/v5.0.2/flask_appbuilder/security/sqla/manager.py) supplies find/add/update operations; [Superset DB login API](https://superset.apache.org/developer-docs/api/create-security-login/) verifies login. Current manuals are references, not evidence of compatibility with the installed images.

Neo4j usage reporting, cloud Fleet Manager and network discovery are disabled in this local-only profile using the [official settings](https://neo4j.com/docs/operations-manual/current/configuration/configuration-settings/). Superset driver installation targets its existing `/app/.venv` and retains the base image package constraints; its build asserts the compatible SQLAlchemy and Trino versions. Native profile startup commands provision the appropriate operational accounts after service readiness.
