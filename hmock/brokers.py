"""Kafka and AMQP mock handling.

The module keeps broker clients behind small adapter methods so the core
configuration, loading, matching, rendering, and reconnect behavior can be
tested without live Kafka or AMQP services.
"""

from __future__ import annotations

import ast
import os
import re
import struct
from concurrent import futures
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}
DEFAULT_KAFKA_BROKERS = "kafka:9092"
DEFAULT_KAFKA_CLIENT_ID = "hmock"
DEFAULT_AMQP_URL = "amqp://guest:guest@rabbitmq:5672"
DEFAULT_GRPC_HOST = "0.0.0.0"
DEFAULT_GRPC_PORT = 50051
TEMPLATE_RE = re.compile(r"{{\s*\.?([A-Za-z_][A-Za-z0-9_]*)\s*}}")
HEADER_GET_RE = re.compile(r'{{\s*\.([A-Za-z_][A-Za-z0-9_]*)\.Get\s+"([^"]+)"\s*}}')
CONDITION_VAR_RE = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)")


class HeaderMap:
    def __init__(self, values: Mapping[str, Any] | None = None) -> None:
        self._values = {
            str(key).lower(): str(value)
            for key, value in (values or {}).items()
        }

    def Get(self, key: str) -> str:
        return self._values.get(key.lower(), "")

    def as_dict(self) -> dict[str, str]:
        return dict(self._values)


@dataclass(frozen=True)
class KafkaSideConfig:
    seed_brokers: tuple[str, ...] = (DEFAULT_KAFKA_BROKERS,)
    sasl_username: str = ""
    sasl_password: str = ""
    tls_enabled: bool = False

    @property
    def sasl_enabled(self) -> bool:
        return bool(self.sasl_username and self.sasl_password)


@dataclass(frozen=True)
class KafkaConfig:
    enabled: bool = False
    client_id: str = DEFAULT_KAFKA_CLIENT_ID
    producer: KafkaSideConfig = field(default_factory=KafkaSideConfig)
    consumer: KafkaSideConfig = field(default_factory=KafkaSideConfig)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> KafkaConfig:
        values = os.environ if env is None else env
        shared_brokers = parse_broker_list(values.get("HM_KAFKA_SEED_BROKERS", DEFAULT_KAFKA_BROKERS))
        shared_username = values.get("HM_KAFKA_SASL_USERNAME", "")
        shared_password = values.get("HM_KAFKA_SASL_PASSWORD", "")
        shared_tls = parse_bool(values.get("HM_KAFKA_TLS_ENABLED"), default=False)

        def side_config(prefix: str) -> KafkaSideConfig:
            return KafkaSideConfig(
                seed_brokers=parse_broker_list(
                    first_non_empty(
                        values.get(f"HM_KAFKA_{prefix}_SEED_BROKERS"),
                        ",".join(shared_brokers),
                    )
                ),
                sasl_username=first_non_empty(
                    values.get(f"HM_KAFKA_SASL_{prefix}_USERNAME"),
                    shared_username,
                ),
                sasl_password=first_non_empty(
                    values.get(f"HM_KAFKA_SASL_{prefix}_PASSWORD"),
                    shared_password,
                ),
                tls_enabled=parse_bool(
                    values.get(f"HM_KAFKA_TLS_{prefix}_ENABLED"),
                    default=shared_tls,
                ),
            )

        return cls(
            enabled=parse_bool(values.get("HM_KAFKA_ENABLED"), default=False),
            client_id=first_non_empty(values.get("HM_KAFKA_CLIENT_ID"), DEFAULT_KAFKA_CLIENT_ID),
            producer=side_config("PRODUCER"),
            consumer=side_config("CONSUMER"),
        )


@dataclass(frozen=True)
class AMQPConfig:
    enabled: bool = False
    url: str = DEFAULT_AMQP_URL

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AMQPConfig:
        values = os.environ if env is None else env
        return cls(
            enabled=parse_bool(values.get("HM_AMQP_ENABLED"), default=False),
            url=first_non_empty(values.get("HM_AMQP_URL"), DEFAULT_AMQP_URL),
        )


