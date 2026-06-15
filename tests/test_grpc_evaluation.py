from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hmock import (
    GRPCConfig,
    GRPCExpectation,
    GRPCServerAdapter,
    MockValidationError,
    ReplyGRPCAction,
    build_grpc_context,
    evaluate_mock_definition,
    frame_grpc_message,
    handle_evaluate_http_request,
    load_mock_definitions,
    render_grpc_reply,
    unframe_grpc_message,
    validate_grpc_startup,
)
from hmock.brokers import render_template


class GRPCConfigAndLoadingTests(unittest.TestCase):
    def test_grpc_defaults_to_disabled(self) -> None:
        config = GRPCConfig.from_env({})

        self.assertFalse(config.enabled)
        self.assertEqual("0.0.0.0", config.host)
        self.assertEqual(50051, config.port)
        self.assertEqual((), config.descriptor_set_paths)

    def test_grpc_env_overrides_and_resolves_descriptor_paths(self) -> None:
        config = GRPCConfig.from_env(
            {
                "HM_GRPC_ENABLED": "true",
                "HM_GRPC_HOST": "127.0.0.1",
                "HM_GRPC_PORT": "50052",
                "HM_TEMPLATES_DIR": "/tmp/templates",
                "HM_GRPC_DESCRIPTOR_SET_PATHS": "echo.pb,/abs/other.pb",
            }
        )

        self.assertTrue(config.enabled)
        self.assertEqual("127.0.0.1", config.host)
        self.assertEqual(50052, config.port)
        self.assertEqual((Path("/tmp/templates/echo.pb"), Path("/abs/other.pb")), config.descriptor_set_paths)

    def test_loads_grpc_expectation_and_reply_action(self) -> None:
        mocks = load_mock_definitions(
            {
                "expect": {"grpc": {"service": "example.Echo", "method": "Ping"}},
                "behaviors": [
                    {
                        "reply_grpc": {
                            "payload": '{"message":"{{ .GRPCPayload }}"}',
                            "headers": {"x-request": "{{ .GRPCHeader.Get \"x-request\" }}"},
                        }
                    }
                ],
            }
        )

        self.assertEqual("example.Echo", mocks.grpc[0].service)
        self.assertEqual("Ping", mocks.grpc[0].method)
        self.assertIsInstance(mocks.grpc[0].behaviors[0], ReplyGRPCAction)

    def test_rejects_missing_grpc_fields_and_ambiguous_reply_payloads(self) -> None:
        with self.assertRaises(MockValidationError) as context:
            load_mock_definitions(
                {
                    "expect": {"grpc": {"service": "", "method": ""}},
                    "behaviors": [
                        {
                            "reply_grpc": {
                                "payload": "{}",
                                "payload_from_file": "payload.json",
                            }
                        }
                    ],
                }
            )

        fields = {item["field"] for item in context.exception.errors}
        self.assertIn("mocks[0].expect.grpc.service", fields)
        self.assertIn("mocks[0].expect.grpc.method", fields)

    def test_startup_requires_descriptors_only_for_grpc_behaviors(self) -> None:
        config = GRPCConfig(enabled=True)
        no_grpc = load_mock_definitions({"expect": {"kafka": {"topic": "orders"}}, "behaviors": []})
        validate_grpc_startup(config, no_grpc)

        grpc_mocks = load_mock_definitions(
            {"expect": {"grpc": {"service": "example.Echo", "method": "Ping"}}, "behaviors": []}
        )
        with self.assertRaises(MockValidationError):
            validate_grpc_startup(config, grpc_mocks)


