## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud
> Extends: vault-resource-management/add-vault-resource-management
> Extends: runtime-migration-strategies/add-runtime-migration-strategies

### Requirement: Kafka environment configuration
The system SHALL enable Kafka handling only when `HM_KAFKA_ENABLED` is true and SHALL resolve Kafka producer and consumer settings from shared defaults with side-specific overrides.

#### Scenario: Kafka defaults are used
- **GIVEN** `HM_KAFKA_ENABLED` is true and no producer or consumer override variables are set
- **WHEN** the system initializes Kafka handling
- **THEN** the Kafka client ID defaults to `hmock`, both producer and consumer broker lists default to `kafka:9092`, TLS defaults to disabled, and SASL is disabled

#### Scenario: Kafka producer and consumer overrides are resolved independently
- **GIVEN** shared Kafka broker, SASL, and TLS defaults are set
- **AND** one or more `HM_KAFKA_PRODUCER_*` or `HM_KAFKA_CONSUMER_*` override variables are set
- **WHEN** the system builds producer and consumer connection settings
- **THEN** each side uses its side-specific value when present and otherwise falls back to the shared default for that setting

#### Scenario: Kafka SASL enablement is side-specific
- **GIVEN** producer and consumer Kafka SASL credentials have been resolved after applying overrides and fallbacks
- **WHEN** the system decides whether to enable SASL
- **THEN** producer SASL is enabled only when the resolved producer username and password are both non-empty
- **AND** consumer SASL is enabled only when the resolved consumer username and password are both non-empty

### Requirement: Kafka expectation handling
The system SHALL support `expect.kafka` mocks that consume messages from topics referenced by loaded mocks, match by topic, evaluate `condition` using Kafka template context, and execute every matching behavior in loaded order.

#### Scenario: Kafka topic consumption is derived from loaded mocks
- **GIVEN** Kafka handling is enabled and loaded mocks contain one or more `expect.kafka` entries
- **WHEN** the runtime starts
- **THEN** the Kafka consumer subscribes to the topics referenced by the loaded `expect.kafka` mocks

#### Scenario: Kafka context is available to conditions and templates
- **GIVEN** a Kafka message is consumed from topic `orders.created` with payload `{"id":"123"}`
- **WHEN** an `expect.kafka` condition or behavior template is evaluated for that message
- **THEN** `.KafkaTopic` is `orders.created`
- **AND** `.KafkaPayload` is `{"id":"123"}`

#### Scenario: Kafka executes all matching behaviors in load order
- **GIVEN** multiple loaded `expect.kafka` behaviors match the same consumed message topic and condition
- **WHEN** the Kafka message is handled
- **THEN** every matching behavior is executed
- **AND** the behaviors execute in their loaded order

### Requirement: Kafka publish behavior
The system SHALL support `publish_kafka` behaviors with a required `topic` and exactly one payload source from `payload` or `payload_from_file`, rendering the selected payload through the standard template rules before publishing.

#### Scenario: Kafka inline payload is published
- **GIVEN** a behavior contains `publish_kafka` with `topic` and `payload`
- **WHEN** the behavior executes
- **THEN** the payload is template-rendered with the active context
- **AND** the rendered payload is published to the configured Kafka producer on the specified topic

#### Scenario: Kafka file-backed payload is published
- **GIVEN** a behavior contains `publish_kafka` with `topic` and `payload_from_file`
- **WHEN** the behavior executes
- **THEN** the payload file is loaded and rendered using the same rules as other `*_from_file` fields
- **AND** the rendered payload is published to the configured Kafka producer on the specified topic

#### Scenario: Kafka publish payload source is required
- **GIVEN** a behavior contains `publish_kafka` without `payload` and without `payload_from_file`
- **WHEN** the mock definition is loaded or validated
- **THEN** the system rejects the behavior with a validation error

