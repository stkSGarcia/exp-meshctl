## ADDED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology
> Extends: one-shot-operations/add-one-shot-operations

### Requirement: Runtime catalog validation
The system SHALL validate `spec.runtime` against the runtime catalog during mesh create and update when `spec.runtime` is present, and SHALL skip catalog validation when `spec.runtime` is absent (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-update-operation).

#### Scenario: Supported runtime accepted
- **GIVEN** the runtime catalog lists version `4.0.0` with status `supported`
- **WHEN** a mesh is created or updated with `spec.runtime = "4.0.0"`
- **THEN** the operation succeeds without runtime catalog warnings.

#### Scenario: Deprecated runtime accepted with warning
- **GIVEN** the runtime catalog lists version `3.0.0` with status `deprecated`
- **WHEN** a mesh is created or updated with `spec.runtime = "3.0.0"` and no validation errors exist
- **THEN** the operation succeeds and emits a warning with `field = "spec.runtime"` and `message = "runtime version '3.0.0' is deprecated"`.

#### Scenario: Skipped runtime rejected
- **GIVEN** the runtime catalog lists version `3.1.0` with status `skipped`
- **WHEN** a mesh is created or updated with `spec.runtime = "3.1.0"`
- **THEN** the operation fails with an error on `field = "spec.runtime"`, `type = "invalid"`, and `message = "runtime version '3.1.0' is skipped and cannot be targeted"`.

#### Scenario: Runtime absent bypasses catalog validation
- **WHEN** a mesh create or update omits `spec.runtime`
- **THEN** the system does not apply runtime catalog validation.

### Requirement: Warning emission
The system SHALL emit warnings only for successful operations, SHALL suppress warnings when any error exists, SHALL sort warnings by `field` then `message`, and SHALL NOT change the success exit code because warnings are present.

#### Scenario: Warnings included on successful operation
- **GIVEN** a mesh create or update succeeds and produces one or more warnings
- **WHEN** the system writes the operation result
- **THEN** the output includes a `warnings` array containing objects with `field` and `message`.

#### Scenario: Warnings suppressed when errors exist
- **GIVEN** a mesh create or update produces at least one validation error and at least one potential warning
- **WHEN** the system writes the operation result
- **THEN** the output includes the errors and omits warnings.

### Requirement: Migration strategy values
The system SHALL accept `FullStop`, `LiveMigration`, and `RollingPatch` as `spec.migration.strategy` values, SHALL default the strategy to `FullStop` when absent, and SHALL reject invalid strategy values with `field = "spec.migration.strategy"` and `type = "invalid"`.

#### Scenario: Missing strategy defaults to FullStop
- **WHEN** a mesh is created or updated without `spec.migration.strategy`
- **THEN** the persisted mesh uses `FullStop` for migration strategy.

#### Scenario: Invalid strategy rejected
- **WHEN** a mesh is created or updated with `spec.migration.strategy = "BlueGreen"`
- **THEN** the operation fails with an error on `field = "spec.migration.strategy"` and `type = "invalid"`.

### Requirement: Runtime version change constraints
The system SHALL treat a change from one catalog runtime version to another as a version change, SHALL reject all downgrades, and SHALL enforce strategy-specific constraints before starting migration.

#### Scenario: Downgrade rejected
- **GIVEN** an existing mesh has `spec.runtime = "4.0.0"`
- **WHEN** the mesh is updated to `spec.runtime = "3.1.1"`
- **THEN** the operation fails with an error on `field = "spec.runtime"`, `type = "invalid"`, and `message = "version downgrade from '4.0.0' to '3.1.1' is not allowed"`.

#### Scenario: FullStop permits upgrade
- **GIVEN** an existing mesh has `spec.runtime = "3.1.1"` and `spec.migration.strategy = "FullStop"`
- **WHEN** the mesh is updated to `spec.runtime = "4.0.0"`
- **THEN** no additional strategy-specific version-change errors are emitted.

#### Scenario: RollingPatch reports each failed rule
- **GIVEN** an existing mesh has `spec.runtime = "3.1.1"` and `spec.migration.strategy = "RollingPatch"`
- **WHEN** the mesh is updated to a target runtime with a different major or minor version and a target major version below `4`
- **THEN** the system reports each applicable `spec.runtime` invalid error independently.

#### Scenario: LiveMigration rejects multi-region topology
- **GIVEN** a mesh update uses `spec.migration.strategy = "LiveMigration"` and `spec.regions` is configured
- **WHEN** the update is validated
- **THEN** the operation fails with an error on `field = "spec.migration.strategy"`, `type = "invalid"`, and `message = "LiveMigration strategy is not supported with multi-region topology"`.

### Requirement: Migration lifecycle state
The system SHALL assign the first runtime without starting migration, and SHALL start migration when `spec.runtime` changes from one catalog version to another by persisting the target runtime, setting a `Migration` condition, and adding `status.migration` (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-instance-lifecycle-transitions).