class GRPCRuntimeTests(unittest.TestCase):
    def test_grpc_framing_round_trips_payload(self) -> None:
        framed = frame_grpc_message(b'{"message":"hi"}')

        compressed, payload = unframe_grpc_message(framed)

        self.assertFalse(compressed)
        self.assertEqual(b'{"message":"hi"}', payload)

    def test_grpc_context_exposes_headers_and_payload(self) -> None:
        context = build_grpc_context(
            "example.Echo",
            "Ping",
            frame_grpc_message(b'{"message":"hi"}'),
            {"x-request": "abc"},
        )

        self.assertEqual("example.Echo", context["GRPCService"])
        self.assertEqual("Ping", context["GRPCMethod"])
        self.assertEqual('{"message":"hi"}', context["GRPCPayload"])
        self.assertEqual("abc", render_template('{{ .GRPCHeader.Get "x-request" }}', context))

    def test_grpc_adapter_tracks_disabled_and_enabled_listen_address(self) -> None:
        mocks = load_mock_definitions({"expect": {"kafka": {"topic": "orders"}}, "behaviors": []})
        disabled = GRPCServerAdapter(GRPCConfig(), mocks)
        disabled.start()
        self.assertFalse(disabled.started)

        enabled = GRPCServerAdapter(GRPCConfig(enabled=True, host="127.0.0.1", port=50052), mocks)
        enabled.start()
        try:
            self.assertTrue(enabled.started)
            self.assertEqual("127.0.0.1", enabled.listen_address[0])
        finally:
            enabled.stop()

    def test_grpc_first_match_wins_and_renders_response_headers(self) -> None:
        mocks = load_mock_definitions(
            [
                {
                    "expect": {"grpc": {"service": "example.Echo", "method": "Ping"}},
                    "behaviors": [
                        {
                            "reply_grpc": {
                                "payload": '{"message":"first {{ .GRPCPayload }}"}',
                                "headers": {"x-request": "{{ .GRPCHeader.Get \"x-request\" }}"},
                            }
                        }
                    ],
                },
                {
                    "expect": {"grpc": {"service": "example.Echo", "method": "Ping"}},
                    "behaviors": [{"reply_grpc": {"payload": '{"message":"second"}'}}],
                },
            ]
        )
        adapter = GRPCServerAdapter(GRPCConfig(), mocks)

        response = adapter.handle_unary(
            "example.Echo",
            "Ping",
            frame_grpc_message(b'{"id":"123"}'),
            {"x-request": "abc"},
        )

        self.assertEqual("0", response["headers"]["grpc-status"])
        self.assertEqual("OK", response["headers"]["grpc-message"])
        self.assertEqual("application/grpc", response["headers"]["Content-Type"])
        self.assertEqual("abc", response["headers"]["x-request"])
        _, payload = unframe_grpc_message(response["body"])
        self.assertEqual(b'{"message":"first {"id":"123"}"}', payload)

    def test_render_grpc_reply_supports_file_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            (base_dir / "payload.json").write_text('{"message":"{{ .GRPCMethod }}"}', encoding="utf-8")
            action = ReplyGRPCAction(payload_from_file="payload.json")

            response = render_grpc_reply(
                action,
                {"GRPCMethod": "Ping"},
                base_dir,
                "example.Echo",
                "Ping",
            )

        _, payload = unframe_grpc_message(response["body"])
        self.assertEqual(b'{"message":"Ping"}', payload)


