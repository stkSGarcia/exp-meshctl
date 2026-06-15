## ADDED Requirements

> Extends: message-broker-handling/add-kafka-amqp-message-handling
> Extends: runtime-migration-strategies/add-runtime-migration-strategies

### Requirement: evaluation endpoint
The system SHALL expose `POST /api/v1/evaluate` for dry-run evaluation of one mock definition against simulated channel context.

#### Scenario: valid request shape
- **GIVEN** a request body contains `mock` as one mock definition object
- **AND** `context` as one JSON object containing one or more channel context sub-objects
- **WHEN** the client posts to `/api/v1/evaluate`
- **THEN** the endpoint evaluates the mock without executing side effects

#### Scenario: context is not an array
- **GIVEN** a request body contains `context` as an array
- **WHEN** the client posts to `/api/v1/evaluate`
- **THEN** the endpoint returns `400 Bad Request`

### Requirement: evaluation request validation
The system SHALL reject invalid evaluation requests with `400 Bad Request`.

#### Scenario: missing mock key
- **GIVEN** `mock.key` is missing or empty
- **WHEN** the client posts to `/api/v1/evaluate`
- **THEN** the endpoint returns `400 Bad Request`

#### Scenario: unsupported matcher
- **GIVEN** `mock.expect` does not include at least one of `http`, `kafka`, `amqp`, or `grpc`
- **WHEN** the client posts to `/api/v1/evaluate`
- **THEN** the endpoint returns `400 Bad Request`

#### Scenario: missing matcher fields
- **GIVEN** a declared matcher is missing one of its required fields
- **WHEN** the client posts to `/api/v1/evaluate`
- **THEN** the endpoint returns `400 Bad Request`

#### Scenario: missing channel context
- **GIVEN** a mock declares a supported matcher
- **AND** `context` does not include the corresponding channel context object
- **WHEN** the client posts to `/api/v1/evaluate`
- **THEN** the endpoint returns `400 Bad Request`

#### Scenario: AMQP queue default
- **GIVEN** `mock.expect.amqp.exchange` and `mock.expect.amqp.routing_key` are present
- **AND** `mock.expect.amqp.queue` is omitted or empty
- **WHEN** the endpoint evaluates the AMQP matcher
- **THEN** the queue is evaluated as the routing key

### Requirement: simulated channel contexts
The system SHALL merge provided HTTP, Kafka, AMQP, and gRPC simulated context objects into one template context for evaluation.

#### Scenario: HTTP context
- **GIVEN** `context.http_context` includes `method`, `path`, `body`, `headers`, and `query_string`
- **WHEN** the endpoint builds the template context
- **THEN** HTTP matcher and template values are populated from those fields

#### Scenario: Kafka context
- **GIVEN** `context.kafka_context` includes `topic` and `payload`
- **WHEN** the endpoint builds the template context
- **THEN** Kafka matcher and template values are populated from those fields

#### Scenario: AMQP context
- **GIVEN** `context.amqp_context` includes `exchange`, `routing_key`, `queue`, and `payload`
- **WHEN** the endpoint builds the template context
- **THEN** AMQP matcher and template values are populated from those fields

#### Scenario: gRPC context
- **GIVEN** `context.grpc_context` includes `service`, `method`, `payload`, and `headers`
- **WHEN** the endpoint builds the template context
- **THEN** gRPC matcher and template values are populated from those fields

### Requirement: evaluation flow
The system SHALL evaluate channel matching before condition rendering and action rendering.

#### Scenario: matcher fails
- **GIVEN** the simulated channel context does not match the mock expectation
- **WHEN** the endpoint evaluates the request
- **THEN** the response includes `expect_passed: false`
- **AND** `actions_performed` is empty

#### Scenario: empty condition
- **GIVEN** the simulated channel context matches the mock expectation
- **AND** the mock condition is empty or missing
- **WHEN** the endpoint evaluates the request
- **THEN** the condition is treated as passing

#### Scenario: condition fails
- **GIVEN** the simulated channel context matches the mock expectation
- **AND** the rendered condition does not evaluate to true
- **WHEN** the endpoint evaluates the request
- **THEN** the response includes `expect_passed: true`
- **AND** the response includes `condition_passed: false`
- **AND** the response includes the raw rendered condition in `condition_rendered`
- **AND** `actions_performed` is empty

#### Scenario: condition passes
- **GIVEN** the simulated channel context matches the mock expectation
- **AND** the condition passes
- **WHEN** the endpoint evaluates the request
- **THEN** actions are evaluated by ascending `order`
- **AND** no action side effects are executed

### Requirement: evaluation response
The system SHALL return dry-run results with `expect_passed`, `condition_passed`, `condition_rendered`, and `actions_performed`.

#### Scenario: reply HTTP action result
- **GIVEN** matching and condition evaluation pass
- **AND** the mock includes a `reply_http` action
- **WHEN** the endpoint renders actions
- **THEN** `actions_performed` includes a `reply_http_action_performed` result
- **AND** the result includes `status_code`, `content_type`, `body`, and `headers`
- **AND** `status_code` is a string
- **AND** `content_type` defaults to `application/json`
- **AND** generated `Content-Type` and `Content-Length` headers are included

#### Scenario: publish Kafka action result
- **GIVEN** matching and condition evaluation pass
- **AND** the mock includes a `publish_kafka` action
- **WHEN** the endpoint renders actions
- **THEN** `actions_performed` includes a `publish_kafka_action_performed` result with `topic` and `payload`

#### Scenario: unsupported dry-run action
- **GIVEN** matching and condition evaluation pass
- **AND** the mock includes an action other than `reply_http` or `publish_kafka`
- **WHEN** the endpoint renders actions
- **THEN** that action performs no side effect
- **AND** that action is omitted from `actions_performed`
