## ADDED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology

### Requirement: Runtime catalog validation
The system SHALL validate `spec.runtime` against the runtime catalog on `mesh create` and `mesh update` when `spec.runtime` is present, and SHALL skip catalog validation when `spec.runtime` is absent.

#### Scenario: Supported runtime is accepted
- **GIVEN** a mesh manifest with `spec.runtime: "3.1.1"`
- **WHEN** the user runs `meshctl mesh create -f <path>` or `meshctl mesh update -f <path>`
- **THEN** validation accepts the runtime version

#### Scenario: Missing runtime skips catalog validation
- **GIVEN** a mesh manifest without `spec.runtime`
- **WHEN** the user runs `meshctl mesh create -f <path>` or `meshctl mesh update -f <path>`
- **THEN** validation does not reject the manifest because of runtime catalog membership

#### Scenario: Skipped runtime is rejected
- **GIVEN** a mesh manifest with `spec.runtime: "3.1.0"`
- **WHEN** the user runs `meshctl mesh create -f <path>` or `meshctl mesh update -f <path>`
- **THEN** validation rejects `spec.runtime` with type `invalid` and message `runtime version '3.1.0' is skipped and cannot be targeted`

#### Scenario: Unknown runtime is rejected
- **GIVEN** a mesh manifest with a runtime version that is not listed in the runtime catalog
- **WHEN** the user runs `meshctl mesh create -f <path>` or `meshctl mesh update -f <path>`
- **THEN** validation rejects `spec.runtime` with type `invalid`

### Requirement: Runtime warnings
The system SHALL emit warnings only for successful operations, SHALL emit a deprecated runtime warning when the targeted catalog runtime is deprecated, and SHALL sort warnings by `field` and then `message`.

#### Scenario: Deprecated runtime warning on success
- **GIVEN** a mesh manifest with `spec.runtime: "3.0.0"` and no validation errors
- **WHEN** the user runs `meshctl mesh create -f <path>` or `meshctl mesh update -f <path>`
- **THEN** the operation succeeds
- **AND** the output contains a warning with `field: "spec.runtime"` and `message: "runtime version '3.0.0' is deprecated"`

#### Scenario: Warnings suppressed on error
- **GIVEN** a mesh manifest that targets deprecated runtime `3.0.0` and also contains a validation error
- **WHEN** the user runs `meshctl mesh create -f <path>` or `meshctl mesh update -f <path>`
- **THEN** the operation fails
- **AND** the output contains no warnings

#### Scenario: Warning exit code remains successful
- **GIVEN** a mesh operation succeeds with one or more warnings
- **WHEN** the command exits
- **THEN** the command uses the success exit code

### Requirement: Migration strategy validation
The system SHALL accept only `FullStop`, `LiveMigration`, and `RollingPatch` for `spec.migration.strategy`, SHALL default the strategy to `FullStop` when omitted, and SHALL reject invalid strategy values with field `spec.migration.strategy` and type `invalid`.

#### Scenario: FullStop default is applied
- **GIVEN** a mesh manifest without `spec.migration.strategy`
- **WHEN** the user creates or updates the mesh
- **THEN** the mesh uses `FullStop` as the migration strategy

#### Scenario: Invalid strategy is rejected
- **GIVEN** a mesh manifest with `spec.migration.strategy: "BlueGreen"`
- **WHEN** the user creates or updates the mesh
- **THEN** validation rejects `spec.migration.strategy` with type `invalid`

### Requirement: Version change rules
The system SHALL treat changing `spec.runtime` from one catalog version to another as a version change, SHALL reject downgrades for every migration strategy, and SHALL apply strategy-specific validation before starting a migration.

#### Scenario: Downgrade is rejected
- **GIVEN** an existing mesh with `spec.runtime: "4.0.0"`
- **WHEN** an update targets `spec.runtime: "3.1.1"`
- **THEN** validation rejects `spec.runtime` with type `invalid` and message `version downgrade from '4.0.0' to '3.1.1' is not allowed`

#### Scenario: FullStop permits upgrade without extra version constraints
- **GIVEN** an existing mesh with `spec.runtime: "3.1.1"` and `spec.migration.strategy: "FullStop"`
- **WHEN** an update targets `spec.runtime: "4.0.0"`
- **THEN** validation applies no strategy-specific version-change error beyond the downgrade rule

#### Scenario: RollingPatch reports all failed constraints
- **GIVEN** an existing mesh with `spec.runtime: "3.1.1"` and `spec.migration.strategy: "RollingPatch"`
- **WHEN** an update targets `spec.runtime: "3.2.0"`
- **THEN** validation rejects `spec.runtime` with type `invalid` for the major/minor compatibility rule
- **AND** validation rejects `spec.runtime` with type `invalid` for the target-major-at-least-4 rule

#### Scenario: RollingPatch permits same major and minor target at major four or later
- **GIVEN** an existing mesh with `spec.runtime: "4.0.0"` and `spec.migration.strategy: "RollingPatch"`
- **WHEN** an update targets another catalog runtime with major `4` and minor `0`
- **THEN** validation applies no RollingPatch version-change error

#### Scenario: LiveMigration rejects multi-region topology
- **GIVEN** a mesh with `spec.regions` configured and `spec.migration.strategy: "LiveMigration"`
- **WHEN** an update changes `spec.runtime`
- **THEN** validation rejects `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`

