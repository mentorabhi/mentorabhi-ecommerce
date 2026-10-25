"""S1-M11 local human UI credentials. No service lifecycle operations.

Run explicitly with .venv/bin/python; importing this module has no side effects.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]


class AccessError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an infrastructure password or bearer token elsewhere.
        return None


def request(method, url, body=None, headers=None, form=False):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username:
        raise AccessError("Only explicit loopback HTTP endpoints are supported.")
    headers = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = (urlencode(body) if form else json.dumps(body)).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
    try:
        # Ignore HTTP_PROXY/HTTPS_PROXY; credentials must stay on this host.
        with build_opener(ProxyHandler({}), NoRedirect()).open(
            Request(url, data=data, headers=headers, method=method), timeout=15
        ) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except HTTPError as error:
        status = error.code
        error.close()
        raise AccessError(f"Local UI request failed (HTTP {status}).", status) from None
    except (URLError, OSError, ValueError):
        raise AccessError("Local UI request unavailable or returned invalid JSON.") from None


def private_directory(root):
    path = root / "devops/.local"
    if path.is_symlink():
        raise AccessError("Refusing symlinked local state directory.")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


def read_private(path, tighten_mode=False):
    """Read a regular, singly linked file without following a final symlink."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "r") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise AccessError("Refusing non-regular or multiply linked local file.")
            if tighten_mode:
                os.fchmod(handle.fileno(), 0o600)
            return handle.read()
    except OSError:
        raise AccessError("Cannot read private local file; missing or unsafe path.") from None


def bootstrap_secret(root, key):
    local = root / "devops/.local"
    if local.is_symlink():
        raise AccessError("Refusing symlinked local state directory.")
    values = {}
    for line in read_private(local / "bootstrap.env").splitlines():
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.partition("=")
        if not sep or name in values:
            raise AccessError("Malformed local bootstrap file; preserved unchanged.")
        values[name] = value
    if not values.get(key):
        raise AccessError("Required local bootstrap credential is missing.")
    return values[key]


def basic_auth_file(root=ROOT):
    """Nginx-supported salted SHA-1, using only Python's standard library.

    SSHA is for this explicit local demo password, not production password storage.
    Atomic replacement also repairs stale/default credentials on existing setups.
    """
    directory = private_directory(root)
    path = directory / "ui.htpasswd"
    current = read_private(path, tighten_mode=True) if path.exists() or path.is_symlink() else ""
    valid = False
    try:
        if current.startswith("admin:{SSHA}") and current.count("\n") == 1:
            raw = base64.b64decode(current.strip()[12:], validate=True)
            valid = len(raw) >= 36 and secrets.compare_digest(
                raw[:20], hashlib.sha1(b"admin" + raw[20:]).digest())
    except ValueError:
        pass
    if valid:
        return path
    salt = secrets.token_bytes(16)
    digest = base64.b64encode(hashlib.sha1(b"admin" + salt).digest() + salt).decode()
    current = f"admin:{{SSHA}}{digest}\n"
    fd, temporary = tempfile.mkstemp(prefix=".ui-auth-", dir=directory)
    try:
        with os.fdopen(fd, "w") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(current)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


def basic(user, password):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


def keycloak(password):
    base = "http://127.0.0.1:8180"

    def token(username, secret):
        return request("POST", base + "/realms/master/protocol/openid-connect/token", {
            "grant_type": "password", "client_id": "admin-cli",
            "username": username, "password": secret}, form=True)["access_token"]

    headers = {"Authorization": "Bearer " + token("bootstrap-admin", password)}
    realm = base + "/admin/realms/master"

    def api(method, path, body=None):
        return request(method, realm + path, body, headers)

    users = api("GET", "/users?username=admin&exact=true")
    profile = {"username": "admin", "enabled": True, "requiredActions": [],
               "firstName": "Local", "lastName": "Admin", "email": "admin@localhost",
               "emailVerified": True}
    if not users:
        try:
            api("POST", "/users", profile)
        except AccessError as error:
            if error.status != 409:
                raise
        users = api("GET", "/users?username=admin&exact=true")
    if len(users) != 1 or users[0]["username"] != "admin":
        raise AccessError("Cannot uniquely locate master UI admin.")
    path = "/users/" + quote(users[0]["id"], safe="")
    api("PUT", path, profile)
    api("PUT", path + "/reset-password", {"type": "password", "value": "admin", "temporary": False})
    role = api("GET", "/roles/admin")
    roles = api("GET", path + "/role-mappings/realm")
    if not any(r["id"] == role["id"] for r in roles):
        api("POST", path + "/role-mappings/realm", [role])
    # Authentication plus an authorized admin API call, not token issuance alone.
    verified = request("GET", realm + path + "/role-mappings/realm", headers={
        "Authorization": "Bearer " + token("admin", "admin")})
    if not any(r["id"] == role["id"] for r in verified):
        raise AccessError("Master admin role verification failed.")