@dataclass(frozen=True)
class GRPCConfig:
    enabled: bool = False
    host: str = DEFAULT_GRPC_HOST
    port: int = DEFAULT_GRPC_PORT
    descriptor_set_paths: tuple[Path, ...] = ()

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> GRPCConfig:
        values = os.environ if env is None else env
        templates_dir = Path(first_non_empty(values.get("HM_TEMPLATES_DIR"), "."))
        return cls(
            enabled=parse_bool(values.get("HM_GRPC_ENABLED"), default=False),
            host=first_non_empty(values.get("HM_GRPC_HOST"), DEFAULT_GRPC_HOST),
            port=parse_int(values.get("HM_GRPC_PORT"), default=DEFAULT_GRPC_PORT),
            descriptor_set_paths=parse_descriptor_set_paths(
                values.get("HM_GRPC_DESCRIPTOR_SET_PATHS", ""),
                templates_dir,
            ),
        )


@dataclass(frozen=True)
class PublishKafkaAction:
    topic: str
    payload: str | None = None
    payload_from_file: str | None = None
    order: int = 0


@dataclass(frozen=True)
class PublishAMQPAction:
    exchange: str
    routing_key: str
    payload: str | None = None
    payload_from_file: str | None = None
    order: int = 0


@dataclass(frozen=True)
class ReplyHTTPAction:
    status_code: str = "200"
    content_type: str = "application/json"
    body: str | None = ""
    body_from_file: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    order: int = 0


@dataclass(frozen=True)
class ReplyGRPCAction:
    payload: str | None = None
    payload_from_file: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    order: int = 0


BrokerAction = PublishKafkaAction | PublishAMQPAction | ReplyHTTPAction | ReplyGRPCAction | Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class KafkaExpectation:
    topic: str
    condition: str | bool | None = None
    behaviors: tuple[BrokerAction, ...] = ()


@dataclass(frozen=True)
class AMQPExpectation:
    exchange: str
    routing_key: str
    queue: str
    condition: str | bool | None = None
    behaviors: tuple[BrokerAction, ...] = ()


@dataclass(frozen=True)
class GRPCExpectation:
    service: str
    method: str
    condition: str | bool | None = None
    behaviors: tuple[BrokerAction, ...] = ()


@dataclass(frozen=True)
class LoadedMocks:
    kafka: tuple[KafkaExpectation, ...] = ()
    amqp: tuple[AMQPExpectation, ...] = ()
    grpc: tuple[GRPCExpectation, ...] = ()
    base_dir: Path = Path(".")

    @property
    def kafka_topics(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(expectation.topic for expectation in self.kafka))

    @property
    def requires_grpc_descriptors(self) -> bool:
        return bool(self.grpc) or any(
            isinstance(behavior, ReplyGRPCAction)
            for expectation in (*self.kafka, *self.amqp, *self.grpc)
            for behavior in expectation.behaviors
        )


class MockValidationError(ValueError):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        self.errors = sorted(errors, key=lambda item: item["field"])
        super().__init__("mock validation failed")


class GRPCDescriptorError(ValueError):
    pass


class InMemoryKafkaBroker:
    def __init__(self) -> None:
        self.subscriptions: list[tuple[tuple[str, ...], Callable[[str, str], Any]]] = []
        self.published: list[dict[str, str]] = []
        self.closed = False

    def subscribe(self, topics: Iterable[str], callback: Callable[[str, str], Any]) -> None:
        self.subscriptions.append((tuple(topics), callback))

    def publish(self, topic: str, payload: str) -> None:
        self.published.append({"topic": topic, "payload": payload})

    def close(self) -> None:
        self.closed = True


class InMemoryAMQPBroker:
    def __init__(self) -> None:
        self.bindings: list[dict[str, str]] = []
        self.consumers: list[dict[str, Any]] = []
        self.published: list[dict[str, str]] = []
        self.reconnects = 0
        self.closed = False

    def ensure_binding(self, exchange: str, queue: str, routing_key: str) -> None:
        binding = {"exchange": exchange, "queue": queue, "routing_key": routing_key}
        if binding not in self.bindings:
            self.bindings.append(binding)

    def consume(self, queue: str, callback: Callable[[str, str, str, str], Any]) -> None:
        self.consumers.append({"queue": queue, "callback": callback})

    def publish(self, exchange: str, routing_key: str, payload: str) -> None:
        self.published.append(
            {"exchange": exchange, "routing_key": routing_key, "payload": payload}
        )

    def reconnect(self) -> None:
        self.reconnects += 1

    def close(self) -> None:
        self.closed = True


