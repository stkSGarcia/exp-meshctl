# Migration Lifecycle

## Purpose

Defines the requirements for how mesh migrations are detected, started, progressed, and completed, including version constraints, strategy-specific rules, locking during active migrations, and rollback support.

## Requirements

### Requirement: Version change detection
The system SHALL detect a version change when `spec.runtime` is updated from one catalog version to another. Setting `spec.runtime` for the first time (from absent to a value) is an initial assignment and SHALL NOT start a migration.

#### Scenario: First assignment is not a version change
- **WHEN** `spec.runtime` was absent and is set to a catalog version for the first time
- **THEN** the version is assigned, no migration is started, and `status.migration` is absent

#### Scenario: Changing runtime starts a migration
- **WHEN** `spec.runtime` changes from one catalog version to another in an update
- **THEN** a migration is started

---

### Requirement: Downgrade rejection
All strategies SHALL forbid downgrading `spec.runtime` to an earlier version. A downgrade occurs when the target version tuple `(major, minor, patch)` is less than the source version tuple.

#### Scenario: Downgrade rejected for FullStop
- **WHEN** `spec.migration.strategy` is `"FullStop"` and the target `spec.runtime` is an earlier version than the current
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"version downgrade from '<current>' to '<target>' is not allowed"}`

#### Scenario: Downgrade rejected for RollingPatch
- **WHEN** `spec.migration.strategy` is `"RollingPatch"` and the target `spec.runtime` is an earlier version than the current
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"version downgrade from '<current>' to '<target>' is not allowed"}`

#### Scenario: Downgrade rejected for LiveMigration
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and the target `spec.runtime` is an earlier version than the current
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"version downgrade from '<current>' to '<target>' is not allowed"}`

---

### Requirement: RollingPatch version constraints
`RollingPatch` SHALL enforce two independent constraints on version changes. Both SHALL be checked and both errors reported when applicable.

1. Source and target versions SHALL share the same major and minor version.
2. Target major version SHALL be at least `4`.

#### Scenario: RollingPatch cross-minor rejected
- **WHEN** `spec.migration.strategy` is `"RollingPatch"` and the source and target versions differ in minor or major version
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}`

#### Scenario: RollingPatch target major below 4 rejected
- **WHEN** `spec.migration.strategy` is `"RollingPatch"` and the target major version is less than `4`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}`

#### Scenario: Both RollingPatch constraints violated simultaneously
- **WHEN** `spec.migration.strategy` is `"RollingPatch"` and both constraints are violated
- **THEN** both errors are reported independently

#### Scenario: Valid RollingPatch version change accepted
- **WHEN** `spec.migration.strategy` is `"RollingPatch"`, source and target share the same major and minor, and target major is at least `4`
- **THEN** no RollingPatch-specific error is produced

---

### Requirement: LiveMigration multi-region restriction
`LiveMigration` SHALL be rejected when `spec.regions` is configured on the mesh.

#### Scenario: LiveMigration rejected with regions
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and `spec.regions` is configured
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}`

#### Scenario: LiveMigration accepted without regions
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and `spec.regions` is not configured
- **THEN** no multi-region restriction error is produced

---

### Requirement: Migration start state
When a version change starts a migration, the system SHALL persist the migration state atomically with the resource update.

#### Scenario: Migration condition added on start
- **WHEN** a migration starts
- **THEN** `status.conditions` includes `{"type":"Migration","status":"True","message":""}`

#### Scenario: status.migration populated on start
- **WHEN** a migration starts
- **THEN** `status.migration` contains `sourceRuntime`, `targetRuntime`, and `stage` set to the first stage for the chosen strategy

#### Scenario: spec.runtime reflects target on start
- **WHEN** a migration starts
- **THEN** `spec.runtime` in the persisted resource equals the target version

---

### Requirement: Stage sequences
Each strategy defines an ordered list of stages. The first call to `mesh migrate` advances to the next stage; the last stage triggers completion.

#### Scenario: FullStop stage sequence
- **WHEN** a `FullStop` migration starts
- **THEN** `status.migration.stage` is set to `"Migrate"` (the only and final stage)

#### Scenario: RollingPatch stage sequence
- **WHEN** a `RollingPatch` migration starts
- **THEN** `status.migration.stage` is set to `"Migrate"` (the only and final stage)

#### Scenario: LiveMigration initial stage
- **WHEN** a `LiveMigration` migration starts
- **THEN** `status.migration.stage` is set to the first stage in the LiveMigration sequence

---

### Requirement: Migration completion
When `mesh migrate` is called on the final stage, the system SHALL complete the migration.

#### Scenario: Migration condition removed on completion
- **WHEN** the migration completes
- **THEN** the `Migration` entry is removed from `status.conditions`

#### Scenario: status.migration removed on completion
- **WHEN** the migration completes
- **THEN** `status.migration` is absent from the response

---

### Requirement: Updates during active migration — runtime lock
While a `Migration` condition is active (status `"True"`), the system SHALL reject changes to `spec.runtime`.

#### Scenario: Runtime change rejected during active migration
- **WHEN** `mesh update` is called and a `Migration` condition with `status="True"` exists
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"cannot change runtime version while a migration is in progress"}`

#### Scenario: Non-runtime fields allowed during active migration
- **WHEN** `mesh update` is called during an active migration and only non-runtime fields change
- **THEN** the update succeeds

---

### Requirement: Updates during active migration — strategy lock
While a `Migration` condition is active, the system SHALL reject changes to `spec.migration.strategy`.

#### Scenario: Strategy change rejected during active migration
- **WHEN** `mesh update` is called during an active migration and `spec.migration.strategy` differs from the stored value
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"cannot change migration strategy while a migration is in progress"}`

---

### Requirement: LiveMigration rollback
Only `LiveMigration` supports rollback during an active migration. Rollback cancels the migration without completing it.

#### Scenario: LiveMigration rollback removes condition and state
- **WHEN** a rollback is triggered on an active `LiveMigration` migration
- **THEN** the `Migration` condition is removed from `status.conditions` and `status.migration` is removed

#### Scenario: Rollback not available for FullStop or RollingPatch
- **WHEN** a rollback is requested on an active `FullStop` or `RollingPatch` migration
- **THEN** the system rejects the rollback
