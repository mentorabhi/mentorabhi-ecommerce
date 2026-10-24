# Local Kafka inspection UI

2026-10-24 · User-requested M06 addition · Reviewed before implementation.

Deploy Kafbat UI as a separately managed container in the existing `streaming` Compose profile. Host access is http://localhost:8091, bound only to `127.0.0.1`. It connects to the existing `kafka:9092` broker and `kafka-connect:8083` Debezium runtime over the Compose network. Show messages, partitions, brokers, consumer groups/lag and connector status. No duplicate broker or cloud service is needed.

Use Kafbat UI v1.5.0, the latest stable official release verified on 2026-10-24, pinned by OCI index digest. The manifest includes Linux ARM64 and AMD64. License: Apache-2.0. Bound initial resources to 512 MiB/0.5 CPU with a 256 MiB Java heap; measure actual use after startup. It is selective with streaming on the 16 GiB host. Disable dynamic configuration, MCP and GitHub update checks; use a read-only cluster for inspection. Authentication is unnecessary for the requested localhost-only development inspector; no credentials are added.

Implementation-owner review: fixed host binding prevents accidental LAN exposure; read-only mode avoids accidental event changes; existing private broker addresses are correct for this container; Kafka Connect integration lets the user see Debezium; Compose profile start/stop/restart must manage the inspector; runtime/API and Selenium checks must prove host access and actual metadata/messages rather than only static config. No unresolved design blocker. UI read-only mode is a local application safeguard, not Kafka ACL enforcement.

Sources: [official release](https://github.com/kafbat/kafka-ui/releases/tag/v1.5.0), [configuration](https://ui.docs.kafbat.io/configuration/configuration-file), [license](https://github.com/kafbat/kafka-ui/blob/main/LICENSE). Diagram: `kafka-ui-flow.mmd`.

Verification plan: unit-test parsed Compose profile/bind/dependency/resource/read-only/image properties; validate Compose; deploy the pinned ARM64 image; verify HTTP health, one broker, event topic partition count, retained messages, consumer group and running connector from the host; Selenium opens the topic/messages UI. Record commands/results and remaining human checks separately.
