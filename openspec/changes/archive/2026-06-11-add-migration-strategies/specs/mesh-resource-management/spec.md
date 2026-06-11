## ADDED Requirements

### Requirement: Mesh runtime catalog validation
The system SHALL validate `spec.runtime` against a runtime catalog when `spec.runtime` is present on mesh create or update.

#### Scenario: Runtime may be omitted
- **WHEN** a mesh create or update input omits `spec.runtime`
- **THEN** the system SHALL skip runtime catalog validation.

#### Scenario: Supported catalog runtime is accepted
- **WHEN** `spec.runtime` is present and names a catalog version whose status is `supported`
- **THEN** the system SHALL accept the runtime version.

#### Scenario: Deprecated catalog runtime is accepted with warning
- **WHEN** `spec.runtime` is present and names a catalog version whose status is `deprecated`
- **THEN** the system SHALL accept the runtime version and emit a warning with field `spec.runtime` and message `runtime version '<version>' is deprecated`.

#### Scenario: Skipped catalog runtime is rejected
- **WHEN** `spec.runtime` is present and names a catalog version whose status is `skipped`
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `runtime version '<version>' is skipped and cannot be targeted`.

#### Scenario: Runtime outside catalog is rejected
- **WHEN** `spec.runtime` is present and does not name a catalog-listed version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

### Requirement: Successful mesh warnings
The system SHALL include warnings only on successful operations and SHALL sort warnings by `field` ascending, then `message` ascending.

#### Scenario: Deprecated runtime create emits warning
- **WHEN** a mesh create succeeds with a deprecated `spec.runtime`
- **THEN** the successful JSON output SHALL include `warnings` containing an object with field `spec.runtime` and message `runtime version '<version>' is deprecated`.

#### Scenario: Deprecated runtime update emits warning
- **WHEN** a mesh update succeeds with a deprecated `spec.runtime`
- **THEN** the successful JSON output SHALL include `warnings` containing an object with field `spec.runtime` and message `runtime version '<version>' is deprecated`.

#### Scenario: Failed operation omits warnings
- **WHEN** any error exists for a mesh create or update
- **THEN** the system SHALL print the error object and SHALL NOT emit warnings.

#### Scenario: Warnings preserve success exit code
- **WHEN** a mesh create or update succeeds with warnings
- **THEN** the command SHALL keep the normal success exit code.

### Requirement: Mesh runtime version change rules
The system SHALL apply migration strategy validation when `spec.runtime` changes from one catalog version to another.

#### Scenario: First runtime assignment does not start migration
- **WHEN** a mesh without stored `spec.runtime` is updated to set `spec.runtime` for the first time
- **THEN** the system SHALL persist the runtime version and SHALL NOT add a `Migration` condition or `status.migration`.

#### Scenario: Runtime downgrade is rejected
- **WHEN** an update changes `spec.runtime` from a higher catalog version to a lower catalog version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `version downgrade from '<current>' to '<target>' is not allowed`.

#### Scenario: FullStop permits non-downgrade version changes
- **WHEN** an update changes `spec.runtime` to a non-downgrade catalog version and `spec.migration.strategy` is `"FullStop"`
- **THEN** the system SHALL accept the version change and start a migration.

#### Scenario: RollingPatch requires same major and minor
- **WHEN** an update changes `spec.runtime` and `spec.migration.strategy` is `"RollingPatch"` but the source and target do not share the same major and minor version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: RollingPatch requires target major at least four
- **WHEN** an update changes `spec.runtime` and `spec.migration.strategy` is `"RollingPatch"` but the target major version is less than `4`
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: RollingPatch reports independent failures
- **WHEN** an update changes `spec.runtime` with `"RollingPatch"` and both RollingPatch constraints fail
- **THEN** the system SHALL report both `spec.runtime` errors.

