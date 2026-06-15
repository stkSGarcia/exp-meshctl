## Context

The checkpoint defines Kafka and AMQP behavior for a mock service, but the current repository only contains `meshctl.py`, `pyproject.toml`, and CLI tests in `tests/test_meshctl_cli.py`. There is no existing broker runtime, mock loader, or message-publishing abstraction, so this change introduces a new message broker handling surface instead of modifying the mesh resource commands.

## Related Work

> **`mesh-resource-management/add-meshctl-mesh-crud`**: Defines a clear command surface and resource lifecycle scenarios — informs the decision to keep broker behavior behind explicit mock fields and environment gates because the related intent established direct, predictable operations for loaded resources. _(see `mesh-resource-management/add-meshctl-mesh-crud`)_

> **`vault-resource-management/add-vault-resource-management`**: Defines explicit field validation and defaulting for resource inputs — informs the decision to normalize `expect.amqp.queue`, payload source validation, and Kafka override fallback behavior at load/config resolution time because the related intent keeps validation failures deterministic. _(see `vault-resource-management/add-vault-resource-management`)_

> **`runtime-migration-strategies/add-runtime-migration-strategies`**: Defines runtime validation, warnings, and progress behavior — informs the decision to model Kafka/AMQP enablement and AMQP reconnect as runtime state handled outside mock matching because the related intent separates accepted configuration from operational progression. _(see `runtime-migration-strategies/add-runtime-migration-strategies`)_

## Goals / Non-Goals

**Goals:**
- Add configuration objects that resolve Kafka and AMQP environment variables exactly once at startup.
- Extend mock parsing to recognize `expect.kafka`, `expect.amqp`, `publish_kafka`, and `publish_amqp`.
- Share existing template and `*_from_file` payload rendering semantics for broker publish actions.
- Provide deterministic matching that executes every matching behavior in loaded order.
- Isolate Kafka and AMQP client code behind small adapter interfaces so unit tests can run without real brokers.

**Non-Goals:**
- Do not add broker management CLI commands.
- Do not require Kafka or AMQP services for normal test execution.
- Do not guarantee exactly-once delivery semantics beyond broker-client publish/consume behavior.
- Do not persist broker messages in the mesh resource store.

## Decisions

### Add broker adapters behind runtime interfaces

Create broker runtime code separate from `meshctl.py`, with `KafkaBroker` and `AMQPBroker` adapters responsible for connecting, consuming, and publishing. The mock engine should depend on interfaces such as `subscribe`, `publish`, and `close`, allowing tests to use fakes.

Alternatives considered: adding broker logic directly to existing command code. That would couple an always-running message workflow to one-shot CLI operations and make reconnect behavior difficult to test.

### Resolve configuration into side-specific Kafka settings

Parse `HM_KAFKA_*` variables into shared defaults first, then materialize separate producer and consumer settings. SASL enablement is computed after fallback resolution for each side, so partial credentials never enable SASL.

Alternatives considered: resolving settings lazily on each publish or consume. Startup resolution gives consistent behavior across all broker operations and simpler validation.

### Normalize mock definitions during load

During mock load/validation, normalize AMQP queue defaulting, validate required publish fields, and require exactly one payload source for each broker publish action. Store loaded mocks in order and preserve that order during matching.

Alternatives considered: validating during message handling. Load-time validation fails earlier and avoids runtime drops caused by malformed actions.

### Reuse template rendering and file-backed payload utilities

Route `payload_from_file` through the same loader and renderer used by other `*_from_file` fields, then publish the rendered string. Kafka and AMQP contexts should be merged into the active template context before behavior execution.

Alternatives considered: adding broker-specific file loading. Reuse keeps escaping, path handling, and rendering behavior consistent.

### Implement AMQP setup and reconnect in the AMQP adapter

The AMQP adapter should declare exchanges, queues, and bindings for loaded expectations before consuming. On transient disconnect, it should reconnect, re-declare resources, and re-establish consumers using the normalized expectations.

Alternatives considered: relying only on client library auto-recovery. Explicit recovery keeps the contract testable and makes resource setup idempotent.

## Risks / Trade-offs

- Kafka/AMQP dependencies can slow installs or require native libraries -> keep imports lazy or optional until the corresponding broker is enabled.
- Broker integration tests can be flaky if they require live services -> cover config, validation, matching, and adapter calls with fakes; reserve live-broker coverage for optional integration tests.
- Executing all matching behaviors can amplify side effects -> preserve loaded order and document that every match runs for broker expectations.
- Reconnect loops can consume CPU during outages -> use bounded backoff and stop cleanly when the runtime shuts down.

## Migration Plan

1. Add broker configuration, mock schema, runtime adapters, and fake-backed unit tests.
2. Keep Kafka and AMQP disabled by default through `HM_KAFKA_ENABLED=false` and `HM_AMQP_ENABLED=false`.
3. Add dependencies in `pyproject.toml` only if broker runtime modules require them, and keep normal CLI tests independent of live brokers.
4. Roll back by disabling the environment flags; code paths remain inactive when brokers are disabled.

## Open Questions

- Which concrete mock-service entry point should own broker runtime startup, since the current repo does not yet expose one?
- Should Kafka and AMQP client libraries be required dependencies or optional extras?
