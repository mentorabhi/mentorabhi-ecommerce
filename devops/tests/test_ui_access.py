"""Focused U1 tests: no Docker daemon, HTTP server or live accounts."""
from pathlib import Path
import base64
import hashlib
import os
import sys
import tempfile
import unittest
from contextlib import nullcontext, redirect_stdout, redirect_stderr
from types import SimpleNamespace
from io import StringIO
from urllib.error import HTTPError
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ui_access as ui


class PrivateFileTests(unittest.TestCase):
    def test_repairs_stale_file_and_loose_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / "devops/.local"
            local.mkdir(parents=True)
            path = local / "ui.htpasswd"
            path.write_text("admin:old\n")
            path.chmod(0o644)
            ui.basic_auth_file(root)
            self.assertTrue(path.read_text().startswith("admin:{SSHA}"))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(local.glob(".ui-auth-*")), [])

    def test_auth_file_is_private_ignored_location_and_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "devops").mkdir()
            path = ui.basic_auth_file(root)
            before = path.read_bytes()
            inode = path.stat().st_ino
            self.assertEqual(path, root / "devops/.local/ui.htpasswd")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(ui.basic_auth_file(root).read_bytes(), before)
            self.assertEqual(path.stat().st_ino, inode)
            encoded = before.decode().strip().removeprefix("admin:{SSHA}")
            raw = base64.b64decode(encoded)
            self.assertEqual(raw[:20], hashlib.sha1(b"admin" + raw[20:]).digest())
            self.assertGreaterEqual(len(raw[20:]), 16)

    def test_refuses_symlink_directory_and_file_without_touching_target(self):
        for link_directory in (True, False):
            with self.subTest(directory=link_directory), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "devops").mkdir()
                outside = root / "outside"
                outside.mkdir()
                target = outside / "private"
                target.write_text("untouched")
                local = root / "devops/.local"
                if link_directory:
                    local.symlink_to(outside, target_is_directory=True)
                else:
                    local.mkdir()
                    (local / "ui.htpasswd").symlink_to(target)
                with self.assertRaises(ui.AccessError):
                    ui.basic_auth_file(root)
                self.assertEqual(target.read_text(), "untouched")

    def test_refuses_hardlink_without_chmod_or_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / "devops/.local"
            local.mkdir(parents=True)
            target = root / "outside"
            target.write_text("untouched")
            os.link(target, local / "ui.htpasswd")
            before = target.stat().st_mode
            with self.assertRaises(ui.AccessError):
                ui.basic_auth_file(root)
            self.assertEqual(target.read_text(), "untouched")
            self.assertEqual(target.stat().st_mode, before)

    def test_bootstrap_read_refuses_symlink_and_does_not_rewrite_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / "devops/.local"
            local.mkdir(parents=True)
            source = root / "source"
            source.write_text("KEYCLOAK_ADMIN_PASSWORD=opaque-test-secret\n")
            (local / "bootstrap.env").symlink_to(source)
            with self.assertRaises(ui.AccessError):
                ui.bootstrap_secret(root, "KEYCLOAK_ADMIN_PASSWORD")
            (local / "bootstrap.env").unlink()
            (local / "bootstrap.env").write_bytes(source.read_bytes())
            self.assertEqual(ui.bootstrap_secret(root, "KEYCLOAK_ADMIN_PASSWORD"), "opaque-test-secret")
            self.assertEqual((local / "bootstrap.env").read_bytes(), source.read_bytes())


