## 1. Data Models and Validation

- [x] 1.1 Extend `hmock/brokers.py` with `GRPCConfig`, `GRPCExpectation`, `ReplyGRPCAction`, and `LoadedMocks.grpc` while preserving existing Kafka/AMQP behavior. [extends `message-broker-handling/add-kafka-amqp-message-handling`]
- [x] 1.2 Extend `hmock/brokers.py` mock parsing to accept `expect.grpc.service`, `expect.grpc.method`, `reply_grpc.payload`, `reply_grpc.payload_from_file`, and `reply_grpc.headers` with required-field and payload-source validation. [extends `message-broker-handling/add-kafka-amqp-message-handling`]
- [x] 1.3 Add `GRPCConfig.from_env` handling for `HM_GRPC_ENABLED`, `HM_GRPC_PORT`, `HM_GRPC_HOST`, and `HM_GRPC_DESCRIPTOR_SET_PATHS`, including defaults and relative descriptor path resolution from `HM_TEMPLATES_DIR`. [extends `mesh-resource-management/add-access-security-model`]
- [x] 1.4 Add validation tests in `tests/test_message_brokers.py` or a focused gRPC test module for gRPC defaults, descriptor requirement rules, required gRPC matcher fields, and `reply_grpc` payload-source exclusivity.

## 2. gRPC Runtime

- [x] 2.1 Add descriptor-set loading and service/method lookup helpers for configured gRPC expectations, with startup failures for missing, unreadable, invalid, or incomplete descriptors when descriptors are required.
- [x] 2.2 Add protobuf JSON decode/encode helpers for unary gRPC requests and responses using standard gRPC length-prefixed framing.
- [x] 2.3 Add gRPC request context construction with `GRPCService`, `GRPCMethod`, `GRPCPayload`, and `GRPCHeader.Get "key"` support, sharing template rendering conventions from `hmock/brokers.py`. [extends `message-broker-handling/add-kafka-amqp-message-handling`]
- [x] 2.4 Add a cleartext HTTP/2 gRPC server adapter that starts only when `HM_GRPC_ENABLED` is true and handles unary requests with first-match-wins behavior.
- [x] 2.5 Render `reply_grpc` responses with required `grpc-status`, `grpc-message`, `Content-Type`, custom rendered metadata headers, and length-prefixed protobuf bodies.
- [x] 2.6 Add gRPC runtime tests for disabled default startup, configured host/port, first-match-wins, metadata context, inline payload rendering, file payload rendering, and response headers.

## 3. Dry-Run Evaluation Core

- [x] 3.1 Create a pure evaluation helper that accepts one mock definition and one `context` object, validates `mock.key`, supported matchers, matcher required fields, and matching channel context.
- [x] 3.2 Implement simulated HTTP, Kafka, AMQP, and gRPC context merging into template context keys while keeping AMQP queue defaulting to routing key when omitted. [extends `message-broker-handling/add-kafka-amqp-message-handling`]
- [x] 3.3 Implement evaluation flow so channel matching runs before condition rendering, empty conditions pass, failed conditions return `condition_rendered`, and no side effects execute. [extends `runtime-migration-strategies/add-runtime-migration-strategies`]
- [x] 3.4 Render dry-run action results only for `reply_http` and `publish_kafka`, sorting by `order`, defaulting HTTP content type to `application/json`, and including generated `Content-Type` and `Content-Length` headers.
- [x] 3.5 Add evaluator tests for validation failures, matcher failures, condition failures, condition success, action ordering, `reply_http` results, `publish_kafka` results, omitted unsupported action types, and no broker/client side effects.

## 4. HTTP Endpoint

- [x] 4.1 Add an HTTP route for `POST /api/v1/evaluate` that parses JSON, calls the pure evaluator, returns `400 Bad Request` on validation failure, and serializes successful evaluation responses.
- [x] 4.2 Add endpoint tests covering valid request shape, array `context` rejection, missing required fields, missing channel context, and successful dry-run responses.

## 5. Documentation and Verification

- [x] 5.1 Update `docs/broker-handling.md` or add focused docs for gRPC environment variables, descriptor-set behavior, `expect.grpc`, gRPC template context, and `reply_grpc`.
- [x] 5.2 Document `POST /api/v1/evaluate` request/response examples for HTTP, Kafka, AMQP, and gRPC simulated contexts.
- [x] 5.3 Run the full test suite with `pytest` and fix regressions in existing Kafka/AMQP tests.
- [x] 5.4 Run `openspec status --change "add-grpc-mocking-evaluation"` and confirm all proposal artifacts are complete before applying the change.
