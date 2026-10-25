"""Measure retained WAL and idle Kafka checkpoints using disposable local resources."""
import argparse
import json
import re
import sys
import time
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import manage
from acceptance_probe import ProbeFailure, connector_running, environment, group_offset, kafka, require, save_report, sql, utc_now
from checkout_soak import planned_orders


BASE = "http://127.0.0.1:8090/connectors"


def remaining_recovery(started, now):
    remaining = 180 - (now - started)
    require(remaining > 0, "Retained source recovery exceeded 180 seconds including connector startup")
    return remaining


def connect_request(url, method="GET", data=None):
    payload = json.dumps(data).encode() if data is not None else None
    request = Request(url, method=method, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read()
            return response.status, json.loads(body) if body else {}
    except HTTPError as error:
        with error:
            return error.code, {}


def topic_bounds(project, topic):
    bounds = []
    for instant in ("-2", "-1"):
        result = kafka(project, "kafka-get-offsets", ["--topic", topic, "--time", instant])
        rows = [line.rsplit(":", 2) for line in result.stdout.splitlines() if line.startswith(topic + ":")]
        require(len(rows) == 1, "Retention topic must have exactly one observable partition")
        bounds.append(int(rows[0][2]))
    return tuple(bounds)


def fold_records(records):
    state, identities = {}, set()
    for raw in records.splitlines():
        event = json.loads(raw)
        op, row = event.get("op"), event.get("after")
        require(op in {"r", "c", "u"} and isinstance(row, dict), "Unexpected retention event shape")
        identity = (op, row["id"], row["version"])
        identities.add(identity)
        state[str(row["id"])] = row
    return state, identities


def retained_coordinates(baseline_slot, current_slot, baseline_bounds, current_bounds, offset):
    require(not current_slot.get("active"), "Stopped connector slot became active")
    require(current_slot.get("confirmed") == baseline_slot.get("confirmed"), "Stopped connector advanced its confirmed LSN")
    require(current_slot.get("walStatus") in {"reserved", "extended"}, "Logical slot no longer retains recoverable WAL")
    require(current_slot.get("retainedBytes", 0) <= 256 * 1024 * 1024, "Disposable slot exceeded the 256 MiB WAL guard")
    require(tuple(current_bounds) == tuple(baseline_bounds), "Idle topic bounds changed or records were truncated")
    require(offset == baseline_bounds[1], "Idle consumer checkpoint changed")


def run_probe(duration, interval, project):
    ticks = planned_orders(duration, interval)
    prefix = "s1_retention_" + uuid.uuid4().hex[:12]
    database, publication, slot = prefix, prefix + "_pub", prefix + "_slot"
    connector, topic, group = prefix, prefix + ".public.retention_probe", prefix + "_reader"
    report = {"kind": "retention", "startedAt": utc_now(), "durationSeconds": duration,
              "intervalSeconds": interval, "transactionsPlanned": ticks, "prefix": prefix,
              "samples": [], "cleanup": {}}
    database_created = connector_created = topic_created = group_created = False
    main_config = None

    def api(suffix="", method="GET", data=None):
        return connect_request(BASE + "/" + connector + suffix, method, data)

    def slot_state():
        result = sql(project, "postgres", f"""SELECT json_build_object('active',active,
            'confirmed',confirmed_flush_lsn::text,'restart',restart_lsn::text,'walStatus',wal_status,
            'retainedBytes',pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn)::bigint)
            FROM pg_replication_slots WHERE slot_name='{slot}'""")
        return json.loads(result.stdout.strip()) if result.stdout.strip() else {}

    def await_connector(expected, timeout=90):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            code, body = api("/status")
            tasks = body.get("tasks", []) if isinstance(body, dict) else []
            if code == 200 and body.get("connector", {}).get("state") == expected:
                if expected == "STOPPED" or tasks and all(task.get("state") == "RUNNING" for task in tasks):
                    return
            time.sleep(1)
        raise ProbeFailure(f"Disposable connector did not reach {expected}")

    def read_records(count, *, use_group=False):
        args = ["--topic", topic, "--max-messages", str(count), "--timeout-ms", "30000",
                "--command-property", "isolation.level=read_committed", "--command-property", "enable.auto.commit=false"]
        args += ["--group", group] if use_group else ["--partition", "0", "--offset", "0"]
        return kafka(project, "kafka-console-consumer", args, timeout=60).stdout

    failed = None
    try:
        report["environment"] = environment(project)
        code, main_config = manage.request_json(BASE + "/supersports-orders-outbox/config")
        require(code == 200, "Main Orders connector is unavailable before retention test")
        code, main_status = manage.request_json(BASE + "/supersports-orders-outbox/status")
        require(code == 200 and connector_running(main_status), "Main connector/task is not RUNNING before retention test")
        credentials = manage.load_credentials(manage.ROOT / "devops/.local/bootstrap.env")
        database_created = True
        sql(project, "postgres", f"CREATE DATABASE {database}")
        sql(project, database, "CREATE TABLE public.retention_probe (id integer PRIMARY KEY, version integer NOT NULL, payload text NOT NULL)")
        sql(project, database, "INSERT INTO public.retention_probe SELECT n,0,repeat(md5(n::text),32) FROM generate_series(1,20) AS n")
        sql(project, "postgres", f"GRANT CONNECT ON DATABASE {database} TO supersports_cdc")
        sql(project, database, f"GRANT USAGE ON SCHEMA public TO supersports_cdc; GRANT SELECT ON public.retention_probe TO supersports_cdc; CREATE PUBLICATION {publication} FOR TABLE public.retention_probe")
        topic_created = True
        kafka(project, "kafka-topics", ["--create", "--topic", topic, "--partitions", "1", "--replication-factor", "1",
            "--config", "retention.ms=-1", "--config", "retention.bytes=-1"])
        config = {"connector.class": "io.debezium.connector.postgresql.PostgresConnector", "tasks.max": "1",
            "database.hostname": "postgres", "database.port": "5432", "database.user": "supersports_cdc",
            "database.password": credentials["CDC_DB_PASSWORD"], "database.dbname": database,
            "topic.prefix": prefix, "plugin.name": "pgoutput", "slot.name": slot,
            "publication.name": publication, "publication.autocreate.mode": "disabled",
            "table.include.list": "public.retention_probe", "snapshot.mode": "initial", "tombstones.on.delete": "false"}
        connector_created = True
        code, _ = manage.request_json(BASE, method="POST", data=json.dumps({"name": connector, "config": config}).encode())
        require(code == 201, f"Cannot create disposable connector (HTTP {code})")
        await_connector("RUNNING")
        deadline = time.monotonic() + 90
        while topic_bounds(project, topic)[1] < 20:
            require(time.monotonic() < deadline, "Initial retention snapshot did not complete")
            time.sleep(1)
        require(topic_bounds(project, topic) == (0, 20), "Unexpected initial snapshot bounds")
        group_created = True
        kafka(project, "kafka-consumer-groups", ["--group", group, "--topic", topic, "--reset-offsets", "--to-offset", "20", "--execute"])
        require(group_offset(project, group, topic)[0]["offset"] == 20, "Could not checkpoint disposable consumer")
        code, _ = api("/stop", "PUT")
        require(code in {202, 204}, f"Cannot stop disposable connector (HTTP {code})")
        await_connector("STOPPED")
        deadline = time.monotonic() + 30
        while slot_state().get("active"):
            require(time.monotonic() < deadline, "Stopped logical slot remains active")
            time.sleep(.5)
        baseline = slot_state()
        require(baseline.get("confirmed"), "Logical slot has no durable confirmed LSN")
        report["slotBefore"] = baseline
        settings = sql(project, "postgres", "SELECT json_build_object('walLevel',current_setting('wal_level'),'maxSlotWalKeepSize',current_setting('max_slot_wal_keep_size'),'walKeepSize',current_setting('wal_keep_size'))")
        report["postgresRetention"] = json.loads(settings.stdout.strip())
        broker = kafka(project, "kafka-configs", ["--entity-type", "brokers", "--entity-name", "1", "--describe", "--all"])
        match = re.search(r"offsets\.retention\.minutes=([0-9]+)", broker.stdout)
        report["brokerOffsetsRetentionMinutes"] = int(match.group(1)) if match else None
        report["topicRetention"] = {"milliseconds": -1, "bytes": -1}
        started = time.monotonic()
        for tick in range(ticks):
            time.sleep(max(0, started + tick * interval - time.monotonic()))
            version = tick + 1
            sql(project, database, f"BEGIN; UPDATE public.retention_probe SET version={version} WHERE id=1; INSERT INTO public.retention_probe VALUES ({20+version},0,repeat(md5('{20+version}'),32)); COMMIT;")
            current = slot_state()
            bounds = topic_bounds(project, topic)
            checkpoint = group_offset(project, group, topic)[0]["offset"]
            code, state = api("/status")
            require(code == 200 and state.get("connector", {}).get("state") == "STOPPED", "Retention connector unexpectedly resumed")
            retained_coordinates(baseline, current, (0, 20), bounds, checkpoint)
            report["samples"].append({"at": utc_now(), "elapsedSeconds": round(time.monotonic() - started, 2),
                "transaction": version, "slot": current, "topicBounds": bounds, "groupOffset": checkpoint})
            if tick % 4 == 0:
                print(f"Retention {time.monotonic()-started:.0f}s: {version} source transactions retained; WAL={current['retainedBytes']} bytes", flush=True)
        time.sleep(max(0, started + duration - time.monotonic()))
        report["stoppedSeconds"] = round(time.monotonic() - started, 2)
        final_slot = slot_state()
        retained_coordinates(baseline, final_slot, (0, 20), topic_bounds(project, topic), group_offset(project, group, topic)[0]["offset"])
        require(final_slot["retainedBytes"] > baseline["retainedBytes"], "WAL did not grow during stopped-connector writes")
        report["slotBeforeResume"] = final_slot
        initial, _ = fold_records(read_records(20))
        require(len(initial) == 20, "Initial Kafka records disappeared during retention window")
        resume = time.monotonic()
        code, _ = api("/resume", "PUT")
        require(code in {202, 204}, f"Cannot resume disposable connector (HTTP {code})")
        await_connector("RUNNING", timeout=remaining_recovery(resume, time.monotonic()))
        expected = 20 + 2 * ticks
        while topic_bounds(project, topic)[1] < expected:
            remaining_recovery(resume, time.monotonic())
            time.sleep(1)
        bounds = topic_bounds(project, topic)
        remaining_recovery(resume, time.monotonic())
        require(bounds[0] == 0, "Retained topic start advanced")
        report["catchupSeconds"] = round(time.monotonic() - resume, 2)
        replay, identities = fold_records(read_records(bounds[1]))
        expected_identities = {("r", row, 0) for row in range(1, 21)}
        expected_identities |= {("u", 1, version) for version in range(1, ticks + 1)}
        expected_identities |= {("c", 20 + version, 0) for version in range(1, ticks + 1)}
        require(identities == expected_identities, "Retained event identity set has missing or unexpected changes")
        source = sql(project, database, "SELECT json_agg(json_build_object('id',id,'version',version,'payload',payload) ORDER BY id) FROM public.retention_probe")
        authoritative = {str(row["id"]): row for row in json.loads(source.stdout.strip())}
        require(replay == authoritative, "Retained topic replay differs from the owned fixture source")
        deferred, deferred_ids = fold_records(read_records(bounds[1] - 20, use_group=True))
        require(deferred_ids == expected_identities - {("r", row, 0) for row in range(1, 21)},
                "Saved consumer checkpoint did not resume at exactly the deferred changes")
        require(group_offset(project, group, topic)[0]["offset"] == 20, "Read-only checkpoint verification changed the saved group")
        report.update(topicFinalBounds=bounds, totalRecords=bounds[1], distinctEventIdentities=len(identities),
            sourceRows=len(authoritative), deferredKeys=len(deferred), outcome="PASS")
    except Exception as error:
        failed = error
        report.update(outcome="FAIL", failureType=type(error).__name__, failure=str(error)[:240])
    finally:
        clean_errors = []
        def cleanup(name, operation):
            try:
                operation()
                report["cleanup"][name] = True
            except Exception as error:
                report["cleanup"][name] = False
                clean_errors.append(f"{name}: {type(error).__name__}")
        if connector_created:
            def remove_connector():
                code, _ = api(method="DELETE")
                require(code in {204, 404}, "Connector delete failed")
                until = time.monotonic() + 45
                while slot_state().get("active"):
                    require(time.monotonic() < until, "Deleted connector retains active slot")
                    time.sleep(.5)
            cleanup("connector", remove_connector)
        if database_created:
            cleanup("slot", lambda: sql(project, "postgres", f"SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots WHERE slot_name='{slot}' AND NOT active"))
            cleanup("database", lambda: sql(project, "postgres", f"DROP DATABASE IF EXISTS {database} WITH (FORCE)"))
        if group_created:
            def remove_group():
                kafka(project, "kafka-consumer-groups", ["--delete", "--group", group], check=False)
                listed = kafka(project, "kafka-consumer-groups", ["--list"])
                require(group not in listed.stdout.splitlines(), "Disposable group remains after cleanup")
            cleanup("group", remove_group)
        if topic_created:
            def remove_topic():
                kafka(project, "kafka-topics", ["--delete", "--topic", topic], check=False)
                until = time.monotonic() + 30
                while topic in kafka(project, "kafka-topics", ["--list"]).stdout.splitlines():
                    require(time.monotonic() < until, "Disposable topic remains after cleanup")
                    time.sleep(1)
            cleanup("topic", remove_topic)
        if main_config is not None:
            def check_main():
                code, actual = manage.request_json(BASE + "/supersports-orders-outbox/config")
                require(code == 200 and actual == main_config, "Main connector configuration changed")
            cleanup("mainConnectorUnchanged", check_main)
            def check_main_health():
                until = time.monotonic() + 60
                while time.monotonic() < until:
                    code, state = manage.request_json(BASE + "/supersports-orders-outbox/status")
                    if code == 200 and connector_running(state):
                        return
                    time.sleep(1)
                raise ProbeFailure("Main connector/task did not return RUNNING after retention cleanup")
            cleanup("mainConnectorHealthy", check_main_health)
        if clean_errors:
            report.update(outcome="FAIL", cleanupErrors=clean_errors)
        report["finishedAt"] = utc_now()
        path = save_report(report, "retention")
        print(f"Retention report: {path.relative_to(manage.ROOT)}", flush=True)
    if failed:
        raise failed
    require(report["outcome"] == "PASS", "Retention cleanup failed; inspect private report")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=int, default=900)
    parser.add_argument("--interval-seconds", type=int, default=15)
    parser.add_argument("--project", default="supersports")
    args = parser.parse_args()
    try:
        report = run_probe(args.duration_seconds, args.interval_seconds, manage.validated_project_name(args.project))
        print(json.dumps({key: report[key] for key in ("outcome", "stoppedSeconds", "catchupSeconds", "totalRecords", "sourceRows", "cleanup")}))
        return 0
    except Exception as error:
        print(f"Retention failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