#### Scenario: LiveMigration rejects multi-region topology
- **WHEN** an update changes `spec.runtime`, `spec.migration.strategy` is `"LiveMigration"`, and `spec.regions` is configured
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`.

#### Scenario: LiveMigration permits non-downgrade version changes without regions
- **WHEN** an update changes `spec.runtime` to a non-downgrade catalog version, `spec.migration.strategy` is `"LiveMigration"`, and `spec.regions` is not configured
- **THEN** the system SHALL accept the version change and start a migration.

### Requirement: Mesh migration lifecycle
The system SHALL persist active runtime migration state when a mesh runtime version change starts a migration.

#### Scenario: Migration start persists target runtime and status
- **WHEN** a mesh update changes `spec.runtime` from one catalog version to another and passes validation
- **THEN** the system SHALL store the target version in `spec.runtime`, add a `Migration` condition with status `"True"` and empty message, and add `status.migration` with `sourceRuntime`, `targetRuntime`, and `stage`.

#### Scenario: FullStop migration starts at Migrate
- **WHEN** a migration starts with `spec.migration.strategy` equal to `"FullStop"`
- **THEN** `status.migration.stage` SHALL be `"Migrate"`.

#### Scenario: RollingPatch migration starts at Migrate
- **WHEN** a migration starts with `spec.migration.strategy` equal to `"RollingPatch"`
- **THEN** `status.migration.stage` SHALL be `"Migrate"`.

#### Scenario: LiveMigration has multiple stages
- **WHEN** a migration starts with `spec.migration.strategy` equal to `"LiveMigration"`
- **THEN** `status.migration.stage` SHALL be the first stage in a deterministic sequence containing more than one stage.

#### Scenario: Migration completion clears migration state
- **WHEN** a migration completes
- **THEN** the system SHALL remove the `Migration` condition and remove `status.migration`.

### Requirement: Mesh migrate operation
The system SHALL expose `mesh migrate <name>` to advance or complete active mesh migrations.

#### Scenario: Migrate command advances active migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` for a mesh whose current migration stage is not final
- **THEN** the system SHALL advance the active migration by one stage and print the full mesh resource after the transition.

#### Scenario: Migrate command completes final stage
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` for a mesh whose current migration stage is final
- **THEN** the system SHALL complete the migration and print the full mesh resource after the transition.

#### Scenario: Migrate missing mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` and the mesh does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Migrate without active migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` and the mesh has no active migration
- **THEN** the system SHALL report field `status.migration` with type `invalid` and message `no active migration for mesh '<name>'`.

### Requirement: Mesh updates during active migration
The system SHALL reject runtime and migration strategy changes while a mesh has an active `Migration` condition, and SHALL allow unrelated spec updates that otherwise pass validation.

#### Scenario: Runtime change during active migration is rejected
- **WHEN** a mesh update changes `spec.runtime` while a migration is active
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `cannot change runtime version while a migration is in progress`.

#### Scenario: Strategy change during active migration is rejected
- **WHEN** a mesh update changes `spec.migration.strategy` while a migration is active
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `cannot change migration strategy while a migration is in progress`.

#### Scenario: Unrelated update during active migration is accepted
- **WHEN** a mesh update changes a spec field other than `spec.runtime` or `spec.migration.strategy` while a migration is active and no other validation errors exist
- **THEN** the system SHALL persist the update and keep the active migration state.

#### Scenario: LiveMigration rollback clears active migration
- **WHEN** rollback is requested during an active migration whose strategy is `"LiveMigration"`
- **THEN** the system SHALL remove the `Migration` condition and remove `status.migration`.

## MODIFIED Requirements

### Requirement: Mesh CLI command surface
The system SHALL expose `mesh create`, `mesh list`, `mesh describe`, `mesh delete`, `mesh update`, and `mesh migrate` operations through `meshctl.py`.

#### Scenario: Create command accepts a YAML file
- **WHEN** the user runs `uv run --project /app meshctl.py mesh create -f <path>`
- **THEN** the system SHALL read `<path>` as the mesh YAML input and attempt to create the resource.

#### Scenario: List command returns existing mesh summaries
- **WHEN** the user runs `uv run --project /app meshctl.py mesh list`
- **THEN** the system SHALL print a JSON array of mesh summaries.

#### Scenario: Describe command returns a named mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh describe <name>`
- **THEN** the system SHALL print the full persisted mesh resource for `<name>`.

#### Scenario: Delete command removes a named mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh delete <name>`
- **THEN** the system SHALL remove the mesh and print a JSON confirmation object.

#### Scenario: Update command applies a partial mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh update -f <path>`
- **THEN** the system SHALL read `<path>` as a partial mesh YAML input and attempt to update the named resource.

