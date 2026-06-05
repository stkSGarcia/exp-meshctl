## MODIFIED Requirements

### Requirement: Success output — create and describe
The system SHALL print the full resource JSON with `metadata`, `spec` (all defaulted fields), and `status`. When `spec.exposure` is configured, the `status` block SHALL include `connectionDetails`. When `spec.management.enabled` is `true`, the `status` block SHALL include `managementConnectionDetails`. Both detail objects contain `host` (string), `port` (integer), and `protocol: "https"`.

#### Scenario: Create success output with exposure
- **WHEN** create succeeds and `spec.exposure` is configured
- **THEN** output includes `status.connectionDetails` with `host`, `port`, and `protocol`

#### Scenario: Create success output without exposure
- **WHEN** create succeeds and `spec.exposure` is absent
- **THEN** output does not include `status.connectionDetails`

#### Scenario: Create success output with management enabled
- **WHEN** create succeeds and `spec.management.enabled` is `true`
- **THEN** output includes `status.managementConnectionDetails` with `host: "<name>-admin"`, `port: 9990`, `protocol: "https"`

#### Scenario: Create success output without management enabled
- **WHEN** `spec.management.enabled` is `false` or absent
- **THEN** output does not include `status.managementConnectionDetails`

---

## ADDED Requirements

### Requirement: Management endpoint field
`spec.management.enabled` SHALL be a boolean that defaults to `false`. It is immutable after create.

#### Scenario: Management defaults to false
- **WHEN** `spec.management.enabled` is not specified
- **THEN** the persisted resource has `spec.management.enabled = false`

#### Scenario: Management enabled on create
- **WHEN** `spec.management.enabled` is `true` in the create YAML
- **THEN** the resource is persisted with `spec.management.enabled = true`

---

### Requirement: Management endpoint immutability
Changing `spec.management.enabled` on `update` SHALL be rejected with an `immutable` error.

#### Scenario: Attempt to change management.enabled on update
- **WHEN** an update YAML provides a different value for `spec.management.enabled` than what was set at creation
- **THEN** output `{"errors":[{"field":"spec.management.enabled","type":"immutable","message":"field 'spec.management.enabled' is immutable after creation"}]}`

---

### Requirement: Error output format — immutable type
The error format SHALL include `"immutable"` as a valid `type` value. Multiple errors SHALL be sorted by `field` ascending, with ties broken by `type` ascending.

#### Scenario: Immutable error produced
- **WHEN** an immutable field is changed on update
- **THEN** output includes `{"field":"<path>","type":"immutable","message":"<msg>"}`

#### Scenario: Multiple errors sorted
- **WHEN** multiple validation rules fail simultaneously
- **THEN** output `{"errors":[...]}` sorted by `field` ascending then `type` ascending (adapts implement-meshctl/mesh-management/error-output-format)