#### Scenario: First runtime assignment does not start migration
- **GIVEN** an existing mesh has no `spec.runtime`
- **WHEN** the mesh is updated to set `spec.runtime = "4.0.0"`
- **THEN** the mesh stores `spec.runtime = "4.0.0"` and does not add a `Migration` condition or `status.migration`.

#### Scenario: Runtime change starts migration
- **GIVEN** an existing mesh has `spec.runtime = "3.1.1"` and no active migration
- **WHEN** the mesh is updated to `spec.runtime = "4.0.0"`
- **THEN** the mesh stores `spec.runtime = "4.0.0"`, adds a `Migration` condition with `status = "True"` and `message = ""`, and adds `status.migration` with `sourceRuntime`, `targetRuntime`, and the first `stage` for the chosen strategy.

### Requirement: Migration command
The system SHALL expose `mesh migrate <name>` to advance an active migration by one stage, print the full mesh resource after the transition, and complete the migration when the current stage is final (adapts one-shot-operations/add-one-shot-operations/one-shot-command-surface).

#### Scenario: Migrate advances active migration
- **GIVEN** mesh `alpha` has an active migration that is not on its final stage
- **WHEN** `meshctl mesh migrate alpha` is run
- **THEN** the system advances the migration by one stage and prints the full updated mesh resource.

#### Scenario: Migrate completes final stage
- **GIVEN** mesh `alpha` has an active migration on its final stage
- **WHEN** `meshctl mesh migrate alpha` is run
- **THEN** the system removes the `Migration` condition, removes `status.migration`, and prints the full updated mesh resource.

#### Scenario: Migrate missing mesh fails
- **WHEN** `meshctl mesh migrate missing` is run and no mesh named `missing` exists
- **THEN** the operation fails with the standard not-found error shape using `field = "metadata.name"`.

#### Scenario: Migrate without active migration fails
- **GIVEN** mesh `alpha` has no active migration
- **WHEN** `meshctl mesh migrate alpha` is run
- **THEN** the operation fails with an error on `field = "status.migration"`, `type = "invalid"`, and `message = "no active migration for mesh 'alpha'"`.

### Requirement: Updates during active migration
The system SHALL reject changes to `spec.runtime` and `spec.migration.strategy` while a `Migration` condition is active, SHALL allow updates to other spec fields, and SHALL support rollback only for active `LiveMigration` migrations.

#### Scenario: Runtime change rejected during active migration
- **GIVEN** mesh `alpha` has an active migration
- **WHEN** the mesh is updated with a different `spec.runtime`
- **THEN** the operation fails with an error on `field = "spec.runtime"`, `type = "invalid"`, and `message = "cannot change runtime version while a migration is in progress"`.

#### Scenario: Strategy change rejected during active migration
- **GIVEN** mesh `alpha` has an active migration
- **WHEN** the mesh is updated with a different `spec.migration.strategy`
- **THEN** the operation fails with an error on `field = "spec.migration.strategy"`, `type = "invalid"`, and `message = "cannot change migration strategy while a migration is in progress"`.

#### Scenario: Other spec updates allowed during active migration
- **GIVEN** mesh `alpha` has an active migration
- **WHEN** the mesh is updated without changing `spec.runtime` or `spec.migration.strategy`
- **THEN** the update may succeed subject to the other mesh validation rules.

#### Scenario: LiveMigration rollback clears migration state
- **GIVEN** mesh `alpha` has an active `LiveMigration` migration
- **WHEN** rollback is requested
- **THEN** the system removes the `Migration` condition and removes `status.migration`.

### Requirement: Migration-aware stability
The system SHALL set `status.stable` to `true` only when `Healthy` is `True`, `PrechecksPassed` is `True`, `GracefulShutdown` is absent or `False`, `Scaling` is absent or `False`, and `Migration` is absent or `False` (adapts one-shot-operations/add-one-shot-operations/snapshot-run-execution).

#### Scenario: Active migration makes mesh unstable
- **GIVEN** a mesh has `Healthy = "True"`, `PrechecksPassed = "True"`, no active `GracefulShutdown`, no active `Scaling`, and `Migration = "True"`
- **WHEN** `status.stable` is derived
- **THEN** `status.stable` is `false`.

#### Scenario: Stable when all stability conditions pass
- **GIVEN** a mesh has `Healthy = "True"`, `PrechecksPassed = "True"`, and `GracefulShutdown`, `Scaling`, and `Migration` are absent or `False`
- **WHEN** `status.stable` is derived
- **THEN** `status.stable` is `true`.

### Requirement: Error accumulation and ordering
The system SHALL accumulate and report all applicable errors, and when errors share the same `field` and `type`, SHALL include every applicable error without treating message ordering among those ties as contractually significant.

#### Scenario: Multiple runtime errors are reported
- **GIVEN** a mesh update violates more than one runtime validation rule
- **WHEN** the system validates the update
- **THEN** each applicable error is included in the validation result.
