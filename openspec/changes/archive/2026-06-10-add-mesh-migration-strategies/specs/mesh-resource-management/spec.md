## ADDED Requirements

### Requirement: Mesh runtime catalog validation
The system SHALL validate `spec.runtime` against a catalog when `spec.runtime` is present on create or update. The catalog SHALL include `3.0.0` as deprecated, `3.1.0` as skipped, `3.1.1` as supported, and `4.0.0` as supported.

#### Scenario: Runtime omitted skips catalog validation
- **WHEN** a create or update input omits `spec.runtime`
- **THEN** the system SHALL NOT require catalog validation for `spec.runtime`.

#### Scenario: Supported runtime accepted
- **WHEN** `spec.runtime` is present and cataloged as supported
- **THEN** the system SHALL accept the runtime value when no other validation errors exist.

#### Scenario: Deprecated runtime accepted
- **WHEN** `spec.runtime` is present and cataloged as deprecated
- **THEN** the system SHALL accept the runtime value when no other validation errors exist.

#### Scenario: Skipped runtime rejected
- **WHEN** `spec.runtime` is present and cataloged as skipped
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `runtime version '<version>' is skipped and cannot be targeted`.

#### Scenario: Uncataloged runtime rejected
- **WHEN** `spec.runtime` is present and is not listed in the runtime catalog
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

### Requirement: Warning output
The system SHALL emit warnings for successful operations only, and warnings SHALL NOT change the success exit code.

#### Scenario: Deprecated runtime warning shape
- **WHEN** a create or update operation succeeds with deprecated `spec.runtime`
- **THEN** the output SHALL include `warnings` with an item whose `field` is `spec.runtime` and `message` is `runtime version '<version>' is deprecated`.

#### Scenario: Warnings emitted only on success
- **WHEN** an operation has any validation, parse, duplicate, not-found, immutable, forbidden, required, conflict, or post-merge constraint error
- **THEN** the system SHALL NOT emit warnings.

#### Scenario: Warning ordering
- **WHEN** multiple warnings are emitted
- **THEN** the system SHALL sort warnings by `field` ascending, then by `message` ascending.

#### Scenario: No warning for supported runtime
- **WHEN** an operation succeeds with a supported `spec.runtime`
- **THEN** the output SHALL NOT include a runtime deprecation warning.

### Requirement: Mesh runtime version change rules
The system SHALL treat changing `spec.runtime` from one catalog version to another catalog version as a version change and SHALL validate version changes against the selected migration strategy.

#### Scenario: First runtime assignment is not migration
- **WHEN** a mesh without `spec.runtime` is updated to set a cataloged `spec.runtime` for the first time
- **THEN** the system SHALL persist the runtime and SHALL NOT create a `Migration` condition or `status.migration`.

#### Scenario: Downgrade is rejected
- **WHEN** an update changes `spec.runtime` from a higher catalog version to a lower catalog version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `version downgrade from '<current>' to '<target>' is not allowed`.

#### Scenario: FullStop allows upgrades
- **WHEN** an update changes `spec.runtime` to a higher catalog version and `spec.migration.strategy` is `FullStop`
- **THEN** the system SHALL allow the version change when no other validation errors exist.

#### Scenario: RollingPatch requires same major and minor
- **WHEN** `spec.migration.strategy` is `RollingPatch` and a runtime version change does not keep the same major and minor version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: RollingPatch requires target major at least four
- **WHEN** `spec.migration.strategy` is `RollingPatch` and the target runtime major version is less than `4`
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: RollingPatch reports both failed constraints
- **WHEN** `spec.migration.strategy` is `RollingPatch` and a runtime version change fails both the same-major-minor rule and the target-major-at-least-four rule
- **THEN** the system SHALL report both `spec.runtime` invalid errors.

#### Scenario: LiveMigration rejects multi-region topology
- **WHEN** `spec.migration.strategy` is `LiveMigration` and `spec.regions` is configured
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`.

#### Scenario: LiveMigration allows otherwise valid upgrades
- **WHEN** `spec.migration.strategy` is `LiveMigration`, `spec.regions` is not configured, and a runtime version change is not a downgrade
- **THEN** the system SHALL allow the version change when no other validation errors exist.

### Requirement: Mesh migration lifecycle
The system SHALL start and persist migration status when an update changes `spec.runtime` from one catalog version to another catalog version.

#### Scenario: Migration start persists target runtime
- **WHEN** an update starts a migration
- **THEN** the system SHALL store the target version in `spec.runtime`.

#### Scenario: Migration start adds condition
- **WHEN** an update starts a migration
- **THEN** the system SHALL add a `Migration` condition to `status.conditions` with status `"True"` and message `""`.

#### Scenario: Migration start stores status
- **WHEN** an update starts a migration
- **THEN** the system SHALL add `status.migration` with `sourceRuntime`, `targetRuntime`, and `stage`.

#### Scenario: FullStop starts at migrate stage
- **WHEN** a `FullStop` runtime version change starts a migration
- **THEN** `status.migration.stage` SHALL be `"Migrate"`.

#### Scenario: RollingPatch starts at migrate stage
- **WHEN** a `RollingPatch` runtime version change starts a migration
- **THEN** `status.migration.stage` SHALL be `"Migrate"`.

#### Scenario: LiveMigration starts at first live migration stage
- **WHEN** a `LiveMigration` runtime version change starts a migration
- **THEN** `status.migration.stage` SHALL be the first stage in the LiveMigration stage sequence.

#### Scenario: Migration completion clears condition
- **WHEN** a migration completes
- **THEN** the system SHALL remove the `Migration` condition from `status.conditions`.

#### Scenario: Migration completion clears status
- **WHEN** a migration completes
- **THEN** the system SHALL remove `status.migration`.

### Requirement: Mesh migrate operation
The system SHALL expose `mesh migrate <name>` to advance an active migration by one stage and print the full mesh resource after the transition.

#### Scenario: Migrate command advances active migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` for a mesh whose active migration is not at the final stage
- **THEN** the system SHALL advance `status.migration.stage` to the next stage and print the full mesh resource.