#### Scenario: Migrate command advances a named mesh migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>`
- **THEN** the system SHALL attempt to advance or complete the active migration for `<name>`.

### Requirement: Mesh field validation
The system SHALL validate mesh scalar fields and map each failed condition to the documented field and error type.

#### Scenario: Invalid instance count
- **WHEN** `spec.instances` is present and is not a non-negative integer
- **THEN** the system SHALL report field `spec.instances` with type `invalid`.

#### Scenario: Invalid runtime version
- **WHEN** `spec.runtime` is present and does not parse as semantic version `major.minor.patch` with non-negative integer parts
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: Invalid migration strategy
- **WHEN** `spec.migration.strategy` is present and is not `"FullStop"`, `"LiveMigration"`, or `"RollingPatch"`
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid`.

### Requirement: Mesh status fields
The system SHALL return `status.state`, `status.stable`, `status.instances`, conditions, stopped resume metadata, and active migration metadata for create, update, migrate, and describe responses.

#### Scenario: Running state for positive instances
- **WHEN** a returned mesh has `spec.instances` greater than `0`
- **THEN** `status.state` SHALL be `"Running"`.

#### Scenario: Stopped state for zero instances
- **WHEN** a returned mesh has `spec.instances` equal to `0`
- **THEN** `status.state` SHALL be `"Stopped"`.

#### Scenario: Stable status for steady state
- **WHEN** a returned mesh has `Healthy` equal to `"True"`, `PrechecksPassed` equal to `"True"`, and no active `GracefulShutdown`, `Scaling`, or `Migration` condition
- **THEN** `status.stable` SHALL be `true`.

#### Scenario: Unstable status for transition state
- **WHEN** a returned mesh lacks `Healthy` equal to `"True"`, lacks `PrechecksPassed` equal to `"True"`, has `GracefulShutdown` equal to `"True"`, has `Scaling` equal to `"True"`, or has `Migration` equal to `"True"`
- **THEN** `status.stable` SHALL be `false`.

#### Scenario: Instance status shape
- **WHEN** a mesh is returned
- **THEN** `status.instances` SHALL contain integer `ready`, `starting`, and `stopped` fields.

#### Scenario: Running create initializes ready instances
- **WHEN** a mesh is created with `spec.instances` greater than `0`
- **THEN** `status.instances.ready` SHALL equal `spec.instances`, `status.instances.starting` SHALL equal `0`, and `status.instances.stopped` SHALL equal `0`.

#### Scenario: Desired instances present only while stopped
- **WHEN** a mesh is stopped
- **THEN** `status.desiredInstancesOnResume` SHALL be present as an integer.

#### Scenario: Desired instances absent while running
- **WHEN** a mesh is running
- **THEN** `status.desiredInstancesOnResume` SHALL be absent.

#### Scenario: Migration status appears only during active migration
- **WHEN** a mesh has an active migration
- **THEN** `status.migration` SHALL be present with `sourceRuntime`, `targetRuntime`, and `stage`.

#### Scenario: Migration status absent outside active migration
- **WHEN** a mesh has no active migration
- **THEN** `status.migration` SHALL be absent.

### Requirement: Error output
The system SHALL print errors as JSON to stdout with an `errors` array and SHALL print nothing to stderr.

#### Scenario: Error object shape
- **WHEN** any validation, parse, duplicate, not-found, immutable, forbidden, required, or post-merge constraint error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.

#### Scenario: Errors are sorted
- **WHEN** multiple errors are returned
- **THEN** the system SHALL sort errors by `field` ascending, then by `type` ascending.

#### Scenario: Same field and type preserves every applicable error
- **WHEN** multiple errors share the same `field` and `type`
- **THEN** the system SHALL include every applicable error and SHALL NOT treat message ordering among those ties as contractual.

#### Scenario: Immutable error message
- **WHEN** an immutable field is changed
- **THEN** the system SHALL report the changed field path with type `immutable` and message `field '<field>' is immutable after creation`.

#### Scenario: Post-merge invalid error message
- **WHEN** replication or another post-merge constraint fails
- **THEN** the system SHALL report the failing field path with type `invalid` and a message that names the actual value and the limit.
