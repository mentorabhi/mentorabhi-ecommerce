"""Lifecycle cases authored in coding phase; final execution is deferred."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import telemetry


class TelemetryStateTest(unittest.TestCase):
    def test_selection_is_project_scoped_private_and_defaults_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(telemetry.enabled(root, "supersports"))
            telemetry.save(root, "supersports", True)
            self.assertTrue(telemetry.enabled(root, "supersports"))
            self.assertFalse(telemetry.enabled(root, "another-project"))
            self.assertEqual(0o600, telemetry.state_path(root, "supersports").stat().st_mode & 0o777)
            telemetry.save(root, "supersports", False)
            self.assertFalse(telemetry.enabled(root, "supersports"))

    def test_invalid_state_does_not_silently_enable_exporters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            telemetry.save(root, "supersports", False)
            path = telemetry.state_path(root, "supersports")
            path.write_text('{"enabled":"false"}')
            with self.assertRaises(ValueError):
                telemetry.enabled(root, "supersports")

    def test_disable_preserves_images_and_only_recreates_running_apps_before_stopping_backends(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            image = "sha256:" + "a" * 64
            manage = SimpleNamespace(DEPLOYABLES=("catalog", "orders", "admin"),
                validated_project_name=lambda p: p,
                compose=lambda args, **kwargs: calls.append((args, kwargs)))
            with patch.object(telemetry, "running_images", return_value=({"catalog": image}, ["catalog"])):
                result = telemetry.switch(manage, root=Path(tmp), project="supersports", version="stage1", enable=False)
            self.assertEqual(["catalog"], result["recreated"])
            self.assertEqual(image, calls[0][1]["images"]["catalog"])
            self.assertIn("--no-deps", calls[0][0])
            self.assertIn("--no-build", calls[0][0])
            self.assertNotIn("orders", calls[0][0])
            self.assertIn("stop", calls[1][0])
            self.assertFalse(telemetry.enabled(Path(tmp), "supersports"))

    def test_enable_rejects_old_image_before_mutating_selection(self):
        container = {"Config": {"Labels": {"com.docker.compose.service": "catalog"},
                                "Entrypoint": ["java", "-jar", "/app/app.jar"]}, "Image": "sha256:" + "a" * 64}
        outputs = iter(("container-id", json.dumps([container])))
        manage = SimpleNamespace(DEPLOYABLES=("catalog",), SERVICES=("catalog",), STREAMING_SERVICES=(),
                                 run=lambda *args, **kwargs: SimpleNamespace(stdout=next(outputs)))
        with self.assertRaisesRegex(ValueError, "Rebuild/deploy"):
            telemetry.running_images(manage, Path("."), "supersports")


if __name__ == "__main__":
    unittest.main()