### Requirement: AMQP environment configuration
The system SHALL enable AMQP handling only when `HM_AMQP_ENABLED` is true and SHALL connect to the URL configured by `HM_AMQP_URL`, defaulting to `amqp://guest:guest@rabbitmq:5672`.

#### Scenario: AMQP defaults are used
- **GIVEN** `HM_AMQP_ENABLED` is true and `HM_AMQP_URL` is not set
- **WHEN** the system initializes AMQP handling
- **THEN** the AMQP connection URL is `amqp://guest:guest@rabbitmq:5672`

#### Scenario: AMQP remains disabled by default
- **GIVEN** `HM_AMQP_ENABLED` is unset or false
- **WHEN** the system starts
- **THEN** AMQP consumers and publishers are not started

### Requirement: AMQP expectation setup and matching
The system SHALL support `expect.amqp` mocks that declare or verify required broker resources on startup, default an omitted or empty queue to the routing key, expose AMQP template context, and execute every matching behavior in loaded order.

#### Scenario: AMQP queue defaults to routing key
- **GIVEN** an `expect.amqp` mock defines an `exchange` and `routing_key` but omits `queue`
- **WHEN** the mock is loaded
- **THEN** the expectation queue is set to the routing key

#### Scenario: AMQP resources are prepared at startup
- **GIVEN** AMQP handling is enabled and loaded mocks contain `expect.amqp` entries
- **WHEN** the runtime starts
- **THEN** the required exchanges, queues, and bindings exist before consumption begins

#### Scenario: AMQP context is available to conditions and templates
- **GIVEN** an AMQP message is consumed from exchange `events`, routing key `orders.created`, queue `orders.created`, and payload `{"id":"123"}`
- **WHEN** an `expect.amqp` condition or behavior template is evaluated for that message
- **THEN** `.AMQPExchange` is `events`
- **AND** `.AMQPRoutingKey` is `orders.created`
- **AND** `.AMQPQueue` is `orders.created`
- **AND** `.AMQPPayload` is `{"id":"123"}`

#### Scenario: AMQP executes all matching behaviors in load order
- **GIVEN** multiple loaded `expect.amqp` behaviors match the same consumed message and condition
- **WHEN** the AMQP message is handled
- **THEN** every matching behavior is executed
- **AND** the behaviors execute in their loaded order

### Requirement: AMQP reconnect recovery
The AMQP consumer SHALL recover consumption automatically after a transient broker or network disconnect.

#### Scenario: AMQP consumption resumes after reconnect
- **GIVEN** AMQP handling is enabled and a consumer is actively consuming from loaded mocks
- **WHEN** the AMQP connection is interrupted and then becomes available again
- **THEN** the system reconnects
- **AND** the required consumers are re-established without requiring process restart

### Requirement: AMQP publish behavior
The system SHALL support `publish_amqp` behaviors with required `exchange` and `routing_key` fields and exactly one payload source from `payload` or `payload_from_file`, rendering the selected payload through the standard template rules before publishing.

#### Scenario: AMQP inline payload is published
- **GIVEN** a behavior contains `publish_amqp` with `exchange`, `routing_key`, and `payload`
- **WHEN** the behavior executes
- **THEN** the payload is template-rendered with the active context
- **AND** the rendered payload is published to the configured AMQP exchange using the specified routing key

#### Scenario: AMQP file-backed payload is published
- **GIVEN** a behavior contains `publish_amqp` with `exchange`, `routing_key`, and `payload_from_file`
- **WHEN** the behavior executes
- **THEN** the payload file is loaded and rendered using the same rules as other `*_from_file` fields
- **AND** the rendered payload is published to the configured AMQP exchange using the specified routing key

#### Scenario: AMQP publish payload source is required
- **GIVEN** a behavior contains `publish_amqp` without `payload` and without `payload_from_file`
- **WHEN** the mock definition is loaded or validated
- **THEN** the system rejects the behavior with a validation error
