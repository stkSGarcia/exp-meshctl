## Context

The current HMock implementation concentrates Kafka and AMQP configuration, mock loading, matching, condition evaluation, template rendering, and runtime dispatch in `hmock/brokers.py`. Tests in `tests/test_message_brokers.py` cover environment defaults, validation, AMQP queue defaulting, ordered behavior execution, and side effects through in-memory brokers.

The checkpoint adds two surfaces that share the same core primitives: gRPC mocking needs protocol-specific request/response handling, while `/api/v1/evaluate` needs pure matching and rendering without invoking runtime side effects.

## Related Work

> **`runtime-migration-strategies/add-runtime-migration-strategies`**: Defines deterministic validation and ordered execution semantics for runtime workflows — informs dry-run action ordering and preflight validation because this change must report what would happen before running effects.

> **`mesh-resource-management/add-access-security-model`**: Defines environment-driven configuration and validation boundaries — informs gRPC startup validation because descriptor sets are required only when enabled behaviors need protobuf handling.

> **`message-broker-handling/add-kafka-amqp-message-handling`**: Defines channel-specific mock loading, template context, matching, rendering, and broker side effects — informs reuse of mock parsing, context construction, and render helpers because gRPC and dry-run evaluation extend existing mock behavior patterns.

## Goals / Non-Goals

**Goals:**

- Add gRPC environment configuration, descriptor loading, `expect.grpc`, context construction, and `reply_grpc` response rendering.
- Keep gRPC disabled by default and avoid TLS support for this checkpoint.
- Add a pure evaluator used by `POST /api/v1/evaluate` so matching, conditions, and supported action rendering can be tested without Kafka, AMQP, HTTP, or gRPC side effects.
- Preserve existing Kafka and AMQP behavior while sharing validation and rendering helpers where practical.

**Non-Goals:**

- Implement TLS or mutual TLS for gRPC.
- Execute dry-run actions other than returning rendered `reply_http` and `publish_kafka` results.
- Support streaming gRPC methods unless descriptor/framing support can safely treat them as unary calls; the contract for this change is unary request and unary response behavior.
- Replace the current template language.

## Decisions

### Keep protocol models explicit

Add explicit dataclasses for `GRPCConfig`, `GRPCExpectation`, and `ReplyGRPCAction`, mirroring the existing Kafka and AMQP dataclass style. Extend `LoadedMocks` with a `grpc` tuple and helper properties for whether descriptors are required.

Alternative considered: represent all channels as one generic matcher/action shape. That would reduce class count, but it would make channel validation less clear and risk regressions in existing Kafka/AMQP behavior.

### Isolate gRPC descriptor and framing logic

Implement descriptor loading, protobuf JSON conversion, and gRPC length-prefixed frame handling in a focused gRPC module or a contained section separate from broker adapters. Relative descriptor-set paths resolve from `HM_TEMPLATES_DIR`, and startup validates descriptor readability only when gRPC is enabled and loaded mocks contain `expect.grpc` or `reply_grpc` _(see `mesh-resource-management/add-access-security-model`)_.

Alternative considered: parse descriptors lazily on the first request. Lazy parsing would defer startup failures and make mock runs less predictable.

### Use first-match wins for gRPC only

Kafka and AMQP currently execute all matching behaviors in loaded order. gRPC should use first-match wins because a unary RPC produces one response, and multiple responses would be invalid for one request _(see `message-broker-handling/add-kafka-amqp-message-handling`)_.

Alternative considered: execute all matching gRPC behaviors and return the last reply. That hides ambiguous mock definitions and complicates metadata merging.

### Build evaluation around pure functions

Create a reusable evaluator that accepts one mock definition and one merged simulated context, then returns an evaluation result object. The HTTP route should only parse JSON, call validation/evaluation, and serialize the response. The evaluator should call shared matching, condition, template, and payload-from-file helpers but never call runtime adapters or broker clients _(see `runtime-migration-strategies/add-runtime-migration-strategies`)_.

Alternative considered: run the existing runtime with in-memory brokers and inspect captured effects. That would work for Kafka and AMQP but does not cover HTTP replies cleanly and makes "no side effects" dependent on test doubles.

### Render only supported dry-run action results

The evaluator returns dry-run objects for `reply_http` and `publish_kafka` because the checkpoint defines their response shape. Other action types are parsed and skipped without side effects. This keeps the API stable and avoids inventing response contracts for `publish_amqp`, `reply_grpc`, or custom callables.

Alternative considered: include a generic `unsupported_action_performed` entry. That would make the response noisier and contradict the checkpoint requirement to omit unsupported action types.

## Risks / Trade-offs

- New gRPC dependencies may increase install size and test setup complexity -> keep descriptor/protobuf dependencies isolated and add narrow unit tests for framing and JSON conversion.
- Descriptor-based request decoding can fail at runtime for unknown services or methods -> validate configured `(service, method)` pairs during startup when descriptors are required.
- Evaluation context merging can produce key collisions across channels -> build channel-specific template keys (`HTTP*`, `Kafka*`, `AMQP*`, `GRPC*`) rather than merging raw fields directly.
- Existing behavior parser currently ignores HTTP and gRPC actions -> extend parsing carefully with validation tests for required fields and payload-source exclusivity.
- The dry-run endpoint may drift from runtime behavior -> make runtime dispatch and dry-run evaluation share matcher, condition, ordering, and rendering helpers.

## Migration Plan

1. Add tests for new dataclasses and validation while keeping gRPC disabled by default.
2. Extend mock loading and action parsing for `expect.grpc`, `reply_grpc`, `reply_http`, and ordered action metadata.
3. Add gRPC descriptor/framing helpers and server adapter behind `HM_GRPC_ENABLED`.
4. Add the pure evaluator and wire it to `POST /api/v1/evaluate`.
5. Update documentation with gRPC environment variables and evaluation examples.

Rollback is straightforward because gRPC is disabled by default and the evaluation endpoint is additive. Reverting the new route and gRPC config restores the prior Kafka/AMQP-only behavior.

## Open Questions

- Which HTTP server framework should expose `/api/v1/evaluate` if no web framework exists in the current package yet?
- Which gRPC/protobuf Python libraries should be accepted as project dependencies for descriptor-driven JSON conversion?
