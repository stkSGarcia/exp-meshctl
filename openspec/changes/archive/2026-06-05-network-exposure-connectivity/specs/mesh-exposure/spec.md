## ADDED Requirements

### Requirement: Exposure field is optional
`spec.exposure` is optional. When omitted, no external access is configured and `status.connectionDetails` SHALL be absent from all output.

#### Scenario: No exposure configured
- **WHEN** a mesh is created without `spec.exposure`
- **THEN** the output does not include `status.connectionDetails`

---

### Requirement: Exposure type is required when exposure is present
When `spec.exposure` is present, `spec.exposure.type` SHALL be required and SHALL be one of `"Gateway"`, `"DirectPort"`, or `"Balancer"`. Missing, null, or empty `type` SHALL produce a `required` error. Any unrecognized value SHALL produce an `invalid` error.

#### Scenario: Missing exposure type
- **WHEN** `spec.exposure` is present but `spec.exposure.type` is absent or null
- **THEN** output `{"errors":[{"field":"spec.exposure.type","type":"required","message":"<msg>"}]}`

#### Scenario: Invalid exposure type
- **WHEN** `spec.exposure.type` is set to an unrecognized value (e.g., `"NodePort"`)
- **THEN** output `{"errors":[{"field":"spec.exposure.type","type":"invalid","message":"<msg>"}]}`

#### Scenario: Valid Gateway type accepted
- **WHEN** `spec.exposure.type` is `"Gateway"`
- **THEN** the exposure section is accepted for further field validation

#### Scenario: Valid DirectPort type accepted
- **WHEN** `spec.exposure.type` is `"DirectPort"`
- **THEN** the exposure section is accepted for further field validation

#### Scenario: Valid Balancer type accepted
- **WHEN** `spec.exposure.type` is `"Balancer"`
- **THEN** the exposure section is accepted for further field validation

---

### Requirement: Gateway mode allowed fields
When `spec.exposure.type` is `"Gateway"`, only `hostname` (string, optional) and `annotations` (map of string to string, optional) are permitted. Any other sub-field SHALL produce a `forbidden` error using the full dot-path.

#### Scenario: Gateway with hostname and annotations
- **WHEN** `spec.exposure.type` is `"Gateway"` and `hostname` and `annotations` are provided
- **THEN** the values are accepted and preserved in output

#### Scenario: Gateway with forbidden field
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.port` is present
- **THEN** output `{"errors":[{"field":"spec.exposure.port","type":"forbidden","message":"<msg>"}]}`

#### Scenario: Annotations map preserved
- **WHEN** `spec.exposure.annotations` contains key-value pairs
- **THEN** the output preserves the mapping exactly as provided

---

### Requirement: DirectPort mode allowed fields
When `spec.exposure.type` is `"DirectPort"`, only `port` (integer, has a default) and `directPort` (integer, optional) are permitted. Any other sub-field SHALL produce a `forbidden` error using the full dot-path.

#### Scenario: DirectPort with forbidden field
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.hostname` is present
- **THEN** output `{"errors":[{"field":"spec.exposure.hostname","type":"forbidden","message":"<msg>"}]}`

#### Scenario: DirectPort with port and directPort
- **WHEN** `spec.exposure.type` is `"DirectPort"` and both `port` and `directPort` are provided
- **THEN** the values are accepted and used for connection detail computation

---

### Requirement: Balancer mode allowed fields
When `spec.exposure.type` is `"Balancer"`, only `port` (integer, has a default) is permitted. Any other sub-field SHALL produce a `forbidden` error using the full dot-path.

#### Scenario: Balancer with forbidden field
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.directPort` is present
- **THEN** output `{"errors":[{"field":"spec.exposure.directPort","type":"forbidden","message":"<msg>"}]}`

#### Scenario: Balancer with port
- **WHEN** `spec.exposure.type` is `"Balancer"` and `port` is provided
- **THEN** the value is accepted and used for connection detail computation

---

### Requirement: Connection details computed when exposure is configured
When exposure is configured, `create` and `describe` SHALL include `status.connectionDetails` with `host` (string), `port` (integer), and `protocol` set to `"https"`.

| Mode | `host` | `port` |
|---|---|---|
| Gateway | `spec.exposure.hostname` if set, else a default value | `443` |
| DirectPort | `"<name>"` (mesh metadata name) | `spec.exposure.directPort` if set, else default |
| Balancer | `"<name>-external"` | `spec.exposure.port` if set, else default |

#### Scenario: Gateway connection details with hostname
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.hostname` is `"example.com"`
- **THEN** `status.connectionDetails.host` is `"example.com"`, `port` is `443`, `protocol` is `"https"`

#### Scenario: Gateway connection details without hostname
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.hostname` is absent
- **THEN** `status.connectionDetails.host` is a non-empty default, `port` is `443`, `protocol` is `"https"`

#### Scenario: DirectPort connection details with directPort
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.directPort` is `8443`
- **THEN** `status.connectionDetails.host` is `"<mesh-name>"`, `port` is `8443`, `protocol` is `"https"`

#### Scenario: DirectPort connection details without directPort
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `directPort` is absent
- **THEN** `status.connectionDetails.host` is `"<mesh-name>"`, `port` is the default port value, `protocol` is `"https"`

#### Scenario: Balancer connection details with port
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.port` is `9000`
- **THEN** `status.connectionDetails.host` is `"<mesh-name>-external"`, `port` is `9000`, `protocol` is `"https"`

#### Scenario: Balancer connection details without port
- **WHEN** `spec.exposure.type` is `"Balancer"` and `port` is absent
- **THEN** `status.connectionDetails.host` is `"<mesh-name>-external"`, `port` is the default port value, `protocol` is `"https"`

### Related Scenarios

**`implement-meshctl/mesh-management/mesh-describe/existing-mesh`** — When the named mesh exists, output the full resource JSON including all defaulted spec fields and `status`. _(matched on: )_