class KeycloakServer:
    """Stateful boundary fake records realm, account, password and role effects."""
    def __init__(self, existing=False):
        self.user = {"id": "u1", "username": "admin", "enabled": False,
                     "requiredActions": ["UPDATE_PASSWORD"]} if existing else None
        self.password = "old" if existing else None
        self.roles = []
        self.created = 0
        self.paths = []

    def __call__(self, method, url, body=None, headers=None, form=False):
        self.paths.append(url)
        if url.endswith("/token"):
            if body["username"] == "admin" and self.password != "admin":
                raise ui.AccessError("login failed", 401)
            return {"access_token": body["username"]}
        if url.endswith("/users?username=admin&exact=true"):
            return [dict(self.user)] if self.user else []
        if url.endswith("/users") and method == "POST":
            self.created += 1
            self.user = {"id": "u1", **body}
            return None
        if url.endswith("/roles/admin"):
            return {"id": "role1", "name": "admin"}
        if url.endswith("/role-mappings/realm"):
            if method == "POST":
                self.roles.extend(body)
            return list(self.roles)
        if url.endswith("/reset-password"):
            self.password = body["value"]
            self.temporary = body["temporary"]
            return None
        if url.endswith("/users/u1") and method == "PUT":
            self.user.update(body)
            return None
        raise AssertionError((method, url))


