## ADDED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology
> Extends: mesh-resource-management/add-access-security-model

### Requirement: Runtime catalog validation
The system SHALL treat `spec.runtime` as optional and, when present on mesh create or update, SHALL accept only runtime versions listed in the runtime catalog.

#### Scenario: Runtime omitted
- **GIVEN** a mesh create or update document omits `spec.runtime`
- **WHEN** the system validates the document
- **THEN** the system skips runtime catalog validation

#### Scenario: Supported runtime accepted
- **GIVEN** a mesh create or update document sets `spec.runtime` to catalog version `3.1.1` or `4.0.0`
- **WHEN** the system validates the document
- **THEN** the operation is not rejected because of `spec.runtime`

#### Scenario: Unknown runtime rejected
- **GIVEN** a mesh create or update document sets `spec.runtime` to a version that is not listed in the runtime catalog
- **WHEN** the system validates the document
- **THEN** validation reports an error with `field = "spec.runtime"` and `type = "invalid"`

#### Scenario: Skipped runtime rejected
- **GIVEN** a mesh create or update document sets `spec.runtime` to catalog version `3.1.0`
- **WHEN** the system validates the document
- **THEN** validation reports an error with `field = "spec.runtime"`, `type = "invalid"`, and `message = "runtime version '3.1.0' is skipped and cannot be targeted"`

### Requirement: Deprecated runtime warnings
The system SHALL accept deprecated catalog runtime versions and SHALL emit warnings only for successful operations.

#### Scenario: Deprecated runtime warning
- **GIVEN** a mesh create or update document sets `spec.runtime` to catalog version `3.0.0`
- **WHEN** the operation succeeds
- **THEN** the JSON output includes `warnings` containing an entry with `field = "spec.runtime"` and `message = "runtime version '3.0.0' is deprecated"`
- **AND** the operation uses the success exit code

#### Scenario: Warnings suppressed on errors
- **GIVEN** a mesh create or update document targets deprecated runtime version `3.0.0` and also has any validation error
- **WHEN** the operation fails validation
- **THEN** the JSON output does not include warnings

#### Scenario: Warnings sorted
- **GIVEN** a successful operation emits more than one warning
- **WHEN** the system writes JSON output
- **THEN** warnings are sorted by `field` and then by `message`

### Requirement: Migration strategy values
The system SHALL accept `FullStop`, `LiveMigration`, and `RollingPatch` as `spec.migration.strategy` values and SHALL default omitted strategy to `FullStop`.

#### Scenario: Default strategy
- **GIVEN** a mesh create or update document omits `spec.migration.strategy`
- **WHEN** the system normalizes the mesh spec
- **THEN** the normalized mesh has `spec.migration.strategy = "FullStop"`

#### Scenario: Supported strategies accepted
- **GIVEN** a mesh create or update document sets `spec.migration.strategy` to `FullStop`, `LiveMigration`, or `RollingPatch`
- **WHEN** the system validates the document
- **THEN** the operation is not rejected because of `spec.migration.strategy`

#### Scenario: Invalid strategy rejected
- **GIVEN** a mesh create or update document sets `spec.migration.strategy` to any other value
- **WHEN** the system validates the document
- **THEN** validation reports an error with `field = "spec.migration.strategy"` and `type = "invalid"`

### Requirement: Runtime version change rules
The system SHALL treat a change from one catalog runtime version to another catalog runtime version as a version change and SHALL enforce all applicable strategy constraints.

#### Scenario: First runtime assignment
- **GIVEN** an existing mesh has no `spec.runtime`
- **WHEN** a mesh update sets `spec.runtime` to a catalog version
- **THEN** the stored mesh has the target `spec.runtime`
- **AND** no migration is started

#### Scenario: Downgrade rejected
- **GIVEN** an existing mesh has `spec.runtime = "4.0.0"`
- **WHEN** a mesh update targets `spec.runtime = "3.1.1"` with any migration strategy
- **THEN** validation reports an error with `field = "spec.runtime"`, `type = "invalid"`, and `message = "version downgrade from '4.0.0' to '3.1.1' is not allowed"`

