## MODIFIED Requirements

### Requirement: Authentication default
`spec.access.authentication.enabled` SHALL default to `true` when absent. When authentication is enabled (the default), `spec.access.authentication.digestAlgorithm` SHALL default to `"SHA-256"`. When authentication is disabled, the `authentication` object in output SHALL contain only `"enabled": false` — `digestAlgorithm` SHALL be absent from output. `spec.access.credentialRef`, when provided, SHALL be stored and output as given; it has no default.

#### Scenario: Authentication defaults to true
- **WHEN** `spec.access.authentication.enabled` is not specified
- **THEN** output has `spec.access.authentication.enabled = true`

#### Scenario: Explicit false accepted
- **WHEN** `spec.access.authentication.enabled` is `false`
- **THEN** output has `spec.access.authentication.enabled = false`

#### Scenario: digestAlgorithm defaults to SHA-256 when auth enabled
- **WHEN** `spec.access.authentication.enabled` is `true` (or absent) and `digestAlgorithm` is not specified
- **THEN** output has `spec.access.authentication.digestAlgorithm = "SHA-256"`

#### Scenario: digestAlgorithm absent from output when auth disabled
- **WHEN** `spec.access.authentication.enabled` is `false`
- **THEN** `spec.access.authentication.digestAlgorithm` is absent from output

#### Scenario: credentialRef stored as given
- **WHEN** `spec.access.credentialRef` is provided
- **THEN** output has `spec.access.credentialRef` equal to the provided value

---

### Requirement: Error output format
All validation and operational errors SHALL be printed as `{"errors":[...]}` to stdout with nothing to stderr. Each error object SHALL have `field` (dot-path string), `message` (human-readable string), and `type` (one of: `required`, `invalid`, `forbidden`, `duplicate`, `not_found`, `parse`, `immutable`). When multiple errors are present, the array SHALL be sorted by `field` ascending, with ties broken by `type` ascending.

#### Scenario: Single error
- **WHEN** one validation rule fails
- **THEN** output `{"errors":[{"field":"<path>","type":"<type>","message":"<msg>"}]}`

#### Scenario: Multiple errors sorted by field then type
- **WHEN** multiple validation rules fail simultaneously
- **THEN** output `{"errors":[...]}` containing all violations, sorted by `field` ascending then `type` ascending

---

### Requirement: Success output — create and describe
The system SHALL print the full resource JSON with `metadata`, `spec` (all defaulted fields including network topology and `access`), and a `status` block containing `state`, `stable`, `instances`, `conditions`, and (when stopped) `desiredInstancesOnResume`. The `spec.access` section SHALL include all applicable defaults for `authentication`, `permissions`, and `encryption`.

#### Scenario: Create success output includes full status
- **WHEN** create succeeds with `spec.instances > 0`
- **THEN** output includes `status.state = "Running"`, `status.stable = true`, `status.instances = {"ready":spec.instances,"starting":0,"stopped":0}`, and `status.conditions` with `Healthy` and `PrechecksPassed`

#### Scenario: New mesh starts as Running
- **WHEN** a mesh is first created with positive instances
- **THEN** `status.state = "Running"`

#### Scenario: spec.access included in output with defaults
- **WHEN** create or describe succeeds and `spec.access` was not specified in input
- **THEN** output includes `spec.access` with all applicable defaults applied

---

## ADDED Requirements

### Requirement: Authentication digest algorithm validation
`spec.access.authentication.digestAlgorithm`, when present, SHALL be one of `"SHA-256"`, `"SHA-384"`, or `"SHA-512"`. Any other value SHALL produce an `invalid` error.

#### Scenario: Valid digestAlgorithm accepted
- **WHEN** `spec.access.authentication.digestAlgorithm` is `"SHA-256"`, `"SHA-384"`, or `"SHA-512"`
- **THEN** the value is accepted and stored

#### Scenario: Invalid digestAlgorithm rejected
- **WHEN** `spec.access.authentication.digestAlgorithm` is any other value (e.g., `"MD5"`)
- **THEN** output error `{"field":"spec.access.authentication.digestAlgorithm","type":"invalid","message":"<msg>"}`

---

### Requirement: Authentication forbidden fields when disabled
When `spec.access.authentication.enabled` is `false`, the fields `digestAlgorithm` and `credentialRef` SHALL be absent. If either is present, the system SHALL produce a `forbidden` error for each.

#### Scenario: digestAlgorithm forbidden when auth disabled
- **WHEN** `spec.access.authentication.enabled` is `false` and `spec.access.authentication.digestAlgorithm` is present
- **THEN** output error `{"field":"spec.access.authentication.digestAlgorithm","type":"forbidden","message":"<msg>"}`

#### Scenario: credentialRef forbidden when auth disabled
- **WHEN** `spec.access.authentication.enabled` is `false` and `spec.access.credentialRef` is present
- **THEN** output error `{"field":"spec.access.credentialRef","type":"forbidden","message":"<msg>"}`

---

