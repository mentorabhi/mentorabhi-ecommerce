"""Operator request validation and secret handling; live replay is integration-tested."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("stream_operations", ROOT / "devops/scripts/stream_operations.py")
stream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stream)


class OperatorCommandTests(unittest.TestCase):
    def test_operator_token_only_travels_on_stdin(self):
        fake = SimpleNamespace(ROOT=ROOT)
        fake.configure_admin_login=lambda root: "private-password"
        fake.token_for=lambda username, password: "private-token"
        fake.compose_command=lambda root,project,args: ["docker", "compose", *args]
        fake.deployment_env=lambda root,version: {}
        calls=[]
        def run(command, **kwargs):
            calls.append((command,kwargs))
            return SimpleNamespace(returncode=0,stdout='SUPERSPORTS_OPERATOR_RESULT {"ok":true,"result":{"status":"PUBLISHED"}}\n',stderr="")
        fake.run=run
        self.assertEqual(stream.operator(fake,{"action":"replay"}),{"status":"PUBLISHED"})
        command,kwargs=calls[0]
        self.assertNotIn("private-token", " ".join(command))
        self.assertNotIn("private-password", " ".join(command))
        self.assertEqual(json.loads(kwargs["input_text"])["token"],"private-token")
        self.assertIn("--spring.main.web-application-type=none", command)

    def test_missing_receipt_does_not_echo_process_output(self):
        fake=SimpleNamespace(ROOT=ROOT,configure_admin_login=lambda root:"password",token_for=lambda *args:"token",
                             compose_command=lambda *args:[],deployment_env=lambda *args:{},
                             run=lambda *args,**kwargs:SimpleNamespace(returncode=2,stdout="sensitive process output",stderr="token"))
        with self.assertRaisesRegex(RuntimeError,"receipt") as raised:
            stream.operator(fake,{"action":"replay"})
        self.assertNotIn("sensitive",str(raised.exception))

    def test_invalid_correction_is_rejected_before_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            payload=Path(directory)/"payload.json"
            payload.write_text('{"eventId":"invalid","customerSubject":"private"}')
            with patch.object(stream,"operator") as operation:
                with self.assertRaises(ValueError):
                    stream.replay(SimpleNamespace(ROOT=ROOT),"commerce.order.events.v1:0:1",payload,
                                  "00000000-0000-0000-0000-000000000001","test")
                operation.assert_not_called()

    def test_demo_writes_correction_to_private_file_and_prints_no_payload(self):
        with patch.object(stream,"operator",return_value={"sourceCoordinate":"commerce.order.events.v1:0:1",
             "correctedPayload":"{\"example\":true}","operationId":"operation"}):
            result=stream.demo(SimpleNamespace(ROOT=ROOT))
        path=Path(result["correctedPayloadFile"])
        try:
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(json.loads(path.read_text()),{"example":True})
            self.assertNotIn("correctedPayload",result)
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
