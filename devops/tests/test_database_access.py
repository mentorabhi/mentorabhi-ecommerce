"""Host database inspection is explicit, loopback-only, and preserves private defaults."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"devops/scripts"))
spec=importlib.util.spec_from_file_location("database_access",ROOT/"devops/scripts/database_access.py")
db=importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)

class HostAccessTests(unittest.TestCase):
    def test_compose_loads_host_override_only_after_explicit_enable(self):
        import manage
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);override=str(root/"devops/compose/host-access.yaml")
            self.assertNotIn(override,manage.compose_command(root,"supersports",["ps"]))
            db.save({"enabled":True,"port":15432},root=root)
            self.assertIn(override,manage.compose_command(root,"supersports",["ps"]))
            db.save({"enabled":False,"port":15432},root=root)
            self.assertNotIn(override,manage.compose_command(root,"supersports",["ps"]))

    def test_private_default_and_persisted_explicit_port(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(db.configuration(root),{"enabled":False,"port":15432})
            db.save({"enabled":True,"port":15432},root=root)
            self.assertEqual(db.configuration(root),{"enabled":True,"port":15432})
            self.assertEqual(db.state_path(root).stat().st_mode & 0o777,0o600)

    def test_invalid_ports_or_host_override_are_rejected_without_overwriting_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            db.save({"enabled":True,"port":15432},root=root)
            for value in ({"enabled":True,"port":0},{"enabled":True,"port":"15432"},
                          {"enabled":True,"port":15432,"host":"0.0.0.0"}):
                with self.assertRaises(ValueError):db.save(value,root=root)
            self.assertEqual(db.configuration(root),{"enabled":True,"port":15432})

    def test_symlinked_state_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); path=db.state_path(root)
            path.parent.mkdir(parents=True)
            external=root/"external";external.write_text("unchanged")
            path.symlink_to(external)
            with self.assertRaises(ValueError):db.save({"enabled":True,"port":15432},root=root)
            self.assertEqual(external.read_text(),"unchanged")

if __name__=="__main__":unittest.main()
