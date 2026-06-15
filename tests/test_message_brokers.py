from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hmock import (
    AMQPConfig,
    InMemoryAMQPBroker,
    InMemoryKafkaBroker,
    KafkaConfig,
    MessageBrokerRuntime,
    MockValidationError,
    PublishAMQPAction,
    PublishKafkaAction,
    load_mock_definitions,
)


class BrokerConfigTests(unittest.TestCase):
    def test_kafka_defaults_when_enabled(self) -> None:
        config = KafkaConfig.from_env({"HM_KAFKA_ENABLED": "true"})

        self.assertTrue(config.enabled)
        self.assertEqual("hmock", config.client_id)
        self.assertEqual(("kafka:9092",), config.producer.seed_brokers)
        self.assertEqual(("kafka:9092",), config.consumer.seed_brokers)
        self.assertFalse(config.producer.tls_enabled)
        self.assertFalse(config.consumer.tls_enabled)
        self.assertFalse(config.producer.sasl_enabled)
        self.assertFalse(config.consumer.sasl_enabled)

    def test_kafka_producer_and_consumer_overrides_are_independent(self) -> None:
        config = KafkaConfig.from_env(
            {
                "HM_KAFKA_ENABLED": "true",
                "HM_KAFKA_CLIENT_ID": "tests",
                "HM_KAFKA_SEED_BROKERS": "shared-a:9092, shared-b:9092",
                "HM_KAFKA_SASL_USERNAME": "shared-user",
                "HM_KAFKA_SASL_PASSWORD": "shared-pass",
                "HM_KAFKA_TLS_ENABLED": "true",
                "HM_KAFKA_PRODUCER_SEED_BROKERS": "producer:9092",
                "HM_KAFKA_SASL_PRODUCER_USERNAME": "producer-user",
                "HM_KAFKA_TLS_CONSUMER_ENABLED": "false",
            }
        )

        self.assertEqual("tests", config.client_id)
        self.assertEqual(("producer:9092",), config.producer.seed_brokers)
        self.assertEqual(("shared-a:9092", "shared-b:9092"), config.consumer.seed_brokers)
        self.assertEqual("producer-user", config.producer.sasl_username)
        self.assertEqual("shared-pass", config.producer.sasl_password)
        self.assertEqual("shared-user", config.consumer.sasl_username)
        self.assertEqual("shared-pass", config.consumer.sasl_password)
        self.assertTrue(config.producer.sasl_enabled)
        self.assertTrue(config.consumer.sasl_enabled)
        self.assertTrue(config.producer.tls_enabled)
        self.assertFalse(config.consumer.tls_enabled)

    def test_kafka_partial_sasl_credentials_do_not_enable_sasl(self) -> None:
        config = KafkaConfig.from_env(
            {
                "HM_KAFKA_ENABLED": "true",
                "HM_KAFKA_SASL_USERNAME": "shared-user",
                "HM_KAFKA_SASL_PRODUCER_PASSWORD": "producer-pass",
                "HM_KAFKA_SASL_CONSUMER_USERNAME": "consumer-user",
                "HM_KAFKA_SASL_CONSUMER_PASSWORD": "",
            }
        )

        self.assertTrue(config.producer.sasl_enabled)
        self.assertFalse(config.consumer.sasl_enabled)

    def test_amqp_defaults_and_disabled_by_default(self) -> None:
        disabled = AMQPConfig.from_env({})
        enabled = AMQPConfig.from_env({"HM_AMQP_ENABLED": "true"})

        self.assertFalse(disabled.enabled)
        self.assertEqual("amqp://guest:guest@rabbitmq:5672", disabled.url)
        self.assertTrue(enabled.enabled)
        self.assertEqual("amqp://guest:guest@rabbitmq:5672", enabled.url)


class MockLoadingTests(unittest.TestCase):
    def test_loads_kafka_and_amqp_expectations(self) -> None:
        mocks = load_mock_definitions(
            [
                {
                    "expect": {"kafka": {"topic": "orders.created"}},
                    "behaviors": [
                        {"publish_kafka": {"topic": "audit", "payload": "{{ .KafkaPayload }}"}}
                    ],
                },
                {
                    "expect": {"amqp": {"exchange": "events", "routing_key": "orders.created"}},
                    "behaviors": [
                        {
                            "publish_amqp": {
                                "exchange": "audit",
                                "routing_key": "orders.audit",
                                "payload": "{{ .AMQPPayload }}",
                            }
                        }
                    ],
                },
            ]
        )

        self.assertEqual(("orders.created",), mocks.kafka_topics)
        self.assertEqual("orders.created", mocks.amqp[0].queue)
        self.assertIsInstance(mocks.kafka[0].behaviors[0], PublishKafkaAction)
        self.assertIsInstance(mocks.amqp[0].behaviors[0], PublishAMQPAction)

    def test_rejects_missing_or_ambiguous_payload_sources(self) -> None:
        cases = [
            {"topic": "audit"},
            {"topic": "audit", "payload": "inline", "payload_from_file": "payload.txt"},
        ]

        for publish_kafka in cases:
            with self.subTest(publish_kafka=publish_kafka):
                with self.assertRaises(MockValidationError) as context:
                    load_mock_definitions(
                        {
                            "expect": {"kafka": {"topic": "orders.created"}},
                            "behaviors": [{"publish_kafka": publish_kafka}],
                        }
                    )
                self.assertEqual("mocks[0].behaviors[0].publish_kafka", context.exception.errors[0]["field"])

    def test_rejects_invalid_required_fields(self) -> None:
        with self.assertRaises(MockValidationError) as context:
            load_mock_definitions(
                {
                    "expect": {"amqp": {"exchange": "", "routing_key": ""}},
                    "behaviors": [
                        {"publish_amqp": {"exchange": "audit", "routing_key": "", "payload": "x"}}
                    ],
                }
            )

        fields = {item["field"] for item in context.exception.errors}
        self.assertIn("mocks[0].expect.amqp.exchange", fields)
        self.assertIn("mocks[0].expect.amqp.routing_key", fields)


