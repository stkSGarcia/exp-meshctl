# Kafka and AMQP Broker Handling

Kafka and AMQP handling is disabled by default. Enable only the broker integrations needed for a mock-service run.

## Kafka

Set `HM_KAFKA_ENABLED=true` to enable Kafka consume and publish handling.

| Variable | Default | Meaning |
| --- | --- | --- |
| `HM_KAFKA_ENABLED` | `false` | Enables Kafka consumers and publishers. |
| `HM_KAFKA_CLIENT_ID` | `hmock` | Kafka client ID. |
| `HM_KAFKA_SEED_BROKERS` | `kafka:9092` | Comma-separated shared broker list. |
| `HM_KAFKA_SASL_USERNAME` | empty | Shared SASL username. |
| `HM_KAFKA_SASL_PASSWORD` | empty | Shared SASL password. |
| `HM_KAFKA_TLS_ENABLED` | `false` | Shared TLS toggle. |

Producer-specific settings override the shared values when set:

| Variable | Meaning |
| --- | --- |
| `HM_KAFKA_PRODUCER_SEED_BROKERS` | Producer broker list. |
| `HM_KAFKA_SASL_PRODUCER_USERNAME` | Producer SASL username. |
| `HM_KAFKA_SASL_PRODUCER_PASSWORD` | Producer SASL password. |
| `HM_KAFKA_TLS_PRODUCER_ENABLED` | Producer TLS toggle. |

Consumer-specific settings override the shared values when set:

| Variable | Meaning |
| --- | --- |
| `HM_KAFKA_CONSUMER_SEED_BROKERS` | Consumer broker list. |
| `HM_KAFKA_SASL_CONSUMER_USERNAME` | Consumer SASL username. |
| `HM_KAFKA_SASL_CONSUMER_PASSWORD` | Consumer SASL password. |
| `HM_KAFKA_TLS_CONSUMER_ENABLED` | Consumer TLS toggle. |

SASL is enabled separately for producer and consumer after overrides are resolved, and only when that side has both username and password.

## AMQP

Set `HM_AMQP_ENABLED=true` to enable AMQP consume and publish handling.

| Variable | Default | Meaning |
| --- | --- | --- |
| `HM_AMQP_ENABLED` | `false` | Enables AMQP consumers and publishers. |
| `HM_AMQP_URL` | `amqp://guest:guest@rabbitmq:5672` | AMQP connection URL. |

AMQP expectations prepare required exchanges, queues, and bindings before consumption. When an AMQP expectation omits `queue`, the routing key is used as the queue name.

## gRPC

gRPC handling is disabled by default. Enable it only when a mock-service run needs to serve unary gRPC requests.

| Variable | Default | Meaning |
| --- | --- | --- |
| `HM_GRPC_ENABLED` | `false` | Enables the gRPC mock server. |
| `HM_GRPC_PORT` | `50051` | gRPC listen port. |
| `HM_GRPC_HOST` | `0.0.0.0` | gRPC listen address. |
| `HM_GRPC_DESCRIPTOR_SET_PATHS` | empty | Comma-separated protobuf descriptor-set files used for request and response conversion. |

The gRPC server uses HTTP/2 cleartext and does not configure TLS. Relative descriptor-set paths are resolved from `HM_TEMPLATES_DIR`. When gRPC is enabled and loaded mocks use `expect.grpc` or `reply_grpc`, startup requires readable, valid descriptor sets that define the configured service and method. If gRPC is enabled but no loaded mock uses gRPC matching or replies, descriptor configuration is optional.

gRPC expectations match by fully-qualified service name and method:

```yaml
key: echo-grpc
expect:
  grpc:
    service: example.Echo
    method: Ping
behaviors:
  - reply_grpc:
      payload: '{"message":"{{ .GRPCPayload }}"}'
      headers:
        x-request-id: '{{ .GRPCHeader.Get "x-request-id" }}'
```

gRPC template context includes:

| Template value | Meaning |
| --- | --- |
| `.GRPCService` | Matched service name. |
| `.GRPCMethod` | Matched method name. |
| `.GRPCPayload` | Request body converted from protobuf to JSON. |
| `.GRPCHeader.Get "key"` | HTTP/2 headers and gRPC metadata lookup. |

`reply_grpc` supports either `payload` or `payload_from_file`. The rendered JSON payload is encoded as the configured protobuf response message and returned with standard gRPC length-prefixed framing. Responses always include `grpc-status: 0`, `grpc-message: OK`, and `Content-Type: application/grpc`, plus rendered custom metadata headers.

## Dry-Run Evaluation

`POST /api/v1/evaluate` evaluates one mock definition against simulated channel context without executing side effects. The request body is a JSON object with `mock` and `context` fields. `context` is a single object, not an array, and may contain any combination of `http_context`, `kafka_context`, `amqp_context`, and `grpc_context`.

Kafka example:

```json
{
  "mock": {
    "key": "orders",
    "expect": {"kafka": {"topic": "orders.created"}},
    "behaviors": [
      {"publish_kafka": {"topic": "audit", "payload": "{{ .KafkaPayload }}"}}
    ]
  },
  "context": {
    "kafka_context": {"topic": "orders.created", "payload": "{\"id\":\"123\"}"}
  }
}
```

Successful response:

```json
{
  "expect_passed": true,
  "condition_passed": true,
  "condition_rendered": "",
  "actions_performed": [
    {
      "publish_kafka_action_performed": {
        "topic": "audit",
        "payload": "{\"id\":\"123\"}"
      }
    }
  ]
}
```

HTTP and gRPC contexts can be evaluated together:

```json
{
  "mock": {
    "key": "proxy",
    "expect": {
      "http": {"method": "POST", "path": "/proxy"},
      "grpc": {"service": "example.Echo", "method": "Ping"}
    },
    "behaviors": [
      {"reply_http": {"status_code": 200, "body": "{{ .HTTPHeader.Get \"x-request\" }} {{ .GRPCPayload }}"}}
    ]
  },
  "context": {
    "http_context": {
      "method": "POST",
      "path": "/proxy",
      "body": "",
      "headers": {"x-request": "abc"},
      "query_string": ""
    },
    "grpc_context": {
      "service": "example.Echo",
      "method": "Ping",
      "payload": "{\"id\":\"123\"}",
      "headers": {"x-request": "abc"}
    }
  }
}
```

AMQP evaluation requires `exchange` and `routing_key`. If `queue` is omitted or empty, evaluation uses the routing key as the queue.

If channel matching fails, the endpoint returns `expect_passed: false` with no actions. If the condition fails, it returns `expect_passed: true`, `condition_passed: false`, the rendered condition string, and no actions. When matching and condition evaluation pass, actions are sorted by `order`; only `reply_http` and `publish_kafka` produce dry-run entries.
