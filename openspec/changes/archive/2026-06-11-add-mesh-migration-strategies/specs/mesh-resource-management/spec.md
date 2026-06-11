## ADDED Requirements

### Requirement: Mesh runtime catalog validation
The system SHALL validate `spec.runtime` against the runtime catalog when `spec.runtime` is present on mesh create or update, and SHALL skip catalog validation when `spec.runtime` is absent.

#### Scenario: Supported runtime version is accepted
- **WHEN** mesh create or update input contains `spec.runtime` equal to a catalog-listed version with status `supported`
- **THEN** the system SHALL accept the runtime version when no other validation errors exist.

#### Scenario: Deprecated runtime version is accepted
- **WHEN** mesh create or update input contains `spec.runtime` equal to a catalog-listed version with status `deprecated`
- **THEN** the system SHALL accept the runtime version when no validation errors exist.

#### Scenario: Skipped runtime version is rejected
- **WHEN** mesh create or update input contains `spec.runtime` equal to a catalog-listed version with status `skipped`
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `runtime version '<version>' is skipped and cannot be targeted`.

#### Scenario: Unknown runtime version is rejected
- **WHEN** mesh create or update input contains `spec.runtime` equal to a version not listed in the runtime catalog
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: Runtime omitted skips catalog validation
- **WHEN** mesh create or update input omits `spec.runtime`
- **THEN** the system SHALL NOT report a runtime catalog validation error.

### Requirement: Mesh runtime warnings
The system SHALL emit sorted warnings on otherwise successful mesh create and update operations that target deprecated catalog versions.

#### Scenario: Deprecated runtime warning shape
- **WHEN** mesh create or update succeeds with `spec.runtime` equal to a catalog-listed version with status `deprecated`
- **THEN** the JSON output SHALL include `warnings` containing an object with field `spec.runtime` and message `runtime version '<version>' is deprecated`.

#### Scenario: Warnings appear only on success
- **WHEN** mesh create or update input targets a deprecated runtime and any validation error exists
- **THEN** the system SHALL return only the standard `errors` output and SHALL NOT include `warnings`.

#### Scenario: Warnings are sorted
- **WHEN** a successful operation emits multiple warnings
- **THEN** the system SHALL sort warnings by `field` ascending, then by `message` ascending.

#### Scenario: Warnings preserve success exit code
- **WHEN** mesh create or update succeeds and emits one or more warnings
- **THEN** the command SHALL exit with the normal success exit code.

### Requirement: Mesh runtime version changes
The system SHALL treat changing `spec.runtime` from one catalog version to another on an existing mesh as a runtime version change and SHALL validate the change against the selected migration strategy.

#### Scenario: First runtime assignment does not start migration
- **WHEN** an existing mesh without `spec.runtime` is updated to a catalog-listed runtime version
- **THEN** the system SHALL store `spec.runtime` and SHALL NOT add `status.migration` or a `Migration` condition.

#### Scenario: Downgrade is rejected
- **WHEN** an update changes `spec.runtime` from a higher catalog semantic version to a lower catalog semantic version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `version downgrade from '<current>' to '<target>' is not allowed`.

#### Scenario: FullStop permits non-downgrade version change
- **WHEN** an update changes `spec.runtime` from one catalog version to a higher catalog version and `spec.migration.strategy` is `"FullStop"`
- **THEN** the system SHALL accept the version change when no other validation errors exist.

#### Scenario: RollingPatch requires same major and minor
- **WHEN** an update changes `spec.runtime` with `spec.migration.strategy` equal to `"RollingPatch"` and the source and target versions do not share the same major and minor version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: RollingPatch requires target major at least four
- **WHEN** an update changes `spec.runtime` with `spec.migration.strategy` equal to `"RollingPatch"` and the target major version is less than `4`
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: RollingPatch reports both independent failures
- **WHEN** a RollingPatch runtime version change violates both the same-major-minor rule and the target-major-at-least-four rule
- **THEN** the system SHALL report both `spec.runtime` invalid errors.

