"""Shared local acceptance-probe reporting and owner-scoped CLI helpers."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

import manage


class ProbeFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ProbeFailure(message)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_report(report, name):
    directory = manage.ROOT / "devops/.local/load-probes"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    target = directory / f"{name}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}.json"
    with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write("\n")
    return target


def kafka(project, command, arguments, *, check=True, timeout=30):
    return manage.compose(["--profile", "streaming", "exec", "-T", "kafka",
        f"/opt/kafka/bin/{command}.sh", "--bootstrap-server", "localhost:9092", *arguments],
        project=project, capture=True, check=check, timeout=timeout)


def sql(project, database, statement, *, check=True):
    return manage.compose(["exec", "-T", "postgres", "psql", "-X", "-v", "ON_ERROR_STOP=1",
        "-U", "postgres", "-d", database, "-tA", "-c", statement],
        project=project, capture=True, check=check, timeout=20)


def parse_group_offsets(output, group, topic, expected_partitions):
    rows = [line.split() for line in output.splitlines()]
    rows = [row for row in rows if len(row) >= 6 and row[:2] == [group, topic]]
    result = {int(row[2]): {"offset": int(row[3]), "end": int(row[4]), "lag": int(row[5])} for row in rows}
    require(set(result) == set(expected_partitions) and len(rows) == len(result),
            "Consumer group offsets do not cover exactly the expected partitions")
    return result


def group_offset(project, group, topic, expected_partitions=(0,)):
    result = kafka(project, "kafka-consumer-groups", ["--describe", "--group", group])
    return parse_group_offsets(result.stdout, group, topic, expected_partitions)


def connector_running(status):
    tasks = status.get("tasks", [])
    return status.get("connector", {}).get("state") == "RUNNING" and bool(tasks) and all(task.get("state") == "RUNNING" for task in tasks)


def environment(project, container_ids=None):
    result = manage.run(["docker", "info", "--format",
        '{"version":"{{.ServerVersion}}","architecture":"{{.Architecture}}","memoryBytes":{{.MemTotal}}}'],
        capture=True, timeout=10)
    info = json.loads(result.stdout)
    containers = container_ids if container_ids is not None else manage.run(
        ["docker", "ps", "--filter", f"label=com.docker.compose.project={project}", "--format", "{{.ID}}"],
        capture=True, timeout=10).stdout.split()
    info["containers"] = []
    for container in containers:
        value = manage.run(["docker", "inspect", "--format",
            '{"id":"{{.Id}}","name":"{{.Name}}","image":"{{.Image}}","running":{{.State.Running}},"restarts":{{.RestartCount}},"oom":{{.State.OOMKilled}}}',
            container], capture=True, timeout=5, check=False)
        info["containers"].append(json.loads(value.stdout) if value.returncode == 0 else {"id": container, "missing": True})
    return info


def verify_containers(before, after):
    original = {c["id"]: c for c in before}
    current = {c["id"]: c for c in after}
    require(set(original) == set(current), "A measured container disappeared or was replaced")
    require(all(not c.get("missing") and c.get("running") and not c["oom"] and
                c["restarts"] == original[identifier]["restarts"] for identifier, c in current.items()),
            "A measured container stopped, restarted or was OOM killed")
