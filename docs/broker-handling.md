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
