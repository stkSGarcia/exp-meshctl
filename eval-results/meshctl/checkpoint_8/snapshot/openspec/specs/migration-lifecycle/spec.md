# migration-lifecycle Specification

## Purpose
TBD - created by archiving change mesh-migration-strategies. Update Purpose after archive.
## Requirements
### Requirement: First runtime assignment is not a migration
The system SHALL treat setting `spec.runtime` for the first time (when it was previously absent) as a version assignment only, without starting a migration.

#### Scenario: First assignment accepted without migration
- **WHEN** `spec.runtime` is absent in the stored mesh and an update sets it to a catalog-supported version
- **THEN** `spec.runtime` is stored, no `status.migration` is created, and no `Migration` condition is added

### Requirement: Version change starts a migration
Changing `spec.runtime` from one catalog version to a different catalog version SHALL start a migration.

#### Scenario: Migration starts on version change
- **WHEN** `spec.runtime` is updated from version A to a different version B (both catalog versions, no active migration)
- **THEN** the response includes `status.migration` with `sourceRuntime = A`, `targetRuntime = B`, and `stage` set to the first stage for the chosen strategy; `status.conditions` includes `{"type":"Migration","status":"True","message":""}`

#### Scenario: spec.runtime in output holds target version
- **WHEN** a migration starts
- **THEN** `spec.runtime` in the stored and returned resource is the target version

### Requirement: Migration status block
`status.migration` SHALL be present only during an active migration and SHALL contain `sourceRuntime`, `targetRuntime`, and `stage`.

#### Scenario: status.migration structure on migration start
- **WHEN** a migration starts with strategy `FullStop` from `3.1.1` to `4.0.0`
- **THEN** `status.migration = {"sourceRuntime":"3.1.1","targetRuntime":"4.0.0","stage":"Migrate"}`

#### Scenario: status.migration absent when no migration active
- **WHEN** no migration is in progress
- **THEN** `status.migration` is absent from the output

### Requirement: Stage sequences per strategy
Each strategy SHALL have a fixed ordered list of stages. The system SHALL set the initial stage to the first element of that list when a migration starts.

| Strategy | Stages |
|---|---|
| `FullStop` | `Migrate` |
| `RollingPatch` | `Migrate` |
| `LiveMigration` | `Prepare`, then `Migrate`, then `Complete` |

#### Scenario: FullStop initial stage is Migrate
- **WHEN** a migration starts with `FullStop` strategy
- **THEN** `status.migration.stage = "Migrate"`

#### Scenario: RollingPatch initial stage is Migrate
- **WHEN** a migration starts with `RollingPatch` strategy
- **THEN** `status.migration.stage = "Migrate"`

#### Scenario: LiveMigration initial stage is Prepare
- **WHEN** a migration starts with `LiveMigration` strategy
- **THEN** `status.migration.stage = "Prepare"`

### Requirement: Migration completion
When a migration reaches the final stage and `mesh migrate` is called, the migration completes. On completion the `Migration` condition SHALL be removed and `status.migration` SHALL be removed.

#### Scenario: Completion removes Migration condition
- **WHEN** `mesh migrate` is called on a mesh whose current stage is the final stage for its strategy
- **THEN** `status.conditions` no longer contains a `Migration` entry and `status.migration` is absent from the response

