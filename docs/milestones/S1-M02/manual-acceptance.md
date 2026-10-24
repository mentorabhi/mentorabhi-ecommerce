# S1-M02 manual acceptance — Local platform bootstrap

Revision 1 · 2026-10-23 · Bootstrap and operator checks; no browser UI is delivered in this milestone.

## Start and check services

From the repository root:

```sh
./devops/scripts/supersports doctor
./devops/scripts/supersports up
./devops/scripts/supersports status
```

Confirm PostgreSQL, Keycloak, Catalog and Configuration are healthy. Confirm the published application ports bind to `127.0.0.1` and PostgreSQL publishes no host port. Probe readiness:

```sh
curl -fsS http://localhost:8081/actuator/health/readiness
curl -fsS http://localhost:8082/actuator/health/readiness
curl -fsS http://localhost:8180/health/ready
```

## Manual API feature check

M02 has no end-user UI. Use the synthetic platform administrator to inspect categorized configuration through its authenticated read API. This reads the generated local credential file without displaying the password or access token:

```sh
DEMO_PLATFORM_ADMIN_PASSWORD=$(awk -F= '$1 == "DEMO_PLATFORM_ADMIN_PASSWORD" {print $2}' devops/.local/bootstrap.env)
TOKEN=$(curl -fsS -X POST http://localhost:8180/realms/supersports/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode grant_type=password \
  --data-urlencode client_id=supersports-cli \
  --data-urlencode username=platform-admin \
  --data-urlencode "password=$DEMO_PLATFORM_ADMIN_PASSWORD" \
  | .venv/bin/python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -fsS http://localhost:8082/api/v1/configuration \
  -H "Authorization: Bearer $TOKEN"
unset TOKEN DEMO_PLATFORM_ADMIN_PASSWORD
```

Confirm the response has the eight configuration categories, defaults for INR, India and English, and no credentials. M02 settings are descriptive migration-only metadata; they are not runtime-editable yet.

## Database checks

Run read-only migration and seed checks inside the local PostgreSQL container:

```sh
docker compose --project-directory . --project-name supersports --env-file devops/.local/bootstrap.env -f devops/compose/core.yaml exec -T postgres sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d catalog -c "SELECT version, success FROM flyway_schema_history WHERE success ORDER BY installed_rank; SELECT service, schema_version FROM bootstrap_metadata;"'
docker compose --project-directory . --project-name supersports --env-file devops/.local/bootstrap.env -f devops/compose/core.yaml exec -T postgres sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d configuration -c "SELECT version, success FROM flyway_schema_history WHERE success ORDER BY installed_rank; SELECT service, schema_version, revision FROM bootstrap_metadata; SELECT count(*) AS categories FROM configuration_category; SELECT count(*) AS settings FROM configuration_setting;"'
```

Expect schema version 1 in both services, eight configuration categories and fourteen settings.

## Manual result

| Check | Result / notes |
|---|---|
| Services healthy and local-only ports | Pending user check |
| Configuration API review | Pending user check |
| Browser UI | N/A by milestone scope |
| Catalog/Configuration database checks | Pending user check |
| Checked by / date |  |