def execute(arguments, input_text=None):
    try:
        result = subprocess.run(arguments, input=input_text, text=True,
                                capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise AccessError("Local container operation unavailable or timed out.") from None
    if result.returncode:
        # Container output can contain tokens, connection URIs and environment values.
        raise AccessError("Local container operation failed; output suppressed.")
    return result.stdout


def running_container(service):
    output = execute(["docker", "ps", "--filter", "label=com.docker.compose.project=supersports",
                      "--filter", f"label=com.docker.compose.service={service}", "--format", "{{.ID}}"])
    ids = output.split()
    if len(ids) > 1:
        raise AccessError("Expected one local UI container.")
    return ids[0] if ids else None


def grafana(container):
    def verify():
        user = request("GET", "http://127.0.0.1:3001/api/user", headers=basic("admin", "admin"))
        if user.get("login") != "admin" or not user.get("isGrafanaAdmin"):
            raise AccessError("Grafana account is not the expected server admin.")
    try:
        verify()
        return
    except AccessError as error:
        if error.status != 401:
            raise
    # The existing Compose installation's initial server administrator has id 1.
    execute(["docker", "exec", container, "grafana", "cli", "--homepath", "/usr/share/grafana",
             "--config", "/etc/grafana/grafana.ini", "--configOverrides",
             "cfg:default.paths.data=/var/lib/grafana", "admin", "reset-admin-password", "admin"])
    verify()


def neo4j(password):
    def query(statement, user="neo4j", secret=password, parameters=None):
        result = request("POST", "http://127.0.0.1:7474/db/system/query/v2",
                         {"statement": statement, "parameters": parameters or {}}, basic(user, secret))
        if result.get("errors"):
            raise AccessError("Neo4j query failed; ensure minimum password length is 5.")
        return result
    # Avoid ALTER on an already correct password (Neo4j rejects unchanged passwords).
    try:
        result = query("SHOW CURRENT USER", "admin", "admin")
    except AccessError as error:
        if error.status not in (401, 403):
            raise
    else:
        fields = result["data"]["fields"]
        row = dict(zip(fields, result["data"]["values"][0]))
        if row.get("user") == "admin" and row.get("passwordChangeRequired") is False:
            return
    users = query("SHOW USERS")
    rows = [dict(zip(users["data"]["fields"], row)) for row in users["data"]["values"]]
    names = [row["user"] for row in rows]
    if any(row["user"] == "admin" and row.get("passwordChangeRequired") for row in rows):
        query("ALTER USER admin SET PASSWORD CHANGE NOT REQUIRED")
        try:
            query("SHOW CURRENT USER", "admin", "admin")
            return
        except AccessError as error:
            if error.status != 401:
                raise
    statement = ("ALTER USER admin SET PASSWORD $password CHANGE NOT REQUIRED" if "admin" in names
                 else "CREATE USER admin SET PASSWORD $password CHANGE NOT REQUIRED")
    query(statement, parameters={"password": "admin"})
    result = query("SHOW CURRENT USER", "admin", "admin")
    row = dict(zip(result["data"]["fields"], result["data"]["values"][0]))
    if row.get("user") != "admin" or row.get("passwordChangeRequired") is not False:
        raise AccessError("Neo4j UI account verification failed.")


SUPERSET_PROVISION = '''
from superset.app import create_app
from superset import security_manager as sm
from werkzeug.security import check_password_hash, generate_password_hash
app = create_app()
with app.app_context():
    role = sm.find_role("Admin")
    if role is None:
        raise RuntimeError("Initialize Superset roles first")
    user = sm.find_user(username="admin")
    if user is None:
        user = sm.add_user("admin", "Super", "Sports", "admin@localhost", role, password="admin")
        if not user:
            raise RuntimeError("Cannot create UI account")
    else:
        changed = False
        if not check_password_hash(user.password, "admin"):
            user.password = generate_password_hash("admin")
            changed = True
        if not user.active:
            user.active = True
            changed = True
        if role not in user.roles:
            user.roles.append(role)
            changed = True
        if changed and sm.update_user(user) is False:
            raise RuntimeError("Cannot update UI account")
    if not check_password_hash(user.password, "admin") or role not in user.roles or not user.active:
        raise RuntimeError("UI account verification failed")
'''


def superset(container):
    execute(["docker", "exec", "-i", container, "python", "-"], SUPERSET_PROVISION)
    result = request("POST", "http://127.0.0.1:8095/api/v1/security/login", {
        "username": "admin", "password": "admin", "provider": "db", "refresh": False})
    if not result.get("access_token"):
        raise AccessError("Superset native login verification failed.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=("basic-auth", "keycloak", "grafana", "neo4j", "superset"))
    args = parser.parse_args(argv)
    failed = False
    for name in ([args.only] if args.only else ["basic-auth", "keycloak", "grafana", "neo4j", "superset"]):
        try:
            if name == "basic-auth":
                basic_auth_file()
                print("basic-auth: private file ready; proxy wiring/HTTP verification pending")
                continue
            container = running_container("identity" if name == "keycloak" else name)
            if not container:
                print(f"{name}: unavailable (not running); no lifecycle action taken")
                failed = failed or name == "keycloak" or bool(args.only)
                continue
            if name == "keycloak":
                keycloak(bootstrap_secret(ROOT, "KEYCLOAK_ADMIN_PASSWORD"))
            elif name == "neo4j":
                neo4j(bootstrap_secret(ROOT, "GRAPH_DB_PASSWORD"))
            elif name == "grafana":
                grafana(container)
            else:
                superset(container)
            print(f"{name}: native admin login verified")
        except (AccessError, KeyError, IndexError, TypeError, ValueError, OSError):
            # Never render exception bodies, subprocess output, request data or tokens.
            print(f"{name}: FAILED; check local availability/configuration and ui-access.md", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