#### Scenario: LiveMigration rejects multi-region topology
- **WHEN** an update changes `spec.runtime` with `spec.migration.strategy` equal to `"LiveMigration"` and `spec.regions` is configured
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`.

#### Scenario: LiveMigration permits non-downgrade single-region version change
- **WHEN** an update changes `spec.runtime` from one catalog version to a higher catalog version, `spec.migration.strategy` is `"LiveMigration"`, and `spec.regions` is not configured
- **THEN** the system SHALL accept the version change when no other validation errors exist.

### Requirement: Mesh migration lifecycle
The system SHALL start and persist migration lifecycle state when an existing mesh changes `spec.runtime` from one catalog version to another.

#### Scenario: Migration start stores target runtime
- **WHEN** an update starts a runtime migration to `<target>`
- **THEN** the system SHALL store `<target>` in `spec.runtime`.

#### Scenario: Migration start adds migration condition
- **WHEN** an update starts a runtime migration
- **THEN** the returned and persisted mesh SHALL include a `Migration` condition with status `"True"` and message `""`.

#### Scenario: Migration start stores migration status
- **WHEN** an update starts a runtime migration from `<source>` to `<target>`
- **THEN** the returned and persisted mesh SHALL include `status.migration.sourceRuntime` equal to `<source>`, `status.migration.targetRuntime` equal to `<target>`, and `status.migration.stage` equal to the first stage for the selected migration strategy.

#### Scenario: FullStop starts at Migrate
- **WHEN** a FullStop runtime migration starts
- **THEN** `status.migration.stage` SHALL equal `"Migrate"`.

#### Scenario: RollingPatch starts at Migrate
- **WHEN** a RollingPatch runtime migration starts
- **THEN** `status.migration.stage` SHALL equal `"Migrate"`.

#### Scenario: LiveMigration starts at Prepare
- **WHEN** a LiveMigration runtime migration starts
- **THEN** `status.migration.stage` SHALL equal `"Prepare"`.

### Requirement: Mesh migrate command
The system SHALL expose `mesh migrate <name>` to advance an active mesh migration by one stage or complete the migration when it is already at the final stage.

#### Scenario: Migrate command advances non-final stage
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` for a mesh whose active migration is not at its final stage
- **THEN** the system SHALL advance `status.migration.stage` to the next stage and print the full mesh resource.

#### Scenario: Migrate command completes final stage
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` for a mesh whose active migration is at its final stage
- **THEN** the system SHALL remove the `Migration` condition, remove `status.migration`, and print the full mesh resource.

#### Scenario: FullStop migration completes from Migrate
- **WHEN** a mesh has an active FullStop migration at stage `"Migrate"` and the user runs `mesh migrate <name>`
- **THEN** the system SHALL complete the migration.

#### Scenario: RollingPatch migration completes from Migrate
- **WHEN** a mesh has an active RollingPatch migration at stage `"Migrate"` and the user runs `mesh migrate <name>`
- **THEN** the system SHALL complete the migration.

#### Scenario: LiveMigration advances through stages
- **WHEN** a mesh has an active LiveMigration migration
- **THEN** successive `mesh migrate <name>` calls SHALL advance stage `"Prepare"` to `"Replicate"`, advance `"Replicate"` to `"Cutover"`, and complete from `"Cutover"`.

#### Scenario: Migrate missing mesh
- **WHEN** the user runs `mesh migrate <name>` for a mesh that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found` using the standard not-found shape.

#### Scenario: Migrate without active migration
- **WHEN** the user runs `mesh migrate <name>` for a mesh without `status.migration`
- **THEN** the system SHALL report field `status.migration` with type `invalid` and message `no active migration for mesh '<name>'`.

### Requirement: Mesh migration rollback
The system SHALL expose `mesh migrate <name> --rollback` to roll back only active LiveMigration migrations.