class ProvisionTests(unittest.TestCase):
    def test_explicit_stopped_optional_service_fails_without_provisioning(self):
        with patch.object(ui, "running_container", return_value=None), patch.object(ui, "neo4j") as provision, redirect_stdout(StringIO()) as output:
            result = ui.main(["--only", "neo4j"])
        self.assertEqual(result, 1)
        self.assertIn("unavailable", output.getvalue())
        provision.assert_not_called()

    def test_cli_suppresses_exception_contents(self):
        with patch.object(ui, "running_container", side_effect=ui.AccessError("private-service-secret")), redirect_stderr(StringIO()) as output:
            result = ui.main(["--only", "grafana"])
        self.assertEqual(result, 1)
        self.assertNotIn("private-service-secret", output.getvalue())
        self.assertIn("FAILED", output.getvalue())

    def test_http_error_does_not_disclose_request_or_response_secrets(self):
        opener = SimpleNamespace(open=lambda *a, **k: (_ for _ in ()).throw(
            HTTPError("http://127.0.0.1", 401, "private-response", {}, StringIO("private-token"))))
        with patch.object(ui, "build_opener", return_value=opener):
            with self.assertRaises(ui.AccessError) as caught:
                ui.request("POST", "http://127.0.0.1:8180/token", {"password": "private-password"})
        self.assertEqual(str(caught.exception), "Local UI request failed (HTTP 401).")

    def test_http_refuses_non_loopback_before_sending_credentials(self):
        with patch.object(ui, "build_opener") as opener:
            with self.assertRaises(ui.AccessError):
                ui.request("POST", "https://example.com", {"password": "private-password"})
        opener.assert_not_called()

    def test_master_creation_and_repeat_do_not_duplicate_users_or_roles(self):
        server = KeycloakServer()
        with patch.object(ui, "request", server):
            ui.keycloak("bootstrap-secret")
            ui.keycloak("bootstrap-secret")
        self.assertEqual(server.created, 1)
        self.assertEqual(len(server.roles), 1)
        self.assertFalse(server.temporary)
        self.assertTrue(server.user["enabled"])
        self.assertEqual(server.user["requiredActions"], [])
        self.assertTrue(all("/master/" in p for p in server.paths))

    def test_existing_master_account_is_repaired_without_creation(self):
        server = KeycloakServer(existing=True)
        with patch.object(ui, "request", server):
            ui.keycloak("bootstrap-secret")
        self.assertEqual(server.created, 0)
        self.assertEqual(server.password, "admin")
        self.assertEqual(server.user["requiredActions"], [])

    def test_grafana_valid_admin_does_not_reset_password(self):
        with patch.object(ui, "request", return_value={"login": "admin", "isGrafanaAdmin": True}), patch.object(ui, "execute") as execute:
            ui.grafana("container")
        execute.assert_not_called()

    def test_grafana_auth_failure_resets_native_identity_then_verifies(self):
        with patch.object(ui, "request", side_effect=[ui.AccessError("auth", 401), {"login": "admin", "isGrafanaAdmin": True}]), patch.object(ui, "execute") as execute:
            ui.grafana("container")
        self.assertIn("reset-admin-password", execute.call_args.args[0])

    def test_grafana_network_error_does_not_reset_password(self):
        with patch.object(ui, "request", side_effect=ui.AccessError("unavailable")), patch.object(ui, "execute") as execute:
            with self.assertRaises(ui.AccessError):
                ui.grafana("container")
        execute.assert_not_called()

    def test_neo4j_create_repair_repeat_preserves_service_password(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                accounts = {"neo4j": "private-service-password"}
                if existing:
                    accounts["admin"] = "old-password"
                writes = []
                def api(method, url, body=None, headers=None, form=False):
                    self.assertEqual(url, "http://127.0.0.1:7474/db/system/query/v2")
                    user, password = base64.b64decode(headers["Authorization"].split()[1]).decode().split(":")
                    if accounts.get(user) != password:
                        raise ui.AccessError("auth", 401)
                    statement = body["statement"]
                    if statement == "SHOW CURRENT USER":
                        return {"data": {"fields": ["user", "passwordChangeRequired"], "values": [[user, False]]}}
                    if statement == "SHOW USERS":
                        return {"data": {"fields": ["user"], "values": [[name] for name in accounts]}}
                    writes.append(statement)
                    accounts["admin"] = body["parameters"]["password"]
                    return {}
                with patch.object(ui, "request", api):
                    ui.neo4j("private-service-password")
                    ui.neo4j("private-service-password")
                self.assertEqual(accounts, {"neo4j": "private-service-password", "admin": "admin"})
                self.assertEqual(len(writes), 1)
                self.assertTrue(writes[0].startswith("ALTER" if existing else "CREATE"))

    def test_neo4j_first_login_clears_flag_without_reusing_same_password(self):
        state = {"required": True}
        def api(method, url, body=None, headers=None, form=False):
            user, password = base64.b64decode(headers["Authorization"].split()[1]).decode().split(":")
            statement = body["statement"]
            if user == "admin":
                self.assertEqual(password, "admin")
                if state["required"]:
                    raise ui.AccessError("change required", 403)
                return {"data": {"fields": ["user", "passwordChangeRequired"], "values": [["admin", False]]}}
            self.assertEqual(password, "private-service-password")
            if statement == "SHOW USERS":
                return {"data": {"fields": ["user", "passwordChangeRequired"], "values": [["admin", True]]}}
            self.assertEqual(statement, "ALTER USER admin SET PASSWORD CHANGE NOT REQUIRED")
            state["required"] = False
            return {}
        with patch.object(ui, "request", api):
            ui.neo4j("private-service-password")
            ui.neo4j("private-service-password")
        self.assertFalse(state["required"])

    def test_superset_native_script_create_repair_repeat(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                role = object()
                state = {"user": SimpleNamespace(password="hash:old", roles=[], active=False) if existing else None,
                         "creates": 0, "updates": 0}
                def add_user(*args, **kwargs):
                    state["creates"] += 1
                    state["user"] = SimpleNamespace(password="hash:" + kwargs["password"], roles=[args[4]], active=True)
                    return state["user"]
                def update_user(user):
                    state["updates"] += 1
                    # FAB 5.0.2 returns None on successful update.
                sm = SimpleNamespace(find_role=lambda name: role, find_user=lambda **kw: state["user"],
                                     add_user=add_user, update_user=update_user)
                modules = {"superset": SimpleNamespace(security_manager=sm),
                           "superset.app": SimpleNamespace(create_app=lambda: SimpleNamespace(app_context=nullcontext)),
                           "werkzeug.security": SimpleNamespace(check_password_hash=lambda h, p: h == "hash:" + p,
                                                               generate_password_hash=lambda p: "hash:" + p)}
                with patch.dict(sys.modules, modules):
                    exec(ui.SUPERSET_PROVISION, {})
                    exec(ui.SUPERSET_PROVISION, {})
                self.assertEqual(state["creates"], 0 if existing else 1)
                self.assertEqual(state["updates"], 1 if existing else 0)
                self.assertEqual(state["user"].password, "hash:admin")
                self.assertEqual(state["user"].roles, [role])
                self.assertTrue(state["user"].active)


if __name__ == "__main__":
    unittest.main()