### Requirement: Migration start state
The system SHALL assign `spec.runtime` without starting a migration when runtime is set for the first time, and SHALL start a migration when an existing catalog runtime changes to another catalog runtime.

#### Scenario: First runtime assignment does not start migration
- **GIVEN** an existing mesh without `spec.runtime`
- **WHEN** an update sets `spec.runtime` to a valid catalog runtime for the first time
- **THEN** the system stores the runtime version
- **AND** the system does not add a `Migration` condition or `status.migration`

#### Scenario: Runtime change starts migration
- **GIVEN** an existing mesh with `spec.runtime: "3.1.1"`
- **WHEN** an update changes `spec.runtime` to `4.0.0`
- **THEN** the system stores `4.0.0` in `spec.runtime`
- **AND** the system adds a `Migration` condition with `status: "True"` and `message: ""`
- **AND** the system adds `status.migration` with `sourceRuntime: "3.1.1"`, `targetRuntime: "4.0.0"`, and the first stage for the selected strategy

#### Scenario: Strategy chooses first stage
- **GIVEN** an update starts a runtime migration
- **WHEN** the selected strategy is `FullStop`, `RollingPatch`, or `LiveMigration`
- **THEN** `status.migration.stage` is set to the first stage for that strategy

### Requirement: Migration command
The system SHALL expose `meshctl mesh migrate <name>` to advance an active migration by one stage and print the full mesh resource after the transition.

#### Scenario: Migration advances one stage
- **GIVEN** a mesh has an active migration that is not at its final stage
- **WHEN** the user runs `meshctl mesh migrate <name>`
- **THEN** the system advances `status.migration.stage` by one stage
- **AND** the command prints the full mesh resource after the transition

#### Scenario: Final migration stage completes
- **GIVEN** a mesh has an active migration at its final stage
- **WHEN** the user runs `meshctl mesh migrate <name>`
- **THEN** the system removes the `Migration` condition
- **AND** the system removes `status.migration`
- **AND** the command prints the full mesh resource after completion

#### Scenario: Missing mesh migration error
- **GIVEN** no mesh exists with the requested name
- **WHEN** the user runs `meshctl mesh migrate <name>`
- **THEN** validation rejects `metadata.name` with type `not_found` using the standard not-found shape

#### Scenario: No active migration error
- **GIVEN** a mesh exists without `status.migration`
- **WHEN** the user runs `meshctl mesh migrate <name>`
- **THEN** validation rejects `status.migration` with type `invalid` and message `no active migration for mesh '<name>'`

### Requirement: Active migration update guards
The system SHALL reject changes to `spec.runtime` and `spec.migration.strategy` while a `Migration` condition is active, and SHALL allow updates to other spec fields.

#### Scenario: Runtime change blocked during active migration
- **GIVEN** a mesh has an active migration
- **WHEN** an update changes `spec.runtime`
- **THEN** validation rejects `spec.runtime` with type `invalid` and message `cannot change runtime version while a migration is in progress`

#### Scenario: Strategy change blocked during active migration
- **GIVEN** a mesh has an active migration
- **WHEN** an update changes `spec.migration.strategy`
- **THEN** validation rejects `spec.migration.strategy` with type `invalid` and message `cannot change migration strategy while a migration is in progress`

#### Scenario: Other spec fields remain updatable during active migration
- **GIVEN** a mesh has an active migration
- **WHEN** an update changes only spec fields other than `spec.runtime` and `spec.migration.strategy`
- **THEN** the update is allowed if all other validation passes

### Requirement: LiveMigration rollback
The system SHALL support rollback during an active migration only for `LiveMigration`, and rollback SHALL remove the `Migration` condition and `status.migration`.

#### Scenario: LiveMigration rollback clears migration state
- **GIVEN** a mesh has an active migration with `spec.migration.strategy: "LiveMigration"`
- **WHEN** the user requests rollback
- **THEN** the system removes the `Migration` condition
- **AND** the system removes `status.migration`

#### Scenario: Non-LiveMigration rollback is rejected
- **GIVEN** a mesh has an active migration with `spec.migration.strategy: "FullStop"` or `spec.migration.strategy: "RollingPatch"`
- **WHEN** the user requests rollback
- **THEN** the system rejects the rollback

### Requirement: Migration-aware stability
The system SHALL set `status.stable` to `true` only when `Healthy` is `"True"`, `PrechecksPassed` is `"True"`, `GracefulShutdown` is absent or `"False"`, `Scaling` is absent or `"False"`, and `Migration` is absent or `"False"`; otherwise the system SHALL set `status.stable` to `false`.

#### Scenario: Stable when all stability conditions pass
- **GIVEN** `Healthy` is `"True"` and `PrechecksPassed` is `"True"`
- **AND** `GracefulShutdown`, `Scaling`, and `Migration` are absent or `"False"`
- **WHEN** status is computed
- **THEN** `status.stable` is `true`

#### Scenario: Active migration makes mesh unstable
- **GIVEN** the `Migration` condition is `"True"`
- **WHEN** status is computed
- **THEN** `status.stable` is `false`

### Requirement: Error accumulation and ordering
The system SHALL accumulate all applicable validation errors and SHALL include every applicable error when multiple errors share the same `field` and `type`; message ordering among those ties is not part of the contract.

#### Scenario: Multiple matching errors are returned
- **GIVEN** an update violates more than one rule for the same `field` and `type`
- **WHEN** validation fails
- **THEN** the output includes every applicable error for that `field` and `type`