#### Scenario: LiveMigration rollback clears active migration
- **WHEN** the user runs `mesh migrate <name> --rollback` for a mesh with an active LiveMigration migration
- **THEN** the system SHALL remove the `Migration` condition, remove `status.migration`, restore `spec.runtime` to the migration source runtime, and print the full mesh resource.

#### Scenario: Non-LiveMigration rollback is rejected
- **WHEN** the user runs `mesh migrate <name> --rollback` for a mesh with an active migration whose strategy is not `"LiveMigration"`
- **THEN** the system SHALL report field `status.migration` with type `invalid`.

#### Scenario: Rollback without active migration
- **WHEN** the user runs `mesh migrate <name> --rollback` for a mesh without `status.migration`
- **THEN** the system SHALL report field `status.migration` with type `invalid` and message `no active migration for mesh '<name>'`.

### Requirement: Mesh updates during active migration
The system SHALL reject changes to `spec.runtime` and `spec.migration.strategy` while a mesh has an active `Migration` condition, and SHALL allow updates to other spec fields.

#### Scenario: Runtime change during active migration is rejected
- **WHEN** an update changes `spec.runtime` while a mesh has an active migration
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `cannot change runtime version while a migration is in progress`.

#### Scenario: Strategy change during active migration is rejected
- **WHEN** an update changes `spec.migration.strategy` while a mesh has an active migration
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `cannot change migration strategy while a migration is in progress`.

#### Scenario: Other spec changes during active migration are allowed
- **WHEN** an update changes only spec fields other than `spec.runtime` and `spec.migration.strategy` while a mesh has an active migration
- **THEN** the system SHALL persist the allowed changes when no other validation errors exist.

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

#### Scenario: Migrate command advances a mesh migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>`
- **THEN** the system SHALL attempt to advance or complete the named mesh migration.

### Requirement: Mesh duplicate and not-found handling
The system SHALL reject duplicate create requests and missing named resources using structured JSON errors.

#### Scenario: Duplicate mesh name on create
- **WHEN** a create request uses a `metadata.name` that already exists
- **THEN** the system SHALL report field `metadata.name` with type `duplicate` and SHALL NOT overwrite the existing resource.

#### Scenario: Missing mesh on describe
- **WHEN** the user describes a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing mesh on delete
- **WHEN** the user deletes a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing mesh on update
- **WHEN** the user updates a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing mesh on migrate
- **WHEN** the user migrates a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

### Requirement: Mesh field validation
The system SHALL validate mesh scalar fields and map each failed condition to the documented field and error type.

#### Scenario: Invalid instance count
- **WHEN** `spec.instances` is present and is not a non-negative integer
- **THEN** the system SHALL report field `spec.instances` with type `invalid`.

