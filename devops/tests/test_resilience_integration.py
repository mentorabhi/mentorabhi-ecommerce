"""Opt-in live checks for M09, enabled during the post-development acceptance pass."""
import os
import unittest
from pathlib import Path

import manage
import recovery_operations


@unittest.skipUnless(os.getenv("SUPERSPORTS_M09_LIVE_ACCEPTANCE") == "true",
                     "Run only in the explicit isolated M09 acceptance pass.")
class ResilienceIntegrationTest(unittest.TestCase):
    def test_database_backup_restores_into_isolated_project_and_cleans(self):
        result = recovery_operations.backup(manage, root=manage.ROOT)
        restored = recovery_operations.restore_drill(manage, result["backupDirectory"], root=manage.ROOT)
        self.assertTrue(restored["isolated"])
        self.assertEqual(len(restored["restoredDatabases"]), len(recovery_operations.DATABASE_OWNERS))
        active = manage.compose(["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "orders", "-tA", "-c",
                                 "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"], capture=True)
        self.assertGreater(int(active.stdout.strip()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
