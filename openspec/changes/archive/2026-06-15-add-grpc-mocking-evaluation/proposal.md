## Why

HMock can model HTTP, Kafka, and AMQP flows, but it cannot mock gRPC calls or preview mock behavior without triggering real side effects. This change adds gRPC behavior support and a dry-run evaluation endpoint so users can validate matching, conditions, and rendered actions before running mocks against live channels.

## Related Work

### Related Changes

- `add-meshctl-mesh-crud`: established testable resource contracts and validation-first behavior; this change applies the same explicit contract style to mock definition evaluation.
- `add-mesh-lifecycle-topology`: expanded existing workflows with lifecycle-aware validation; this change similarly extends the mock runtime with protocol-aware validation before serving.
- `add-access-security-model`: tightened runtime configuration and validation around sensitive access settings; this change follows that pattern by requiring descriptor configuration only when enabled gRPC behaviors need protobuf decoding.

### Related Specs

- `runtime-migration-strategies/add-runtime-migration-strategies`: defines validation and ordered action semantics for runtime workflows; this change reuses the idea of deterministic, preflightable behavior for dry-run mock evaluation.
- `mesh-resource-management/add-access-security-model`: defines environment-driven configuration and validation boundaries; this change adapts that approach for gRPC enablement, host, port, and descriptor-set configuration.
- `message-broker-handling/add-kafka-amqp-message-handling`: defines channel-specific mock loading, template context, matching, rendering, and broker side effects; this change extends those capabilities to gRPC and adds a no-side-effect evaluator for HTTP, Kafka, AMQP, and gRPC mock definitions.

## What Changes

- Add optional HTTP/2 cleartext gRPC serving controlled by `HM_GRPC_ENABLED`, `HM_GRPC_HOST`, `HM_GRPC_PORT`, and `HM_GRPC_DESCRIPTOR_SET_PATHS`.
- Add `expect.grpc` matching by fully-qualified service name and method name.
- Add gRPC template context values for service, method, JSON payload, and metadata headers.
- Add protobuf descriptor-set loading, inbound request decoding, response JSON encoding, and standard gRPC length-prefixed framing.
- Add `reply_grpc` actions with templated payloads, file-backed payloads, templated metadata headers, and required successful gRPC response headers.
- Add `POST /api/v1/evaluate` to evaluate one mock definition against simulated channel context without executing side effects.
- Add evaluation validation for required mock, matcher, context, AMQP default queue behavior, and supported action rendering.

## Capabilities

### New Capabilities

- `grpc-mock-handling`: Optional gRPC server, descriptor-backed protobuf handling, gRPC matching, gRPC template context, and `reply_grpc` responses.
- `mock-dry-run-evaluation`: API endpoint that validates and evaluates a supplied mock definition against simulated HTTP, Kafka, AMQP, or gRPC context without side effects.

### Modified Capabilities

- None.

## Impact

- Affects mock parsing, validation, matching, context construction, template rendering, and runtime dispatch in `hmock/brokers.py` or new protocol-specific modules.
- Adds an HTTP API surface for `POST /api/v1/evaluate`.
- Adds tests alongside `tests/test_message_brokers.py` for gRPC configuration, descriptor validation, gRPC request/response handling, and dry-run evaluation.
- May add dependencies for cleartext gRPC HTTP/2 serving and protobuf descriptor-based JSON conversion.
