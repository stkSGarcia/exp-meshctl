# mesh-migration-lifecycle Specification

## Purpose
TBD - created by archiving change mesh-migration-strategies. Update Purpose after archive.
## Requirements
### Requirement: First runtime assignment does not start migration
Setting `spec.runtime` for the first time (i.e., the stored resource has no `spec.runtime`) SHALL assign the version without starting a migration.

#### Scenario: First runtime assignment
- **WHEN** a mesh has no stored `spec.runtime` and an update sets `spec.runtime` to a catalog version
- **THEN** the version is stored, no `status.migration` is created, and no `Migration` condition is added

---

### Requirement: Runtime version change starts migration
Changing `spec.runtime` from one catalog version to a different catalog version SHALL start a migration.

#### Scenario: Migration starts on runtime version change
- **WHEN** a mesh has `spec.runtime = "3.1.1"` and an update sets `spec.runtime = "4.0.0"`
- **THEN** `status.migration` is populated with `sourceRuntime`, `stage`, and `targetRuntime`, and a `Migration` condition with `status = "True"` and `message = ""` is added to `status.conditions`

#### Scenario: Migration sourceRuntime and targetRuntime recorded
- **WHEN** a migration starts from version A to version B
- **THEN** `status.migration.sourceRuntime = A` and `status.migration.targetRuntime = B`

---

### Requirement: Initial migration stage set by strategy
On migration start, `status.migration.stage` SHALL be set to the first stage of the sequence for the chosen `spec.migration.strategy`.

#### Scenario: FullStop initial stage
- **WHEN** a migration starts with `spec.migration.strategy = "FullStop"`
- **THEN** `status.migration.stage = "Migrate"`

#### Scenario: RollingPatch initial stage
- **WHEN** a migration starts with `spec.migration.strategy = "RollingPatch"`
- **THEN** `status.migration.stage = "Migrate"`

#### Scenario: LiveMigration initial stage
- **WHEN** a migration starts with `spec.migration.strategy = "LiveMigration"`
- **THEN** `status.migration.stage` is set to the first stage of the LiveMigration sequence (e.g., `"Drain"`)

---

### Requirement: Migration completion clears migration state
When a migration completes (its final stage is advanced past), the system SHALL remove the `Migration` condition and remove `status.migration`.

#### Scenario: Migration condition removed on completion
- **WHEN** a migration is completed
- **THEN** `Migration` is absent from `status.conditions`

#### Scenario: status.migration removed on completion
- **WHEN** a migration is completed
- **THEN** `status.migration` is absent from the resource

---

### Requirement: Active migration blocks runtime change
While the `Migration` condition is active (`status = "True"`), the system SHALL reject any update that changes `spec.runtime`.

#### Scenario: Runtime change blocked during migration
- **WHEN** a mesh has an active migration and an update provides a different `spec.runtime` value
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"cannot change runtime version while a migration is in progress"}`

#### Scenario: Runtime unchanged allowed during migration
- **WHEN** a mesh has an active migration and an update omits `spec.runtime`
- **THEN** the update is not rejected on account of the migration guard

---

### Requirement: Active migration blocks strategy change
While the `Migration` condition is active, the system SHALL reject any update that changes `spec.migration.strategy`.

#### Scenario: Strategy change blocked during migration
- **WHEN** a mesh has an active migration and an update provides a different `spec.migration.strategy`
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"cannot change migration strategy while a migration is in progress"}`

---

### Requirement: LiveMigration rollback
Only `LiveMigration` supports rollback while a migration is active. Invoking rollback SHALL remove the `Migration` condition and `status.migration` without advancing to the next stage.

#### Scenario: LiveMigration rollback clears migration state
- **WHEN** an active LiveMigration is rolled back
- **THEN** `Migration` is removed from `status.conditions` and `status.migration` is removed

#### Scenario: Non-LiveMigration strategies do not support rollback
- **WHEN** an active `FullStop` or `RollingPatch` migration is in progress
- **THEN** rollback is not available

---

### Requirement: Migration stability impact
`status.stable` SHALL be `false` when the `Migration` condition is present with `status = "True"`.

#### Scenario: Stable is false during active migration
- **WHEN** a mesh has an active migration
- **THEN** `status.stable = false`

#### Scenario: Stable may be true after migration completes
- **WHEN** a migration completes and all other stability conditions are met
- **THEN** `status.stable = true`

