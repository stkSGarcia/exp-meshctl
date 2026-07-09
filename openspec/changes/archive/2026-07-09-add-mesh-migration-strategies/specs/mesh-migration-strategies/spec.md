## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud
> Extends: mesh-resource-management/add-vault-resource-management

### Requirement: Runtime catalog validation
The system SHALL validate `spec.runtime` against the runtime catalog on `mesh create` and `mesh update` when `spec.runtime` is present, and SHALL skip catalog validation when `spec.runtime` is absent.

#### Scenario: Supported runtime accepted
- **GIVEN** the runtime catalog contains `3.1.1` with status `supported`
- **WHEN** a mesh is created or updated with `spec.runtime` set to `3.1.1`
- **THEN** the operation succeeds without a runtime warning

#### Scenario: Deprecated runtime accepted with warning
- **GIVEN** the runtime catalog contains `3.0.0` with status `deprecated`
- **WHEN** a mesh is created or updated with `spec.runtime` set to `3.0.0` and no validation errors exist
- **THEN** the operation succeeds with success exit code
- **AND** the response includes a warning with `field` set to `spec.runtime` and `message` set to `runtime version '3.0.0' is deprecated`

#### Scenario: Skipped runtime rejected
- **GIVEN** the runtime catalog contains `3.1.0` with status `skipped`
- **WHEN** a mesh is created or updated with `spec.runtime` set to `3.1.0`
- **THEN** the operation is rejected with `field` set to `spec.runtime`, `type` set to `invalid`, and `message` set to `runtime version '3.1.0' is skipped and cannot be targeted`

#### Scenario: Unlisted runtime rejected
- **GIVEN** the runtime catalog does not contain `2.9.9`
- **WHEN** a mesh is created or updated with `spec.runtime` set to `2.9.9`
- **THEN** the operation is rejected with `field` set to `spec.runtime` and `type` set to `invalid`

#### Scenario: Runtime validation skipped when absent
- **GIVEN** a mesh payload omits `spec.runtime`
- **WHEN** the mesh is created or updated
- **THEN** runtime catalog validation does not add a validation error

### Requirement: Warning emission
The system SHALL emit warnings only for successful operations, SHALL suppress warnings when any validation error exists, and SHALL sort warnings by `field` and then `message`.

#### Scenario: Deprecated warning suppressed by errors
- **GIVEN** a mesh update targets a deprecated runtime
- **AND** the same update has another validation error
- **WHEN** the update is validated
- **THEN** the operation fails
- **AND** the response does not include warnings

#### Scenario: Warnings sorted deterministically
- **GIVEN** a successful operation produces multiple warnings
- **WHEN** the response is serialized
- **THEN** warnings are sorted by `field` and then `message`

### Requirement: Migration strategy values
The system SHALL accept `spec.migration.strategy` values of `FullStop`, `LiveMigration`, and `RollingPatch`, SHALL default the strategy to `FullStop`, and SHALL reject any other strategy value.

#### Scenario: Default migration strategy
- **GIVEN** a mesh payload omits `spec.migration.strategy`
- **WHEN** the mesh is created or updated
- **THEN** the effective migration strategy is `FullStop`

#### Scenario: Invalid migration strategy rejected
- **GIVEN** a mesh payload sets `spec.migration.strategy` to `Canary`
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.migration.strategy` and `type` set to `invalid`

### Requirement: Version change constraints
The system SHALL treat changing `spec.runtime` from one catalog version to another as a version change and SHALL enforce strategy-specific version change constraints.

#### Scenario: First runtime assignment does not start migration
- **GIVEN** an existing mesh has no `spec.runtime`
- **WHEN** the mesh is updated to set `spec.runtime` to a catalog-listed runtime
- **THEN** the runtime is assigned
- **AND** no `Migration` condition or `status.migration` is added

#### Scenario: Downgrade rejected for every strategy
- **GIVEN** an existing mesh has `spec.runtime` set to `4.0.0`
- **WHEN** the mesh is updated to set `spec.runtime` to `3.1.1`
- **THEN** the operation is rejected with `field` set to `spec.runtime`, `type` set to `invalid`, and `message` set to `version downgrade from '4.0.0' to '3.1.1' is not allowed`

#### Scenario: FullStop allows catalog version upgrade
- **GIVEN** an existing mesh has `spec.runtime` set to `3.1.1`
- **AND** the effective migration strategy is `FullStop`
- **WHEN** the mesh is updated to set `spec.runtime` to `4.0.0`
- **THEN** the version change is accepted subject to catalog validation and the downgrade rule

#### Scenario: RollingPatch reports every failed rule
- **GIVEN** an existing mesh has `spec.runtime` set to `3.1.1`
- **AND** the effective migration strategy is `RollingPatch`
- **WHEN** the mesh is updated to set `spec.runtime` to `3.2.0`
- **THEN** the operation reports each applicable `spec.runtime` invalid error for failing the same-major-and-minor rule and the target-major-at-least-4 rule

#### Scenario: RollingPatch accepts same minor target at major four or later
- **GIVEN** an existing mesh has `spec.runtime` set to `4.0.0`
- **AND** the effective migration strategy is `RollingPatch`
- **WHEN** the mesh is updated to set `spec.runtime` to `4.0.1`
- **THEN** the version change is accepted subject to catalog validation and the downgrade rule

#### Scenario: LiveMigration rejects multi-region topology
- **GIVEN** a mesh has `spec.regions` configured
- **AND** the effective migration strategy is `LiveMigration`
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.migration.strategy`, `type` set to `invalid`, and `message` set to `LiveMigration strategy is not supported with multi-region topology`

