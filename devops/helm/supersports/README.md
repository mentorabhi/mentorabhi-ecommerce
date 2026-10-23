# SuperSports local chart

Helm 4.3.1; no subcharts or downloaded dependencies. Namespace ownership belongs
to Helm's `--namespace` / `--create-namespace`, with no namespace in templates.
Follow [the lesson](../../../docs/lessons/S1-M02.md) from the repository root.

Required values: `existingSecret`, `bootstrap.postgresExistingConfigMap`,
`bootstrap.realmExistingConfigMap`. Empty defaults deliberately fail schema
validation/rendering. Required messages also cover rendering with schema checks
disabled. ConfigMaps must contain `init.sh` and `supersports-realm.json` respectively,
created directly from host-owned files; the chart keeps no divergent copies.

External Secret keys:
`POSTGRES_PASSWORD`, `CATALOG_DB_PASSWORD`, `CONFIGURATION_DB_PASSWORD`,
`IDENTITY_DB_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`, `DEMO_CUSTOMER_PASSWORD`,
`DEMO_PLATFORM_ADMIN_PASSWORD`, `DEMO_CATALOG_ADMIN_PASSWORD`.
The chart never creates or renders a Secret. PostgreSQL receives DB bootstrap
credentials; each app receives only its own DB password; identity receives its
own DB/bootstrap/demo credentials. PostgreSQL initialization runs only against
an empty volume; realm import does not overwrite a realm already in its database.
Updating Secret values alone does not rotate stored credentials.

Services are ClusterIP. Keycloak uses local development mode; its health port
9000 is pod-only. Use explicit loopback port-forwards for the lesson. App images
must be built and loaded into kind before installation (`Never` by default).
For a local release, override each app `image` with its verified immutable digest
and use `IfNotPresent` after making that artifact available to the local nodes.
No external registry access or release verification is performed by this chart.

App pods use UID/GID 10001, no privileges, dropped capabilities, read-only root
filesystems and writable `/tmp`. Dependency images retain their upstream runtime
users/filesystem behavior. Memory limits total 2176 MiB plus Kubernetes/node
and host overhead; requests total 1088 MiB. These are design allocations, not
measured RSS or a demonstrated 16 GB fit. Stop the Compose stack before this
alternate exercise. Local kind default storage backs the PostgreSQL PVC.

Host checks (with the verified Helm binary available):

```sh
HELM=devops/.local/bin/helm
# Expected failure: required external resource names are absent.
"$HELM" lint devops/helm/supersports
# Expected success: fixture names only, no passwords rendered.
"$HELM" lint devops/helm/supersports \
  --set existingSecret=fixture-secret \
  --set bootstrap.postgresExistingConfigMap=fixture-init \
  --set bootstrap.realmExistingConfigMap=fixture-realm
"$HELM" template exercise devops/helm/supersports --namespace alternate \
  --set existingSecret=fixture-secret \
  --set bootstrap.postgresExistingConfigMap=fixture-init \
  --set bootstrap.realmExistingConfigMap=fixture-realm
# Expected failure: disallowed app pull policy.
"$HELM" template exercise devops/helm/supersports \
  --set existingSecret=fixture-secret \
  --set bootstrap.postgresExistingConfigMap=fixture-init \
  --set bootstrap.realmExistingConfigMap=fixture-realm \
  --set apps.catalog.imagePullPolicy=Always
```

Inspect rendered references, issuer/JWK distinction, ports, security contexts,
resources, probes and PVC path. These validators replace YAML-mirroring tests;
real readiness, auth, isolation, persistence and RSS require cluster execution.
