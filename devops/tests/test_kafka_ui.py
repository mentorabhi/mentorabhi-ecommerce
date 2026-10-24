"""Validate the rendered inspector profile without loading real credentials."""
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class KafkaUiConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / "devops/compose/core.yaml"
        environment = os.environ.copy()
        environment.update({name: "unit-test-placeholder" for name in re.findall(r"\$\{(\w+):\?", source.read_text())})
        environment.update(json.loads((ROOT / "devops/images.lock.json").read_text()))
        result = subprocess.run(["docker", "compose", "--env-file", "/dev/null", "-f", str(source),
                                 "--profile", "streaming", "config", "--format", "json"],
                                env=environment, capture_output=True, text=True, check=True)
        cls.service = json.loads(result.stdout)["services"]["kafka-ui"]

    def test_inspector_is_local_and_selectively_managed(self):
        service = self.service
        self.assertEqual(service["profiles"], ["streaming"])
        self.assertEqual(service["ports"][0]["host_ip"], "127.0.0.1")
        self.assertEqual(str(service["ports"][0]["published"]), "8091")
        self.assertEqual(service["restart"], "unless-stopped")
        self.assertEqual(service["depends_on"]["kafka"]["condition"], "service_healthy")
        self.assertEqual(service["depends_on"]["kafka-connect"]["condition"], "service_healthy")

    def test_inspection_preserves_cluster_and_stays_resource_bounded(self):
        service = self.service
        env = service["environment"]
        self.assertEqual(env["KAFKA_CLUSTERS_0_READONLY"], "true")
        self.assertEqual(env["KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS"], "kafka:9092")
        self.assertEqual(env["KAFKA_CLUSTERS_0_KAFKACONNECT_0_ADDRESS"], "http://kafka-connect:8083")
        for name in ("DYNAMIC_CONFIG_ENABLED", "MCP_ENABLED", "GITHUB_RELEASE_INFO_ENABLED"):
            self.assertEqual(env[name], "false")
        self.assertEqual(int(service["mem_limit"]), 512 * 1024 * 1024)
        self.assertIn("@sha256:", service["image"])


if __name__ == "__main__":
    unittest.main()