#### Scenario: Invalid runtime version
- **WHEN** `spec.runtime` is present and is not a catalog-listed runtime version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: Invalid migration strategy
- **WHEN** `spec.migration.strategy` is present and is not `"FullStop"`, `"LiveMigration"`, or `"RollingPatch"`
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid`.

### Requirement: Mesh conditions
The system SHALL include `status.conditions` as a sorted array of unique condition objects.

#### Scenario: Created meshes include default conditions
- **WHEN** a mesh is created successfully
- **THEN** the system SHALL include `Healthy` and `PrechecksPassed` conditions with status `"True"` and empty messages.

#### Scenario: Conditions are sorted
- **WHEN** a resource is returned with multiple conditions
- **THEN** the system SHALL sort `status.conditions` by `type` ascending.

#### Scenario: Condition types are unique
- **WHEN** a resource would contain more than one condition with the same `type`
- **THEN** the system SHALL return at most one condition for that `type`.

#### Scenario: Clearing a condition removes it
- **WHEN** lifecycle or migration reconciliation clears a condition
- **THEN** the system SHALL remove that condition from `status.conditions`.

#### Scenario: Migration condition participates in condition ordering
- **WHEN** a returned mesh has an active migration
- **THEN** `status.conditions` SHALL include exactly one `Migration` condition sorted with all other condition types.

### Requirement: Mesh status fields
The system SHALL return `status.state`, `status.stable`, `status.instances`, conditions, active migration metadata, and stopped resume metadata for create, update, migrate, and describe responses.

#### Scenario: Running state for positive instances
- **WHEN** a returned mesh has `spec.instances` greater than `0`
- **THEN** `status.state` SHALL be `"Running"`.

#### Scenario: Stopped state for zero instances
- **WHEN** a returned mesh has `spec.instances` equal to `0`
- **THEN** `status.state` SHALL be `"Stopped"`.

#### Scenario: Stable status for steady state
- **WHEN** a returned mesh has `Healthy` equal to `"True"`, `PrechecksPassed` equal to `"True"`, no `GracefulShutdown` condition with status `"True"`, no `Scaling` condition with status `"True"`, and no `Migration` condition with status `"True"`
- **THEN** `status.stable` SHALL be `true`.

#### Scenario: Unstable status for transition state
- **WHEN** a returned mesh does not satisfy every stable status condition
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

#### Scenario: Active migration status present only during migration
- **WHEN** a returned mesh has an active migration
- **THEN** `status.migration` SHALL contain `sourceRuntime`, `targetRuntime`, and `stage`.

#### Scenario: Migration status absent after completion
- **WHEN** a returned mesh does not have an active migration
- **THEN** `status.migration` SHALL be absent.

### Requirement: Successful mesh output
The system SHALL print successful command results as JSON to stdout, print nothing to stderr, and include all defaulted fields, warning fields when applicable, and required status fields.

#### Scenario: Create returns full resource
- **WHEN** a mesh is created successfully
- **THEN** the system SHALL print the full resource with `metadata.name`, the defaulted `spec`, `status.state`, `status.stable`, `status.instances`, and `status.conditions`.

#### Scenario: Describe returns full resource
- **WHEN** an existing mesh is described
- **THEN** the system SHALL print the full persisted mesh resource after applying any pending transient lifecycle reconciliation and public output projection.

#### Scenario: Update returns full resource
- **WHEN** an existing mesh is updated successfully
- **THEN** the system SHALL print the full updated resource after applying merge semantics, validation, lifecycle status, conditions, migration status, and public output projection.

#### Scenario: Migrate returns full resource
- **WHEN** an existing mesh migration is advanced or completed successfully
- **THEN** the system SHALL print the full updated resource after applying migration status, conditions, and public output projection.

#### Scenario: Warning-bearing success returns full resource with warnings
- **WHEN** mesh create or update succeeds with one or more warnings
- **THEN** the system SHALL print the full resource and include a top-level `warnings` array.

#### Scenario: Delete returns confirmation object
- **WHEN** an existing mesh is deleted
- **THEN** the system SHALL print a JSON object containing a non-empty `message` and `metadata.name`.

### Requirement: Error output
The system SHALL print errors as JSON to stdout with an `errors` array and SHALL print nothing to stderr.

#### Scenario: Error object shape
- **WHEN** any validation, parse, duplicate, not-found, immutable, forbidden, required, or post-merge constraint error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.

#### Scenario: Errors are sorted
- **WHEN** multiple errors are returned
- **THEN** the system SHALL sort errors by `field` ascending, then by `type` ascending.

#### Scenario: Errors with same field and type are all reported
- **WHEN** multiple applicable errors have the same `field` and `type`
- **THEN** the system SHALL include every applicable error.

#### Scenario: Same-field same-type message ordering is not contractual
- **WHEN** multiple returned errors share the same `field` and `type`
- **THEN** callers SHALL NOT rely on the relative ordering of those messages.

#### Scenario: Immutable error message
- **WHEN** an immutable field is changed
- **THEN** the system SHALL report the changed field path with type `immutable` and message `field '<field>' is immutable after creation`.

#### Scenario: Post-merge invalid error message
- **WHEN** replication, migration, or another post-merge constraint fails
- **THEN** the system SHALL report the failing field path with type `invalid` and a message that names the actual value and the limit when a numeric limit exists.
