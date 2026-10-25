"""Explicit project-local telemetry lifecycle, preserving actual running images."""
import json
import os
from pathlib import Path
import re

BACKENDS = ("tempo", "loki", "otel-collector", "health-exporter", "prometheus", "prometheus-ui", "grafana")


def state_path(root, project):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", project):
        raise ValueError("Invalid telemetry project")
    return Path(root) / "devops/.local" / f"telemetry-{project}.json"


def enabled(root, project):
    path = state_path(root, project)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Refusing symlinked telemetry state")
    if not path.exists():
        return False
    value = json.loads(path.read_text())
    if set(value) != {"enabled"} or type(value["enabled"]) is not bool:
        raise ValueError("Invalid telemetry state; existing state preserved")
    return value["enabled"]


def save(root, project, value):
    if type(value) is not bool:
        raise ValueError("Telemetry selection must be boolean")
    path = state_path(root, project)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Refusing symlinked telemetry state")
    temporary = path.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump({"enabled": value}, handle)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def running_images(manage, root, project, require_agent=True):
    result = manage.run(["docker", "ps", "-q", "--filter", f"label=com.docker.compose.project={project}"],
                        capture=True, cwd=root)
    ids = result.stdout.split()
    if not ids:
        return {}, []
    containers = json.loads(manage.run(["docker", "inspect", *ids], capture=True, cwd=root).stdout)
    images, apps = {}, []
    for container in containers:
        service = container["Config"]["Labels"].get("com.docker.compose.service")
        if service not in manage.DEPLOYABLES:
            continue
        image = container["Image"]
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
            raise ValueError("Invalid actual running image identity")
        images[service] = image
        if service in (*manage.SERVICES, *manage.STREAMING_SERVICES):
            entrypoint = container["Config"].get("Entrypoint") or []
            if require_agent and "-javaagent:/app/opentelemetry-javaagent.jar" not in entrypoint:
                raise ValueError(f"Rebuild/deploy {service} with the pinned telemetry agent before enabling telemetry")
            apps.append(service)
    return images, sorted(apps)


def switch(manage, *, root, project, version, enable):
    project = manage.validated_project_name(project)
    observed, apps = running_images(manage, root, project, require_agent=enable)
    images = {service: observed.get(service, f"supersports/{service}:{version}") for service in manage.DEPLOYABLES}
    if enable:
        manage.compose(["--profile", "observability", "up", "-d", "--build", "--wait", "--wait-timeout", "180", *BACKENDS],
                       root=root, project=project, version=version, images=images)
        from ui_access import grafana
        result = manage.compose(["--profile", "observability", "ps", "-q", "grafana"], root=root,
                                project=project, version=version, images=images, capture=True)
        ids = result.stdout.split()
        if len(ids) != 1:
            raise ValueError("Expected one Grafana container in the selected project")
        grafana(ids[0])
    save(root, project, enable)
    if apps:
        manage.compose(["--profile", "streaming", "up", "-d", "--no-deps", "--no-build", "--pull", "never",
                        "--force-recreate", "--wait", "--wait-timeout", "240", *apps],
                       root=root, project=project, version=version, images=images)
    if not enable:
        manage.compose(["--profile", "observability", "stop", *BACKENDS], root=root, project=project, version=version)
    return {"enabled": enable, "recreated": apps, "images": {name: images[name] for name in apps}}
