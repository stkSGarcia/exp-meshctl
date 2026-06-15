## Why

The mock service needs first-class broker-driven workflows so tests can consume, match, and publish Kafka and AMQP messages with the same deterministic behavior already expected from loaded mocks. This change defines the contract for enabling broker integrations, resolving connection settings, evaluating message expectations, and publishing inline or file-backed payloads.

## Related Work

### Related Changes
- `add-mesh-lifecycle-topology`: Motivated lifecycle and topology validation for mesh resources; this change complements that structured-resource approach by defining broker setup, matching, and publish behavior for message-driven mocks.
- `add-runtime-migration-strategies`: Motivated explicit validation and operational status for runtime changes; this change similarly makes environment resolution and reconnect behavior explicit for broker runtimes.
- `add-one-shot-operations`: Motivated formal contracts for operational actions; this change extends that action-oriented pattern to `publish_kafka` and `publish_amqp` behaviors.

### Related Specs
- `mesh-resource-management/add-meshctl-mesh-crud`: Covers a command-surface capability for mesh resources; this change reuses its direct requirement/scenario structure but introduces a distinct message broker handling capability.
- `vault-resource-management/add-vault-resource-management`: Covers resource management and validation patterns for vault resources; this change adapts the same explicit field/default style for broker expectation configuration.
- `runtime-migration-strategies/add-runtime-migration-strategies`: Covers runtime validation and operational progression; this change builds on that style for Kafka/AMQP enablement, connection resolution, and transient AMQP recovery.

## What Changes

- Add Kafka environment configuration for shared defaults plus producer/consumer-specific broker, SASL, and TLS overrides.
- Add Kafka expectation handling that consumes messages from referenced topics, exposes Kafka template context, evaluates conditions, and executes every matching behavior in loaded order.
- Add `publish_kafka` behavior with required topic and inline or file-backed template-rendered payload support.
- Add AMQP environment configuration for enablement and connection URL.
- Add AMQP expectation handling with exchange, routing key, queue defaulting, startup resource/binding setup, template context, and loaded-order matching.
- Add transient AMQP reconnect behavior so consumption recovers automatically after disconnects.
- Add `publish_amqp` behavior with required exchange, routing key, and inline or file-backed template-rendered payload support.

## Capabilities

### New Capabilities
- `message-broker-handling`: Defines Kafka and AMQP configuration, expectations, matching semantics, template contexts, publish actions, file-backed payloads, startup setup, and reconnect behavior.

### Modified Capabilities
- None.

## Impact

- Mock configuration and environment parsing for Kafka and AMQP.
- Mock schema/loading for `expect.kafka`, `expect.amqp`, `publish_kafka`, and `publish_amqp`.
- Runtime message consumers and publishers for Kafka and AMQP.
- Template rendering contexts and payload-from-file handling.
- Startup lifecycle for AMQP resource setup and broker reconnect handling.
- Tests covering environment resolution, matching order, publish payload rendering, queue defaulting, AMQP setup, and reconnect recovery.