### Requirement: Migration lifecycle state
The system SHALL start a migration when `spec.runtime` changes from one catalog version to another and SHALL persist the target runtime, a `Migration` condition, and `status.migration` state for the selected strategy.

#### Scenario: Migration state starts on version change
- **GIVEN** an existing mesh has `spec.runtime` set to `3.1.1`
- **AND** the effective migration strategy is `FullStop`
- **WHEN** the mesh is updated to set `spec.runtime` to `4.0.0`
- **THEN** the stored `spec.runtime` is `4.0.0`
- **AND** `status.conditions` includes `Migration` with `status` set to `True` and `message` set to an empty string
- **AND** `status.migration` includes `sourceRuntime` set to `3.1.1`, `targetRuntime` set to `4.0.0`, and `stage` set to the first stage for `FullStop`

#### Scenario: Single-stage migration sequence
- **GIVEN** the selected strategy is `FullStop` or `RollingPatch`
- **WHEN** a migration starts
- **THEN** the stage sequence contains only `Migrate`

#### Scenario: LiveMigration uses multiple stages
- **GIVEN** the selected strategy is `LiveMigration`
- **WHEN** a migration starts
- **THEN** `status.migration.stage` is set to the first stage in the `LiveMigration` stage sequence
- **AND** the `LiveMigration` stage sequence contains multiple stages

### Requirement: Mesh migrate command
The system SHALL expose `meshctl mesh migrate <name>` to advance an active migration by one stage, complete a migration at its final stage, and print the full mesh resource after the transition.

#### Scenario: Migration advances to next stage
- **GIVEN** a mesh has an active migration that is not at its final stage
- **WHEN** `meshctl mesh migrate <name>` is run for that mesh
- **THEN** the migration advances by one stage
- **AND** the command prints the full mesh resource after the transition

#### Scenario: Migration completes at final stage
- **GIVEN** a mesh has an active migration at its final stage
- **WHEN** `meshctl mesh migrate <name>` is run for that mesh
- **THEN** the `Migration` condition is removed
- **AND** `status.migration` is removed
- **AND** the command prints the full mesh resource after completion

#### Scenario: Missing mesh migration rejected
- **GIVEN** no mesh exists with name `missing`
- **WHEN** `meshctl mesh migrate missing` is run
- **THEN** the operation is rejected with `field` set to `metadata.name`, `type` set to `not_found`, and the standard not-found shape

#### Scenario: Inactive migration rejected
- **GIVEN** a mesh named `api` has no active migration
- **WHEN** `meshctl mesh migrate api` is run
- **THEN** the operation is rejected with `field` set to `status.migration`, `type` set to `invalid`, and `message` set to `no active migration for mesh 'api'`

### Requirement: Active migration updates and rollback
The system SHALL reject changes to `spec.runtime` and `spec.migration.strategy` while a `Migration` condition is active, SHALL allow updates to other spec fields, and SHALL support rollback only for active `LiveMigration` migrations.

#### Scenario: Runtime change rejected during active migration
- **GIVEN** a mesh has an active `Migration` condition
- **WHEN** the mesh is updated to change `spec.runtime`
- **THEN** the operation is rejected with `field` set to `spec.runtime`, `type` set to `invalid`, and `message` set to `cannot change runtime version while a migration is in progress`

#### Scenario: Strategy change rejected during active migration
- **GIVEN** a mesh has an active `Migration` condition
- **WHEN** the mesh is updated to change `spec.migration.strategy`
- **THEN** the operation is rejected with `field` set to `spec.migration.strategy`, `type` set to `invalid`, and `message` set to `cannot change migration strategy while a migration is in progress`

#### Scenario: Other spec fields update during active migration
- **GIVEN** a mesh has an active `Migration` condition
- **WHEN** the mesh is updated without changing `spec.runtime` or `spec.migration.strategy`
- **THEN** the update is allowed subject to all other validation rules

#### Scenario: LiveMigration rollback clears migration state
- **GIVEN** a mesh has an active migration using `LiveMigration`
- **WHEN** rollback is requested for that migration
- **THEN** the `Migration` condition is removed
- **AND** `status.migration` is removed

#### Scenario: Non-LiveMigration rollback rejected
- **GIVEN** a mesh has an active migration using `FullStop` or `RollingPatch`
- **WHEN** rollback is requested for that migration
- **THEN** the rollback is rejected

### Requirement: Mesh stability during migration
The system SHALL set `status.stable` to `true` only when `Healthy` is `True`, `PrechecksPassed` is `True`, `GracefulShutdown` is absent or `False`, `Scaling` is absent or `False`, and `Migration` is absent or `False`; otherwise it SHALL set `status.stable` to `false`.

#### Scenario: Active migration makes mesh unstable
- **GIVEN** a mesh has `Healthy` set to `True` and `PrechecksPassed` set to `True`
- **AND** `GracefulShutdown` and `Scaling` are absent or `False`
- **AND** `Migration` is `True`
- **WHEN** `status.stable` is computed
- **THEN** `status.stable` is `false`

#### Scenario: All stable conditions satisfied
- **GIVEN** a mesh has `Healthy` set to `True` and `PrechecksPassed` set to `True`
- **AND** `GracefulShutdown`, `Scaling`, and `Migration` are absent or `False`
- **WHEN** `status.stable` is computed
- **THEN** `status.stable` is `true`

### Requirement: Validation error accumulation
The system SHALL accumulate and report all applicable validation errors, including multiple errors with the same `field` and `type`.

#### Scenario: Multiple same-field errors retained
- **GIVEN** a `RollingPatch` version change violates more than one `spec.runtime` rule
- **WHEN** validation errors are serialized
- **THEN** every applicable `spec.runtime` error with `type` set to `invalid` is included
- **AND** message ordering among those same-field and same-type errors is not part of the contract
