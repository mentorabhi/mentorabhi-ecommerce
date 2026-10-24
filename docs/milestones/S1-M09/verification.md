# S1-M09 verification record

## Stage 1 verification restart — 2026-10-24

Before the full M06 acceptance pass, the management status command could not load the local credentials. The file contained the complete recognized `PRE_M07_SECRET_KEYS` set. `configure()` accepted that set in its version check but its per-line allowlist omitted `CDC_DB_PASSWORD`, `ORDER_HISTORY_DB_PASSWORD`, and `ORDER_HISTORY_OWNER_KEY`, so it rejected the migration before appending current keys.

- Added a regression for extending the known M06 credential set while preserving all existing values.
- Fixed line validation to accept only keys in current `SECRET_KEYS`; exact prior-version set matching remains the migration gate.
- `.venv/bin/python -m unittest devops.tests.test_manage.ConfigureTests.test_configure_extends_known_m06_credentials_without_rotating_them -v`: 1 passed.
- `.venv/bin/python devops/scripts/manage.py configure`: succeeded, adding missing local keys and retaining existing values; command did not print secret values.
- `.venv/bin/python devops/scripts/manage.py status`: all 15 active services healthy.

This is a focused setup regression, not an M09 full test/build/runtime acceptance. Broader Stage 1 verification continues from the M06 completion matrix.
