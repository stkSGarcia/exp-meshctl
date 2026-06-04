## MODIFIED Requirements

> Extends: spec:mesh-management

### Requirement: YAML input schema

**Updated:** The system SHALL accept the following additional top-level keys under `spec` as recognized input fields (adapts mesh-management/yaml-input-schema):

- `spec.regions` (optional) — multi-region topology configuration
- `spec.placement` (optional) — affinity/placement policy
- `spec.configBundleRef` (optional) — config bundle reference string
- `spec.extensions` (optional) — array of extension objects

`metadata.tags` (optional string→string map) SHALL also be accepted at the top level.

#### Scenario: new spec fields accepted without error

- **GIVEN** a create input that includes `spec.regions`, `spec.placement`, `spec.configBundleRef`, and `spec.extensions`
- **WHEN** create is called with otherwise valid input
- **THEN** the system SHALL NOT produce unknown-field errors for any of these fields

---

### Requirement: Success output — create and describe

**Updated:** The full resource JSON for create and describe SHALL include (adapts mesh-management/success-output-create-and-describe):

- `spec.placement` — always present with defaults applied
- `status.telemetryProbe` — always present
- `status.configRefresh` — present in update responses only when `configBundleRef` changed (absent from describe)
- `status.conditions` — includes region conditions when `spec.regions` is present

#### Scenario: create response includes placement and telemetryProbe

- **GIVEN** a minimal mesh create input without placement or telemetry tags
- **WHEN** create succeeds
- **THEN** the response SHALL include `spec.placement.affinity` with defaults and `status.telemetryProbe: {"enabled": true}`

---

### Requirement: Migration strategy validation and default

**Updated:** `spec.migration.strategy` SHALL default to `"FullStop"` when absent. Accepted values are `"FullStop"` and `"LiveMigration"`. `"LiveMigration"` is accepted when `spec.regions` is absent, but SHALL be rejected when `spec.regions` is present. Any other value SHALL produce an `invalid` error. (adapts mesh-management/migration-strategy-validation-and-default)

#### Scenario: LiveMigration rejected when regions present

- **GIVEN** a mesh input with `spec.regions` set and `spec.migration.strategy: "LiveMigration"`
- **WHEN** create or update is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.migration.strategy"` and `message = "LiveMigration strategy is not supported with multi-region topology"`

#### Scenario: LiveMigration accepted without regions

- **GIVEN** a mesh input without `spec.regions` and `spec.migration.strategy: "LiveMigration"`
- **WHEN** create is called
- **THEN** the system SHALL NOT reject the migration strategy
