## 1. Project Structure and Dependencies

- [x] 1.1 Inspect `meshctl.py` and `tests/test_meshctl_cli.py` as the current validation, YAML loading, and test style starting points.
- [x] 1.2 Decide whether broker client libraries belong in `pyproject.toml` as required dependencies or optional extras.
- [x] 1.3 Create a mock-service module structure for broker configuration, mock loading, template rendering, runtime matching, and broker adapters. [extends `mesh-resource-management/add-meshctl-mesh-crud`]

## 2. Broker Configuration

- [x] 2.1 Implement Kafka environment parsing with defaults for `HM_KAFKA_ENABLED`, `HM_KAFKA_CLIENT_ID`, `HM_KAFKA_SEED_BROKERS`, shared SASL credentials, and shared TLS. [extends `runtime-migration-strategies/add-runtime-migration-strategies`]
- [x] 2.2 Implement Kafka producer and consumer override resolution for broker lists, SASL credentials, and TLS settings.
- [x] 2.3 Implement side-specific Kafka SASL enablement after override/fallback resolution.
- [x] 2.4 Implement AMQP environment parsing for `HM_AMQP_ENABLED` and `HM_AMQP_URL`.
- [x] 2.5 Add unit tests for Kafka defaults, Kafka overrides, partial SASL credentials, AMQP defaults, and disabled-by-default behavior.

## 3. Mock Schema and Loading

- [x] 3.1 Extend mock loading to parse `expect.kafka` with topic matching and optional condition evaluation context. [extends `vault-resource-management/add-vault-resource-management`]
- [x] 3.2 Extend mock loading to parse `expect.amqp` with `exchange`, `routing_key`, and `queue` defaulting to `routing_key`.
- [x] 3.3 Extend behavior loading to parse `publish_kafka` with required `topic` and exactly one of `payload` or `payload_from_file`.
- [x] 3.4 Extend behavior loading to parse `publish_amqp` with required `exchange`, `routing_key`, and exactly one of `payload` or `payload_from_file`.
- [x] 3.5 Add validation tests for missing broker publish payload sources, queue defaulting, and invalid required fields.

## 4. Runtime Matching and Template Context

- [x] 4.1 Implement Kafka message handling that consumes topics referenced by loaded mocks and exposes `.KafkaTopic` and `.KafkaPayload`.
- [x] 4.2 Implement AMQP message handling that exposes `.AMQPExchange`, `.AMQPRoutingKey`, `.AMQPQueue`, and `.AMQPPayload`.
- [x] 4.3 Implement loaded-order matching so every matching Kafka behavior executes in order.
- [x] 4.4 Implement loaded-order matching so every matching AMQP behavior executes in order.
- [x] 4.5 Add fake-backed tests proving multiple matching Kafka and AMQP behaviors all execute in loaded order.

## 5. Publish Actions

- [x] 5.1 Implement `publish_kafka` execution with inline payload template rendering and adapter publish calls.
- [x] 5.2 Implement `publish_kafka` execution with `payload_from_file` using the same file loading and rendering rules as other `*_from_file` fields.
- [x] 5.3 Implement `publish_amqp` execution with inline payload template rendering and adapter publish calls.
- [x] 5.4 Implement `publish_amqp` execution with `payload_from_file` using the same file loading and rendering rules as other `*_from_file` fields.
- [x] 5.5 Add tests covering inline and file-backed publish payloads for both brokers.

## 6. AMQP Startup and Reconnect

- [x] 6.1 Implement AMQP startup setup that ensures exchanges, queues, and bindings exist before consumption begins.
- [x] 6.2 Implement AMQP reconnect recovery that reconnects after transient disconnects and re-establishes required consumers.
- [x] 6.3 Add fake-backed tests for AMQP resource setup and reconnect recovery without requiring a live broker.

## 7. Verification

- [x] 7.1 Run the existing test suite and keep `tests/test_meshctl_cli.py` passing.
- [x] 7.2 Run the new broker unit tests for configuration, loading, matching, publishing, setup, and reconnect behavior.
- [x] 7.3 Document how to enable Kafka and AMQP through the new `HM_KAFKA_*` and `HM_AMQP_*` environment variables.
