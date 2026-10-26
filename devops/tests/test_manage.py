"""Unit tests for local bootstrap behavior; no Docker daemon required."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "devops/scripts"))
spec = importlib.util.spec_from_file_location("supersports_manage", ROOT / "devops/scripts/manage.py")
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class ConfigureTests(unittest.TestCase):
    def test_local_admin_login_is_separate_private_and_persistent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "devops/.local/admin-login.env"
            self.assertEqual(manage.configure_admin_login(root), path.read_text().strip().partition("=")[2])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.write_text("ADMIN_PASSWORD=admin\n")
            self.assertEqual(manage.configure_admin_login(root), "admin")
            self.assertEqual(path.read_text(), "ADMIN_PASSWORD=admin\n")

    def test_local_admin_login_refuses_symlinked_password_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / "devops/.local"
            local.mkdir(parents=True)
            external = root / "external"
            external.write_text("ADMIN_PASSWORD=admin\n")
            (local / "admin-login.env").symlink_to(external)
            with self.assertRaises(ValueError):
                manage.configure_admin_login(root)
            self.assertEqual(external.read_text(), "ADMIN_PASSWORD=admin\n")

    def test_configure_generates_private_credentials_without_printing_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = StringIO()
            with redirect_stdout(output):
                path = manage.configure(root)
            values = manage.load_credentials(path)
            self.assertEqual(set(values), set(manage.SECRET_KEYS))
            self.assertEqual(len(set(values.values())), len(values))
            self.assertTrue(all(len(value) >= 32 for value in values.values()))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertTrue(all(value not in output.getvalue() for value in values.values()))

    def test_configure_preserves_existing_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = manage.configure(root)
            before = path.read_bytes()
            manage.configure(root)
            self.assertEqual(before, path.read_bytes())

    def test_configure_extends_known_m03_credentials_without_rotating_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = manage.configure(root)
            values = manage.load_credentials(path)
            old = {key: values[key] for key in manage.LEGACY_SECRET_KEYS}
            path.write_text("\n".join(f"{key}={value}" for key, value in old.items()) + "\n")
            manage.configure(root)
            extended = manage.load_credentials(path)
            self.assertEqual({key: extended[key] for key in old}, old)
            self.assertEqual(set(extended), set(manage.SECRET_KEYS))

    def test_configure_extends_known_m02_credentials_without_rotating_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = manage.configure(root)
            values = manage.load_credentials(path)
            old = {key: values[key] for key in manage.M02_SECRET_KEYS}
            path.write_text("\n".join(f"{key}={value}" for key, value in old.items()) + "\n")
            manage.configure(root)
            extended = manage.load_credentials(path)
            self.assertEqual({key: extended[key] for key in old}, old)
            self.assertEqual(set(extended), set(manage.SECRET_KEYS))

    def test_configure_extends_known_m06_credentials_without_rotating_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = manage.configure(root)
            values = manage.load_credentials(path)
            old = {key: values[key] for key in manage.PRE_M07_SECRET_KEYS}
            path.write_text("\n".join(f"{key}={value}" for key, value in old.items()) + "\n")
            manage.configure(root)
            extended = manage.load_credentials(path)
            self.assertEqual({key: extended[key] for key in old}, old)
            self.assertEqual(set(extended), set(manage.SECRET_KEYS))

    def test_customer_realm_is_self_registration_only_with_its_own_api_audience(self):
        realm = json.loads((ROOT / "devops/identity/supersports-customers-realm.json").read_text())
        self.assertEqual(realm["realm"], "supersports-customers")
        self.assertTrue(realm["registrationAllowed"])
        client = next(client for client in realm["clients"] if client["clientId"] == "supersports-customer-web")
        self.assertEqual(client["clientId"], "supersports-customer-web")
        self.assertFalse(client["directAccessGrantsEnabled"])
        audiences = [mapper["config"]["included.custom.audience"] for mapper in client["protocolMappers"]]
        self.assertEqual(audiences, ["supersports-customer-api"])
        self.assertNotIn("supersports-api", audiences)
        test_client = next(client for client in realm["clients"] if client["clientId"] == "supersports-customer-test")
        self.assertTrue(test_client["directAccessGrantsEnabled"])
        self.assertEqual(test_client["name"], "Local integration tests only")

    def test_incomplete_existing_credentials_are_rejected_not_rotated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = manage.configure(root)
            path.write_text("POSTGRES_PASSWORD=existing\n")
            with self.assertRaises(ValueError):
                manage.configure(root)
            self.assertEqual(path.read_text(), "POSTGRES_PASSWORD=existing\n")

    def test_configure_refuses_symlinked_secret_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / "devops/.local"
            local.mkdir(parents=True)
            external = root / "external"
            external.write_text("unchanged")
            (local / "bootstrap.env").symlink_to(external)
            with self.assertRaises(ValueError):
                manage.configure(root)
            self.assertEqual(external.read_text(), "unchanged")


class CommandTests(unittest.TestCase):
    def test_graph_down_includes_kafka_dependency_profile(self):
        from unittest.mock import patch
        with patch.object(manage, "configure"), patch.object(manage, "compose") as compose:
            self.assertEqual(manage.main(["graph-down"]), 0)
        arguments = compose.call_args.args[0]
        self.assertIn("--profile", arguments)
        self.assertIn("streaming", arguments)
        self.assertEqual(arguments[-2:], ["neo4j", "relationship-graph"])

    def test_dockerignore_includes_graph_project_and_shared_event_contract(self):
        dockerignore=(ROOT/".dockerignore").read_text().splitlines()
        self.assertIn("!services/relationship-graph/",dockerignore)
        self.assertIn("!services/relationship-graph/**",dockerignore)
        self.assertIn("!contracts/",dockerignore)
        self.assertIn("!contracts/order_events.py",dockerignore)

    def test_active_history_target_is_persisted_and_validates_database_group_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(manage.history_target(root),{"database":"order_history","group":"order-history-v1"})
            target={"database":"order_history_r_012345abcdef","group":"order-history-r-012345abcdef"}
            manage.set_history_target(target,root=root)
            self.assertEqual(manage.history_target(root),target)
            self.assertEqual(manage.history_target_path(root).stat().st_mode & 0o777,0o600)
            for invalid in ({"database":"orders","group":"order-history-v1"},
                            {"database":"order_history_r_012345abcdef","group":"order-history-r-ffffffffffff"}):
                with self.assertRaises(ValueError):manage.set_history_target(invalid,root=root)
            self.assertEqual(manage.history_target(root),target)

    def test_up_recreates_services_from_the_latest_built_images(self):
        from unittest.mock import patch
        with patch.object(manage, "provision_databases"), \
             patch.object(manage, "provision_local_identity"), \
             patch.object(manage, "compose") as compose:
            self.assertEqual(manage.main(["up"]), 0)
        arguments = next(call.args[0] for call in compose.call_args_list
                         if call.args[0][0] == "up" and "--build" in call.args[0])
        self.assertIn("--force-recreate", arguments)

    def test_project_names_stay_in_supersports_namespace(self):
        self.assertEqual(manage.validated_project_name("supersports"), "supersports")
        self.assertEqual(manage.validated_project_name("supersports-regression"), "supersports-regression")
        for name in ("other-project", "../supersports", "supersports;rm", "", "SUPERSPORTS"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                manage.validated_project_name(name)

    def test_reset_requires_exact_project_confirmation(self):
        manage.validate_reset("supersports-regression", "supersports-regression")
        for confirmation in (None, "supersports", "yes"):
            with self.subTest(confirmation=confirmation), self.assertRaises(ValueError):
                manage.validate_reset("supersports-regression", confirmation)

    def test_compose_command_is_explicit_and_independent_of_working_directory(self):
        root = Path("/tmp/project with spaces")
        command = manage.compose_command(root, "supersports", ["config", "--quiet"])
        self.assertEqual(command[:2], ["docker", "compose"])
        self.assertIn(str(root), command)
        self.assertIn(str(root / "devops/compose/core.yaml"), command)
        self.assertIn(str(root / "devops/.local/bootstrap.env"), command)
        self.assertEqual(command[-2:], ["config", "--quiet"])

    def test_release_names_cannot_be_shell_or_path_fragments(self):
        self.assertEqual(manage.validated_version("s1-m02-v1"), "s1-m02-v1")
        for version in ("../v1", "v1;echo", "latest tag", ""):
            with self.subTest(version=version), self.assertRaises(ValueError):
                manage.validated_version(version)

    def test_stream_fault_requires_known_target_one_shot_and_order_uuid(self):
        from unittest.mock import patch
        with self.assertRaises(ValueError):
            manage.stream_fault("unknown", "00000000-0000-0000-0000-000000000001")
        with self.assertRaises(ValueError):
            manage.stream_fault("consumer-after-db-commit", "not-a-uuid")
        with patch.object(manage, "compose") as compose:
            manage.stream_fault("consumer-after-db-commit", "00000000-0000-0000-0000-000000000001")
        command = compose.call_args.args[0]
        self.assertEqual(command[0:3], ["--profile", "streaming", "exec"])
        self.assertIn("/tmp/order-history-fault/armed/$1", command[-3])
        self.assertEqual(command[-1], "00000000-0000-0000-0000-000000000001")

    def test_stream_fault_can_arm_the_next_valid_order_event(self):
        from unittest.mock import patch
        with patch.object(manage, "compose") as compose:
            manage.stream_fault("consumer-after-db-commit", next_event=True)
        command = compose.call_args.args[0]
        self.assertIn("/tmp/order-history-fault/armed/$1", command[-3])
        self.assertEqual(command[-1], "NEXT")

    def test_dlq_fault_is_limited_to_named_transaction_boundaries(self):
        import stream_operations
        from unittest.mock import patch
        with self.assertRaises(ValueError):stream_operations.arm_dlq_fault(manage,"unknown")
        with patch.object(manage,"compose") as compose:
            result=stream_operations.arm_dlq_fault(manage,"before-commit")
        self.assertTrue(result["armed"])
        self.assertEqual(result["boundary"],"before-commit")
        self.assertIn("dlq-armed/$1",compose.call_args.args[0][-3])



class HttpProbeTests(unittest.TestCase):
    def test_empty_success_response_preserves_http_status(self):
        from io import BytesIO
        from unittest.mock import patch
        class Response(BytesIO):
            status = 204
        with patch.object(manage, "urlopen", return_value=Response(b"")):
            self.assertEqual(manage.request_json("http://127.0.0.1", method="DELETE"), (204, {}))

    def test_request_json_preserves_custom_idempotency_header(self):
        from io import BytesIO
        from unittest.mock import patch
        class Response(BytesIO):
            status = 202
        response = Response(b'{"status":"VALIDATING"}')
        with patch.object(manage, "urlopen", return_value=response) as opened:
            self.assertEqual(manage.request_json("http://localhost", method="POST", data=b"{}",
                                                 headers={"Idempotency-Key":"integration-1"}),
                             (202, {"status":"VALIDATING"}))
        self.assertEqual(opened.call_args.args[0].get_header("Idempotency-key"), "integration-1")

    def test_restart_connection_drop_is_a_retryable_probe_result(self):
        from http.client import RemoteDisconnected
        from unittest.mock import patch
        with patch.object(manage, "urlopen", side_effect=RemoteDisconnected("restart")):
            self.assertEqual(manage.request_json("http://127.0.0.1:8081/actuator/health/readiness"), (0, {}))

    def test_http_error_response_is_closed_after_reading(self):
        from io import BytesIO
        from urllib.error import HTTPError
        from unittest.mock import patch
        body = BytesIO(b'{"status":"DOWN"}')
        error = HTTPError("http://127.0.0.1", 503, "unavailable", {}, body)
        with patch.object(manage, "urlopen", side_effect=error):
            self.assertEqual(manage.request_json("http://127.0.0.1"), (503, {"status": "DOWN"}))
        self.assertTrue(body.closed)


    def test_http_error_non_json_preserves_status_and_closes_body(self):
        from io import BytesIO
        from urllib.error import HTTPError
        from unittest.mock import patch
        for raw in (b"backend starting private-sentinel", b"<html>Bad Gateway</html>", b"\xff"):
            with self.subTest(raw=raw):
                body = BytesIO(raw)
                error = HTTPError("http://127.0.0.1", 503, "unavailable", {}, body)
                with patch.object(manage, "urlopen", side_effect=error):
                    self.assertEqual(manage.request_json("http://127.0.0.1"), (503, {}))
                self.assertTrue(body.closed)


class ReleaseRegistryTests(unittest.TestCase):
    def test_legacy_rollback_preserves_the_running_admin_image_id(self):
        from unittest.mock import patch
        from subprocess import CompletedProcess
        images = {service: "sha256:" + "a" * 64 for service in manage.DEPLOYABLES if service != "admin"}
        current_admin = "sha256:" + "b" * 64
        with patch.object(manage, "read_releases", return_value={"legacy": images}), \
             patch.object(manage, "compose") as compose, \
             patch.object(manage, "run", return_value=CompletedProcess([], 0, current_admin+"\n")) as run, \
             patch.object(manage, "provision_local_identity") as identity, \
             patch.object(manage, "integration"):
            compose.return_value = CompletedProcess([], 0, "admin-container-id\n")
            manage.rollback(version="legacy")
        self.assertEqual(compose.call_args.kwargs["images"]["admin"], current_admin)
        self.assertEqual(compose.call_args.kwargs["images"]["catalog"], images["catalog"])
        self.assertTrue(any("container" in c.args[0] for c in run.call_args_list))
        identity.assert_called_once_with(manage.ROOT)

    def test_records_exact_image_ids_and_does_not_overwrite_a_release(self):
        images = {service: "sha256:" + f"{i:064x}" for i, service in enumerate(manage.DEPLOYABLES, 1)}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manage.record_release(root, "supersports", "v1", images)
            self.assertEqual(manage.read_releases(root, "supersports"), {"v1": images})
            with self.assertRaises(ValueError):
                manage.record_release(root, "supersports", "v1", images)
            self.assertEqual(manage.read_releases(root, "supersports"), {"v1": images})

    def test_rejects_mutable_tags_in_rollback_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                manage.record_release(Path(directory), "supersports", "v1",
                                      {service: "latest" for service in manage.DEPLOYABLES})

    def test_release_failure_does_not_record_a_release(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(manage, "compose") as compose, \
                 patch.object(manage, "provision_databases"), \
                 patch.object(manage, "provision_local_identity"), \
                 patch.object(manage, "integration", side_effect=RuntimeError("failed")):
                with self.assertRaises(RuntimeError):
                    manage.release(root=root, project="supersports", version="v2")
                manage.provision_local_identity.assert_called_once_with(root)
            self.assertEqual(manage.read_releases(root, "supersports"), {})
            self.assertEqual(compose.call_count, 2)

    def test_rollback_rejects_unknown_release_before_deployment(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(manage, "compose") as compose:
                with self.assertRaises(ValueError):
                    manage.rollback(root=Path(directory), project="supersports", version="missing")
            compose.assert_not_called()

    def test_rollback_deploys_exact_recorded_images_before_integration(self):
        from unittest.mock import patch, call
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = {service: "sha256:" + f"{i:064x}" for i, service in enumerate(manage.DEPLOYABLES, 1)}
            manage.record_release(root, "supersports", "v1", images)
            with patch.object(manage, "run") as run, \
                 patch.object(manage, "compose") as compose, \
                 patch.object(manage, "integration") as integration, \
                 patch.object(manage, "provision_local_identity"):
                manage.rollback(root=root, project="supersports", version="v1")
            self.assertEqual(run.call_args_list, [
                *[call(["docker", "image", "inspect", images[service]], capture=True) for service in manage.DEPLOYABLES],
            ])
            compose.assert_called_once_with(
                ["up", "-d", "--no-build", "--wait", "--wait-timeout", "180"],
                root=root, project="supersports", version="v1", images=images)
            integration.assert_called_once_with(root, "supersports")


class ApplicationProfileTests(unittest.TestCase):
    def test_shared_service_set_excludes_frontends_and_includes_storefront_customer_path(self):
        self.assertNotIn("admin", manage.SHARED_COMMERCE_SERVICES)
        self.assertNotIn("storefront", manage.SHARED_COMMERCE_SERVICES)
        for service in ("postgres", "identity", "catalog", "pricing", "inventory", "configuration",
                        "customer", "orders", "payment-simulator", "fulfillment-simulator", "reviews", "support"):
            with self.subTest(service=service):
                self.assertIn(service, manage.SHARED_COMMERCE_SERVICES)

    def test_app_profile_start_is_shared_then_selected_frontend_and_health(self):
        from unittest.mock import patch, call
        for app, port in (("admin", 3002), ("storefront", 3000)):
            with self.subTest(app=app), patch.object(manage, "provision_databases") as provision_db, \
                 patch.object(manage, "compose") as compose, \
                 patch.object(manage, "provision_local_identity") as provision_identity, \
                 patch.object(manage, "wait_status") as wait_status:
                manage.app_profile_up(app, project="supersports", version="local")
                provision_db.assert_called_once_with(root=manage.ROOT, project="supersports", version="local")
                self.assertEqual(compose.call_count, 2)
                self.assertEqual(compose.call_args_list[0].args[0][-len(manage.SHARED_COMMERCE_SERVICES):],
                                 list(manage.SHARED_COMMERCE_SERVICES))
                self.assertEqual(compose.call_args_list[1].args[0][-1], app)
                provision_identity.assert_called_once_with(root=manage.ROOT)
                wait_status.assert_called_once_with(f"http://127.0.0.1:{port}/healthz")

    def test_unknown_app_profile_is_rejected_before_side_effects(self):
        from unittest.mock import patch
        with patch.object(manage, "provision_databases") as provision_db:
            with self.assertRaises(ValueError):
                manage.app_profile_up("analytics")
            provision_db.assert_not_called()


class DeploymentGateTests(unittest.TestCase):
    def test_negative_gate_requires_the_expected_constraint(self):
        from unittest.mock import patch
        from subprocess import CompletedProcess
        import sys
        specification = importlib.util.spec_from_file_location(
            "deployment_checks", ROOT / "devops/scripts/check_deployment.py")
        module = importlib.util.module_from_spec(specification)
        with patch.dict(sys.modules, {"manage": manage}):
            specification.loader.exec_module(module)
        for result, should_pass in (
            (CompletedProcess([], 1, "", "missing existingSecret"), True),
            (CompletedProcess([], 0, "", "missing existingSecret"), False),
            (CompletedProcess([], 1, "", "image download failed"), False),
        ):
            with self.subTest(result=result.returncode, should_pass=should_pass):
                with patch.object(module, "run", return_value=result):
                    if should_pass:
                        module.expect_rejection(["helm"], ["existingSecret"])
                    else:
                        with self.assertRaises(RuntimeError):
                            module.expect_rejection(["helm"], ["existingSecret"])

if __name__ == "__main__":
    unittest.main()
