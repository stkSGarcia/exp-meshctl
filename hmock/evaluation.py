"""Dry-run mock evaluation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .brokers import (
    HeaderMap,
    MockValidationError,
    evaluate_condition,
    render_payload,
    render_template,
    validation_error,
)


SUPPORTED_MATCHERS = ("http", "kafka", "amqp", "grpc")


def evaluate_mock_definition(
    mock: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    base_dir: str | Path = ".",
) -> dict[str, Any]:
    errors = validate_evaluation_request(mock, context)
    if errors:
        raise MockValidationError(errors)

    expect = mock["expect"]
    template_context = build_template_context(context)
    if not match_expectations(expect, context):
        return {"expect_passed": False, "actions_performed": []}

    condition = selected_condition(mock, expect)
    condition_rendered = render_condition(condition, template_context)
    if not evaluate_condition(condition, template_context):
        return {
            "expect_passed": True,
            "condition_passed": False,
            "condition_rendered": condition_rendered,
            "actions_performed": [],
        }

    return {
        "expect_passed": True,
        "condition_passed": True,
        "condition_rendered": condition_rendered,
        "actions_performed": render_dry_run_actions(
            mock.get("behaviors", mock.get("actions", [])),
            template_context,
            Path(base_dir),
        ),
    }


def validate_evaluation_request(
    mock: Mapping[str, Any] | Any,
    context: Mapping[str, Any] | Any,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(mock, Mapping):
        return [validation_error("mock", "Mock definition must be an object", "invalid")]
    if not isinstance(context, Mapping) or isinstance(context, list):
        errors.append(validation_error("context", "Context must be an object", "invalid"))
    if not isinstance(mock.get("key"), str) or not mock.get("key"):
        errors.append(validation_error("mock.key", "Field must be a non-empty string", "required"))
    expect = mock.get("expect")
    if not isinstance(expect, Mapping):
        errors.append(validation_error("mock.expect", "Expectation must be an object", "required"))
        return errors

    declared = [name for name in SUPPORTED_MATCHERS if name in expect]
    if not declared:
        errors.append(
            validation_error(
                "mock.expect",
                "At least one supported matcher is required",
                "required",
            )
        )
        return errors

    if isinstance(context, Mapping):
        for name in declared:
            matcher = expect[name]
            if not isinstance(matcher, Mapping):
                errors.append(validation_error(f"mock.expect.{name}", "Matcher must be an object", "invalid"))
                continue
            errors.extend(required_matcher_field_errors(name, matcher))
            if context_field_name(name) not in context:
                errors.append(
                    validation_error(
                        f"context.{context_field_name(name)}",
                        "Channel context is required for declared matcher",
                        "required",
                    )
                )
    return errors


def required_matcher_field_errors(name: str, matcher: Mapping[str, Any]) -> list[dict[str, str]]:
    field_names = {
        "http": ("method", "path"),
        "kafka": ("topic",),
        "amqp": ("exchange", "routing_key"),
        "grpc": ("service", "method"),
    }[name]
    errors: list[dict[str, str]] = []
    for field_name in field_names:
        if not isinstance(matcher.get(field_name), str) or not matcher.get(field_name):
            errors.append(
                validation_error(
                    f"mock.expect.{name}.{field_name}",
                    "Field must be a non-empty string",
                    "required",
                )
            )
    return errors


def context_field_name(matcher_name: str) -> str:
    return f"{matcher_name}_context"


def build_template_context(context: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    http = mapping_or_empty(context.get("http_context"))
    if http:
        result.update(
            {
                "HTTPMethod": str(http.get("method", "")),
                "HTTPPath": str(http.get("path", "")),
                "HTTPBody": str(http.get("body", "")),
                "HTTPQueryString": str(http.get("query_string", "")),
                "HTTPHeader": HeaderMap(mapping_or_empty(http.get("headers"))),
            }
        )
    kafka = mapping_or_empty(context.get("kafka_context"))
    if kafka:
        result.update(
            {
                "KafkaTopic": str(kafka.get("topic", "")),
                "KafkaPayload": str(kafka.get("payload", "")),
            }
        )
    amqp = mapping_or_empty(context.get("amqp_context"))
    if amqp:
        routing_key = str(amqp.get("routing_key", ""))
        result.update(
            {
                "AMQPExchange": str(amqp.get("exchange", "")),
                "AMQPRoutingKey": routing_key,
                "AMQPQueue": str(amqp.get("queue") or routing_key),
                "AMQPPayload": str(amqp.get("payload", "")),
            }
        )
    grpc = mapping_or_empty(context.get("grpc_context"))
    if grpc:
        result.update(
            {
                "GRPCService": str(grpc.get("service", "")),
                "GRPCMethod": str(grpc.get("method", "")),
                "GRPCPayload": str(grpc.get("payload", "")),
                "GRPCHeader": HeaderMap(mapping_or_empty(grpc.get("headers"))),
            }
        )
    return result


def match_expectations(expect: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    for name in SUPPORTED_MATCHERS:
        if name not in expect:
            continue
        matcher = mapping_or_empty(expect[name])
        channel_context = mapping_or_empty(context.get(context_field_name(name)))
        if not match_one(name, matcher, channel_context):
            return False
    return True


def match_one(name: str, matcher: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    if name == "http":
        return matcher.get("method") == context.get("method") and matcher.get("path") == context.get("path")
    if name == "kafka":
        return matcher.get("topic") == context.get("topic")
    if name == "amqp":
        routing_key = context.get("routing_key")
        expected_queue = matcher.get("queue") or matcher.get("routing_key")
        actual_queue = context.get("queue") or routing_key
        return (
            matcher.get("exchange") == context.get("exchange")
            and matcher.get("routing_key") == routing_key
            and expected_queue == actual_queue
        )
    if name == "grpc":
        return matcher.get("service") == context.get("service") and matcher.get("method") == context.get("method")
    return False


def selected_condition(mock: Mapping[str, Any], expect: Mapping[str, Any]) -> Any:
    condition = mock.get("condition")
    for name in SUPPORTED_MATCHERS:
        matcher = expect.get(name)
        if isinstance(matcher, Mapping) and matcher.get("condition") is not None:
            condition = matcher.get("condition")
    return condition


def render_condition(condition: Any, context: Mapping[str, Any]) -> str:
    if condition is None:
        return ""
    if isinstance(condition, bool):
        return "true" if condition else "false"
    if not isinstance(condition, str):
        return str(condition)
    return render_template(condition, context)


def render_dry_run_actions(
    actions: Any,
    context: Mapping[str, Any],
    base_dir: Path,
) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    rendered: list[dict[str, Any]] = []
    for item in sorted((item for item in actions if isinstance(item, Mapping)), key=action_order):
        if "reply_http" in item and isinstance(item["reply_http"], Mapping):
            rendered.append(render_reply_http_action(item["reply_http"], context, base_dir))
        elif "publish_kafka" in item and isinstance(item["publish_kafka"], Mapping):
            rendered.append(render_publish_kafka_action(item["publish_kafka"], context, base_dir))
    return rendered


def render_reply_http_action(
    value: Mapping[str, Any],
    context: Mapping[str, Any],
    base_dir: Path,
) -> dict[str, Any]:
    content_type = str(value.get("content_type") or "application/json")
    body = render_payload(
        string_or_none(value.get("body", value.get("payload", ""))),
        string_or_none(value.get("body_from_file", value.get("payload_from_file"))),
        context,
        base_dir,
    )
    headers = {
        str(key): render_template(str(item), context)
        for key, item in mapping_or_empty(value.get("headers")).items()
    }
    headers["Content-Type"] = content_type
    headers["Content-Length"] = str(len(body.encode("utf-8")))
    return {
        "reply_http_action_performed": {
            "status_code": str(value.get("status_code", value.get("status", "200"))),
            "content_type": content_type,
            "body": body,
            "headers": headers,
        }
    }


def render_publish_kafka_action(
    value: Mapping[str, Any],
    context: Mapping[str, Any],
    base_dir: Path,
) -> dict[str, Any]:
    return {
        "publish_kafka_action_performed": {
            "topic": render_template(str(value.get("topic", "")), context),
            "payload": render_payload(
                string_or_none(value.get("payload")),
                string_or_none(value.get("payload_from_file")),
                context,
                base_dir,
            ),
        }
    }


def action_order(item: Mapping[str, Any]) -> int:
    try:
        return int(item.get("order", 0))
    except (TypeError, ValueError):
        return 0


def mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
