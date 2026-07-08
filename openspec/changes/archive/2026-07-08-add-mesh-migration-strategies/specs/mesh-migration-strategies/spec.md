## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud

### Requirement: Runtime catalog validation
The mesh runtime validator SHALL treat `spec.runtime` as optional. When `spec.runtime` is present on create or update, the validator SHALL accept only catalog-listed runtime versions, SHALL accept `supported` versions, SHALL accept `deprecated` versions with a warning, and SHALL reject `skipped` versions.

#### Scenario: Runtime omitted
- **WHEN** a mesh create or update omits `spec.runtime`
- **THEN** runtime catalog validation is skipped

#### Scenario: Supported runtime accepted
- **WHEN** a mesh create or update sets `spec.runtime` to catalog version `3.1.1` with status `supported`
- **THEN** the operation succeeds without a runtime warning

#### Scenario: Deprecated runtime accepted with warning
- **WHEN** a mesh create or update sets `spec.runtime` to catalog version `3.0.0` with status `deprecated` and no validation errors exist
- **THEN** the operation succeeds
- **AND** the response includes a warning with `field` set to `spec.runtime` and `message` set to `runtime version '3.0.0' is deprecated`

#### Scenario: Skipped runtime rejected
- **WHEN** a mesh create or update sets `spec.runtime` to catalog version `3.1.0` with status `skipped`
- **THEN** the operation fails with an error whose `field` is `spec.runtime`, `type` is `invalid`, and `message` is `runtime version '3.1.0' is skipped and cannot be targeted`

#### Scenario: Unlisted runtime rejected
- **WHEN** a mesh create or update sets `spec.runtime` to a version that is not listed in the runtime catalog
- **THEN** the operation fails with an error whose `field` is `spec.runtime` and `type` is `invalid`

### Requirement: Warning emission
The mesh CLI SHALL emit warnings only for successful operations, SHALL suppress all warnings when any validation error exists, SHALL sort warnings by `field` and then `message`, and SHALL NOT change the success exit code when warnings are present.

#### Scenario: Warnings suppressed on error
- **WHEN** a mesh create or update would otherwise produce a deprecated runtime warning and also has a validation error
- **THEN** the operation fails
- **AND** the response does not include warnings

#### Scenario: Warnings sorted
- **WHEN** a successful operation produces multiple warnings
- **THEN** the warnings are ordered by `field` and then by `message`

#### Scenario: Warning success exit code
- **WHEN** a mesh create or update succeeds with warnings
- **THEN** the command exits successfully

### Requirement: Migration strategy validation
The mesh validator SHALL accept `FullStop`, `LiveMigration`, and `RollingPatch` as `spec.migration.strategy` values, SHALL default the strategy to `FullStop` when absent, and SHALL reject any other strategy with `field` set to `spec.migration.strategy` and `type` set to `invalid`.

#### Scenario: Default migration strategy
- **WHEN** a mesh create or update omits `spec.migration.strategy`
- **THEN** the mesh uses `FullStop` as the migration strategy

#### Scenario: Invalid migration strategy
- **WHEN** a mesh create or update sets `spec.migration.strategy` to an unsupported value
- **THEN** the operation fails with an error whose `field` is `spec.migration.strategy` and `type` is `invalid`

### Requirement: Version change validation
The mesh update flow SHALL treat changing `spec.runtime` from one catalog version to another as a version change. All migration strategies SHALL reject downgrades. `FullStop` SHALL apply no additional version-change constraints. `RollingPatch` SHALL require source and target versions to share the same major and minor version and SHALL require the target major version to be at least `4`. `LiveMigration` SHALL reject meshes with configured `spec.regions`; otherwise, when no active migration exists, `LiveMigration` SHALL apply no version-change constraints beyond the downgrade rule.

#### Scenario: Downgrade rejected
- **WHEN** a mesh update changes `spec.runtime` from `4.0.0` to `3.1.1`
- **THEN** the operation fails with an error whose `field` is `spec.runtime`, `type` is `invalid`, and `message` is `version downgrade from '4.0.0' to '3.1.1' is not allowed`

#### Scenario: FullStop permits upgrade
- **WHEN** a mesh update uses `FullStop` to change `spec.runtime` from `3.1.1` to `4.0.0`
- **THEN** no strategy-specific version-change error is produced

#### Scenario: RollingPatch reports independent failures
- **WHEN** a mesh update uses `RollingPatch` to change `spec.runtime` across a different major or minor version and the target major version is below `4`
- **THEN** the operation reports both applicable `spec.runtime` errors with `type` set to `invalid`

#### Scenario: LiveMigration rejects multi-region topology
- **WHEN** a mesh update uses `LiveMigration` while `spec.regions` is configured
- **THEN** the operation fails with an error whose `field` is `spec.migration.strategy`, `type` is `invalid`, and `message` is `LiveMigration strategy is not supported with multi-region topology`