#### Scenario: FullStop version change
- **GIVEN** an existing mesh has one catalog runtime version
- **WHEN** a mesh update targets a later catalog runtime version with `spec.migration.strategy = "FullStop"`
- **THEN** the system does not apply additional version-change constraints beyond the downgrade rule

#### Scenario: RollingPatch incompatible minor and major
- **GIVEN** an existing mesh has `spec.runtime = "3.0.0"`
- **WHEN** a mesh update targets `spec.runtime = "4.0.0"` with `spec.migration.strategy = "RollingPatch"`
- **THEN** validation reports all applicable `spec.runtime` invalid errors for failing RollingPatch constraints

#### Scenario: RollingPatch accepted
- **GIVEN** an existing mesh has `spec.runtime = "4.0.0"`
- **WHEN** a mesh update targets another catalog runtime version that shares the same major and minor version and has target major version at least `4` with `spec.migration.strategy = "RollingPatch"`
- **THEN** the system accepts the RollingPatch version-change constraints

#### Scenario: LiveMigration multi-region rejected
- **GIVEN** a mesh create or update document has `spec.migration.strategy = "LiveMigration"` and configures `spec.regions`
- **WHEN** the system validates the document
- **THEN** validation reports an error with `field = "spec.migration.strategy"`, `type = "invalid"`, and `message = "LiveMigration strategy is not supported with multi-region topology"`

#### Scenario: LiveMigration version change
- **GIVEN** an existing mesh has one catalog runtime version and no active migration
- **WHEN** a mesh update targets a later catalog runtime version with `spec.migration.strategy = "LiveMigration"` and no multi-region topology
- **THEN** the system does not apply additional version-change constraints beyond the downgrade rule

### Requirement: Migration start state
The system SHALL start a migration when `spec.runtime` changes from one catalog version to another and SHALL persist the target runtime, a `Migration` condition, and `status.migration`.

#### Scenario: Migration starts
- **GIVEN** an existing mesh has `spec.runtime = "3.1.1"` and no active migration
- **WHEN** a mesh update targets `spec.runtime = "4.0.0"`
- **THEN** the stored mesh has `spec.runtime = "4.0.0"`
- **AND** `status.conditions` includes `Migration` with `status = "True"` and `message = ""`
- **AND** `status.migration` includes `sourceRuntime = "3.1.1"`, `targetRuntime = "4.0.0"`, and the first stage for the chosen strategy

#### Scenario: FullStop first stage
- **GIVEN** a runtime version change uses `spec.migration.strategy = "FullStop"`
- **WHEN** the migration starts
- **THEN** `status.migration.stage = "Migrate"`

#### Scenario: RollingPatch first stage
- **GIVEN** a runtime version change uses `spec.migration.strategy = "RollingPatch"`
- **WHEN** the migration starts
- **THEN** `status.migration.stage = "Migrate"`

#### Scenario: LiveMigration first stage
- **GIVEN** a runtime version change uses `spec.migration.strategy = "LiveMigration"`
- **WHEN** the migration starts
- **THEN** `status.migration.stage` is the first stage in the LiveMigration stage sequence

### Requirement: Mesh migrate command
The system SHALL expose `meshctl mesh migrate <name>` to advance an active mesh migration by one stage, complete a migration at its final stage, and print the full mesh resource after the transition.

#### Scenario: Advance active migration
- **GIVEN** a mesh has an active migration that is not at its final stage
- **WHEN** the user runs `meshctl mesh migrate <name>`
- **THEN** the system advances `status.migration.stage` by one stage
- **AND** the JSON output is the full mesh resource after the transition

#### Scenario: Complete final migration stage
- **GIVEN** a mesh has an active migration at its final stage
- **WHEN** the user runs `meshctl mesh migrate <name>`
- **THEN** the system completes the migration
- **AND** the JSON output is the full mesh resource after completion

#### Scenario: Migrate missing mesh
- **GIVEN** no mesh exists with the requested name
- **WHEN** the user runs `meshctl mesh migrate <name>`
- **THEN** the system reports the standard not-found error shape with `field = "metadata.name"` and `type = "not_found"`