class BrokerRuntimeTests(unittest.TestCase):
    def test_kafka_matching_executes_all_behaviors_in_loaded_order(self) -> None:
        calls: list[dict[str, object]] = []
        mocks = load_mock_definitions(
            [
                {"expect": {"kafka": {"topic": "orders.created"}}, "behaviors": []},
                {"expect": {"kafka": {"topic": "orders.created"}}, "behaviors": []},
            ]
        )
        mocks = type(mocks)(
            kafka=(
                type(mocks.kafka[0])("orders.created", None, (lambda context: calls.append({"first": context}),)),
                type(mocks.kafka[1])("orders.created", None, (lambda context: calls.append({"second": context}),)),
            ),
            amqp=mocks.amqp,
            base_dir=mocks.base_dir,
        )
        runtime = MessageBrokerRuntime(mocks, kafka_broker=InMemoryKafkaBroker())

        executed = runtime.handle_kafka_message("orders.created", '{"id":"123"}')

        self.assertEqual(2, len(executed))
        self.assertEqual(["first", "second"], [next(iter(call)) for call in calls])
        self.assertEqual("orders.created", calls[0]["first"]["KafkaTopic"])
        self.assertEqual('{"id":"123"}', calls[0]["first"]["KafkaPayload"])

    def test_amqp_matching_executes_all_behaviors_in_loaded_order(self) -> None:
        calls: list[str] = []
        mocks = load_mock_definitions(
            [
                {
                    "expect": {"amqp": {"exchange": "events", "routing_key": "orders.created"}},
                    "behaviors": [],
                },
                {
                    "expect": {"amqp": {"exchange": "events", "routing_key": "orders.created"}},
                    "behaviors": [],
                },
            ]
        )
        mocks = type(mocks)(
            kafka=mocks.kafka,
            amqp=(
                type(mocks.amqp[0])(
                    "events",
                    "orders.created",
                    "orders.created",
                    None,
                    (lambda context: calls.append(f"first:{context['AMQPQueue']}"),),
                ),
                type(mocks.amqp[1])(
                    "events",
                    "orders.created",
                    "orders.created",
                    None,
                    (lambda context: calls.append(f"second:{context['AMQPPayload']}"),),
                ),
            ),
            base_dir=mocks.base_dir,
        )
        runtime = MessageBrokerRuntime(mocks, amqp_broker=InMemoryAMQPBroker())

        executed = runtime.handle_amqp_message("events", "orders.created", "orders.created", "payload")

        self.assertEqual(2, len(executed))
        self.assertEqual(["first:orders.created", "second:payload"], calls)

    def test_publish_actions_render_inline_and_file_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            (base_dir / "payload.txt").write_text("file {{ .KafkaPayload }}", encoding="utf-8")
            mocks = load_mock_definitions(
                [
                    {
                        "expect": {"kafka": {"topic": "orders.created"}},
                        "behaviors": [
                            {"publish_kafka": {"topic": "audit.inline", "payload": "inline {{ .KafkaTopic }}"}},
                            {"publish_kafka": {"topic": "audit.file", "payload_from_file": "payload.txt"}},
                            {
                                "publish_amqp": {
                                    "exchange": "audit",
                                    "routing_key": "orders.audit",
                                    "payload": "amqp {{ .KafkaPayload }}",
                                }
                            },
                        ],
                    }
                ],
                base_dir=base_dir,
            )
            kafka = InMemoryKafkaBroker()
            amqp = InMemoryAMQPBroker()
            runtime = MessageBrokerRuntime(mocks, kafka_broker=kafka, amqp_broker=amqp)

            runtime.handle_kafka_message("orders.created", "123")

        self.assertEqual(
            [
                {"topic": "audit.inline", "payload": "inline orders.created"},
                {"topic": "audit.file", "payload": "file 123"},
            ],
            kafka.published,
        )
        self.assertEqual(
            [{"exchange": "audit", "routing_key": "orders.audit", "payload": "amqp 123"}],
            amqp.published,
        )

    def test_amqp_setup_and_reconnect_reestablish_consumers(self) -> None:
        mocks = load_mock_definitions(
            [
                {
                    "expect": {"amqp": {"exchange": "events", "routing_key": "orders.created"}},
                    "behaviors": [{"publish_amqp": {"exchange": "audit", "routing_key": "x", "payload": "ok"}}],
                }
            ]
        )
        amqp = InMemoryAMQPBroker()
        runtime = MessageBrokerRuntime(mocks, amqp_broker=amqp)

        runtime.start()
        runtime.recover_amqp()

        self.assertEqual(
            [{"exchange": "events", "queue": "orders.created", "routing_key": "orders.created"}],
            amqp.bindings,
        )
        self.assertEqual(2, len(amqp.consumers))
        self.assertEqual(1, amqp.reconnects)


if __name__ == "__main__":
    unittest.main()
