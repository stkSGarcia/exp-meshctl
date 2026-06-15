## ADDED Requirements

> Extends: message-broker-handling/add-kafka-amqp-message-handling
> Extends: mesh-resource-management/add-access-security-model

### Requirement: gRPC runtime configuration
The system SHALL support an optional cleartext HTTP/2 gRPC mock server controlled by environment configuration.

#### Scenario: disabled by default
- **GIVEN** no gRPC environment variables are set
- **WHEN** the mock runtime starts
- **THEN** the gRPC server is not started

#### Scenario: configured listen address
- **GIVEN** `HM_GRPC_ENABLED` is `true`, `HM_GRPC_HOST` is `127.0.0.1`, and `HM_GRPC_PORT` is `50052`
- **WHEN** the mock runtime starts
- **THEN** the gRPC server listens on `127.0.0.1:50052` using HTTP/2 cleartext
- **AND** the server does not require or configure TLS

### Requirement: descriptor-set loading
The system SHALL load comma-separated protobuf descriptor-set files from `HM_GRPC_DESCRIPTOR_SET_PATHS` when enabled gRPC behaviors require protobuf decoding or encoding.

#### Scenario: relative descriptor paths
- **GIVEN** `HM_GRPC_DESCRIPTOR_SET_PATHS` contains a relative path
- **WHEN** the system loads descriptor sets
- **THEN** the relative path is resolved from `HM_TEMPLATES_DIR`

#### Scenario: descriptors required by loaded behavior
- **GIVEN** gRPC is enabled
- **AND** at least one loaded behavior uses `expect.grpc` or `reply_grpc`
- **WHEN** `HM_GRPC_DESCRIPTOR_SET_PATHS` is missing, unreadable, or invalid
- **THEN** startup fails with a validation error

#### Scenario: descriptors not required
- **GIVEN** gRPC is enabled
- **AND** no loaded behavior uses `expect.grpc` or `reply_grpc`
- **WHEN** `HM_GRPC_DESCRIPTOR_SET_PATHS` is empty
- **THEN** startup succeeds

### Requirement: gRPC expectation matching
The system SHALL match gRPC behaviors by the tuple of fully-qualified protobuf service name and method name.

#### Scenario: matching service and method
- **GIVEN** a mock definition with `expect.grpc.service` set to `example.Echo` and `expect.grpc.method` set to `Ping`
- **WHEN** a gRPC request targets service `example.Echo` and method `Ping`
- **THEN** the expectation matches

#### Scenario: different method
- **GIVEN** a mock definition with `expect.grpc.service` set to `example.Echo` and `expect.grpc.method` set to `Ping`
- **WHEN** a gRPC request targets service `example.Echo` and method `Pong`
- **THEN** the expectation does not match

#### Scenario: first matching behavior wins
- **GIVEN** multiple loaded gRPC behaviors match the same service and method
- **WHEN** a matching gRPC request is received
- **THEN** only the first matching behavior is used to produce the response

### Requirement: gRPC template context
The system SHALL expose matched gRPC request values to templates using `.GRPCService`, `.GRPCMethod`, `.GRPCPayload`, and `.GRPCHeader`.

#### Scenario: protobuf request decoded to JSON
- **GIVEN** a descriptor set for the target service and method
- **WHEN** the system receives a standard length-prefixed protobuf gRPC request body
- **THEN** `.GRPCPayload` contains the request body converted to a JSON string

#### Scenario: metadata headers exposed
- **GIVEN** a gRPC request includes HTTP/2 headers and gRPC metadata
- **WHEN** the system builds the template context
- **THEN** `.GRPCHeader.Get "key"` resolves the metadata value for `key`

### Requirement: gRPC reply rendering
The system SHALL support `reply_grpc` actions that render JSON response payloads and metadata headers into standard gRPC responses.

#### Scenario: inline response payload
- **GIVEN** a matching gRPC behavior has `reply_grpc.payload`
- **WHEN** the behavior is rendered
- **THEN** the payload is treated as a template
- **AND** the rendered JSON is encoded as the configured protobuf response message
- **AND** the response body uses standard gRPC length-prefixed framing

#### Scenario: file response payload
- **GIVEN** a matching gRPC behavior has `reply_grpc.payload_from_file`
- **WHEN** the behavior is rendered
- **THEN** the file content is loaded from the templates directory when relative
- **AND** the file content is rendered as the response payload template

#### Scenario: response headers
- **GIVEN** a matching gRPC behavior has `reply_grpc.headers`
- **WHEN** the response is returned
- **THEN** the response includes `grpc-status: 0`
- **AND** the response includes `grpc-message: OK`
- **AND** the response includes `Content-Type: application/grpc`
- **AND** custom `reply_grpc.headers` values are rendered and included as metadata headers
