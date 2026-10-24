"""Read-only host integration checks for the optional Kafka inspector profile."""
import json
import os
import unittest
from urllib.request import urlopen

BASE = os.environ.get("KAFKA_UI_URL", "http://localhost:8091")
ENABLED = os.environ.get("SUPERSPORTS_KAFKA_UI_INTEGRATION") == "1"


def get(path):
    with urlopen(BASE + path, timeout=15) as response:
        return json.load(response)


@unittest.skipUnless(ENABLED, "Set SUPERSPORTS_KAFKA_UI_INTEGRATION=1 with streaming profile running")
class KafkaUiRuntimeTests(unittest.TestCase):
    def test_health_cluster_broker_event_partitions_and_messages(self):
        self.assertEqual(get("/actuator/health")["status"], "UP")
        cluster = get("/api/clusters")[0]
        self.assertEqual(cluster["name"], "supersports")
        self.assertEqual(cluster["status"], "ONLINE")
        self.assertEqual(cluster["brokerCount"], 1)
        self.assertTrue(cluster["readOnly"])
        self.assertEqual(get("/api/clusters/supersports/brokers")[0]["id"], 1)
        topic = get("/api/clusters/supersports/topics/commerce.order.events.v1")
        self.assertEqual(topic["partitionCount"], 3)
        self.assertGreater(topic["partitions"][0]["offsetMax"], 0)
        with urlopen(BASE + "/api/clusters/supersports/topics/commerce.order.events.v1/messages/v2?mode=LATEST&limit=1", timeout=15) as response:
            stream = response.read().decode()
        records = [json.loads(line.removeprefix("data:")) for line in stream.splitlines()
                   if line.startswith("data:{")]
        self.assertTrue(any(record.get("type") == "MESSAGE" for record in records))

    def test_consumer_groups_and_debezium_connector_are_visible(self):
        groups = get("/api/clusters/supersports/consumer-groups/paged?page=0&perPage=100")["consumerGroups"]
        self.assertTrue(any(group["groupId"].startswith("order-history-") for group in groups))
        connector = get("/api/clusters/supersports/connects/debezium/connectors/supersports-orders-outbox")
        self.assertEqual(connector["status"]["state"], "RUNNING")
        tasks = get("/api/clusters/supersports/connects/debezium/connectors/supersports-orders-outbox/tasks")
        self.assertEqual(tasks[0]["status"]["state"], "RUNNING")


if __name__ == "__main__":
    unittest.main()
