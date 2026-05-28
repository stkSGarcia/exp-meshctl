## ADDED Requirements

### Requirement: Management endpoint flag
The mesh spec SHALL support `spec.management.enabled` (boolean, default `false`). This field SHALL be immutable after creation.

#### Scenario: Management disabled by default
- **WHEN** `spec.management.enabled` is absent from the input
- **THEN** the persisted resource has `spec.management.enabled = false`

#### Scenario: Management enabled accepted
- **WHEN** `spec.management.enabled` is `true`
- **THEN** the field is accepted and stored

#### Scenario: Management field immutable after create
- **WHEN** an update attempts to change `spec.management.enabled` from its stored value
- **THEN** output error `{"field":"spec.management.enabled","type":"immutable","message":"field 'spec.management.enabled' is immutable after creation"}`

---

### Requirement: Management connection details
When `spec.management.enabled` is `true`, `status.managementConnectionDetails` SHALL be present in `create` and `describe` responses with a fixed shape: `host` = `"<name>-admin"`, `port` = `9990`, `protocol` = `"https"`.

#### Scenario: managementConnectionDetails present when enabled
- **WHEN** a mesh has `spec.management.enabled = true` and is created or described
- **THEN** `status.managementConnectionDetails` is `{"host":"<name>-admin","port":9990,"protocol":"https"}`

#### Scenario: managementConnectionDetails absent when disabled
- **WHEN** a mesh has `spec.management.enabled = false` (or defaulted)
- **THEN** `status.managementConnectionDetails` is absent from the output

## MODIFIED Requirements

### Requirement: Success output — create and describe
The system SHALL print the full resource JSON with `metadata`, `spec` (all defaulted fields including network topology and `access`), and a `status` block containing `state`, `stable`, `instances`, `conditions`, and (when stopped) `desiredInstancesOnResume`. The `spec.access` section SHALL include all applicable defaults for `authentication`, `permissions`, and `encryption`. When `spec.exposure` is configured, `status.connectionDetails` SHALL be included. When `spec.management.enabled` is `true`, `status.managementConnectionDetails` SHALL be included.

#### Scenario: Create success output includes full status
- **WHEN** create succeeds with `spec.instances > 0`
- **THEN** output includes `status.state = "Running"`, `status.stable = true`, `status.instances = {"ready":spec.instances,"starting":0,"stopped":0}`, and `status.conditions` with `Healthy` and `PrechecksPassed`

#### Scenario: New mesh starts as Running
- **WHEN** a mesh is first created with positive instances
- **THEN** `status.state = "Running"`

#### Scenario: spec.access included in output with defaults
- **WHEN** create or describe succeeds and `spec.access` was not specified in input
- **THEN** output includes `spec.access` with all applicable defaults applied

#### Scenario: connectionDetails included when exposure configured
- **WHEN** create or describe succeeds and `spec.exposure` is configured
- **THEN** `status.connectionDetails` is included in the output

#### Scenario: connectionDetails absent when no exposure
- **WHEN** create or describe succeeds and `spec.exposure` is absent
- **THEN** `status.connectionDetails` is absent from the output

#### Scenario: managementConnectionDetails included when management enabled
- **WHEN** create or describe succeeds and `spec.management.enabled` is `true`
- **THEN** `status.managementConnectionDetails` is `{"host":"<name>-admin","port":9990,"protocol":"https"}`

#### Scenario: managementConnectionDetails absent when management disabled
- **WHEN** create or describe succeeds and `spec.management.enabled` is `false`
- **THEN** `status.managementConnectionDetails` is absent from the output
