"""Live checks for the local Orders CDC and owner-scoped history projection."""
from __future__ import annotations

import os
import json
from http.client import RemoteDisconnected
from pathlib import Path
import sys
import time
import unittest
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "devops/scripts"))
import manage
import stream_operations
import projection_operations


class StreamingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("SUPERSPORTS_INTEGRATION") != "1":
            raise unittest.SkipTest("Run through devops/scripts/supersports test")
        try:
            with urlopen("http://127.0.0.1:8089/actuator/health/readiness", timeout=3) as response:
                if response.status != 200:
                    raise unittest.SkipTest("Start the streaming profile before these checks")
        except (HTTPError, URLError, TimeoutError):
            raise unittest.SkipTest("Start the streaming profile before these checks")
        cls.credentials = manage.load_credentials(manage.ROOT / "devops/.local/bootstrap.env")
        cls.project = manage.validated_project_name(os.environ.get("SUPERSPORTS_PROJECT", "supersports"))
        cls.customer = manage.customer_token_for("checkout-test-customer", cls.credentials["DEMO_CUSTOMER_PASSWORD"])
        cls.other = manage.customer_token_for("checkout-test-customer-b", cls.credentials["DEMO_CUSTOMER_PASSWORD"])

    def consumer_restart_count(self):
        result = manage.compose(["ps", "-q", "order-history"], project=self.project, capture=True)
        container = result.stdout.strip()
        self.assertTrue(container, "Order History container is not running")
        inspected = manage.run(["docker", "inspect", "--format", "{{.RestartCount}}", container], capture=True)
        return int(inspected.stdout.strip())

    def source_dlq_count(self,coordinate):
        result=manage.compose(["--profile","streaming","exec","-T","kafka","/opt/kafka/bin/kafka-console-consumer.sh",
            "--bootstrap-server","localhost:9092","--topic","commerce.order.events.dlq.v1","--from-beginning",
            "--consumer-property","isolation.level=read_committed","--property","print.key=true","--property","print.value=false","--timeout-ms","2000"],
            project=self.project,capture=True,check=False)
        return sum(1 for line in result.stdout.splitlines() if line.split("\t",1)[0]==coordinate)

    def arm_dlq_fault(self,boundary):
        receipt=stream_operations.arm_dlq_fault(manage,boundary,project=self.project)
        self.assertTrue(receipt["armed"])

    def wait_for_zero_lag(self):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            group=manage.history_target(project=self.project)["group"]
            result = manage.compose(["--profile", "streaming", "exec", "-T", "kafka",
                "/opt/kafka/bin/kafka-consumer-groups.sh", "--bootstrap-server", "localhost:9092",
                "--describe", "--group", group], project=self.project, capture=True, check=False)
            rows = [line.split() for line in result.stdout.splitlines()
                    if line.strip().startswith(group+" commerce.order.events.v1")]
            if len(rows) == 3 and all(row[5] == "0" for row in rows):
                return
            time.sleep(1)
        self.fail("Order History consumer did not drain to zero lag before fault injection")

    @unittest.skipUnless(os.environ.get("SUPERSPORTS_OUTBOX_ROLLBACK") == "1",
                         "Enable only for the UUID-scoped Orders/outbox rollback probe")
    def test_order_transition_rolls_back_when_outbox_insert_fails(self):
        from acceptance_probe import sql
        code, products = manage.request_json("http://127.0.0.1:8081/api/v1/catalog/products?q=football")
        self.assertEqual(code, 200)
        sku = products[0]["skus"][0]["id"]
        inventory = f"http://127.0.0.1:8084/api/v1/inventory/availability/{sku}"
        code, before = manage.request_json(inventory)
        self.assertEqual(code, 200)
        self.assertGreaterEqual(before["available"], 1)
        code, accepted = manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout",
            token=self.customer, method="POST", headers={"Idempotency-Key": "s1-rollback-" + uuid.uuid4().hex},
            data=json.dumps({"lines": [{"skuId": sku, "quantity": 1}], "couponCode": None}).encode())
        self.assertEqual(code, 202, accepted)
        order = str(uuid.UUID(accepted["orderId"]))
        fault = "s1_rollback_" + uuid.uuid4().hex[:12]

        def snapshot():
            result = sql(self.project, "orders", f"""SELECT json_build_object(
                'step',s.current_step,'error',s.last_error_code,'state',o.state,
                'sequence',(SELECT last_sequence FROM order_event_sequence WHERE aggregate_id=o.id),
                'events',(SELECT json_agg(json_build_object('sequence',aggregate_sequence,'type',event_type)
                    ORDER BY aggregate_sequence) FROM order_outbox WHERE aggregate_id=o.id))
                FROM checkout_saga s JOIN customer_order o ON o.id=s.order_id WHERE o.id='{order}'""")
            return json.loads(result.stdout.strip())

        try:
            sql(self.project, "orders", f"""CREATE FUNCTION public.{fault}() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'S1_ATOMIC_OUTBOX_PROBE'; END $$;
                CREATE TRIGGER {fault} BEFORE INSERT ON order_outbox FOR EACH ROW
                WHEN (NEW.aggregate_id='{order}'::uuid AND NEW.event_type='OrderConfirmed')
                EXECUTE FUNCTION public.{fault}();""")
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                observed = snapshot()
                if observed["step"] == "CONFIRM" and observed["error"] == "CHECKOUT_STEP_RETRY":
                    break
                time.sleep(.25)
            else:
                self.fail("Confirmation write fault did not reach a recorded Saga retry")
            self.assertEqual(observed["state"], "PENDING_PAYMENT")
            self.assertEqual(observed["sequence"], 1)
            self.assertEqual(observed["events"], [{"sequence": 1, "type": "OrderAccepted"}])
            self.wait_for_zero_lag()
            code, history = manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{order}", token=self.customer)
            self.assertEqual(code, 200)
            self.assertEqual((history["state"], history["lastSequence"]), ("PENDING_PAYMENT", 1))
        finally:
            sql(self.project, "orders", f"DROP TRIGGER IF EXISTS {fault} ON order_outbox; DROP FUNCTION IF EXISTS public.{fault}();")

        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            code, result = manage.request_json(f"http://127.0.0.1:8086/api/v1/orders/{order}", token=self.customer)
            if code == 200 and result.get("state") == "FULFILLMENT_SCHEDULED":
                break
            time.sleep(.5)
        else:
            self.fail("Order did not recover after the scoped trigger was removed")
        final = snapshot()
        self.assertEqual(final["sequence"], 3)
        self.assertEqual(final["events"], [{"sequence": 1, "type": "OrderAccepted"},
            {"sequence": 2, "type": "OrderConfirmed"}, {"sequence": 3, "type": "FulfillmentScheduled"}])
        self.wait_for_zero_lag()
        code, history = manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{order}", token=self.customer)
        self.assertEqual(code, 200)
        self.assertEqual((history["state"], history["lastSequence"]), ("FULFILLMENT_SCHEDULED", 3))
        code, after = manage.request_json(inventory)
        self.assertEqual(code, 200)
        self.assertEqual(after["available"], before["available"] - 1)
        code, payment = manage.request_json(f"http://127.0.0.1:8087/api/v1/internal/checkout/payments/{order}/status",
                                          token=manage.checkout_worker_token())
        self.assertEqual(code, 200)
        self.assertEqual(sum(operation["state"] == "CAPTURED" for operation in payment["operations"]), 1)

    @unittest.skipUnless(os.environ.get("SUPERSPORTS_CDC_SNAPSHOT_OVERLAP") == "1",
                         "Enable only for the isolated Debezium snapshot/WAL-overlap acceptance probe")
    def test_initial_snapshot_overlaps_concurrent_wal_changes(self):
        """Verify Debezium initial snapshot plus concurrent WAL updates in isolated resources."""
        prefix = "s1_snapshot_" + uuid.uuid4().hex[:12]
        database = prefix[:30]
        publication = prefix + "_pub"
        slot = prefix + "_slot"
        connector = prefix
        topic = prefix + ".public.snapshot_probe"
        rows, updates, inserts = 100_000, 500, 500
        base = "http://127.0.0.1:8090/connectors"

        def psql(db, sql, *, check=True):
            return manage.compose(["--profile", "streaming", "exec", "-T", "postgres", "psql", "-X",
                "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", db, "-tA", "-c", sql],
                project=self.project, capture=True, check=check)

        def topic_end(topic_name):
            result = manage.compose(["--profile", "streaming", "exec", "-T", "kafka",
                "/opt/kafka/bin/kafka-get-offsets.sh", "--bootstrap-server", "localhost:9092",
                "--topic", topic_name, "--time", "-1"], project=self.project, capture=True, check=False, timeout=10)
            if result.returncode != 0 or not result.stdout.strip():
                return 0
            return sum(int(line.rsplit(":", 1)[1]) for line in result.stdout.splitlines() if line.strip())

        def connector_status():
            try:
                with urlopen(base + "/" + connector + "/status", timeout=5) as response:
                    return json.loads(response.read())
            except HTTPError as error:
                if error.code == 404:
                    error.close()
                    return None
                raise

        def wait_topic_count(expected, timeout=180):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                count = topic_end(topic)
                if count >= expected:
                    return count
                time.sleep(.5)
            self.fail(f"Probe topic did not reach {expected} records; last count={topic_end(topic)}")

        main_config = None
        main_end = None
        connector_created = False
        database_created = False
        publication_created = False
        try:
            with urlopen(base + "/supersports-orders-outbox/config", timeout=5) as response:
                main_config = json.loads(response.read())
            main_end = {
                name: topic_end(name) for name in ("commerce.order.events.v1", "commerce.order.events.dlq.v1")
            }
            psql("postgres", f"CREATE DATABASE {database}")
            database_created = True
            psql(database, "CREATE TABLE public.snapshot_probe (id integer PRIMARY KEY, version integer NOT NULL, payload text NOT NULL)")
            psql(database, f"INSERT INTO public.snapshot_probe SELECT n,0,repeat(md5(n::text),8) FROM generate_series(1,{rows}) AS n")
            psql("postgres", f"GRANT CONNECT ON DATABASE {database} TO supersports_cdc")
            psql(database, f"GRANT USAGE ON SCHEMA public TO supersports_cdc; GRANT SELECT ON public.snapshot_probe TO supersports_cdc")
            psql(database, f"CREATE PUBLICATION {publication} FOR TABLE public.snapshot_probe")
            publication_created = True
            manage.compose(["--profile", "streaming", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh",
                "--bootstrap-server", "localhost:9092", "--create", "--if-not-exists", "--topic", topic,
                "--partitions", "1", "--replication-factor", "1"], project=self.project)

            credentials = manage.load_credentials(manage.ROOT / "devops/.local/bootstrap.env")
            config = {
                "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
                "tasks.max": "1", "database.hostname": "postgres", "database.port": "5432",
                "database.user": "supersports_cdc", "database.password": credentials["CDC_DB_PASSWORD"],
                "database.dbname": database, "topic.prefix": prefix, "plugin.name": "pgoutput",
                "slot.name": slot, "publication.name": publication, "publication.autocreate.mode": "disabled",
                "table.include.list": "public.snapshot_probe", "snapshot.mode": "initial",
                "tombstones.on.delete": "false", "snapshot.fetch.size": "1000",
            }
            request = Request(base, data=json.dumps({"name": connector, "config": config}).encode(),
                              headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=15):
                connector_created = True

            deadline = time.monotonic() + 120
            observed_partial_snapshot = 0
            while time.monotonic() < deadline:
                state = connector_status()
                if state is None:
                    time.sleep(.5)
                    continue
                self.assertEqual(state.get("connector", {}).get("state"), "RUNNING", state)
                task_states = [task.get("state") for task in state.get("tasks", [])]
                if not task_states:
                    time.sleep(.5)
                    continue
                self.assertTrue(all(item == "RUNNING" for item in task_states), state)
                observed_partial_snapshot = topic_end(topic)
                if 0 < observed_partial_snapshot < rows:
                    break
                if observed_partial_snapshot >= rows:
                    self.fail("Initial snapshot completed before concurrent mutations; overlap was not exercised")
                time.sleep(.5)
            else:
                self.fail("Debezium did not begin the snapshot before the bounded deadline")

            psql(database, f"UPDATE public.snapshot_probe SET version=1 WHERE id BETWEEN 1 AND {updates}")
            psql(database, f"INSERT INTO public.snapshot_probe SELECT n,0,repeat(md5(n::text),8) FROM generate_series({rows+1},{rows+inserts}) AS n")
            wait_topic_count(rows + updates + inserts)
            first_end = topic_end(topic)
            time.sleep(2)
            self.assertEqual(topic_end(topic), first_end, "Probe topic was not quiescent after snapshot/WAL drain")

            records = manage.compose(["--profile", "streaming", "exec", "-T", "kafka",
                "/opt/kafka/bin/kafka-console-consumer.sh", "--bootstrap-server", "localhost:9092",
                "--topic", topic, "--from-beginning", "--max-messages", str(rows + updates + inserts),
                "--formatter-property", "print.key=true", "--formatter-property", "key.separator=|", "--timeout-ms", "30000"],
                project=self.project, capture=True, timeout=90)
            keyed_state = {}
            operations = {}
            for line in records.stdout.splitlines():
                self.assertIn("|", line, f"Kafka formatter did not include the record key: {line[:200]!r}")
                key, raw = line.split("|", 1)
                event = json.loads(raw)
                op = event.get("op")
                after = event.get("after")
                self.assertIn(op, {"r", "u", "c"}, f"Unexpected Debezium operation {op!r}")
                self.assertIsInstance(after, dict, "Expected a row image for snapshot/create/update")
                key_value = str(after["id"])
                decoded_key = json.loads(key)
                if isinstance(decoded_key, dict):
                    decoded_key = decoded_key.get("payload", decoded_key)
                    decoded_key = decoded_key.get("id")
                self.assertEqual(str(decoded_key), key_value, "Kafka key does not match source primary key")
                keyed_state[key_value] = after
                operations.setdefault(key_value, []).append(op)

            source = psql(database, "SELECT json_agg(json_build_object('id',id,'version',version,'payload',payload) ORDER BY id) FROM public.snapshot_probe")
            expected_rows = json.loads(source.stdout.strip())
            expected = {str(row["id"]): row for row in expected_rows}
            self.assertEqual(set(keyed_state), set(expected), "Folded Kafka state has missing or unexpected source keys")
            self.assertEqual(keyed_state, expected, "Folded snapshot/WAL state differs from the authoritative source table")
            self.assertEqual(len(keyed_state), rows + inserts)
            for key in (str(index) for index in range(1, updates + 1)):
                self.assertIn("r", operations[key], f"Updated key {key} did not appear in the initial snapshot")
                self.assertIn("u", operations[key], f"Updated key {key} did not appear in WAL changes")
            for key in (str(index) for index in range(rows + 1, rows + inserts + 1)):
                self.assertIn("c", operations[key], f"Concurrent insert {key} was absent from WAL")
            self.assertEqual(sum(len(value) for value in operations.values()), rows + updates + inserts)

        finally:
            if connector_created:
                try:
                    request = Request(base + "/" + connector, method="DELETE")
                    with urlopen(request, timeout=15):
                        pass
                except HTTPError as error:
                    if error.code != 404:
                        raise
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    try:
                        with urlopen(base + "/" + connector + "/status", timeout=3):
                            time.sleep(.5)
                    except HTTPError as error:
                        if error.code == 404:
                            error.close()
                            break
                        raise
                    except URLError:
                        time.sleep(.5)
                psql("postgres", f"SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots WHERE slot_name='{slot}' AND NOT active", check=False)
            if publication_created and database_created:
                psql(database, f"DROP PUBLICATION IF EXISTS {publication}", check=False)
            if database_created:
                psql("postgres", f"DROP DATABASE IF EXISTS {database} WITH (FORCE)", check=False)
            manage.compose(["--profile", "streaming", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh",
                "--bootstrap-server", "localhost:9092", "--delete", "--topic", topic],
                project=self.project, capture=True, check=False)
            if main_config is not None:
                with urlopen(base + "/supersports-orders-outbox/config", timeout=5) as response:
                    self.assertEqual(json.loads(response.read()), main_config, "Production Orders connector config changed")
                self.assertEqual({name: topic_end(name) for name in main_end}, main_end,
                                 "Production Commerce topic high-water mark changed during isolated probe")

    def test_cdc_projection_and_tenant_scoped_read_api(self):
        with urlopen("http://127.0.0.1:8090/connectors/supersports-orders-outbox/status", timeout=5) as response:
            connector = __import__("json").loads(response.read())
        self.assertEqual(connector["connector"]["state"], "RUNNING")
        self.assertEqual(connector["tasks"][0]["state"], "RUNNING")

        status, history = manage.request_json("http://127.0.0.1:8089/api/v1/order-history", token=self.customer)
        self.assertEqual(status, 200)
        self.assertTrue(history["orders"])
        order = history["orders"][0]
        self.assertIsInstance(order["lines"], list)
        self.assertGreater(order["lastSequence"], 0)
        self.assertEqual(manage.request_json("http://127.0.0.1:8089/api/v1/order-history?customerKey=forged", token=self.customer)[0], 400)
        self.assertEqual(manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{order['id']}", token=self.other)[0], 404)

        _, products = manage.request_json("http://127.0.0.1:8081/api/v1/catalog/products?q=football")
        sku_id = products[0]["skus"][0]["id"]
        _, profile = manage.request_json("http://127.0.0.1:8085/api/v1/customer/profile", token=self.customer)
        address = {"fullName": "Streaming Test", "phone": "9876543210", "line1": "12 Test Road",
                   "line2": "", "city": "Pune", "state": "Maharashtra", "postalCode": "411001",
                   "country": "IN", "expectedRevision": profile["revision"]}
        self.assertEqual(manage.request_json("http://127.0.0.1:8085/api/v1/customer/profile", token=self.customer,
                                             method="PUT", data=json.dumps(address).encode())[0], 200)
        self.wait_for_zero_lag()
        restart_count = self.consumer_restart_count()
        manage.stream_fault("consumer-after-db-commit", next_event=True, project=self.project)
        key = "streaming-" + uuid.uuid4().hex
        status, accepted = manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout", token=self.customer,
                                               method="POST", data=json.dumps({"lines": [{"skuId": sku_id, "quantity": 1}], "couponCode": None}).encode(),
                                               headers={"Idempotency-Key": key})
        self.assertEqual(status, 202)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline and self.consumer_restart_count() <= restart_count:
            time.sleep(1)
        self.assertGreater(self.consumer_restart_count(), restart_count,
                           "One-shot fault did not crash the consumer after its database commit")
        deadline = time.monotonic() + 45
        projected = None
        while time.monotonic() < deadline:
            projected_status, projected = manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{accepted['orderId']}", token=self.customer)
            # The checkout saga emits accepted, confirmed and scheduled events;
            # wait until the complete aggregate has been projected before
            # comparing inbox rows with the API snapshot.
            if projected_status == 200 and projected["lastSequence"] >= 3:
                break
            time.sleep(0.5)
        self.assertEqual(projected_status, 200, "CDC event did not reach the owner-scoped projection")
        self.assertEqual(projected["totalMinor"], accepted["totalMinor"])
        self.assertEqual(len(projected["lines"]), 1)
        inbox = manage.compose(["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", manage.history_target(project=self.project)["database"],
            "-tA", "-c", f"SELECT count(*),count(DISTINCT aggregate_sequence) FROM order_history_state_event WHERE order_id='{accepted['orderId']}'"],
            project=self.project, capture=True).stdout.strip().split("|")
        self.assertEqual(int(inbox[0]), int(inbox[1]))
        self.assertEqual(int(inbox[0]), projected["lastSequence"],
                         "Redelivery after database commit must not duplicate projected sequence events")
        self.assertEqual(manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{accepted['orderId']}", token=self.other)[0], 404)

        schemas={version:json.loads((ROOT/f"contracts/orders/order-lifecycle-v{version}.schema.json").read_text()) for version in (1,2)}
        validators={version:Draft202012Validator(schema,format_checker=FormatChecker()) for version,schema in schemas.items()}
        query = manage.compose_command(ROOT, self.project, ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "orders", "-tA", "-c", "SELECT payload::text FROM order_outbox ORDER BY id"])
        rows = manage.run(query, environment=manage.deployment_env(ROOT), capture=True).stdout.splitlines()
        self.assertGreaterEqual(len(rows), 60)
        for index, row in enumerate(rows):
            with self.subTest(outbox_row=index + 1):
                event=json.loads(row)
                validators[event["eventVersion"]].validate(event)

        private_read = manage.compose(["exec", "-T", "postgres", "sh", "-ec",
            'export PGPASSWORD="$ORDER_HISTORY_DB_PASSWORD"; exec psql -X -A -t -h 127.0.0.1 -U supersports_order_history -d orders -c "SELECT 1"'],
            project=self.project, capture=True, check=False)
        self.assertNotEqual(private_read.returncode, 0)
        self.assertIn("permission denied for database", private_read.stderr.lower())
        self.assertIn("does not have connect privilege", private_read.stderr.lower())

    def test_cdc_resumes_outbox_after_connect_and_broker_restart(self):
        self.wait_for_zero_lag()
        status,products=manage.request_json("http://127.0.0.1:8081/api/v1/catalog/products?q=football")
        self.assertEqual(status,200)
        sku=products[0]["skus"][0]["id"]
        order=None
        try:
            manage.compose(["--profile","streaming","stop","kafka-connect","kafka"],project=self.project)
            status,order=manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout",token=self.customer,method="POST",
                data=json.dumps({"lines":[{"skuId":sku,"quantity":1}],"couponCode":None}).encode(),
                headers={"Idempotency-Key":"cdc-restart-"+uuid.uuid4().hex})
            self.assertEqual(status,202)
            pending=manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d","orders","-tA","-c",
                f"SELECT count(*) FROM order_outbox WHERE aggregate_id='{order['orderId']}'"],project=self.project,capture=True)
            self.assertGreater(int(pending.stdout.strip()),0,"outbox must commit while broker/Connect are stopped")

            manage.compose(["--profile","streaming","up","-d","--wait","--wait-timeout","120","kafka"],project=self.project)
            manage.compose(["--profile","streaming","up","-d","--wait","--wait-timeout","120","kafka-connect"],project=self.project)

            deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                try:
                    with urlopen("http://127.0.0.1:8090/connectors/supersports-orders-outbox/status",timeout=3) as response:
                        connector=json.loads(response.read())
                    if connector["connector"]["state"]=="RUNNING" and connector["tasks"] and connector["tasks"][0]["state"]=="RUNNING":break
                except (HTTPError,URLError,TimeoutError):pass
                time.sleep(1)
            else:self.fail("Debezium connector/task did not recover after broker restart")
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                projected_status,projected=manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{order['orderId']}",token=self.customer)
                if projected_status==200 and projected["state"]=="FULFILLMENT_SCHEDULED":break
                time.sleep(.5)
            self.assertEqual(projected_status,200)
            self.assertEqual(projected["state"],"FULFILLMENT_SCHEDULED")
            source=manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d","orders","-tA","-c",
                f"SELECT json_agg(json_build_object('eventId',payload->>'eventId','sequence',aggregate_sequence) ORDER BY aggregate_sequence) FROM order_outbox WHERE aggregate_id='{order['orderId']}'"],project=self.project,capture=True)
            events=json.loads(source.stdout.strip())
            history_target=manage.history_target(project=self.project)
            inbox=manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d",history_target["database"],"-tA","-c",
                f"SELECT json_agg(json_build_object('eventId',event_id::text,'sequence',aggregate_sequence) ORDER BY aggregate_sequence) FROM event_inbox WHERE aggregate_id='{order['orderId']}'"],project=self.project,capture=True)
            self.assertEqual(json.loads(inbox.stdout.strip()),events)
            self.assertEqual([row["sequence"] for row in events],list(range(1,len(events)+1)))
            self.wait_for_zero_lag()
        finally:
            manage.compose(["--profile","streaming","up","-d","--wait","--wait-timeout","120","kafka"],project=self.project)
            manage.compose(["--profile","streaming","up","-d","--wait","--wait-timeout","120","kafka-connect"],project=self.project)

    def test_isolated_gap_parking_owner_freshness_and_browser_fallback(self):
        """Exercise real History/HTTP/UI behavior using disposable topic, DB and consumer."""
        # Full Stage 1 runs can reach this scenario after the local access
        # token lifetime. Refresh identities so late assertions measure the
        # ownership behavior under test, not token age.
        self.customer=manage.customer_token_for("checkout-test-customer",self.credentials["DEMO_CUSTOMER_PASSWORD"])
        self.other=manage.customer_token_for("checkout-test-customer-b",self.credentials["DEMO_CUSTOMER_PASSWORD"])
        def pick_order(token,minimum_sequence):
            status,body=manage.request_json("http://127.0.0.1:8089/api/v1/order-history",token=token)
            self.assertEqual(status,200)
            return next(order for order in body["orders"] if order["lastSequence"]>=minimum_sequence)

        owner_a=pick_order(self.customer,3)
        _,profile=manage.request_json("http://127.0.0.1:8085/api/v1/customer/profile",token=self.other)
        address={"fullName":"Gap Probe","phone":"9876543210","line1":"12 Test Road","line2":"","city":"Pune",
            "state":"Maharashtra","postalCode":"411001","country":"IN","expectedRevision":profile["revision"]}
        self.assertEqual(manage.request_json("http://127.0.0.1:8085/api/v1/customer/profile",token=self.other,method="PUT",
            data=json.dumps(address).encode())[0],200)
        _,products=manage.request_json("http://127.0.0.1:8081/api/v1/catalog/products?q=football")
        checkout_status,checkout=manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout",token=self.other,method="POST",
            data=json.dumps({"lines":[{"skuId":products[0]["skus"][0]["id"],"quantity":1}],"couponCode":None}).encode(),
            headers={"Idempotency-Key":"m06-gap-owner-"+uuid.uuid4().hex})
        self.assertEqual(checkout_status,202)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            projection_status,projection=manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{checkout['orderId']}",token=self.other)
            if projection_status==200 and projection["lastSequence"]>=3:break
            time.sleep(.5)
        self.assertEqual(projection_status,200)
        self.wait_for_zero_lag()
        owner_b=pick_order(self.other,1)
        self.assertNotEqual(owner_a["id"],owner_b["id"])
        suffix=uuid.uuid4().hex[:12]
        database=f"m06gap_{suffix}"
        topic=f"m06gap.{suffix}.events"
        dlq=f"m06gap.{suffix}.dlq"
        group=f"m06gap-{suffix}"
        container=f"supersports-m06-gap-probe-{suffix}"
        def events(order_id):
            result=manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d","orders","-tA","-c",
                f"SELECT json_agg(payload ORDER BY aggregate_sequence) FROM order_outbox WHERE aggregate_id='{order_id}'"],project=self.project,capture=True)
            parsed=json.loads(result.stdout.strip())
            self.assertGreaterEqual(len(parsed),1)
            return parsed
        events_a=events(owner_a["id"]);events_b=events(owner_b["id"])
        db_created=topic_created=dlq_created=probe_started=False
        try:
            manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d","postgres","-v","ON_ERROR_STOP=1","-c",
                f'CREATE DATABASE "{database}" OWNER supersports_order_history'],project=self.project,capture=True)
            db_created=True
            for name in (topic,dlq):
                manage.compose(["--profile","streaming","exec","-T","kafka","/opt/kafka/bin/kafka-topics.sh","--create","--if-not-exists",
                    "--bootstrap-server","localhost:9092","--topic",name,"--partitions","1","--replication-factor","1"],project=self.project,capture=True)
                if name==topic:topic_created=True
                else:dlq_created=True
            manage.compose(["--profile","streaming","stop","order-history"],project=self.project)
            run=manage.compose(["--profile","streaming","run","-d","--no-deps","--use-aliases","--name",container,
                "-p","127.0.0.1:8089:8080","-e",f"SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/{database}",
                "-e",f"ORDER_HISTORY_CONSUMER_GROUP={group}","-e",f"ORDER_HISTORY_TOPIC={topic}","-e",f"ORDER_HISTORY_DLQ_TOPIC={dlq}",
                "-e","ORDER_HISTORY_GAP_TIMEOUT_SECONDS=8","order-history"],project=self.project,capture=True)
            probe_started=True
            self.assertTrue(run.stdout.strip())
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                try:
                    with urlopen("http://127.0.0.1:8089/actuator/health/readiness",timeout=2) as response:
                        if response.status==200:break
                except (HTTPError,URLError,TimeoutError,RemoteDisconnected,ConnectionResetError):pass
                time.sleep(.5)
            else:
                logs=manage.run(["docker","logs","--tail","60",container],capture=True,check=False)
                self.fail("isolated Order History probe did not become ready: "+logs.stdout[-3000:]+logs.stderr[-3000:])

            def publish(records):
                lines="".join(f"{record['aggregateId']}|{json.dumps(record,separators=(',',':'))}\n" for record in records)
                manage.compose(["--profile","streaming","exec","-T","kafka","/opt/kafka/bin/kafka-console-producer.sh",
                    "--bootstrap-server","localhost:9092","--topic",topic,"--property","parse.key=true","--property","key.separator=|"],
                    project=self.project,input_text=lines)
            # Same partition: A's future sequence parks while B's full stream proceeds.
            publish([events_a[2],*events_b])
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                code_a,history_a=manage.request_json("http://127.0.0.1:8089/api/v1/order-history",token=self.customer)
                code_b,history_b=manage.request_json("http://127.0.0.1:8089/api/v1/order-history",token=self.other)
                # Projection rows can appear before the remaining records and
                # the periodic broker-lag observation have caught up.
                if (code_a==200 and code_b==200
                    and any(order["id"]==owner_b["id"]
                        and order["lastSequence"]==events_b[-1]["aggregateSequence"]
                        for order in history_b["orders"])
                    and history_b["freshness"]["state"]=="CURRENT"
                    and history_b["freshness"]["pendingOwnEvents"]==0):break
                time.sleep(.5)
            self.assertEqual(code_a,200);self.assertEqual(code_b,200)
            self.assertEqual(history_a["orders"],[])
            self.assertEqual(history_a["freshness"]["pendingOwnEvents"],1)
            self.assertEqual(history_a["freshness"]["state"],"DELAYED")
            self.assertEqual(history_b["freshness"]["state"],"CURRENT")
            self.assertEqual(history_b["freshness"]["pendingOwnEvents"],0)
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                _,history_a=manage.request_json("http://127.0.0.1:8089/api/v1/order-history",token=self.customer)
                if history_a["freshness"]["state"]=="BLOCKED":break
                time.sleep(.5)
            self.assertEqual(history_a["freshness"]["state"],"BLOCKED")
            proxy_status,proxy_history=manage.request_json("http://127.0.0.1:3000/api/order-history",token=self.customer)
            self.assertEqual(proxy_status,200,proxy_history)
            self.assertEqual(proxy_history["freshness"]["state"],"BLOCKED",proxy_history)
            browser_env=os.environ.copy()
            browser_env.update({"SUPERSPORTS_FRESHNESS_PROBE_ORDER_ID":owner_a["id"],"SUPERSPORTS_UI_URL":"http://localhost:3000"})
            manage.run([str(manage.ROOT/".venv/bin/python"),"-m","unittest","discover","-s","apps/storefront/tests",
                "-p","test_customer_history_ui.py","-k","customer_sees_blocked_gap","-v"],environment=browser_env,cwd=manage.ROOT)

            source=events_a
            publish(source[:2])
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                detail_status,detail=manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{owner_a['id']}",token=self.customer)
                if detail_status==200 and detail["lastSequence"]==3:break
                time.sleep(.5)
            self.assertEqual(detail_status,200)
            self.assertEqual(detail["lastSequence"],3)
            publish([source[0]]) # Duplicate delivery must not add an inbox event.
            self.wait_for_zero_lag_for_group(group,topic)
            conflicted={**source[0],"occurredAt":"2099-01-01T00:00:00Z"}
            publish([conflicted]) # Same ID with changed content is quarantined, never applied.
            self.wait_for_zero_lag_for_group(group,topic)
            inbox=manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d",database,"-tA","-c",
                f"SELECT count(*) FROM event_inbox WHERE aggregate_id='{owner_a['id']}'"],project=self.project,capture=True)
            self.assertEqual(int(inbox.stdout.strip()),3)
            final_status,final_detail=manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{owner_a['id']}",token=self.customer)
            self.assertEqual(final_status,200)
            self.assertEqual(final_detail["lastSequence"],3)

            manage.run(["docker","stop",container],cwd=manage.ROOT)
            probe_started=False
            manage.run(["docker","rm",container],cwd=manage.ROOT)
            browser_env["SUPERSPORTS_FRESHNESS_PROBE_ORDER_ID"]=owner_a["id"]
            manage.run([str(manage.ROOT/".venv/bin/python"),"-m","unittest","discover","-s","apps/storefront/tests",
                "-p","test_customer_history_ui.py","-k","customer_sees_unavailable_stream","-v"],environment=browser_env,cwd=manage.ROOT)
        finally:
            if probe_started:
                manage.run(["docker","rm","-f",container],cwd=manage.ROOT,check=False)
            if db_created:
                manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d","postgres","-v","ON_ERROR_STOP=1","-c",
                    f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'],project=self.project,capture=True,check=False)
            for name,created in ((topic,topic_created),(dlq,dlq_created)):
                if created:manage.compose(["--profile","streaming","exec","-T","kafka","/opt/kafka/bin/kafka-topics.sh","--delete",
                    "--bootstrap-server","localhost:9092","--topic",name],project=self.project,capture=True,check=False)
            manage.compose(["--profile","streaming","up","-d","--wait","--wait-timeout","120","order-history"],project=self.project)

    def wait_for_zero_lag_for_group(self,group,topic):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            result=manage.compose(["--profile","streaming","exec","-T","kafka","/opt/kafka/bin/kafka-consumer-groups.sh",
                "--bootstrap-server","localhost:9092","--describe","--group",group],project=self.project,capture=True,check=False)
            rows=[line.split() for line in result.stdout.splitlines() if line.strip().startswith(group+" "+topic)]
            if rows and all(row[5]=="0" for row in rows):return
            time.sleep(.5)
        self.fail(f"probe consumer group {group} did not reach zero lag")
    def test_operator_poison_replay_is_audited_idempotent_and_restartable(self):
        self.wait_for_zero_lag()
        demo=stream_operations.demo(manage,project=self.project)
        path=Path(demo["correctedPayloadFile"])
        try:
            corrected=path.read_text()
            event=json.loads(corrected)
            operation=demo["operationId"]
            request={"action":"replay","sourceCoordinate":demo["sourceCoordinate"],"correctedPayload":corrected,
                     "operationId":operation,"reason":"integration poison version correction"}
            def sql(query,check=True):
                return manage.compose(["exec","-T","postgres","psql","-U","postgres","-d",manage.history_target(project=self.project)["database"],"-tA","-c",query],
                                      project=self.project,capture=True,check=check)
            before=sql("SELECT count(*) FROM event_inbox").stdout.strip()
            with self.assertRaisesRegex(RuntimeError,"OPERATOR_AUTHENTICATION_REQUIRED"):
                stream_operations.operator(manage,request,project=self.project,token=self.customer)
            with self.assertRaisesRegex(RuntimeError,"INJECTED_BEFORE_PUBLISH"):
                stream_operations.operator(manage,{**request,"failBeforePublish":True},project=self.project)
            self.assertEqual(sql(f"SELECT count(*) FROM order_history_replay_audit WHERE operation_id='{operation}'").stdout.strip(),"1")
            with self.assertRaisesRegex(RuntimeError,"INJECTED_AFTER_PUBLISH"):
                stream_operations.operator(manage,{**request,"failAfterPublish":True},project=self.project)
            self.wait_for_zero_lag()
            self.assertEqual(sql(f"SELECT count(*) FROM order_history_replay_delivery WHERE operation_id='{operation}' AND published_at IS NULL").stdout.strip(),"1")
            result=stream_operations.replay(manage,demo["sourceCoordinate"],path,operation,request["reason"],project=self.project)
            self.assertEqual(result["status"],"PUBLISHED")
            self.assertEqual(result["eventId"],event["eventId"])
            self.assertEqual(result,stream_operations.replay(manage,demo["sourceCoordinate"],path,operation,request["reason"],project=self.project))
            self.wait_for_zero_lag()
            self.assertEqual(sql("SELECT count(*) FROM event_inbox").stdout.strip(),before)
            with self.assertRaisesRegex(RuntimeError,"REPLAY_OPERATION_ID_CONFLICT"):
                stream_operations.operator(manage,{**request,"reason":"changed reason"},project=self.project)
            changed={**event,"occurredAt":"2026-10-24T01:02:03Z"}
            with self.assertRaisesRegex(RuntimeError,"APPLIED_EVENT_CANNOT_BE_REWRITTEN"):
                stream_operations.operator(manage,{**request,"operationId":str(uuid.uuid4()),"correctedPayload":json.dumps(changed)},project=self.project)
            formatted=json.dumps(event,sort_keys=True,indent=2)
            second=stream_operations.operator(manage,{**request,"operationId":str(uuid.uuid4()),"correctedPayload":formatted},project=self.project)
            self.assertEqual(second["status"],"PUBLISHED")
            self.wait_for_zero_lag()
            self.assertEqual(sql("SELECT count(*) FROM event_inbox").stdout.strip(),before)
            immutable=sql(f"UPDATE order_history_replay_audit SET reason='rewrite' WHERE operation_id='{operation}'",check=False)
            self.assertNotEqual(immutable.returncode,0)
            self.assertIn("append-only",immutable.stderr)
        finally:
            path.unlink(missing_ok=True)

    def test_dlq_and_source_offset_commit_atomically_across_both_crash_boundaries(self):
        self.wait_for_zero_lag()
        for boundary in ("before-commit","after-commit"):
            with self.subTest(boundary=boundary):
                self.wait_for_zero_lag()
                restarts=self.consumer_restart_count()
                self.arm_dlq_fault(boundary)
                demo=stream_operations.demo(manage,project=self.project)
                coordinate=demo["sourceCoordinate"]
                try:
                    self.assertEqual(self.source_dlq_count(coordinate),1)
                    deadline=time.monotonic()+30
                    while time.monotonic()<deadline and self.consumer_restart_count()<=restarts:time.sleep(.5)
                    self.assertGreater(self.consumer_restart_count(),restarts,"fault marker did not terminate the consumer at the requested boundary")
                    self.wait_for_zero_lag()
                    self.assertEqual(self.source_dlq_count(coordinate),1,"one source coordinate must have exactly one visible committed DLQ record")
                    source_topic,partition,offset=coordinate.split(":")
                    committed=manage.compose(["--profile","streaming","exec","-T","kafka","/opt/kafka/bin/kafka-consumer-groups.sh",
                        "--bootstrap-server","localhost:9092","--describe","--group",manage.history_target(project=self.project)["group"]],
                        project=self.project,capture=True)
                    rows=[line.split() for line in committed.stdout.splitlines() if line.strip().startswith(f"{manage.history_target(project=self.project)['group']} {source_topic} {partition} ")]
                    self.assertEqual(len(rows),1)
                    self.assertGreater(int(rows[0][3]),int(offset),"source offset must advance only with its visible DLQ record")
                    # Resolve the deliberately poisoned coordinate before later
                    # reconciliation checks the retained Kafka history.
                    stream_operations.replay(manage,coordinate,Path(demo["correctedPayloadFile"]),
                        demo["operationId"],"resolve transactional DLQ crash probe",project=self.project)
                    self.wait_for_zero_lag()
                finally:
                    Path(demo["correctedPayloadFile"]).unlink(missing_ok=True)

    def test_z_isolated_rebuild_failure_dry_run_cutover_and_new_event_delivery(self):
        self.wait_for_zero_lag()
        old=manage.history_target(project=self.project)
        self.assertTrue(projection_operations.reconcile(manage,project=self.project)["ok"])
        with stream_operations.exclusive(manage,self.project):
            dry=projection_operations.rebuild(manage,project=self.project,dry_run=True)
            self.assertTrue(dry["ok"],dry)
            self.assertEqual(dry["status"],"DRY_RUN_VERIFIED")
            self.assertEqual(manage.history_target(project=self.project),old)
            failed=projection_operations.rebuild(manage,project=self.project,inject_mismatch=True)
            self.assertFalse(failed["ok"],failed)
            self.assertEqual(failed["status"],"RECONCILIATION_FAILED")
            self.assertTrue(any(error.startswith("ORDER_STATE_OWNER_MONEY_MISMATCH") for error in failed["reconciliation"]["errors"]))
            self.assertEqual(manage.history_target(project=self.project),old)
            healthy=manage.request_json("http://127.0.0.1:8089/actuator/health/readiness")
            self.assertEqual(healthy[0],200)
            active=projection_operations.rebuild(manage,project=self.project)
            self.assertTrue(active["ok"],active)
            self.assertEqual(active["status"],"ACTIVE")
        self.assertEqual(manage.history_target(project=self.project),active["candidate"])
        self.assertNotEqual(active["candidate"],old)
        first=active["watermarks"]["firstHighWater"]; second=active["watermarks"]["secondHighWater"]
        self.assertEqual(set(first),{"0","1","2"})
        self.assertTrue(all(second[key]>=first[key] for key in first))
        self.customer=manage.customer_token_for("checkout-test-customer",self.credentials["DEMO_CUSTOMER_PASSWORD"])
        self.other=manage.customer_token_for("checkout-test-customer-b",self.credentials["DEMO_CUSTOMER_PASSWORD"])
        status,history=manage.request_json("http://127.0.0.1:8089/api/v1/order-history",token=self.customer)
        self.assertEqual(status,200);self.assertTrue(history["orders"])
        existing=history["orders"][0]["id"]
        self.assertEqual(manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{existing}",token=self.other)[0],404)
        _,products=manage.request_json("http://127.0.0.1:8081/api/v1/catalog/products?q=football")
        sku=products[0]["skus"][0]["id"]
        status,accepted=manage.request_json("http://127.0.0.1:8086/api/v1/orders/checkout",token=self.customer,method="POST",
            data=json.dumps({"lines":[{"skuId":sku,"quantity":1}],"couponCode":None}).encode(),headers={"Idempotency-Key":"post-rebuild-"+uuid.uuid4().hex})
        self.assertEqual(status,202)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            projected_status,projected=manage.request_json(f"http://127.0.0.1:8089/api/v1/order-history/{accepted['orderId']}",token=self.customer)
            if projected_status==200 and projected["lastSequence"]>=3:break
            time.sleep(0.5)
        self.assertEqual(projected_status,200)
        self.assertEqual(projected["state"],"FULFILLMENT_SCHEDULED")
        self.assertEqual(projected["totalMinor"],accepted["totalMinor"])
        self.wait_for_zero_lag()
        reconciled=projection_operations.reconcile(manage,project=self.project)
        self.assertTrue(reconciled["ok"],reconciled)
        self.assertEqual(reconciled["target"],active["candidate"])


if __name__ == "__main__":
    unittest.main()
