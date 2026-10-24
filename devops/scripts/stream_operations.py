"""Local authenticated Order History operator workflows; invoked by manage.py."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
import fcntl
from contextlib import contextmanager
from uuid import UUID
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


def operator(manage, request, *, project="supersports", version="s1-m06", token=None, target=None):
    """Use stdin for the token/payload; return only the structured operator receipt."""
    if token is None:
        token = manage.token_for("admin", manage.configure_admin_login(manage.ROOT))
    body = {**request, "token": token}
    arguments = ["--profile", "streaming", "run", "--rm", "-T", "--no-deps"]
    if request.get("action")=="rebuild" and (target is None or target==manage.history_target(project=project)):
        raise ValueError("Rebuild requires a candidate different from the active target.")
    if target is not None:
        target=manage.validated_history_target(target)
        arguments += ["-e", "SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/"+target["database"],
                      "-e", "ORDER_HISTORY_CONSUMER_GROUP="+target["group"]]
        if request.get("action")=="rebuild":arguments += ["-e","ORDER_HISTORY_REBUILD_TARGET=true"]
    arguments += ["order-history",
                 "--spring.main.web-application-type=none", "--order-history.operator-mode=true",
                 "--spring.main.banner-mode=off", "--logging.level.root=WARN"]
    result = manage.run(manage.compose_command(manage.ROOT, project, arguments),
                        environment=manage.deployment_env(manage.ROOT, version, project=project),
                        input_text=json.dumps(body), capture=True, check=False)
    receipts = [line.removeprefix("SUPERSPORTS_OPERATOR_RESULT ")
                for line in result.stdout.splitlines() if line.startswith("SUPERSPORTS_OPERATOR_RESULT ")]
    if len(receipts) != 1:
        raise RuntimeError("Order History operator returned no usable receipt; inspect service startup and migrations.")
    receipt = json.loads(receipts[0])
    if result.returncode or not receipt.get("ok"):
        code = receipt.get("error", "OPERATOR_OPERATION_FAILED")
        if not isinstance(code, str) or not re.fullmatch(r"[A-Z_]{3,80}", code):
            code = "OPERATOR_OPERATION_FAILED"
        raise RuntimeError(f"Order History operator: {code}")
    return receipt["result"]


@contextmanager
def exclusive(manage, project="supersports"):
    directory=manage.ROOT/"devops/.local"
    if directory.is_symlink():raise ValueError("Refusing a symlinked local state directory.")
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=directory/f"stream-operator-{manage.validated_project_name(project)}.lock"
    descriptor=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise RuntimeError("Another streaming operator is active; retry after it finishes.") from error
        yield
    finally:
        os.close(descriptor)


def demo(manage, *, project="supersports", version="s1-m06"):
    receipt = operator(manage, {"action": "demo-poison"}, project=project, version=version)
    descriptor, filename = tempfile.mkstemp(prefix="supersports-replay-", suffix=".json", dir="/tmp")
    with os.fdopen(descriptor, "w") as handle:
        handle.write(receipt.pop("correctedPayload"))
    return {**receipt, "correctedPayloadFile": filename}


def replay(manage, coordinate, payload_file, operation_id, reason, *, project="supersports", version="s1-m06"):
    if not isinstance(coordinate, str) or not re.fullmatch(r"commerce\.order\.events\.v1:[0-9]+:[0-9]+", coordinate):
        raise ValueError("Replay requires --source-coordinate <topic:partition:offset> from the Orders DLQ.")
    try:
        operation_id = str(UUID(operation_id))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("Replay requires a stable --operation-id UUID.") from error
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError("Replay requires a non-empty --reason of at most 500 characters.")
    if payload_file is None:
        raise ValueError("Replay requires --corrected-payload-file.")
    path = Path(payload_file)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 262_144:
        raise ValueError("Correction must be an ordinary JSON file no larger than 256 KiB.")
    payload = path.read_text()
    try:
        schema = json.loads((manage.ROOT / "contracts/orders/order-lifecycle-v1.schema.json").read_text())
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(json.loads(payload))
    except (ValidationError, json.JSONDecodeError) as error:
        raise ValueError("Correction does not satisfy the order-lifecycle-v1 event contract.") from error
    return operator(manage, {"action": "replay", "sourceCoordinate": coordinate,
                            "correctedPayload": payload, "operationId": operation_id, "reason": reason},
                    project=project, version=version)
