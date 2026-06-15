"""Kafka and AMQP mock handling.

The module keeps broker clients behind small adapter methods so the core
configuration, loading, matching, rendering, and reconnect behavior can be
tested without live Kafka or AMQP services.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}
DEFAULT_KAFKA_BROKERS = "kafka:9092"
DEFAULT_KAFKA_CLIENT_ID = "hmock"
DEFAULT_AMQP_URL = "amqp://guest:guest@rabbitmq:5672"
TEMPLATE_RE = re.compile(r"{{\s*\.?([A-Za-z_][A-Za-z0-9_]*)\s*}}")
CONDITION_VAR_RE = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)")


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
class PublishKafkaAction:
    topic: str
    payload: str | None = None
    payload_from_file: str | None = None


@dataclass(frozen=True)
class PublishAMQPAction:
    exchange: str
    routing_key: str
    payload: str | None = None
    payload_from_file: str | None = None


BrokerAction = PublishKafkaAction | PublishAMQPAction | Callable[[dict[str, Any]], Any]


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
class LoadedMocks:
    kafka: tuple[KafkaExpectation, ...] = ()
    amqp: tuple[AMQPExpectation, ...] = ()
    base_dir: Path = Path(".")

    @property
    def kafka_topics(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(expectation.topic for expectation in self.kafka))


class MockValidationError(ValueError):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        self.errors = sorted(errors, key=lambda item: item["field"])
        super().__init__("mock validation failed")


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


def first_non_empty(value: str | None, fallback: str) -> str:
    if value is None or value == "":
        return fallback
    return value


def parse_broker_list(value: str) -> tuple[str, ...]:
    brokers = tuple(item.strip() for item in value.split(",") if item.strip())
    return brokers or (DEFAULT_KAFKA_BROKERS,)


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
        except MockValidationError as exc:
            errors.extend(exc.errors)

    if errors:
        raise MockValidationError(errors)
    return LoadedMocks(tuple(kafka), tuple(amqp), Path(base_dir))


def parse_expectation(document: Mapping[str, Any], index: int) -> KafkaExpectation | AMQPExpectation | None:
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


def validation_error(field: str, message: str, kind: str) -> dict[str, str]:
    return {"field": field, "message": message, "type": kind}
