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
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SECRET_KEYS = (
    "POSTGRES_PASSWORD", "CATALOG_DB_PASSWORD", "CONFIGURATION_DB_PASSWORD",
    "IDENTITY_DB_PASSWORD", "PRICING_DB_PASSWORD", "INVENTORY_DB_PASSWORD", "CUSTOMER_DB_PASSWORD",
    "KEYCLOAK_ADMIN_PASSWORD", "DEMO_CUSTOMER_PASSWORD",
    "DEMO_PLATFORM_ADMIN_PASSWORD", "DEMO_CATALOG_ADMIN_PASSWORD", "DEMO_INVENTORY_OPERATOR_PASSWORD",
)
M02_SECRET_KEYS = (
    "POSTGRES_PASSWORD", "CATALOG_DB_PASSWORD", "CONFIGURATION_DB_PASSWORD",
    "IDENTITY_DB_PASSWORD", "KEYCLOAK_ADMIN_PASSWORD", "DEMO_CUSTOMER_PASSWORD",
    "DEMO_PLATFORM_ADMIN_PASSWORD", "DEMO_CATALOG_ADMIN_PASSWORD",
)
LEGACY_SECRET_KEYS = (*M02_SECRET_KEYS, "PRICING_DB_PASSWORD", "INVENTORY_DB_PASSWORD",
                      "DEMO_INVENTORY_OPERATOR_PASSWORD")
SERVICES = ("catalog", "configuration", "pricing", "inventory", "customer")
DEPLOYABLES = (*SERVICES, "storefront")
SERVICE_PORTS = (8081, 8082, 8083, 8084, 8085)
DEFAULT_VERSION = "s1-m04"
TOKEN_URL = "http://127.0.0.1:8180/realms/supersports/protocol/openid-connect/token"


def token_for(username: str, password: str, client: str = "supersports-cli") -> str:
    body = urlencode({"grant_type": "password", "client_id": client,
                      "username": username, "password": password}).encode()
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
            if set(existing) not in (set(M02_SECRET_KEYS), set(LEGACY_SECRET_KEYS)):
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


def deployment_env(root: Path, version: str = DEFAULT_VERSION, images: dict | None = None) -> dict:
    environment = os.environ.copy()
    environment.update(load_credentials(root / "devops/.local/bootstrap.env"))
    lock = json.loads((root / "devops/images.lock.json").read_text())
    for key in ("BUILD_IMAGE", "JAVA_IMAGE", "POSTGRES_IMAGE", "KEYCLOAK_IMAGE"):
        environment[key] = lock[key]
    for key in ("STOREFRONT_NODE_IMAGE", "STOREFRONT_NGINX_IMAGE"):
        environment[key] = lock[key]
    environment["RELEASE_VERSION"] = validated_version(version)
    for service in DEPLOYABLES:
        environment[f"{service.upper()}_IMAGE"] = (
            images[service] if images else f"supersports/{service}:{version}"
        )
    return environment


def run(command: list[str], *, environment=None, capture=False, check=True, cwd=ROOT):
    result = subprocess.run(
        command, cwd=cwd, env=environment, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None, check=False,
    )
    if check and result.returncode:
        # Never include the environment, token bodies or command arguments in an exception.
        raise RuntimeError(f"Operation failed with exit {result.returncode}; inspect the service status/logs.")
    return result


def compose(arguments: list[str], *, root=ROOT, project="supersports",
            version=DEFAULT_VERSION, images=None, capture=False, check=True):
    return run(compose_command(root, project, arguments),
               environment=deployment_env(root, version, images),
               capture=capture, check=check, cwd=root)


def provision_databases(root=ROOT, project="supersports", version=DEFAULT_VERSION):
    compose(["up", "-d", "postgres", "--wait", "--wait-timeout", "120"],
            root=root, project=project, version=version)
    command = compose_command(root, project, ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1"])
    command.extend(["-f", "/opt/supersports/provision.sql"])
    run(command, cwd=root)


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


def request_json(url: str, *, token: str | None = None, method: str = "GET", data=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=5) as response:
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
         "-s", "devops/tests", "-p", "test_manage.py", "-v"], cwd=root)
    image = json.loads((root / "devops/images.lock.json").read_text())["BUILD_IMAGE"]
    for service in SERVICES:
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
        "ui-test",
    ])
    parser.add_argument("release_version", nargs="?")
    parser.add_argument("--project", default="supersports")
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--confirm-reset")
    parser.add_argument("--recovery", action="store_true")
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
        elif action == "reset":
            compose(["down", "--volumes", "--remove-orphans"], project=project, version=version)
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
