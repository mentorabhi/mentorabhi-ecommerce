"""Permission-restricted PostgreSQL backup and isolated restore drills."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess

DATABASE_OWNERS = {
    "catalog": "supersports_catalog", "configuration": "supersports_configuration",
    "identity": "supersports_identity", "pricing": "supersports_pricing",
    "inventory": "supersports_inventory", "customer": "supersports_customer",
    "orders": "supersports_orders", "payment": "supersports_payment",
    "fulfillment": "supersports_fulfillment", "order_history": "supersports_order_history",
    "reviews": "supersports_reviews", "support": "supersports_support",
    "lakehouse": "supersports_lakehouse",
}


def _backup_root(root: Path) -> Path:
    local = root / "devops/.local"
    if local.is_symlink():
        raise ValueError("Refusing a symlinked local state directory.")
    path = local / "backups"
    if path.is_symlink():
        raise ValueError("Refusing a symlinked backup directory.")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def backup(manager, *, root: Path, project: str = "supersports") -> dict:
    base = _backup_root(root)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
    destination = base / name
    destination.mkdir(mode=0o700)
    records = []
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        environment = manager.deployment_env(root, project=project)
        for database in DATABASE_OWNERS:
            filename = database + ".dump"
            path = destination / filename
            with path.open("xb") as output:
                result = subprocess.run(
                    manager.compose_command(root, project, ["exec", "-T", "postgres", "pg_dump", "-U", "postgres", "--format=custom", "--dbname", database]),
                    cwd=root, env=environment, stdout=output, stderr=subprocess.PIPE, check=False, timeout=1800,
                )
            if result.returncode != 0:
                raise RuntimeError(f"PostgreSQL backup failed for {database}; inspect local database logs.")
            path.chmod(0o600)
            digest = _sha256(path)
            records.append({"database": database, "file": filename, "bytes": path.stat().st_size, "sha256": digest})
        manifest = {"format": 1, "startedAt": started_at, "createdAt": datetime.now(timezone.utc).isoformat(), "sourceProject": project,
                    "dumpFormat": "pg_dump custom", "databases": records}
        manifest_path = destination / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        manifest_path.chmod(0o600)
        return {"backupDirectory": str(destination), "databaseCount": len(records), "manifest": str(manifest_path)}
    except subprocess.TimeoutExpired as error:
        shutil.rmtree(destination, ignore_errors=True)
        raise RuntimeError("PostgreSQL backup exceeded the 30-minute per-database timeout; incomplete files were removed.") from error
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def _verified_backup(root: Path, value: str) -> tuple[Path, dict]:
    base = _backup_root(root).resolve()
    supplied = Path(value).expanduser()
    if not supplied.is_absolute():
        supplied = root / supplied
    if supplied.is_symlink() or supplied.resolve(strict=True).parent != base:
        raise ValueError("Restore source must be one direct, non-symlinked directory under devops/.local/backups.")
    directory = supplied.resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("Restore source is not a directory.")
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Restore manifest is missing or unsafe.")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("format") != 1 or not isinstance(manifest.get("databases"), list):
        raise ValueError("Unsupported backup manifest format.")
    if not all(isinstance(record, dict) for record in manifest["databases"]):
        raise ValueError("Backup manifest contains invalid database records.")
    listed = [record.get("database") for record in manifest["databases"]]
    if not all(isinstance(database, str) for database in listed):
        raise ValueError("Backup manifest contains an invalid database name.")
    if set(listed) != set(DATABASE_OWNERS) or len(listed) != len(DATABASE_OWNERS):
        raise ValueError("Backup is incomplete or contains an unexpected database list.")
    for record in manifest["databases"]:
        database = record["database"]
        expected_name = database + ".dump"
        if record.get("file") != expected_name:
            raise ValueError("Unsafe backup filename in manifest.")
        dump = directory / expected_name
        if dump.is_symlink() or not dump.is_file():
            raise ValueError(f"Backup dump is missing or unsafe for {database}.")
        if _sha256(dump) != record.get("sha256") or dump.stat().st_size != record.get("bytes"):
            raise ValueError(f"Backup checksum or size mismatch for {database}.")
    return directory, manifest


def restore_drill(manager, backup_directory: str, *, root: Path, source_project: str = "supersports") -> dict:
    directory, manifest = _verified_backup(root, backup_directory)
    source_project = manager.validated_project_name(source_project)
    if manifest.get("sourceProject") != source_project:
        raise ValueError("Backup source project does not match the selected local project.")
    project = "supersports-restore-" + secrets.token_hex(4)
    backup_name = directory.name
    try:
        manager.compose(["--profile", "restore-drill", "up", "-d", "--wait", "--wait-timeout", "90", "restore-postgres"],
                        root=root, project=project, timeout=1800)
        manager.compose(["exec", "-T", "restore-postgres", "psql", "-U", "postgres", "-d", "postgres",
                         "-v", "ON_ERROR_STOP=1", "-f", "/opt/supersports/provision.sql"], root=root, project=project, timeout=1800)
        verified = []
        for record in manifest["databases"]:
            database = record["database"]
            manager.compose(["exec", "-T", "restore-postgres", "pg_restore", "--exit-on-error", "--clean", "--if-exists",
                             "--no-owner", "--role", DATABASE_OWNERS[database], "-U", "postgres", "-d", database,
                             f"/backups/{backup_name}/{database}.dump"], root=root, project=project, timeout=1800)
            result = manager.compose(["exec", "-T", "restore-postgres", "psql", "-X", "-U", "postgres", "-d", database,
                                      "-tA", "-c", "SELECT current_database() || '|' || count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')"],
                                     root=root, project=project, capture=True, timeout=120)
            restored_database, table_count = result.stdout.strip().split("|", 1)
            if restored_database != database:
                raise RuntimeError(f"Restore drill connected to the wrong database while checking {database}.")
            count = int(table_count)
            verified.append({"database": database, "applicationTables": count})
        return {"restoreProject": project, "sourceProject": source_project, "restoredDatabases": verified,
                "isolated": True, "cleanup": "completed"}
    finally:
        cleanup = manager.compose(["--profile", "restore-drill", "down", "--volumes", "--remove-orphans"],
                                  root=root, project=project, check=False, timeout=120)
        if cleanup is not None and getattr(cleanup, "returncode", 0) != 0:
            raise RuntimeError(f"Isolated restore project {project} could not be cleaned up; active project was not targeted.")
