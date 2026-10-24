"""SuperSports local operations. Invoke through the repository .venv."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from uuid import UUID
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SECRET_KEYS = (
    "POSTGRES_PASSWORD", "CATALOG_DB_PASSWORD", "CONFIGURATION_DB_PASSWORD",
    "IDENTITY_DB_PASSWORD", "PRICING_DB_PASSWORD", "INVENTORY_DB_PASSWORD", "CUSTOMER_DB_PASSWORD", "ORDERS_DB_PASSWORD", "PAYMENT_DB_PASSWORD", "FULFILLMENT_DB_PASSWORD",
    "KEYCLOAK_ADMIN_PASSWORD", "CHECKOUT_WORKER_CLIENT_SECRET", "DEMO_CUSTOMER_PASSWORD",
    "DEMO_PLATFORM_ADMIN_PASSWORD", "DEMO_CATALOG_ADMIN_PASSWORD", "DEMO_INVENTORY_OPERATOR_PASSWORD",
    "CDC_DB_PASSWORD", "ORDER_HISTORY_DB_PASSWORD", "ORDER_HISTORY_OWNER_KEY",
)
M02_SECRET_KEYS = (
    "POSTGRES_PASSWORD", "CATALOG_DB_PASSWORD", "CONFIGURATION_DB_PASSWORD",
    "IDENTITY_DB_PASSWORD", "KEYCLOAK_ADMIN_PASSWORD", "DEMO_CUSTOMER_PASSWORD",
    "DEMO_PLATFORM_ADMIN_PASSWORD", "DEMO_CATALOG_ADMIN_PASSWORD",
)
PRE_M05_SECRET_KEYS = (*M02_SECRET_KEYS, "PRICING_DB_PASSWORD", "INVENTORY_DB_PASSWORD",
                       "DEMO_INVENTORY_OPERATOR_PASSWORD", "CUSTOMER_DB_PASSWORD", "ORDERS_DB_PASSWORD", "CHECKOUT_WORKER_CLIENT_SECRET")
LEGACY_SECRET_KEYS = (*PRE_M05_SECRET_KEYS, "PAYMENT_DB_PASSWORD", "FULFILLMENT_DB_PASSWORD")
SERVICES = ("catalog", "configuration", "pricing", "inventory", "customer", "orders", "payment-simulator", "fulfillment-simulator")
STREAMING_SERVICES = ("order-history",)
DEPLOYABLES = (*SERVICES, *STREAMING_SERVICES, "storefront")
SERVICE_PORTS = (8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088)
DEFAULT_VERSION = "s1-m06"
TOKEN_URL = "http://127.0.0.1:8180/realms/supersports/protocol/openid-connect/token"
CUSTOMER_TOKEN_URL = "http://127.0.0.1:8180/realms/supersports-customers/protocol/openid-connect/token"


def token_for(username: str, password: str, client: str = "supersports-cli") -> str:
    body = urlencode({"grant_type": "password", "client_id": client,
                      "username": username, "password": password}).encode()
    with urlopen(Request(TOKEN_URL, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded"
    }), timeout=10) as response:
        return json.loads(response.read())["access_token"]


def customer_token_for(username: str, password: str) -> str:
    body = urlencode({"grant_type": "password", "client_id": "supersports-customer-test",
                      "username": username, "password": password}).encode()
    with urlopen(Request(CUSTOMER_TOKEN_URL, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded"
    }), timeout=10) as response:
        return json.loads(response.read())["access_token"]


def checkout_worker_token(root: Path = ROOT) -> str:
    credentials = load_credentials(root / "devops/.local/bootstrap.env")
    body = urlencode({"grant_type": "client_credentials", "client_id": "supersports-checkout-worker",
                      "client_secret": credentials["CHECKOUT_WORKER_CLIENT_SECRET"]}).encode()
    with urlopen(Request(TOKEN_URL, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded"
    }), timeout=10) as response:
        return json.loads(response.read())["access_token"]


def validated_project_name(value: str) -> str:
    if not re.fullmatch(r"supersports(?:-[a-z0-9][a-z0-9-]{0,31})?", value):
        raise ValueError("Project name must be supersports or supersports-<local-suffix>.")
    return value


def validated_version(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", value):
        raise ValueError("Release version must be a lowercase image tag, not a path.")
    return value


def validate_reset(project: str, confirmation: str | None) -> None:
    validated_project_name(project)
    if confirmation != project:
        raise ValueError(f"Reset requires --confirm-reset {project}; it removes only that project's data.")


def load_credentials(path: Path) -> dict[str, str]:
    if path.is_symlink():
        raise ValueError("Refusing a symlinked credentials file.")
    values = {}
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in SECRET_KEYS or key in values:
            raise ValueError("Malformed bootstrap credentials; existing file was preserved.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", value):
            raise ValueError("Bootstrap credentials must be generated opaque values.")
        values[key] = value
    if set(values) != set(SECRET_KEYS):
        raise ValueError("Incomplete bootstrap credentials; existing file was preserved.")
    return values


def configure_admin_login(root: Path = ROOT) -> str:
    """Keep the editable local application password separate from infrastructure secrets."""
    directory = root / "devops/.local"
    if directory.is_symlink():
        raise ValueError("Refusing a symlinked local state directory.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    path = directory / "admin-login.env"
    if path.is_symlink():
        raise ValueError("Refusing a symlinked admin login file.")
    if not path.exists():
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(f"ADMIN_PASSWORD={secrets.token_hex(24)}\n")
    value = path.read_text().strip()
    if not re.fullmatch(r"ADMIN_PASSWORD=[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Invalid local admin login file; existing value was preserved.")
    path.chmod(0o600)
    return value.partition("=")[2]


def configure(root: Path = ROOT) -> Path:
    local = root / "devops/.local"
    if local.is_symlink():
        raise ValueError("Refusing a symlinked local state directory.")
    local.mkdir(parents=True, exist_ok=True, mode=0o700)
    local.chmod(0o700)
    path = local / "bootstrap.env"
    if path.is_symlink():
        raise ValueError("Refusing a symlinked credentials file.")
    if path.exists():
        try:
            load_credentials(path)
        except ValueError:
            if not path.is_file():
                raise
            existing = {}
            for line in path.read_text().splitlines():
                if not line or line.startswith("#"):
                    continue
                key, separator, value = line.partition("=")
                if not separator or key not in LEGACY_SECRET_KEYS or key in existing or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", value):
                    raise
                existing[key] = value
            if set(existing) not in (set(M02_SECRET_KEYS), set(PRE_M05_SECRET_KEYS), set(LEGACY_SECRET_KEYS)):
                raise
            with path.open("a") as handle:
                for key in sorted(set(SECRET_KEYS) - set(existing)):
                    handle.write(f"{key}={secrets.token_hex(24)}\n")
            load_credentials(path)
        path.chmod(0o600)
        configure_admin_login(root)
        return path
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write("# Generated locally. Do not commit, print or rotate independently of database state.\n")
        for key in SECRET_KEYS:
            handle.write(f"{key}={secrets.token_hex(24)}\n")
    configure_admin_login(root)
    return path


def compose_command(root: Path, project: str, arguments: list[str]) -> list[str]:
    return [
        "docker", "compose", "--project-directory", str(root),
        "--project-name", validated_project_name(project),
        "--env-file", str(root / "devops/.local/bootstrap.env"),
        "-f", str(root / "devops/compose/core.yaml"), *arguments,
    ]


def history_target_path(root: Path = ROOT, project="supersports") -> Path:
    return root / "devops/.local" / f"order-history-target-{validated_project_name(project)}.json"


def validated_history_target(value):
    if not isinstance(value, dict) or set(value) != {"database", "group"}:
        raise ValueError("Invalid Order History database/group target.")
    if value == {"database": "order_history", "group": "order-history-v1"}:
        return dict(value)
    database = value.get("database")
    match = re.fullmatch(r"order_history_r_([a-f0-9]{12})", database) if isinstance(database, str) else None
    if not match or value["group"] != "order-history-r-" + match.group(1):
        raise ValueError("Order History candidate database/group must have the same generated suffix.")
    return dict(value)


def history_target(root: Path = ROOT, project="supersports"):
    path = history_target_path(root, project)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Refusing a symlinked Order History target.")
    if not path.exists():
        return {"database": "order_history", "group": "order-history-v1"}
    return validated_history_target(json.loads(path.read_text()))


def set_history_target(value, *, root: Path = ROOT, project="supersports"):
    target = validated_history_target(value)
    path = history_target_path(root, project)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Refusing a symlinked Order History target.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".history-target-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(target, handle); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def deployment_env(root: Path, version: str = DEFAULT_VERSION, images: dict | None = None, project="supersports") -> dict:
    environment = os.environ.copy()
    environment.update(load_credentials(root / "devops/.local/bootstrap.env"))
    lock = json.loads((root / "devops/images.lock.json").read_text())
    for key in ("BUILD_IMAGE", "JAVA_IMAGE", "POSTGRES_IMAGE", "KEYCLOAK_IMAGE", "KAFKA_IMAGE", "DEBEZIUM_CONNECT_IMAGE"):
        environment[key] = lock[key]
    for key in ("STOREFRONT_NODE_IMAGE", "STOREFRONT_NGINX_IMAGE"):
        environment[key] = lock[key]
    environment["RELEASE_VERSION"] = validated_version(version)
    target = history_target(root, project)
    environment["ORDER_HISTORY_DATABASE_NAME"] = target["database"]
    environment["ORDER_HISTORY_CONSUMER_GROUP"] = target["group"]
    for service in DEPLOYABLES:
        environment[f"{service.upper().replace('-', '_')}_IMAGE"] = (
            images[service] if images else f"supersports/{service}:{version}"
        )
    return environment


def run(command: list[str], *, environment=None, capture=False, check=True, cwd=ROOT, input_text=None):
    result = subprocess.run(
        command, cwd=cwd, env=environment, text=True, input=input_text,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None, check=False,
    )
    if check and result.returncode:
        # Never include the environment, token bodies or command arguments in an exception.
        raise RuntimeError(f"Operation failed with exit {result.returncode}; inspect the service status/logs.")
    return result


def compose(arguments: list[str], *, root=ROOT, project="supersports",
            version=DEFAULT_VERSION, images=None, capture=False, check=True, input_text=None, history_override=None):
    environment=deployment_env(root,version,images,project=project)
    if history_override is not None:
        target=validated_history_target(history_override)
        environment["ORDER_HISTORY_DATABASE_NAME"]=target["database"]
        environment["ORDER_HISTORY_CONSUMER_GROUP"]=target["group"]
    return run(compose_command(root, project, arguments),
               environment=environment,
               capture=capture, check=check, cwd=root, input_text=input_text)


def provision_databases(root=ROOT, project="supersports", version=DEFAULT_VERSION):
    compose(["up", "-d", "postgres", "--wait", "--wait-timeout", "120"],
            root=root, project=project, version=version)
    command = compose_command(root, project, ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1"])
    command.extend(["-f", "/opt/supersports/provision.sql"])
    run(command, cwd=root)


def register_orders_connector(root=ROOT, project="supersports", version=DEFAULT_VERSION):
    publication_check = compose_command(root, project, ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "orders", "-tAc", "SELECT 1 FROM pg_publication WHERE pubname='supersports_orders_publication'"])
    environment = deployment_env(root, version)
    publication = run(publication_check, environment=environment, capture=True, cwd=root).stdout.strip()
    if publication != "1":
        create_publication = compose_command(root, project, ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "orders", "-v", "ON_ERROR_STOP=1", "-c", "CREATE PUBLICATION supersports_orders_publication FOR TABLE public.order_outbox"])
        run(create_publication, environment=environment, cwd=root)
    credentials = load_credentials(root / "devops/.local/bootstrap.env")
    config = {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "tasks.max": "1",
        "database.hostname": "postgres",
        "database.port": "5432",
        "database.user": "supersports_cdc",
        "database.password": credentials["CDC_DB_PASSWORD"],
        "database.dbname": "orders",
        "topic.prefix": "supersports",
        "plugin.name": "pgoutput",
        "slot.name": "supersports_orders_outbox",
        "publication.name": "supersports_orders_publication",
        "publication.autocreate.mode": "disabled",
        "table.include.list": "public.order_outbox",
        "snapshot.mode": "initial",
        "tombstones.on.delete": "false",
        "transforms": "outbox",
        "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
        "transforms.outbox.table.field.event.id": "event_id",
        "transforms.outbox.table.field.event.key": "aggregate_id",
        "transforms.outbox.table.field.event.aggregate.type": "aggregate_type",
        "transforms.outbox.table.field.event.type": "event_type",
        "transforms.outbox.table.field.event.payload": "payload",
        "transforms.outbox.route.by.field": "event_type",
        "transforms.outbox.route.topic.replacement": "commerce.order.events.v1",
        "transforms.outbox.table.expand.json.payload": "true",
    }
    base = "http://127.0.0.1:8090/connectors"
    try:
        with urlopen(base, timeout=10) as response:
            names = json.loads(response.read())
        if "supersports-orders-outbox" in names:
            request = Request(base + "/supersports-orders-outbox/config", data=json.dumps(config).encode(),
                              headers={"Content-Type": "application/json"}, method="PUT")
            with urlopen(request, timeout=15):
                pass
        else:
            request = Request(base, data=json.dumps({"name": "supersports-orders-outbox", "config": config}).encode(),
                              headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=15):
                pass
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError("Could not configure the local Orders CDC connector; inspect Connect status.") from error


def streaming_up(project="supersports", version=DEFAULT_VERSION):
    provision_databases(project=project, version=version)
    compose(["--profile", "streaming", "up", "-d", "--build", "--wait", "--wait-timeout", "240"],
            project=project, version=version)
    provision_local_identity()
    wait_status("http://127.0.0.1:8090/connectors", timeout=180)
    for topic, partitions in (("commerce.order.events.v1", 3), ("commerce.order.events.dlq.v1", 1)):
        compose(["--profile", "streaming", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh",
                 "--bootstrap-server", "localhost:9092", "--create", "--if-not-exists", "--topic", topic,
                 "--partitions", str(partitions), "--replication-factor", "1"], project=project, version=version)
        compose(["--profile", "streaming", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-configs.sh",
                 "--bootstrap-server", "localhost:9092", "--entity-type", "topics", "--entity-name", topic,
                 "--alter", "--add-config", "retention.ms=-1"], project=project, version=version)
    register_orders_connector(project=project, version=version)


def streaming_status(project="supersports", version=DEFAULT_VERSION):
    compose(["--profile", "streaming", "ps"], project=project, version=version)
    try:
        with urlopen("http://127.0.0.1:8090/connectors/supersports-orders-outbox/status", timeout=10) as response:
            status = json.loads(response.read())
        print("Orders CDC connector status:", status.get("connector", {}).get("state", "UNKNOWN"))
        for task in status.get("tasks", []):
            print(f"Orders CDC task {task.get('id')}: {task.get('state', 'UNKNOWN')}")
        for name, count in (("commerce.order.events.v1", "3"), ("commerce.order.events.dlq.v1", "1")):
            compose(["--profile", "streaming", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh",
                     "--bootstrap-server", "localhost:9092", "--describe", "--topic", name], project=project, version=version)
        compose(["--profile", "streaming", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-consumer-groups.sh",
                 "--bootstrap-server", "localhost:9092", "--describe", "--group", history_target(project=project)["group"]], project=project, version=version, check=False)
        print("Active Order History target:", json.dumps(history_target(project=project)))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        print("Orders CDC connector status: unavailable")


def stream_fault(mode: str | None, order_id: str | None = None, next_event: bool = False,
                 project="supersports", version=DEFAULT_VERSION):
    if mode != "consumer-after-db-commit" or (order_id is None) == (not next_event):
        raise ValueError("Use stream-fault consumer-after-db-commit --once and exactly one of --order-id <UUID> or --next-event.")
    if next_event:
        marker = "NEXT"
    else:
        try:
            marker = str(UUID(order_id))
        except (ValueError, AttributeError) as error:
            raise ValueError("Fault injection requires a valid order UUID.") from error
    script = (
        "mkdir -p /tmp/order-history-fault/armed /tmp/order-history-fault/fired; "
        "test ! -e /tmp/order-history-fault/fired/$1 || "
        "{ echo 'one-shot fault already consumed for this order' >&2; exit 2; }; "
        "test ! -e /tmp/order-history-fault/armed/$1 || "
        "{ echo 'one-shot fault already armed for this order' >&2; exit 2; }; "
        ": > /tmp/order-history-fault/armed/$1"
    )
    compose(["--profile", "streaming", "exec", "-T", "order-history", "sh", "-ec", script, "stream-fault", marker],
            project=project, version=version)
    target = "the next valid order event" if next_event else f"order {marker}"
    print(f"Armed one-shot crash after Order History commits {target} and before it commits the Kafka offset.")


def provision_local_identity(root=ROOT):
    credentials = load_credentials(root / "devops/.local/bootstrap.env")
    token_body = urlencode({
        "grant_type": "password", "client_id": "admin-cli",
        "username": "bootstrap-admin", "password": credentials["KEYCLOAK_ADMIN_PASSWORD"],
    }).encode()
    with urlopen(Request("http://127.0.0.1:8180/realms/master/protocol/openid-connect/token",
                        data=token_body, headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=15) as response:
        token = json.loads(response.read())["access_token"]
    base = "http://127.0.0.1:8180/admin/realms/supersports"

    def admin(method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        try:
            with urlopen(Request(base + path, data=data, headers=headers, method=method), timeout=15) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except HTTPError as error:
            with error:
                raw = error.read()
                return error.code, json.loads(raw) if raw else None

    status, role = admin("GET", "/roles/inventory-operator")
    if status == 404:
        status, _ = admin("POST", "/roles", {"name": "inventory-operator", "description": "May inspect and adjust local warehouse stock"})
        if status not in (201, 204):
            raise RuntimeError("Could not provision the inventory operator role in local Keycloak.")
        status, role = admin("GET", "/roles/inventory-operator")
    if status != 200:
        raise RuntimeError("Could not read the inventory operator role from local Keycloak.")
    status, users = admin("GET", "/users?username=inventory-operator&exact=true")
    if status != 200:
        raise RuntimeError("Could not inspect the inventory operator in local Keycloak.")
    if not users:
        status, _ = admin("POST", "/users", {
            "username": "inventory-operator", "enabled": True, "emailVerified": True,
            "firstName": "Synthetic", "lastName": "Inventory",
            "email": "inventory-operator@supersports.local",
            "credentials": [{"type": "password", "value": credentials["DEMO_INVENTORY_OPERATOR_PASSWORD"], "temporary": False}],
        })
        if status not in (201, 204):
            raise RuntimeError("Could not create the synthetic inventory operator in local Keycloak.")
        status, users = admin("GET", "/users?username=inventory-operator&exact=true")
    if status != 200 or not users:
        raise RuntimeError("Could not read the synthetic inventory operator in local Keycloak.")
    user_id = users[0]["id"]
    status, mappings = admin("GET", f"/users/{user_id}/role-mappings/realm")
    if status != 200:
        raise RuntimeError("Could not inspect inventory operator role mappings in local Keycloak.")
    if not any(item.get("name") == "inventory-operator" for item in mappings):
        status, _ = admin("POST", f"/users/{user_id}/role-mappings/realm", [role])
        if status not in (201, 204):
            raise RuntimeError("Could not assign the inventory operator role in local Keycloak.")
    status, scopes = admin("GET", "/client-scopes")
    basic = next((scope for scope in scopes or [] if scope.get("name") == "basic"), None)
    if status != 200 or basic is None:
        raise RuntimeError("Local Keycloak is missing its standard basic client scope.")
    for client_id in ("supersports-cli", "supersports-other-cli", "supersports-web"):
        status, clients = admin("GET", f"/clients?clientId={client_id}")
        if status != 200 or not clients:
            raise RuntimeError(f"Could not inspect local Keycloak client {client_id}.")
        client = clients[0]
        if "basic" not in client.get("defaultClientScopes", []):
            status, _ = admin("PUT", f"/clients/{client['id']}/default-client-scopes/{basic['id']}")
            if status not in (201, 204):
                raise RuntimeError(f"Could not attach the standard subject scope to {client_id}.")

    checkout_scopes = (
        "checkout:catalog.read", "checkout:configuration.read", "checkout:inventory.reserve",
        "checkout:inventory.protect", "checkout:inventory.commit", "checkout:inventory.release",
        "checkout:pricing.quote", "checkout:pricing.coupon.hold", "checkout:pricing.coupon.protect",
        "checkout:pricing.coupon.commit", "checkout:pricing.coupon.release",
        "checkout:payment.authorize", "checkout:payment.capture", "checkout:payment.status",
        "checkout:payment.void", "checkout:payment.refund", "checkout:fulfillment.schedule",
        "checkout:fulfillment.status",
    )
    status, existing_scopes = admin("GET", "/client-scopes")
    if status != 200:
        raise RuntimeError("Could not inspect local checkout scopes.")
    scopes_by_name = {scope.get("name"): scope for scope in existing_scopes or []}
    for scope_name in checkout_scopes:
        if scope_name not in scopes_by_name:
            status, _ = admin("POST", "/client-scopes", {"name": scope_name, "protocol": "openid-connect"})
            if status != 201:
                raise RuntimeError("Could not create a local checkout operation scope.")
            status, existing_scopes = admin("GET", "/client-scopes")
            if status != 200:
                raise RuntimeError("Could not read local checkout operation scopes.")
            scopes_by_name = {scope.get("name"): scope for scope in existing_scopes or []}
    status, checkout_clients = admin("GET", "/clients?clientId=supersports-checkout-worker")
    checkout_client = {"clientId": "supersports-checkout-worker", "name": "SuperSports local checkout worker",
        "enabled": True, "protocol": "openid-connect", "publicClient": False,
        "standardFlowEnabled": False, "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": True, "clientAuthenticatorType": "client-secret",
        "secret": credentials["CHECKOUT_WORKER_CLIENT_SECRET"],
        "defaultClientScopes": [], "protocolMappers": [{"name": "supersports-checkout-internal-api-audience",
            "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper",
            "config": {"included.custom.audience": "supersports-checkout-internal-api",
                "id.token.claim": "false", "access.token.claim": "true",
                "introspection.token.claim": "true"}}]}
    if status != 200:
        raise RuntimeError("Could not inspect the local checkout worker client.")
    if not checkout_clients:
        status, _ = admin("POST", "/clients", checkout_client)
        if status != 201:
            raise RuntimeError("Could not create the local checkout worker client.")
        status, checkout_clients = admin("GET", "/clients?clientId=supersports-checkout-worker")
    if status != 200 or len(checkout_clients) != 1:
        raise RuntimeError("Could not resolve the local checkout worker client.")
    checkout_client_id = checkout_clients[0]["id"]
    status, attached_scopes = admin("GET", f"/clients/{checkout_client_id}/default-client-scopes")
    if status != 200:
        raise RuntimeError("Could not inspect checkout worker scopes.")
    attached_names = {scope.get("name") for scope in attached_scopes or []}
    for scope_name in checkout_scopes:
        scope = scopes_by_name[scope_name]
        if scope_name not in attached_names:
            status, _ = admin("PUT", f"/clients/{checkout_client_id}/default-client-scopes/{scope['id']}")
            if status not in (201, 204):
                raise RuntimeError("Could not grant a checkout worker operation scope.")

    status, users = admin("GET", "/users?username=admin&exact=true")
    if status != 200:
        raise RuntimeError("Could not inspect the local admin account.")
    if not users:
        status, _ = admin("POST", "/users", {
            "username": "admin", "enabled": True, "emailVerified": True,
            "firstName": "Local", "lastName": "Admin", "email": "admin@supersports.local",
        })
        if status != 201:
            raise RuntimeError("Could not create the local admin account.")
        status, users = admin("GET", "/users?username=admin&exact=true")
    if status != 200 or len(users) != 1:
        raise RuntimeError("Could not resolve the local admin account.")
    status, _ = admin("PUT", f"/users/{users[0]['id']}/reset-password", {
        "type": "password", "value": configure_admin_login(root), "temporary": False,
    })
    if status != 204:
        raise RuntimeError("Could not synchronize the local admin password.")

    customer_base = "http://127.0.0.1:8180/admin/realms/supersports-customers"
    def customer_admin(method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        try:
            with urlopen(Request(customer_base + path, data=data, headers=headers, method=method), timeout=15) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except HTTPError as error:
            with error:
                raw = error.read()
                return error.code, json.loads(raw) if raw else None

    status, test_clients = customer_admin("GET", "/clients?clientId=supersports-customer-test")
    if status != 200:
        raise RuntimeError("Could not inspect the local customer integration client.")
    if not test_clients:
        status, _ = customer_admin("POST", "/clients", {
            "clientId": "supersports-customer-test", "name": "Local integration tests only",
            "enabled": True, "protocol": "openid-connect", "publicClient": True,
            "standardFlowEnabled": False, "directAccessGrantsEnabled": True,
            "implicitFlowEnabled": False,
            "protocolMappers": [{"name": "supersports-customer-test-api-audience",
                "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper",
                "config": {"included.custom.audience": "supersports-customer-api",
                    "id.token.claim": "false", "access.token.claim": "true",
                    "introspection.token.claim": "true"}}],
        })
        if status != 201:
            raise RuntimeError("Could not create the local customer integration client.")
    for username in ("checkout-test-customer", "checkout-test-customer-b"):
        status, users = customer_admin("GET", f"/users?username={username}&exact=true")
        if status != 200:
            raise RuntimeError("Could not inspect a local checkout test customer.")
        if not users:
            status, _ = customer_admin("POST", "/users", {
                "username": username, "enabled": True, "emailVerified": True,
                "firstName": "Checkout", "lastName": "Test",
                "email": username + "@supersports.local",
            })
            if status != 201:
                raise RuntimeError("Could not create a local checkout test customer.")
            status, users = customer_admin("GET", f"/users?username={username}&exact=true")
        if status != 200 or len(users) != 1:
            raise RuntimeError("Could not resolve a local checkout test customer.")
        status, _ = customer_admin("PUT", f"/users/{users[0]['id']}/reset-password", {
            "type": "password", "value": credentials["DEMO_CUSTOMER_PASSWORD"], "temporary": False,
        })
        if status != 204:
            raise RuntimeError("Could not synchronize a local checkout test customer password.")


def request_json(url: str, *, token: str | None = None, method: str = "GET", data=None, headers=None):
    request_headers = {"Accept": "application/json"}
    request_headers.update(headers or {})
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(url, data=data, headers=request_headers, method=method), timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        with error:
            body = error.read()
            return error.code, json.loads(body) if body else {}
    except (URLError, ConnectionError, TimeoutError, json.JSONDecodeError):
        return 0, {}


def wait_status(url: str, expected: int = 200, timeout: int = 120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, body = request_json(url)
        if status == expected:
            return body
        time.sleep(1)
    raise RuntimeError(f"Health check did not reach HTTP {expected}: {url}")


def unit(root=ROOT, project="supersports"):
    run([str(root / ".venv/bin/python"), "-m", "unittest", "discover",
         "-s", "devops/tests", "-p", "test_*.py", "-v"], cwd=root)
    image = json.loads((root / "devops/images.lock.json").read_text())["BUILD_IMAGE"]
    for service in (*SERVICES, *STREAMING_SERVICES):
        run([
            "docker", "run", "--rm",
            "--mount", f"type=bind,source={root / 'services' / service},target=/workspace",
            "--mount", f"type=volume,source={project}-maven-cache,target=/root/.m2",
            "--workdir", "/workspace", image, "mvn", "-B", "-ntp", "verify",
        ], cwd=root)


def integration(root=ROOT, project="supersports"):
    run([str(root / ".venv/bin/python"), str(root / "data/pipelines/catalog-fixtures/import.py")], cwd=root)
    environment = os.environ.copy()
    environment["SUPERSPORTS_PROJECT"] = validated_project_name(project)
    environment["SUPERSPORTS_INTEGRATION"] = "1"
    run([str(root / ".venv/bin/python"), "-m", "unittest", "discover",
         "-s", "devops/tests", "-p", "test_core_integration.py", "-v"],
        environment=environment, cwd=root)
    run([str(root / ".venv/bin/python"), "-m", "unittest", "discover",
         "-s", "devops/tests", "-p", "test_streaming_integration.py", "-v"],
        environment=environment, cwd=root)


def ui_test(root=ROOT):
    try:
        with urlopen("http://127.0.0.1:3000/healthz", timeout=5) as response:
            if response.status != 200 or response.read().decode().strip() != "ok":
                raise RuntimeError("Storefront health check returned an unexpected response.")
    except (URLError, TimeoutError) as error:
        raise RuntimeError("Storefront is not running; start it with devops/scripts/supersports up.") from error
    run([str(root / ".venv/bin/python"), "-m", "unittest", "discover",
         "-s", "apps/storefront/tests", "-p", "test_*.py", "-v"], cwd=root)


def recovery(root=ROOT, project="supersports"):
    credentials = load_credentials(root / "devops/.local/bootstrap.env")
    token = token_for("platform-admin", credentials["DEMO_PLATFORM_ADMIN_PASSWORD"])
    url = "http://127.0.0.1:8082/api/v1/configuration"
    before = request_json(url, token=token)
    if before[0] != 200:
        raise RuntimeError("Configuration snapshot is unavailable before recovery test.")
    compose(["restart", *SERVICES], root=root, project=project)
    for port in SERVICE_PORTS:
        wait_status(f"http://127.0.0.1:{port}/actuator/health/readiness")
    if request_json(url, token=token) != before:
        raise RuntimeError("Configuration changed unexpectedly across application restart.")
    print("PASS: configuration and migration state survive application restart")
    try:
        compose(["stop", "postgres"], root=root, project=project)
        for port in SERVICE_PORTS:
            wait_status(f"http://127.0.0.1:{port}/actuator/health/readiness", 503, timeout=45)
            wait_status(f"http://127.0.0.1:{port}/actuator/health/liveness", 200, timeout=15)
        print("PASS: database outage removes readiness without killing liveness")
    finally:
        compose(["start", "postgres"], root=root, project=project)
        for port in SERVICE_PORTS:
            wait_status(f"http://127.0.0.1:{port}/actuator/health/readiness", timeout=120)
    print("PASS: database reconnection restores readiness")
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            token_for("customer", credentials["DEMO_CUSTOMER_PASSWORD"])
            break
        except HTTPError as error:
            with error:
                if error.code < 500:
                    raise RuntimeError("Identity recovery failed authentication; credentials were not logged.") from None
        except (URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Identity token endpoint did not recover within 120 seconds.")
    print("PASS: identity token issuance recovers after database outage")
    integration(root, project)


def release_path(root: Path, project: str) -> Path:
    return root / "devops/.local" / f"releases-{validated_project_name(project)}.json"


def read_releases(root: Path, project: str) -> dict:
    path = release_path(root, project)
    return json.loads(path.read_text()) if path.exists() else {}


def record_release(root: Path, project: str, version: str, images: dict) -> None:
    validated_version(version)
    if set(images) != set(DEPLOYABLES) or not all(
        re.fullmatch(r"sha256:[0-9a-f]{64}", value) for value in images.values()
    ):
        raise ValueError("A release records exact image IDs for every application image.")
    releases = read_releases(root, project)
    if version in releases:
        raise ValueError("Release version is already recorded; choose a new version.")
    releases[version] = images
    path = release_path(root, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(releases, indent=2) + "\n")
    path.chmod(0o600)


def release(root=ROOT, project="supersports", version=None):
    version = validated_version(version or "")
    if version in read_releases(root, project):
        raise ValueError("Release already recorded; choose a new version.")
    compose(["build"], root=root, project=project, version=version)
    compose(["up", "-d", "--no-build", "--wait", "--wait-timeout", "180"],
            root=root, project=project, version=version)
    integration(root, project)
    images = {}
    for service in DEPLOYABLES:
        result = run(["docker", "image", "inspect", "--format", "{{.Id}}",
                      f"supersports/{service}:{version}"], capture=True)
        images[service] = result.stdout.strip()
    record_release(root, project, version, images)
    print(f"Recorded verified local release {version}; no publication performed.")


def rollback(root=ROOT, project="supersports", version=None):
    version = validated_version(version or "")
    releases = read_releases(root, project)
    if version not in releases:
        raise ValueError("Rollback requires a recorded, previously verified local release.")
    images = releases[version]
    for image in images.values():
        run(["docker", "image", "inspect", image], capture=True)
    compose(["up", "-d", "--no-build", "--wait", "--wait-timeout", "180"],
            root=root, project=project, version=version, images=images)
    integration(root, project)
    print(f"Rolled back to recorded image IDs for {version}; schema/data were not reverted.")


def doctor():
    if not shutil.which("docker"):
        raise RuntimeError("Docker is required.")
    result = run(["docker", "info", "--format", "{{.Architecture}} {{.MemTotal}} {{.ServerVersion}}"],
                 capture=True)
    architecture, memory, version = result.stdout.strip().split()
    print(f"Docker {version}; architecture {architecture}; allocated RAM {int(memory) / 1024**3:.2f} GiB")
    print(f"Python {sys.version.split()[0]}; repository virtual environment: {sys.prefix != sys.base_prefix}")
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Use the repository .venv interpreter.")
    if int(memory) < 4 * 1024**3:
        raise RuntimeError("Allocate at least 4 GiB to Docker for this bootstrap profile.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=[
        "doctor", "configure", "validate", "build", "up", "down", "status",
        "unit", "test", "reset", "release", "rollback",
        "ui-test", "streaming-up", "streaming-down", "stream-status", "stream-fault", "restart", "stream-demo-poison", "stream-replay", "stream-reconcile", "stream-rebuild",
    ])
    parser.add_argument("release_version", nargs="?")
    parser.add_argument("--project", default="supersports")
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--confirm-reset")
    parser.add_argument("--recovery", action="store_true")
    parser.add_argument("--order-id")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--next-event", action="store_true")
    parser.add_argument("--source-coordinate")
    parser.add_argument("--corrected-payload-file")
    parser.add_argument("--operation-id")
    parser.add_argument("--reason")
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--inject-reconciliation-mismatch",action="store_true")
    arguments = parser.parse_args(argv)
    try:
        project = validated_project_name(arguments.project)
        version = validated_version(arguments.version)
        action = arguments.action
        if action == "doctor":
            doctor()
            return 0
        if action == "reset":
            validate_reset(project, arguments.confirm_reset)
        configure()
        if action == "configure":
            print("Local credentials initialized/preserved; values are not printed.")
        elif action == "validate":
            compose(["config", "--quiet"], project=project, version=version)
            print("PASS: Compose configuration")
        elif action == "build":
            compose(["build"], project=project, version=version)
        elif action == "up":
            provision_databases(project=project, version=version)
            compose(["up", "-d", "--build", "--force-recreate", "--wait", "--wait-timeout", "180"],
                    project=project, version=version)
            provision_local_identity()
        elif action == "down":
            compose(["down"], project=project, version=version)
        elif action == "status":
            compose(["ps"], project=project, version=version)
        elif action == "unit":
            unit(project=project)
        elif action == "test":
            integration(project=project)
            if arguments.recovery:
                recovery(project=project)
        elif action == "ui-test":
            ui_test()
        elif action == "streaming-up":
            streaming_up(project=project, version=version)
        elif action == "streaming-down":
            compose(["--profile", "streaming", "stop", *STREAMING_SERVICES, "kafka-connect", "kafka"], project=project, version=version)
        elif action == "stream-status":
            streaming_status(project=project, version=version)
        elif action == "stream-fault":
            if not arguments.once:
                raise ValueError("Fault injection is one-shot; pass --once.")
            stream_fault(arguments.release_version, arguments.order_id, next_event=arguments.next_event,
                         project=project, version=version)
        elif action in ("stream-demo-poison", "stream-replay", "stream-rebuild", "stream-reconcile"):
            import stream_operations
            import projection_operations
            if action == "stream-reconcile":
                result=projection_operations.reconcile(sys.modules[__name__],project=project,version=version)
            else:
                with stream_operations.exclusive(sys.modules[__name__],project):
                    if action == "stream-demo-poison":
                        result = stream_operations.demo(sys.modules[__name__], project=project, version=version)
                    elif action == "stream-replay":
                        result = stream_operations.replay(sys.modules[__name__], arguments.source_coordinate,
                            arguments.corrected_payload_file, arguments.operation_id, arguments.reason, project=project, version=version)
                    else:
                        result=projection_operations.rebuild(sys.modules[__name__],project=project,version=version,
                            dry_run=arguments.dry_run,inject_mismatch=arguments.inject_reconciliation_mismatch)
            print(json.dumps(result, indent=2))
            if result.get("ok") is False:return 1
        elif action == "restart":
            service = arguments.release_version
            allowed = (*SERVICES, "kafka-connect", "kafka", *STREAMING_SERVICES)
            if service not in allowed:
                raise ValueError("Restart requires a known SuperSports service name.")
            compose(["--profile", "streaming", "restart", service], project=project, version=version)
        elif action == "reset":
            compose(["down", "--volumes", "--remove-orphans"], project=project, version=version)
            history_target_path(project=project).unlink(missing_ok=True)
            print(f"Removed {project} runtime volumes; local credentials and build cache preserved.")
        elif action == "release":
            release(project=project, version=arguments.release_version)
        elif action == "rollback":
            rollback(project=project, version=arguments.release_version)
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
