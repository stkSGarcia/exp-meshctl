## ADDED Requirements

### Requirement: Connection details included when exposure is configured
When `spec.exposure` is present, `create` and `describe` SHALL include `status.connectionDetails` with `host` (string), `port` (integer), and `protocol` (always `"https"`).

#### Scenario: Connection details on create with exposure
- **WHEN** a mesh is created with a valid `spec.exposure` block
- **THEN** the create response includes `status.connectionDetails` with host, port, and `"protocol": "https"`

#### Scenario: Connection details on describe with exposure
- **WHEN** a mesh that has exposure configured is described
- **THEN** the describe response includes `status.connectionDetails`

---

### Requirement: Gateway mode connection details
For `spec.exposure.type = "Gateway"`, the system SHALL compute connection details as follows:
- `host`: `spec.exposure.hostname` if set; otherwise a default value
- `port`: `443`
- `protocol`: `"https"`

#### Scenario: Gateway with hostname
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.hostname` is set
- **THEN** `status.connectionDetails.host` equals `spec.exposure.hostname` and `status.connectionDetails.port` is `443`

#### Scenario: Gateway without hostname uses default host
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.hostname` is absent
- **THEN** `status.connectionDetails.host` is a non-empty default and `status.connectionDetails.port` is `443`

---

### Requirement: DirectPort mode connection details
For `spec.exposure.type = "DirectPort"`, the system SHALL compute connection details as follows:
- `host`: the mesh `name`
- `port`: `spec.exposure.directPort` if set; otherwise a default value
- `protocol`: `"https"`

#### Scenario: DirectPort with directPort set
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.directPort` is set
- **THEN** `status.connectionDetails.host` equals the mesh name and `status.connectionDetails.port` equals `spec.exposure.directPort`

#### Scenario: DirectPort without directPort uses default
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.directPort` is absent
- **THEN** `status.connectionDetails.host` equals the mesh name and `status.connectionDetails.port` is a non-zero default

---

### Requirement: Balancer mode connection details
For `spec.exposure.type = "Balancer"`, the system SHALL compute connection details as follows:
- `host`: `"<name>-external"` where `<name>` is the mesh name
- `port`: `spec.exposure.port` if set; otherwise a default value
- `protocol`: `"https"`

#### Scenario: Balancer with port set
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.port` is set
- **THEN** `status.connectionDetails.host` equals `"<name>-external"` and `status.connectionDetails.port` equals `spec.exposure.port`

#### Scenario: Balancer without port uses default
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.port` is absent
- **THEN** `status.connectionDetails.host` equals `"<name>-external"` and `status.connectionDetails.port` is a non-zero default