### Requirement: Permissions
The mesh spec SHALL support `spec.access.permissions.enabled` (boolean, default `false`). When `permissions.enabled` is `true`, `spec.access.permissions.roles` SHALL be required and SHALL contain at least one entry. Each role SHALL have a non-empty `name` (string) and a non-empty `permissions` array of strings. Role names SHALL be unique within the list. When `permissions.enabled` is `false`, `roles` SHALL be omitted from output.

#### Scenario: Permissions disabled by default
- **WHEN** `spec.access.permissions.enabled` is not specified
- **THEN** output has `spec.access.permissions.enabled = false` and `roles` is absent from output

#### Scenario: Roles required when permissions enabled
- **WHEN** `spec.access.permissions.enabled` is `true` and `spec.access.permissions.roles` is absent or empty
- **THEN** output error `{"field":"spec.access.permissions.roles","type":"required","message":"<msg>"}`

#### Scenario: Role missing name rejected
- **WHEN** a role entry has an absent or empty `name`
- **THEN** output error `{"field":"spec.access.permissions.roles[<index>].name","type":"required","message":"<msg>"}`

#### Scenario: Role missing permissions rejected
- **WHEN** a role entry has an absent or empty `permissions` array
- **THEN** output error `{"field":"spec.access.permissions.roles[<index>].permissions","type":"required","message":"<msg>"}`

#### Scenario: Duplicate role names rejected
- **WHEN** two or more roles have the same `name`
- **THEN** output error `{"field":"spec.access.permissions.roles","type":"duplicate","message":"<msg>"}`

#### Scenario: Valid permissions accepted
- **WHEN** `spec.access.permissions.enabled` is `true` and at least one valid role is provided
- **THEN** the permissions section is accepted and output includes `spec.access.permissions.roles`

---

### Requirement: Encryption
The mesh spec SHALL support `spec.access.encryption` with `source` (string, default `"None"`), `certRef` (string, optional), `certServiceRef` (string, optional), and `clientMode` (string, default `"None"`). The `source` field determines which certificate reference fields are required or forbidden. When `source` is `"None"`, `clientMode` SHALL be `"None"`.

Valid values for `source` are `"None"`, `"Secret"`, and `"Service"`. Valid values for `clientMode` are implementation-defined but SHALL produce an `invalid` error for unrecognized values.

| source value | certRef | certServiceRef |
|---|---|---|
| `"None"` | forbidden | forbidden |
| `"Secret"` | required | forbidden |
| `"Service"` | forbidden | required |

#### Scenario: Encryption defaults applied when absent
- **WHEN** `spec.access.encryption` is not specified
- **THEN** output has `spec.access.encryption.source = "None"` and `spec.access.encryption.clientMode = "None"`

#### Scenario: Invalid source rejected
- **WHEN** `spec.access.encryption.source` is not one of the valid values
- **THEN** output error `{"field":"spec.access.encryption.source","type":"invalid","message":"<msg>"}`

#### Scenario: Invalid clientMode rejected
- **WHEN** `spec.access.encryption.clientMode` is not one of the valid values
- **THEN** output error `{"field":"spec.access.encryption.clientMode","type":"invalid","message":"<msg>"}`

#### Scenario: certRef required when source is Secret
- **WHEN** `spec.access.encryption.source` is `"Secret"` and `certRef` is absent
- **THEN** output error `{"field":"spec.access.encryption.certRef","type":"required","message":"<msg>"}`

#### Scenario: certServiceRef required when source is Service
- **WHEN** `spec.access.encryption.source` is `"Service"` and `certServiceRef` is absent
- **THEN** output error `{"field":"spec.access.encryption.certServiceRef","type":"required","message":"<msg>"}`

#### Scenario: certRef forbidden when source is not Secret
- **WHEN** `spec.access.encryption.source` is `"None"` or `"Service"` and `certRef` is present
- **THEN** output error `{"field":"spec.access.encryption.certRef","type":"forbidden","message":"<msg>"}`

#### Scenario: certServiceRef forbidden when source is not Service
- **WHEN** `spec.access.encryption.source` is `"None"` or `"Secret"` and `certServiceRef` is present
- **THEN** output error `{"field":"spec.access.encryption.certServiceRef","type":"forbidden","message":"<msg>"}`

#### Scenario: clientMode None required when source is None
- **WHEN** `spec.access.encryption.source` is `"None"` and `clientMode` is `"Authenticate"` or `"Validate"`
- **THEN** the system SHALL produce an error for `spec.access.encryption.clientMode`

---

### Requirement: Access section defaults when omitted
When `spec.access` is entirely absent from the input, the system SHALL output the full `spec.access` section with all applicable sub-section defaults applied.

#### Scenario: Full access defaults when spec.access omitted
- **WHEN** `spec.access` is not present in the input
- **THEN** output includes `spec.access.authentication.enabled = true`, `spec.access.authentication.digestAlgorithm = "SHA-256"`, `spec.access.permissions.enabled = false`, `spec.access.encryption.source = "None"`, and `spec.access.encryption.clientMode = "None"`

#### Scenario: roles absent when permissions disabled by default
- **WHEN** `spec.access.permissions.enabled` is `false` (or defaulted to false)
- **THEN** `spec.access.permissions.roles` is absent from output
