# migration-active-guards Specification

## Purpose
TBD - created by archiving change mesh-migration-strategies. Update Purpose after archive.
## Requirements
### Requirement: Runtime change blocked during active migration
While a `Migration` condition is active on a mesh, any update that changes `spec.runtime` SHALL be rejected.

#### Scenario: Runtime change rejected during migration
- **WHEN** a mesh has an active migration and an update provides a different `spec.runtime` value
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"cannot change runtime version while a migration is in progress"}`

#### Scenario: Other fields may be updated during migration
- **WHEN** a mesh has an active migration and an update changes `spec.instances` (or another unlocked field)
- **THEN** the update succeeds if all other validations pass

### Requirement: Strategy change blocked during active migration
While a `Migration` condition is active, any update that changes `spec.migration.strategy` SHALL be rejected.

#### Scenario: Strategy change rejected during migration
- **WHEN** a mesh has an active migration and an update provides a different `spec.migration.strategy` value
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"cannot change migration strategy while a migration is in progress"}`

### Requirement: LiveMigration rollback
Only `LiveMigration` supports rollback during an active migration. A rollback SHALL remove the `Migration` condition and `status.migration`, restoring the mesh to a non-migrating state.

#### Scenario: LiveMigration rollback clears migration state
- **WHEN** a `LiveMigration` is active and a rollback is triggered
- **THEN** the `Migration` condition is removed and `status.migration` is absent from the response

#### Scenario: Non-LiveMigration strategies do not support rollback
- **WHEN** a `FullStop` or `RollingPatch` migration is active
- **THEN** no rollback operation is available for that mesh

