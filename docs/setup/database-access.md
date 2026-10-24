# Host PostgreSQL access with DBeaver

2026-10-24 · ADR 0007 · Optional local inspection; application service database ownership is unchanged.

In DBeaver choose **New Database Connection → PostgreSQL**:

| Setting | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `15432` |
| Database | `postgres` |
| Username | `postgres` |
| Password | Existing `POSTGRES_PASSWORD` in ignored `devops/.local/bootstrap.env`; shared directly with the user |
| Show all databases | Enable |

Click **Test Connection**, then **Finish**. The PostgreSQL JDBC driver may need its initial download. This is a local development administrator connection; avoid changing service-owned records during inspection. Passwords and connection exports do not belong in Git.

From the repository root:

```sh
.venv/bin/python devops/scripts/database_access.py enable
.venv/bin/python devops/scripts/database_access.py status
.venv/bin/python -m pip install -r devops/tests/host-access-requirements.txt
.venv/bin/python devops/scripts/database_access.py verify
```

Enablement recreates PostgreSQL on its existing volume. The ignored project-specific setting preserves the loopback mapping through subsequent Compose operations. A fresh checkout stays private by default. Use `disable` in place of `enable` to remove the host mapping. Never expose this mapping on all interfaces.

The optional native verification dependency is Psycopg/binary 3.3.6 (LGPL-3.0-only), verified on Python 3.14.7/macOS ARM64 against PostgreSQL 18.6. It is a development test client; services continue using JDBC. Version/support sources: [PyPI](https://pypi.org/project/psycopg/), [Psycopg installation](https://www.psycopg.org/install/), [DBeaver PostgreSQL documentation](https://dbeaver.com/docs/dbeaver/Database-driver-PostgreSQL/).

## Manual end-user checks

- [ ] Run `./devops/scripts/supersports status`; verify services are healthy after enablement.
- [ ] Use DBeaver **Test Connection** and browse the database list.
- [ ] Execute `SELECT current_user, current_database(), version();` and confirm the expected local server.
- [ ] Open a service database and inspect its `public` tables using read-only queries; inspect the current History target using the saved local target configuration, since rebuilds change its database name.
- [ ] Open http://localhost:3000, sign in and browse Orders; open http://localhost:3000/admin and confirm catalog loading.
- [ ] After an ordinary profile restart, reconnect from DBeaver.
- [ ] Optionally disable host access, confirm DBeaver fails to reconnect, then enable it again if wanted.

Record date, tested checks and result here without secrets. Automated native authentication and binding checks passed; DBeaver GUI setup and these human checks remain unperformed.