#### Scenario: Migrate without active migration
- **GIVEN** a mesh exists without `status.migration`
- **WHEN** the user runs `meshctl mesh migrate <name>`
- **THEN** the system reports an error with `field = "status.migration"`, `type = "invalid"`, and `message = "no active migration for mesh '<name>'"`

### Requirement: Migration completion
The system SHALL complete a migration by removing the `Migration` condition and removing `status.migration`.

#### Scenario: Completion clears migration state
- **GIVEN** a mesh has an active migration at its final stage
- **WHEN** the migration completes
- **THEN** `status.conditions` does not include a `Migration` condition
- **AND** `status.migration` is absent

### Requirement: Active migration update restrictions
The system SHALL reject changes to `spec.runtime` and `spec.migration.strategy` while `Migration` is active, and SHALL allow updates to other spec fields.

#### Scenario: Runtime change rejected during migration
- **GIVEN** a mesh has an active migration
- **WHEN** a mesh update changes `spec.runtime`
- **THEN** validation reports an error with `field = "spec.runtime"`, `type = "invalid"`, and `message = "cannot change runtime version while a migration is in progress"`

#### Scenario: Strategy change rejected during migration
- **GIVEN** a mesh has an active migration
- **WHEN** a mesh update changes `spec.migration.strategy`
- **THEN** validation reports an error with `field = "spec.migration.strategy"`, `type = "invalid"`, and `message = "cannot change migration strategy while a migration is in progress"`

#### Scenario: Other spec fields allowed during migration
- **GIVEN** a mesh has an active migration
- **WHEN** a mesh update changes only spec fields other than `spec.runtime` and `spec.migration.strategy`
- **THEN** the system accepts the update when all other validation rules pass

### Requirement: Active migration rollback
The system SHALL support rollback only for active LiveMigration migrations and SHALL remove migration state on rollback.

#### Scenario: LiveMigration rollback
- **GIVEN** a mesh has an active migration started with `spec.migration.strategy = "LiveMigration"`
- **WHEN** rollback is requested for the migration
- **THEN** the system removes the `Migration` condition
- **AND** the system removes `status.migration`

#### Scenario: Non-LiveMigration rollback rejected
- **GIVEN** a mesh has an active migration started with any strategy other than `LiveMigration`
- **WHEN** rollback is requested for the migration
- **THEN** the system rejects the rollback

### Requirement: Stability during migration
The system SHALL set `status.stable = true` only when `Healthy` is `True`, `PrechecksPassed` is `True`, `GracefulShutdown` is absent or `False`, `Scaling` is absent or `False`, and `Migration` is absent or `False`.

#### Scenario: Stable when all conditions permit
- **GIVEN** a mesh status has `Healthy = "True"`, `PrechecksPassed = "True"`, and no active `GracefulShutdown`, `Scaling`, or `Migration` condition
- **WHEN** the system calculates `status.stable`
- **THEN** `status.stable = true`

#### Scenario: Unstable during migration
- **GIVEN** a mesh status includes a `Migration` condition with `status = "True"`
- **WHEN** the system calculates `status.stable`
- **THEN** `status.stable = false`

#### Scenario: Unstable when health gates fail
- **GIVEN** a mesh status is missing `Healthy = "True"` or `PrechecksPassed = "True"` or has active `GracefulShutdown` or `Scaling`
- **WHEN** the system calculates `status.stable`
- **THEN** `status.stable = false`

### Requirement: Validation error accumulation
The system SHALL accumulate and report all applicable validation errors, including multiple errors with the same `field` and `type`.

#### Scenario: Multiple applicable errors
- **GIVEN** a mesh create or update document violates multiple runtime migration validation rules
- **WHEN** the system validates the document
- **THEN** every applicable validation error is present in the JSON output

#### Scenario: Same field and type errors retained
- **GIVEN** a mesh create or update document causes multiple errors with the same `field` and `type`
- **WHEN** the system builds the validation response
- **THEN** every applicable error is included
- **AND** message ordering among those ties is not part of the contract