class DryRunEvaluationTests(unittest.TestCase):
    def test_evaluation_rejects_invalid_requests(self) -> None:
        with self.assertRaises(MockValidationError) as context:
            evaluate_mock_definition({"key": "", "expect": {"kafka": {"topic": "orders"}}}, {})

        fields = {item["field"] for item in context.exception.errors}
        self.assertIn("mock.key", fields)
        self.assertIn("context.kafka_context", fields)

    def test_matcher_failure_returns_no_actions(self) -> None:
        result = evaluate_mock_definition(
            {
                "key": "orders",
                "expect": {"kafka": {"topic": "orders.created"}},
                "behaviors": [{"publish_kafka": {"topic": "audit", "payload": "x"}}],
            },
            {"kafka_context": {"topic": "orders.updated", "payload": "123"}},
        )

        self.assertEqual({"expect_passed": False, "actions_performed": []}, result)

    def test_condition_failure_returns_rendered_condition(self) -> None:
        result = evaluate_mock_definition(
            {
                "key": "orders",
                "expect": {"kafka": {"topic": "orders.created"}},
                "condition": ".KafkaPayload == '456'",
                "behaviors": [{"publish_kafka": {"topic": "audit", "payload": "x"}}],
            },
            {"kafka_context": {"topic": "orders.created", "payload": "123"}},
        )

        self.assertTrue(result["expect_passed"])
        self.assertFalse(result["condition_passed"])
        self.assertEqual(".KafkaPayload == '456'", result["condition_rendered"])
        self.assertEqual([], result["actions_performed"])

    def test_renders_supported_actions_in_order_and_omits_unsupported(self) -> None:
        result = evaluate_mock_definition(
            {
                "key": "orders",
                "expect": {"amqp": {"exchange": "events", "routing_key": "orders.created"}},
                "condition": "",
                "behaviors": [
                    {"order": 20, "publish_amqp": {"exchange": "audit", "routing_key": "ignored", "payload": "x"}},
                    {"order": 10, "publish_kafka": {"topic": "audit.{{ .AMQPQueue }}", "payload": "{{ .AMQPPayload }}"}},
                    {
                        "order": 5,
                        "reply_http": {
                            "status_code": 201,
                            "body": "created {{ .AMQPRoutingKey }}",
                        },
                    },
                ],
            },
            {
                "amqp_context": {
                    "exchange": "events",
                    "routing_key": "orders.created",
                    "payload": "payload",
                }
            },
        )

        self.assertTrue(result["expect_passed"])
        self.assertTrue(result["condition_passed"])
        self.assertEqual("", result["condition_rendered"])
        self.assertEqual(
            [
                {
                    "reply_http_action_performed": {
                        "status_code": "201",
                        "content_type": "application/json",
                        "body": "created orders.created",
                        "headers": {
                            "Content-Type": "application/json",
                            "Content-Length": "22",
                        },
                    }
                },
                {
                    "publish_kafka_action_performed": {
                        "topic": "audit.orders.created",
                        "payload": "payload",
                    }
                },
            ],
            result["actions_performed"],
        )

    def test_merges_http_and_grpc_contexts(self) -> None:
        result = evaluate_mock_definition(
            {
                "key": "grpc",
                "expect": {
                    "http": {"method": "POST", "path": "/proxy"},
                    "grpc": {"service": "example.Echo", "method": "Ping"},
                },
                "behaviors": [
                    {
                        "reply_http": {
                            "body": "{{ .HTTPHeader.Get \"x-request\" }} {{ .GRPCPayload }}",
                        }
                    }
                ],
            },
            {
                "http_context": {
                    "method": "POST",
                    "path": "/proxy",
                    "body": "",
                    "headers": {"x-request": "abc"},
                    "query_string": "",
                },
                "grpc_context": {
                    "service": "example.Echo",
                    "method": "Ping",
                    "payload": '{"id":"123"}',
                    "headers": {},
                },
            },
        )

        self.assertEqual("abc {\"id\":\"123\"}", result["actions_performed"][0]["reply_http_action_performed"]["body"])


class EvaluationEndpointTests(unittest.TestCase):
    def test_endpoint_rejects_array_context(self) -> None:
        status, _, body = handle_evaluate_http_request(
            "POST",
            "/api/v1/evaluate",
            json.dumps({"mock": {"key": "x", "expect": {"kafka": {"topic": "orders"}}}, "context": []}).encode(),
        )

        self.assertEqual(400, status)
        self.assertEqual("context", json.loads(body)["errors"][0]["field"])

    def test_endpoint_returns_successful_evaluation(self) -> None:
        status, headers, body = handle_evaluate_http_request(
            "POST",
            "/api/v1/evaluate",
            json.dumps(
                {
                    "mock": {
                        "key": "orders",
                        "expect": {"kafka": {"topic": "orders"}},
                        "behaviors": [{"publish_kafka": {"topic": "audit", "payload": "{{ .KafkaPayload }}"}}],
                    },
                    "context": {"kafka_context": {"topic": "orders", "payload": "123"}},
                }
            ).encode(),
        )

        self.assertEqual(200, status)
        self.assertEqual("application/json", headers["Content-Type"])
        self.assertEqual(
            [
                {
                    "publish_kafka_action_performed": {
                        "topic": "audit",
                        "payload": "123",
                    }
                }
            ],
            json.loads(body)["actions_performed"],
        )


if __name__ == "__main__":
    unittest.main()