### Requirement: Migration lifecycle
The mesh update flow SHALL assign `spec.runtime` on first runtime assignment without starting a migration. When an existing mesh changes `spec.runtime` from one catalog version to another, the update flow SHALL start a migration by storing the target version in `spec.runtime`, adding a `Migration` condition with `status` set to `True` and `message` set to an empty string, and adding `status.migration` with `sourceRuntime`, `stage`, and `targetRuntime`. The initial `stage` SHALL be the first stage for the selected strategy.

#### Scenario: First runtime assignment
- **WHEN** a mesh without `spec.runtime` is updated to set `spec.runtime`
- **THEN** the runtime version is assigned
- **AND** no `Migration` condition or `status.migration` is added

#### Scenario: Runtime change starts migration
- **WHEN** an existing mesh changes `spec.runtime` from one catalog version to another
- **THEN** `spec.runtime` stores the target version
- **AND** `status.conditions` includes `Migration` with `status` set to `True` and `message` set to an empty string
- **AND** `status.migration` records `sourceRuntime`, `stage`, and `targetRuntime`

#### Scenario: Single-stage strategy starts at Migrate
- **WHEN** a runtime change starts a `FullStop` or `RollingPatch` migration
- **THEN** `status.migration.stage` is `Migrate`

#### Scenario: LiveMigration starts at first live stage
- **WHEN** a runtime change starts a `LiveMigration` migration
- **THEN** `status.migration.stage` is the first stage in the LiveMigration stage sequence

### Requirement: Mesh migrate command
The system SHALL expose `meshctl mesh migrate <name>` to advance an active migration by one stage. The command SHALL print the full mesh resource after the transition. If the current stage is the final stage, the command SHALL complete the migration by removing the `Migration` condition and removing `status.migration`.

#### Scenario: Advance active migration
- **WHEN** `meshctl mesh migrate <name>` runs for a mesh with an active migration that is not at its final stage
- **THEN** the migration advances by one stage
- **AND** the command prints the full mesh resource

#### Scenario: Complete final stage migration
- **WHEN** `meshctl mesh migrate <name>` runs for a mesh with an active migration at its final stage
- **THEN** the `Migration` condition is removed
- **AND** `status.migration` is removed
- **AND** the command prints the full mesh resource

#### Scenario: Missing mesh migration error
- **WHEN** `meshctl mesh migrate <name>` targets a mesh that does not exist
- **THEN** the command fails with the standard not-found error shape using `field` set to `metadata.name` and `type` set to `not_found`

#### Scenario: No active migration error
- **WHEN** `meshctl mesh migrate <name>` targets a mesh with no active migration
- **THEN** the command fails with an error whose `field` is `status.migration`, `type` is `invalid`, and `message` is `no active migration for mesh '<name>'`

### Requirement: Active migration update restrictions
The mesh update flow SHALL reject changes to `spec.runtime` and `spec.migration.strategy` while the `Migration` condition is active, and SHALL allow updates to other spec fields. During an active migration, only `LiveMigration` SHALL support rollback; a successful rollback SHALL remove the `Migration` condition and remove `status.migration`.

#### Scenario: Runtime change rejected during migration
- **WHEN** a mesh update changes `spec.runtime` while `Migration` is active
- **THEN** the operation fails with an error whose `field` is `spec.runtime`, `type` is `invalid`, and `message` is `cannot change runtime version while a migration is in progress`

#### Scenario: Strategy change rejected during migration
- **WHEN** a mesh update changes `spec.migration.strategy` while `Migration` is active
- **THEN** the operation fails with an error whose `field` is `spec.migration.strategy`, `type` is `invalid`, and `message` is `cannot change migration strategy while a migration is in progress`

#### Scenario: Unrelated spec update allowed during migration
- **WHEN** a mesh update changes a spec field other than `spec.runtime` or `spec.migration.strategy` while `Migration` is active
- **THEN** the update is allowed if all other validation succeeds

#### Scenario: LiveMigration rollback clears migration state
- **WHEN** rollback is requested during an active `LiveMigration`
- **THEN** the `Migration` condition is removed
- **AND** `status.migration` is removed

### Requirement: Migration-aware stability
The mesh status calculator SHALL set `status.stable` to `true` only when `Healthy` is `True`, `PrechecksPassed` is `True`, `GracefulShutdown` is absent or `False`, `Scaling` is absent or `False`, and `Migration` is absent or `False`. Otherwise, `status.stable` SHALL be `false`.

#### Scenario: Active migration is unstable
- **WHEN** a mesh has `Migration` present with `status` set to `True`
- **THEN** `status.stable` is `false`

#### Scenario: Stable without blocking conditions
- **WHEN** a mesh has `Healthy` set to `True`, `PrechecksPassed` set to `True`, and no active `GracefulShutdown`, `Scaling`, or `Migration` condition
- **THEN** `status.stable` is `true`

### Requirement: Validation error accumulation
The mesh validator SHALL accumulate and report all applicable validation errors. When errors share the same `field` and `type`, every applicable error SHALL be included, and message ordering among those ties is not part of the contract.

#### Scenario: Multiple applicable errors
- **WHEN** a mesh update violates multiple independent validation rules
- **THEN** every applicable validation error is reported

#### Scenario: Same field and type errors retained
- **WHEN** multiple errors have the same `field` and `type`
- **THEN** each applicable error is included in the response
