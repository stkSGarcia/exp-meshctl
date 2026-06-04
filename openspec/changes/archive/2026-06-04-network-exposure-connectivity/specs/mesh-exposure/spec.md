## ADDED Requirements

### Requirement: Exposure is optional
`spec.exposure` is optional. When absent, no external access is configured and `status.connectionDetails` SHALL be absent from create and describe output.

#### Scenario: No exposure configured
- **WHEN** a mesh is created or described without `spec.exposure`
- **THEN** the output does not include `status.connectionDetails`

---

### Requirement: Exposure type required when exposure is present
When `spec.exposure` is present, `spec.exposure.type` SHALL be required and non-null.

#### Scenario: Missing exposure type
- **WHEN** `spec.exposure` is present but `spec.exposure.type` is missing, null, or empty
- **THEN** output an error with `field = "spec.exposure.type"` and `type = "required"`

---

### Requirement: Exposure type must be valid
`spec.exposure.type` SHALL be one of `"Gateway"`, `"DirectPort"`, or `"Balancer"`. Any other value is invalid.

#### Scenario: Invalid exposure type
- **WHEN** `spec.exposure.type` is set to an unrecognized value
- **THEN** output an error with `field = "spec.exposure.type"` and `type = "invalid"`

---

### Requirement: Exposure type field allowlist
Each exposure type restricts which sub-fields are allowed. Fields not allowed for the selected type SHALL be rejected.

| Type | Allowed Fields |
|---|---|
| `"Gateway"` | `hostname`, `annotations` |
| `"DirectPort"` | `port`, `directPort` |
| `"Balancer"` | `port` |

Use the full dot-path for forbidden-field errors (e.g., `spec.exposure.directPort`).

#### Scenario: Forbidden field for Gateway
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.directPort` is set
- **THEN** output an error with `field = "spec.exposure.directPort"` and `type = "forbidden"`

#### Scenario: Forbidden field for Balancer
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.hostname` is set
- **THEN** output an error with `field = "spec.exposure.hostname"` and `type = "forbidden"`

#### Scenario: Forbidden field for DirectPort
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.annotations` is set
- **THEN** output an error with `field = "spec.exposure.annotations"` and `type = "forbidden"`

---

### Requirement: Exposure field types and defaults
The exposure sub-fields SHALL have the following types and behaviors:

| Field | Type | Default | Applicable Types |
|---|---|---|---|
| `spec.exposure.hostname` | string | none | Gateway only |
| `spec.exposure.annotations` | map string→string | none | Gateway only |
| `spec.exposure.port` | integer | has a default | DirectPort, Balancer |
| `spec.exposure.directPort` | integer | none | DirectPort only |

`spec.exposure.annotations` SHALL be preserved as-is in output.

#### Scenario: Annotations preserved
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.annotations` contains key-value pairs
- **THEN** the output includes `spec.exposure.annotations` with all pairs unchanged

