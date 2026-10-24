"""Enable, disable or verify localhost-only PostgreSQL inspection."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import socket
import tempfile

ROOT=Path(__file__).resolve().parents[2]


def state_path(root=ROOT,project="supersports"):
    if not re.fullmatch(r"supersports(?:-[a-z0-9][a-z0-9-]{0,31})?",project):raise ValueError("Invalid local project name.")
    return root/"devops/.local"/f"postgres-host-access-{project}.json"


def validated(value):
    if (not isinstance(value,dict) or set(value)!={"enabled","port"} or not isinstance(value["enabled"],bool)
            or not isinstance(value["port"],int) or not 1024<=value["port"]<=65535):
        raise ValueError("Host access requires an enabled flag and an unprivileged integer port; bind address is fixed to localhost.")
    return dict(value)


def configuration(root=ROOT,project="supersports"):
    path=state_path(root,project)
    if path.is_symlink() or path.parent.is_symlink():raise ValueError("Refusing a symlinked host-access state file.")
    return validated(json.loads(path.read_text())) if path.exists() else {"enabled":False,"port":15432}


def save(value,*,root=ROOT,project="supersports"):
    value=validated(value);path=state_path(root,project)
    if path.is_symlink() or path.parent.is_symlink():raise ValueError("Refusing a symlinked host-access state file.")
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    descriptor,temporary=tempfile.mkstemp(prefix=".postgres-host-",dir=path.parent)
    try:
        with os.fdopen(descriptor,"w") as handle:json.dump(value,handle);handle.write("\n");handle.flush();os.fsync(handle.fileno())
        os.replace(temporary,path)
    finally:Path(temporary).unlink(missing_ok=True)


def apply(manage,enabled,*,project="supersports",port=15432):
    old=configuration(manage.ROOT,project);path=state_path(manage.ROOT,project);existed=path.exists()
    value=validated({"enabled":enabled,"port":port})
    if enabled and (not old["enabled"] or old["port"]!=port):
        with socket.socket() as probe:probe.bind(("127.0.0.1",port))
    command=["up","-d","--no-deps","--force-recreate","--wait","--wait-timeout","120","postgres"]
    save(value,root=manage.ROOT,project=project)
    try:manage.compose(command,project=project)
    except RuntimeError as error:
        if existed:save(old,root=manage.ROOT,project=project)
        else:path.unlink(missing_ok=True)
        manage.compose(command,project=project)
        raise RuntimeError("Host access failed; previous database binding was restored.") from error
    rows=manage.compose(["ps","--format","json"],project=project,capture=True).stdout.splitlines()
    running={json.loads(row)["Service"] for row in rows if row.strip()}
    ports={**dict(zip(manage.SERVICES,manage.SERVICE_PORTS)),"order-history":8089}
    for service,service_port in ports.items():
        if service in running:manage.wait_status(f"http://127.0.0.1:{service_port}/actuator/health/readiness",timeout=120)
    return {**value,"host":"127.0.0.1","database":"postgres","username":"postgres"}


def verify(manage,*,project="supersports"):
    import psycopg
    value=configuration(manage.ROOT,project)
    if not value["enabled"]:raise ValueError("Host database access is disabled.")
    credentials=manage.load_credentials(manage.ROOT/"devops/.local/bootstrap.env")
    try:
        with psycopg.connect(host="127.0.0.1",port=value["port"],dbname="postgres",user="postgres",
                             password=credentials["POSTGRES_PASSWORD"],connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_user,current_database(),inet_server_port(),version()")
                row=cursor.fetchone()
    except psycopg.Error:raise RuntimeError("Host PostgreSQL authentication or query failed.") from None
    return {"host":"127.0.0.1","port":value["port"],"username":row[0],"database":row[1],"serverPort":row[2],"serverVersion":row[3]}


def main():
    import manage
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["enable","disable","status","verify"])
    parser.add_argument("--project",default="supersports")
    parser.add_argument("--port",type=int,default=15432)
    args=parser.parse_args()
    try:
        manage.configure()
        if args.action in ("enable","disable"):result=apply(manage,args.action=="enable",project=args.project,port=args.port)
        elif args.action=="verify":result=verify(manage,project=args.project)
        else:result=configuration(manage.ROOT,args.project)
        print(json.dumps(result,indent=2));return 0
    except (ValueError,RuntimeError,OSError) as error:print(f"ERROR: {error}");return 1

if __name__=="__main__":raise SystemExit(main())