#### Scenario: Migrate command completes final stage
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` for a mesh whose active migration is at the final stage
- **THEN** the system SHALL complete the migration and print the full mesh resource without `status.migration` or a `Migration` condition.

#### Scenario: Migrate missing mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` for a mesh that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Migrate without active migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>` for a mesh without `status.migration`
- **THEN** the system SHALL report field `status.migration` with type `invalid` and message `no active migration for mesh '<name>'`.

### Requirement: Mesh active migration updates
The system SHALL reject runtime and migration strategy changes while a `Migration` condition is active, while allowing updates to other spec fields.

#### Scenario: Runtime change rejected during active migration
- **WHEN** an update changes `spec.runtime` while a migration is active
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `cannot change runtime version while a migration is in progress`.

#### Scenario: Strategy change rejected during active migration
- **WHEN** an update changes `spec.migration.strategy` while a migration is active
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `cannot change migration strategy while a migration is in progress`.

#### Scenario: Other spec update allowed during active migration
- **WHEN** an update changes spec fields other than `spec.runtime` and `spec.migration.strategy` while a migration is active
- **THEN** the system SHALL persist the allowed changes when no other validation errors exist.

#### Scenario: LiveMigration rollback clears active migration
- **WHEN** an active `LiveMigration` rollback is requested
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

#### Scenario: Migrate command advances migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>`
- **THEN** the system SHALL attempt to advance the active migration for the named mesh.

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
The system SHALL return `status.state`, `status.stable`, `status.instances`, conditions, active migration metadata, and stopped resume metadata for create, update, migrate, and describe responses.

#### Scenario: Running state for positive instances
- **WHEN** a returned mesh has `spec.instances` greater than `0`
- **THEN** `status.state` SHALL be `"Running"`.

#### Scenario: Stopped state for zero instances
- **WHEN** a returned mesh has `spec.instances` equal to `0`
- **THEN** `status.state` SHALL be `"Stopped"`.

#### Scenario: Stable status for steady state
- **WHEN** a returned mesh has `Healthy` equal to `"True"`, `PrechecksPassed` equal to `"True"`, and no `GracefulShutdown`, `Scaling`, or `Migration` condition with status `"True"`
- **THEN** `status.stable` SHALL be `true`.

#### Scenario: Unstable status for transition state
- **WHEN** a returned mesh has transient lifecycle work or a `Migration` condition with status `"True"`
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

#### Scenario: Active migration metadata appears only during migration
- **WHEN** a mesh has an active migration
- **THEN** `status.migration` SHALL include `sourceRuntime`, `targetRuntime`, and `stage`.

#### Scenario: Migration metadata absent outside active migration
- **WHEN** a mesh has no active migration
- **THEN** `status.migration` SHALL be absent.

### Requirement: Successful mesh output
The system SHALL print successful command results as JSON to stdout, print nothing to stderr, and include all defaulted fields, required status fields, and applicable warnings.

#### Scenario: Create returns full resource
- **WHEN** a mesh is created successfully
- **THEN** the system SHALL print the full resource with `metadata.name`, the defaulted `spec`, `status.state`, `status.stable`, `status.instances`, and `status.conditions`.

#### Scenario: Describe returns full resource
- **WHEN** an existing mesh is described
- **THEN** the system SHALL print the full persisted resource after applying any pending transient lifecycle reconciliation and public output projection.

#### Scenario: Update returns full resource
- **WHEN** an existing mesh is updated successfully
- **THEN** the system SHALL print the full updated resource after applying merge semantics, validation, lifecycle status, migration status, conditions, warnings, and public output projection.

#### Scenario: Migrate returns full resource
- **WHEN** an active mesh migration is advanced or completed successfully
- **THEN** the system SHALL print the full updated resource after applying migration status, conditions, and public output projection.

#### Scenario: Delete returns confirmation object
- **WHEN** an existing mesh is deleted
- **THEN** the system SHALL print a JSON object containing a non-empty `message` and `metadata.name`.

### Requirement: Error output
The system SHALL print errors as JSON to stdout with an `errors` array, SHALL print nothing to stderr, and SHALL NOT print warnings when errors exist.

#### Scenario: Error object shape
- **WHEN** any validation, parse, duplicate, not-found, immutable, forbidden, required, conflict, or post-merge constraint error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.

#### Scenario: Errors are sorted
- **WHEN** multiple errors are returned
- **THEN** the system SHALL sort errors by `field` ascending, then by `type` ascending.

#### Scenario: Duplicate field and type errors are preserved
- **WHEN** multiple applicable errors share the same `field` and `type`
- **THEN** the system SHALL include every applicable error.

#### Scenario: Tied message ordering is not contractual
- **WHEN** multiple errors share the same `field` and `type`
- **THEN** callers SHALL NOT rely on message ordering among those tied errors.

#### Scenario: Immutable error message
- **WHEN** an immutable field is changed
- **THEN** the system SHALL report the changed field path with type `immutable` and message `field '<field>' is immutable after creation`.

#### Scenario: Post-merge invalid error message
- **WHEN** replication or another post-merge constraint fails
- **THEN** the system SHALL report the failing field path with type `invalid` and a message that names the actual value and the limit.