class MessageBrokerRuntime:
    def __init__(
        self,
        mocks: LoadedMocks,
        kafka_broker: Any | None = None,
        amqp_broker: Any | None = None,
    ) -> None:
        self.mocks = mocks
        self.kafka_broker = kafka_broker
        self.amqp_broker = amqp_broker

    def start(self) -> None:
        if self.kafka_broker is not None and self.mocks.kafka_topics:
            self.kafka_broker.subscribe(self.mocks.kafka_topics, self.handle_kafka_message)
        if self.amqp_broker is not None:
            self.setup_amqp()
            self.subscribe_amqp()

    def setup_amqp(self) -> None:
        if self.amqp_broker is None:
            return
        for expectation in self.mocks.amqp:
            self.amqp_broker.ensure_binding(
                expectation.exchange,
                expectation.queue,
                expectation.routing_key,
            )

    def subscribe_amqp(self) -> None:
        if self.amqp_broker is None:
            return
        for queue in dict.fromkeys(expectation.queue for expectation in self.mocks.amqp):
            self.amqp_broker.consume(queue, self.handle_amqp_message)

    def recover_amqp(self) -> None:
        if self.amqp_broker is None:
            return
        self.amqp_broker.reconnect()
        self.setup_amqp()
        self.subscribe_amqp()

    def handle_kafka_message(self, topic: str, payload: str) -> list[BrokerAction]:
        context = {"KafkaTopic": topic, "KafkaPayload": payload}
        executed: list[BrokerAction] = []
        for expectation in self.mocks.kafka:
            if expectation.topic != topic:
                continue
            if not evaluate_condition(expectation.condition, context):
                continue
            for behavior in expectation.behaviors:
                self.execute_behavior(behavior, context)
                executed.append(behavior)
        return executed

    def handle_amqp_message(
        self,
        exchange: str,
        routing_key: str,
        queue: str,
        payload: str,
    ) -> list[BrokerAction]:
        context = {
            "AMQPExchange": exchange,
            "AMQPRoutingKey": routing_key,
            "AMQPQueue": queue,
            "AMQPPayload": payload,
        }
        executed: list[BrokerAction] = []
        for expectation in self.mocks.amqp:
            if expectation.exchange != exchange:
                continue
            if expectation.routing_key != routing_key:
                continue
            if expectation.queue != queue:
                continue
            if not evaluate_condition(expectation.condition, context):
                continue
            for behavior in expectation.behaviors:
                self.execute_behavior(behavior, context)
                executed.append(behavior)
        return executed

    def execute_behavior(self, behavior: BrokerAction, context: Mapping[str, Any]) -> None:
        if isinstance(behavior, PublishKafkaAction):
            if self.kafka_broker is None:
                return
            self.kafka_broker.publish(
                behavior.topic,
                render_payload(behavior.payload, behavior.payload_from_file, context, self.mocks.base_dir),
            )
            return
        if isinstance(behavior, PublishAMQPAction):
            if self.amqp_broker is None:
                return
            self.amqp_broker.publish(
                behavior.exchange,
                behavior.routing_key,
                render_payload(behavior.payload, behavior.payload_from_file, context, self.mocks.base_dir),
            )
            return
        behavior(dict(context))

    def close(self) -> None:
        if self.kafka_broker is not None and hasattr(self.kafka_broker, "close"):
            self.kafka_broker.close()
        if self.amqp_broker is not None and hasattr(self.amqp_broker, "close"):
            self.amqp_broker.close()


def parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def parse_int(value: str | None, *, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def first_non_empty(value: str | None, fallback: str) -> str:
    if value is None or value == "":
        return fallback
    return value


def parse_broker_list(value: str) -> tuple[str, ...]:
    brokers = tuple(item.strip() for item in value.split(",") if item.strip())
    return brokers or (DEFAULT_KAFKA_BROKERS,)


def parse_descriptor_set_paths(value: str, base_dir: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for item in value.split(","):
        stripped = item.strip()
        if not stripped:
            continue
        path = Path(stripped)
        paths.append(path if path.is_absolute() else base_dir / path)
    return tuple(paths)


def load_mock_definitions(
    documents: Mapping[str, Any] | Iterable[Mapping[str, Any]],
    *,
    base_dir: str | Path = ".",
) -> LoadedMocks:
    if isinstance(documents, Mapping):
        document_list = [documents]
    else:
        document_list = list(documents)

    kafka: list[KafkaExpectation] = []
    amqp: list[AMQPExpectation] = []
    grpc: list[GRPCExpectation] = []
    errors: list[dict[str, str]] = []
    for index, document in enumerate(document_list):
        if not isinstance(document, Mapping):
            errors.append(validation_error(f"mocks[{index}]", "Mock definition must be an object", "invalid"))
            continue
        try:
            expectation = parse_expectation(document, index)
            if isinstance(expectation, KafkaExpectation):
                kafka.append(expectation)
            elif isinstance(expectation, AMQPExpectation):
                amqp.append(expectation)
            elif isinstance(expectation, GRPCExpectation):
                grpc.append(expectation)
        except MockValidationError as exc:
            errors.extend(exc.errors)

    if errors:
        raise MockValidationError(errors)
    return LoadedMocks(tuple(kafka), tuple(amqp), tuple(grpc), Path(base_dir))


def parse_expectation(document: Mapping[str, Any], index: int) -> KafkaExpectation | AMQPExpectation | GRPCExpectation | None:
    expect = document.get("expect")
    if not isinstance(expect, Mapping):
        return None
    condition = document.get("condition")
    if "kafka" in expect:
        kafka = expect["kafka"]
        if not isinstance(kafka, Mapping):
            raise MockValidationError(
                [validation_error(f"mocks[{index}].expect.kafka", "Kafka expectation must be an object", "invalid")]
            )
        errors = require_strings(
            [(kafka.get("topic"), f"mocks[{index}].expect.kafka.topic")]
        )
        if errors:
            raise MockValidationError(errors)
        topic = kafka["topic"]
        if kafka.get("condition") is not None:
            condition = kafka.get("condition")
        behaviors = parse_behaviors(document.get("behaviors", document.get("actions", [])), f"mocks[{index}].behaviors")
        return KafkaExpectation(topic=topic, condition=condition, behaviors=behaviors)
    if "amqp" in expect:
        amqp = expect["amqp"]
        if not isinstance(amqp, Mapping):
            raise MockValidationError(
                [validation_error(f"mocks[{index}].expect.amqp", "AMQP expectation must be an object", "invalid")]
            )
        errors = require_strings(
            [
                (amqp.get("exchange"), f"mocks[{index}].expect.amqp.exchange"),
                (amqp.get("routing_key"), f"mocks[{index}].expect.amqp.routing_key"),
            ]
        )
        if errors:
            raise MockValidationError(errors)
        exchange = amqp["exchange"]
        routing_key = amqp["routing_key"]
        queue_value = amqp.get("queue")
        queue = routing_key if queue_value in (None, "") else required_string(queue_value, f"mocks[{index}].expect.amqp.queue")
        if amqp.get("condition") is not None:
            condition = amqp.get("condition")
        behaviors = parse_behaviors(document.get("behaviors", document.get("actions", [])), f"mocks[{index}].behaviors")
        return AMQPExpectation(
            exchange=exchange,
            routing_key=routing_key,
            queue=queue,
            condition=condition,
            behaviors=behaviors,
        )
    if "grpc" in expect:
        grpc = expect["grpc"]
        if not isinstance(grpc, Mapping):
            raise MockValidationError(
                [validation_error(f"mocks[{index}].expect.grpc", "gRPC expectation must be an object", "invalid")]
            )
        errors = require_strings(
            [
                (grpc.get("service"), f"mocks[{index}].expect.grpc.service"),
                (grpc.get("method"), f"mocks[{index}].expect.grpc.method"),
            ]
        )
        if errors:
            raise MockValidationError(errors)
        if grpc.get("condition") is not None:
            condition = grpc.get("condition")
        behaviors = parse_behaviors(document.get("behaviors", document.get("actions", [])), f"mocks[{index}].behaviors")
        return GRPCExpectation(
            service=grpc["service"],
            method=grpc["method"],
            condition=condition,
            behaviors=behaviors,
        )
    return None


def parse_behaviors(value: Any, path: str) -> tuple[BrokerAction, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise MockValidationError([validation_error(path, "Behaviors must be an array", "invalid")])
    behaviors: list[BrokerAction] = []
    errors: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            errors.append(validation_error(f"{path}[{index}]", "Behavior must be an object", "invalid"))
            continue
        try:
            behavior = parse_behavior(item, f"{path}[{index}]")
            if behavior is not None:
                behaviors.append(behavior)
        except MockValidationError as exc:
            errors.extend(exc.errors)
    if errors:
        raise MockValidationError(errors)
    return tuple(behaviors)


def parse_behavior(item: Mapping[str, Any], path: str) -> BrokerAction | None:
    order = parse_int(str(item.get("order")) if item.get("order") is not None else None, default=0)
    if "publish_kafka" in item:
        value = require_mapping(item["publish_kafka"], f"{path}.publish_kafka", "Kafka publish must be an object")
        errors = require_strings([(value.get("topic"), f"{path}.publish_kafka.topic")])
        errors.extend(payload_source_errors(value, f"{path}.publish_kafka"))
        if errors:
            raise MockValidationError(errors)
        return PublishKafkaAction(
            topic=value["topic"],
            payload=string_or_none(value.get("payload"), f"{path}.publish_kafka.payload"),
            payload_from_file=string_or_none(
                value.get("payload_from_file"),
                f"{path}.publish_kafka.payload_from_file",
            ),
            order=order,
        )
    if "publish_amqp" in item:
        value = require_mapping(item["publish_amqp"], f"{path}.publish_amqp", "AMQP publish must be an object")
        errors = require_strings(
            [
                (value.get("exchange"), f"{path}.publish_amqp.exchange"),
                (value.get("routing_key"), f"{path}.publish_amqp.routing_key"),
            ]
        )
        errors.extend(payload_source_errors(value, f"{path}.publish_amqp"))
        if errors:
            raise MockValidationError(errors)
        return PublishAMQPAction(
            exchange=value["exchange"],
            routing_key=value["routing_key"],
            payload=string_or_none(value.get("payload"), f"{path}.publish_amqp.payload"),
            payload_from_file=string_or_none(
                value.get("payload_from_file"),
                f"{path}.publish_amqp.payload_from_file",
            ),
            order=order,
        )
    if "reply_http" in item:
        value = require_mapping(item["reply_http"], f"{path}.reply_http", "HTTP reply must be an object")
        has_body = value.get("body") is not None or value.get("payload") is not None
        has_file = value.get("body_from_file") is not None or value.get("payload_from_file") is not None
        if has_body and has_file:
            raise MockValidationError(
                [validation_error(f"{path}.reply_http", "at most one inline body or body_from_file is allowed", "invalid")]
            )
        headers = string_map(value.get("headers", {}), f"{path}.reply_http.headers")
        body_value = value.get("body", value.get("payload", ""))
        file_value = value.get("body_from_file", value.get("payload_from_file"))
        return ReplyHTTPAction(
            status_code=str(value.get("status_code", value.get("status", "200"))),
            content_type=first_non_empty(string_or_none(value.get("content_type"), f"{path}.reply_http.content_type"), "application/json"),
            body=string_or_none(body_value, f"{path}.reply_http.body"),
            body_from_file=string_or_none(file_value, f"{path}.reply_http.body_from_file"),
            headers=headers,
            order=order,
        )
    if "reply_grpc" in item:
        value = require_mapping(item["reply_grpc"], f"{path}.reply_grpc", "gRPC reply must be an object")
        errors = payload_source_errors(value, f"{path}.reply_grpc")
        if errors:
            raise MockValidationError(errors)
        headers = string_map(value.get("headers", {}), f"{path}.reply_grpc.headers")
        return ReplyGRPCAction(
            payload=string_or_none(value.get("payload"), f"{path}.reply_grpc.payload"),
            payload_from_file=string_or_none(
                value.get("payload_from_file"),
                f"{path}.reply_grpc.payload_from_file",
            ),
            headers=headers,
            order=order,
        )
    return None


def payload_source_errors(value: Mapping[str, Any], path: str) -> list[dict[str, str]]:
    has_payload = value.get("payload") is not None
    has_file = value.get("payload_from_file") is not None
    if has_payload == has_file:
        return [validation_error(path, "exactly one of payload or payload_from_file is required", "invalid")]
    return []


def render_payload(
    payload: str | None,
    payload_from_file: str | None,
    context: Mapping[str, Any],
    base_dir: Path,
) -> str:
    if payload_from_file is not None:
        path = Path(payload_from_file)
        if not path.is_absolute():
            path = base_dir / path
        payload = path.read_text(encoding="utf-8")
    if payload is None:
        raise ValueError("payload or payload_from_file is required")
    return render_template(payload, context)


def render_template(template: str, context: Mapping[str, Any]) -> str:
    def replace_header_get(match: re.Match[str]) -> str:
        value = context.get(match.group(1))
        if hasattr(value, "Get"):
            return str(value.Get(match.group(2)))
        if isinstance(value, Mapping):
            return str(value.get(match.group(2), value.get(match.group(2).lower(), "")))
        return ""

    template = HEADER_GET_RE.sub(replace_header_get, template)

    def replace(match: re.Match[str]) -> str:
        return str(context.get(match.group(1), ""))

    return TEMPLATE_RE.sub(replace, template)


def evaluate_condition(condition: str | bool | None, context: Mapping[str, Any]) -> bool:
    if condition is None:
        return True
    if isinstance(condition, bool):
        return condition
    if not isinstance(condition, str):
        return False
    stripped = condition.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    expression = CONDITION_VAR_RE.sub(lambda match: repr(context.get(match.group(1), "")), stripped)
    try:
        parsed = ast.parse(expression, mode="eval")
        if not is_safe_expression(parsed):
            return False
        return bool(eval(compile(parsed, "<condition>", "eval"), {"__builtins__": {}}, {}))
    except Exception:
        rendered = render_template(stripped, context).strip()
        return rendered.lower() not in FALSE_VALUES


def is_safe_expression(node: ast.AST) -> bool:
    allowed = (
        ast.Expression,
        ast.BoolOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Constant,
        ast.And,
        ast.Or,
        ast.Not,
        ast.Eq,
        ast.NotEq,
        ast.In,
        ast.NotIn,
        ast.Load,
        ast.List,
        ast.Tuple,
    )
    return all(isinstance(child, allowed) for child in ast.walk(node))


def require_mapping(value: Any, path: str, message: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MockValidationError([validation_error(path, message, "invalid")])
    return value


def required_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise MockValidationError([validation_error(path, "Field must be a non-empty string", "required")])
    return value


def require_strings(fields: Iterable[tuple[Any, str]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for value, path in fields:
        if not isinstance(value, str) or not value:
            errors.append(validation_error(path, "Field must be a non-empty string", "required"))
    return errors


def string_or_none(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MockValidationError([validation_error(path, "Field must be a string", "invalid")])
    return value


def string_map(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise MockValidationError([validation_error(path, "Field must be a string map", "invalid")])
    errors: list[dict[str, str]] = []
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            errors.append(validation_error(path, "Field must be a string map", "invalid"))
            continue
        result[key] = item
    if errors:
        raise MockValidationError(errors)
    return result


def validation_error(field: str, message: str, kind: str) -> dict[str, str]:
    return {"field": field, "message": message, "type": kind}


def validate_grpc_startup(config: GRPCConfig, mocks: LoadedMocks) -> None:
    if not config.enabled or not mocks.requires_grpc_descriptors:
        return
    if not config.descriptor_set_paths:
        raise MockValidationError(
            [validation_error("HM_GRPC_DESCRIPTOR_SET_PATHS", "descriptor-set paths are required for gRPC mocks", "required")]
        )
    load_grpc_descriptors(config.descriptor_set_paths, mocks)


class GRPCDescriptorRegistry:
    def __init__(self, pool: Any, message_factory: Any, json_format: Any) -> None:
        self.pool = pool
        self.message_factory = message_factory
        self.json_format = json_format

    def method_descriptors(self, service: str, method: str) -> tuple[Any, Any]:
        service_descriptor = self.pool.FindServiceByName(service)
        method_descriptor = service_descriptor.FindMethodByName(method)
        if method_descriptor is None:
            raise GRPCDescriptorError(f"unknown gRPC method: {service}/{method}")
        return method_descriptor.input_type, method_descriptor.output_type

    def decode_request_json(self, service: str, method: str, payload: bytes) -> str:
        input_type, _ = self.method_descriptors(service, method)
        message_class = self.message_factory.GetMessageClass(input_type)
        message = message_class()
        message.ParseFromString(payload)
        return self.json_format.MessageToJson(message, preserving_proto_field_name=True)

    def encode_response_json(self, service: str, method: str, payload_json: str) -> bytes:
        _, output_type = self.method_descriptors(service, method)
        message_class = self.message_factory.GetMessageClass(output_type)
        message = message_class()
        self.json_format.Parse(payload_json, message)
        return message.SerializeToString()


def load_grpc_descriptors(
    descriptor_set_paths: Iterable[Path],
    mocks: LoadedMocks | None = None,
) -> GRPCDescriptorRegistry:
    try:
        from google.protobuf import descriptor_pb2, descriptor_pool, json_format, message_factory
    except Exception as exc:  # pragma: no cover - depends on optional install
        raise MockValidationError(
            [validation_error("HM_GRPC_DESCRIPTOR_SET_PATHS", "protobuf support is not installed", "invalid")]
        ) from exc

    pool = descriptor_pool.DescriptorPool()
    for path in descriptor_set_paths:
        try:
            raw = path.read_bytes()
            descriptor_set = descriptor_pb2.FileDescriptorSet()
            descriptor_set.ParseFromString(raw)
            for file_descriptor in descriptor_set.file:
                pool.Add(file_descriptor)
        except Exception as exc:
            raise MockValidationError(
                [validation_error(str(path), "descriptor-set file is missing, unreadable, or invalid", "invalid")]
            ) from exc

    registry = GRPCDescriptorRegistry(pool, message_factory, json_format)
    if mocks is not None:
        for expectation in mocks.grpc:
            try:
                registry.method_descriptors(expectation.service, expectation.method)
            except Exception as exc:
                raise MockValidationError(
                    [
                        validation_error(
                            f"{expectation.service}/{expectation.method}",
                            "descriptor set does not define the configured gRPC service and method",
                            "invalid",
                        )
                    ]
                ) from exc
    return registry


def frame_grpc_message(payload: bytes, *, compressed: bool = False) -> bytes:
    return struct.pack(">BI", 1 if compressed else 0, len(payload)) + payload


def unframe_grpc_message(data: bytes) -> tuple[bool, bytes]:
    if len(data) < 5:
        raise ValueError("gRPC frame is too short")
    compressed, length = struct.unpack(">BI", data[:5])
    payload = data[5:]
    if len(payload) != length:
        raise ValueError("gRPC frame length does not match payload")
    return bool(compressed), payload


def decode_grpc_payload_json(
    framed_body: bytes,
    service: str,
    method: str,
    registry: GRPCDescriptorRegistry | None = None,
) -> str:
    compressed, payload = unframe_grpc_message(framed_body)
    if compressed:
        raise ValueError("compressed gRPC messages are not supported")
    if registry is None:
        return payload.decode("utf-8")
    return registry.decode_request_json(service, method, payload)


def encode_grpc_payload_json(
    payload_json: str,
    service: str,
    method: str,
    registry: GRPCDescriptorRegistry | None = None,
) -> bytes:
    if registry is None:
        payload = payload_json.encode("utf-8")
    else:
        payload = registry.encode_response_json(service, method, payload_json)
    return frame_grpc_message(payload)


def build_grpc_context(
    service: str,
    method: str,
    framed_body: bytes,
    headers: Mapping[str, Any] | None = None,
    registry: GRPCDescriptorRegistry | None = None,
) -> dict[str, Any]:
    return {
        "GRPCService": service,
        "GRPCMethod": method,
        "GRPCPayload": decode_grpc_payload_json(framed_body, service, method, registry),
        "GRPCHeader": HeaderMap(headers),
    }


def render_grpc_reply(
    action: ReplyGRPCAction,
    context: Mapping[str, Any],
    base_dir: Path,
    service: str,
    method: str,
    registry: GRPCDescriptorRegistry | None = None,
) -> dict[str, Any]:
    rendered_payload = render_payload(action.payload, action.payload_from_file, context, base_dir)
    headers = {
        "grpc-status": "0",
        "grpc-message": "OK",
        "Content-Type": "application/grpc",
    }
    headers.update({key: render_template(value, context) for key, value in action.headers.items()})
    return {
        "headers": headers,
        "body": encode_grpc_payload_json(rendered_payload, service, method, registry),
    }


class GRPCServerAdapter:
    def __init__(
        self,
        config: GRPCConfig,
        mocks: LoadedMocks,
        registry: GRPCDescriptorRegistry | None = None,
    ) -> None:
        self.config = config
        self.mocks = mocks
        self.registry = registry
        self.started = False
        self.listen_address: tuple[str, int] | None = None
        self._server: Any | None = None

    def start(self) -> None:
        if not self.config.enabled:
            return
        validate_grpc_startup(self.config, self.mocks)
        try:
            import grpc  # type: ignore
        except Exception:
            grpc = None
        if grpc is not None:
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
            server.add_generic_rpc_handlers((self._generic_rpc_handler(grpc),))
            bound_port = server.add_insecure_port(f"{self.config.host}:{self.config.port}")
            server.start()
            self._server = server
            self.listen_address = (self.config.host, bound_port or self.config.port)
        else:
            self.listen_address = (self.config.host, self.config.port)
        self.started = True

    def stop(self, grace: float | None = None) -> None:
        if self._server is not None:
            self._server.stop(grace)
        self.started = False

    def _generic_rpc_handler(self, grpc_module: Any) -> Any:
        adapter = self

        class Handler(grpc_module.GenericRpcHandler):
            def service(self, handler_call_details: Any) -> Any:
                service, method = split_grpc_method_path(handler_call_details.method)
                if not service or not method:
                    return None

                def unary_unary(request: bytes, context: Any) -> bytes:
                    response = adapter.handle_unary(
                        service,
                        method,
                        frame_grpc_message(request),
                        dict(handler_call_details.invocation_metadata or ()),
                    )
                    if response is None:
                        context.set_code(grpc_module.StatusCode.NOT_FOUND)
                        context.set_details("No matching gRPC mock")
                        return b""
                    headers = response["headers"]
                    metadata = [
                        (key, value)
                        for key, value in headers.items()
                        if key.lower() not in {"content-type", "grpc-status", "grpc-message"}
                    ]
                    if metadata:
                        context.send_initial_metadata(metadata)
                    _, payload = unframe_grpc_message(response["body"])
                    return payload

                return grpc_module.unary_unary_rpc_method_handler(
                    unary_unary,
                    request_deserializer=lambda value: value,
                    response_serializer=lambda value: value,
                )

        return Handler()

    def handle_unary(
        self,
        service: str,
        method: str,
        framed_body: bytes,
        headers: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        context = build_grpc_context(service, method, framed_body, headers, self.registry)
        for expectation in self.mocks.grpc:
            if expectation.service != service or expectation.method != method:
                continue
            if not evaluate_condition(expectation.condition, context):
                continue
            for behavior in sorted(expectation.behaviors, key=behavior_order):
                if isinstance(behavior, ReplyGRPCAction):
                    return render_grpc_reply(
                        behavior,
                        context,
                        self.mocks.base_dir,
                        service,
                        method,
                        self.registry,
                    )
            return None
        return None


def behavior_order(behavior: BrokerAction) -> int:
    return int(getattr(behavior, "order", 0))


def split_grpc_method_path(path: str) -> tuple[str, str]:
    parts = path.strip("/").split("/")
    if len(parts) != 2:
        return "", ""
    return parts[0], parts[1]
