import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import recovery_operations as recovery


class RecoveryOperationsTest(unittest.TestCase):
    def test_data_fingerprint_ignores_row_order_but_detects_money_and_sequence_changes(self):
        first="COPY public.orders (id, amount) FROM stdin;\n1\t100\n2\t200\n\\.\nSELECT pg_catalog.setval('public.seq', 2, true);\n"
        reordered=first.replace("1\t100\n2\t200", "2\t200\n1\t100")
        self.assertEqual(recovery._data_fingerprint(first), recovery._data_fingerprint(reordered))
        self.assertNotEqual(recovery._data_fingerprint(first), recovery._data_fingerprint(first.replace("1\t100","1\t101")))
        self.assertNotEqual(recovery._data_fingerprint(first), recovery._data_fingerprint(first.replace(", 2, true",", 3, true")))
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / "devops/.local/backups/fixture"
        self.directory.mkdir(parents=True)
        rows = []
        for database in recovery.DATABASE_OWNERS:
            filename = database + ".dump"
            content = ("fixture:" + database).encode()
            (self.directory / filename).write_bytes(content)
            rows.append({"database": database, "file": filename, "bytes": len(content),
                         "sha256": hashlib.sha256(content).hexdigest()})
        (self.directory / "manifest.json").write_text(json.dumps({"format": 1, "sourceProject": "supersports", "databases": rows}))

    def test_backup_verification_rejects_tampering_before_restore(self):
        (self.directory / "orders.dump").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            recovery._verified_backup(self.root, str(self.directory))

    def test_verified_backup_requires_complete_database_set(self):
        manifest_path = self.directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["databases"].pop()
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "incomplete"):
            recovery._verified_backup(self.root, str(self.directory))

    def test_restore_uses_unique_isolated_project_and_cleans_it(self):
        class Manager:
            def __init__(self): self.calls=[]
            @staticmethod
            def validated_project_name(value): return value
            def compose(self, args, **kwargs):
                self.calls.append((args, kwargs))
                if kwargs.get("capture"):
                    if "pg_dump" in args or "pg_restore" in args:
                        return type("Result", (), {"stdout": "COPY public.fixture (id) FROM stdin;\n1\n\\.\n"})()
                    database = args[args.index("-d") + 1]
                    count = 0 if database == "lakehouse" else 3
                    return type("Result", (), {"stdout": f"{database}|{count}\n"})()
        manager=Manager()
        result=recovery.restore_drill(manager, str(self.directory), root=self.root, source_project="supersports")
        self.assertTrue(result["restoreProject"].startswith("supersports-restore-"))
        self.assertTrue(result["isolated"])
        self.assertEqual(len(result["restoredDatabases"]), len(recovery.DATABASE_OWNERS))
        self.assertEqual(manager.calls[-1][0][-1], "--remove-orphans")
        self.assertTrue(all(call[1]["project"] != "supersports" for call in manager.calls))
        self.assertEqual(next(item["applicationTables"] for item in result["restoredDatabases"] if item["database"] == "lakehouse"), 0)

    def test_backup_timeout_removes_incomplete_dump_directory(self):
        class Manager:
            @staticmethod
            def deployment_env(_root, project):
                return {"PROJECT": project}
            @staticmethod
            def compose_command(_root, project, _arguments):
                return ["docker", "compose", "--project-name", project]
        with patch("recovery_operations.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="pg_dump", timeout=1800)):
            with self.assertRaisesRegex(RuntimeError, "30-minute"):
                recovery.backup(Manager(), root=self.root)
        remaining = list((self.root / "devops/.local/backups").iterdir())
        self.assertEqual([item.name for item in remaining], ["fixture"])


if __name__ == "__main__":
    unittest.main()
