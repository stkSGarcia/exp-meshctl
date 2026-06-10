## ADDED Requirements

### Requirement: Mesh update operation
The system SHALL expose `mesh update -f <path>` to apply a partial YAML update to an existing mesh selected by `metadata.name`.

#### Scenario: Update command accepts a YAML file
- **WHEN** the user runs `uv run --project /app meshctl.py mesh update -f <path>`
- **THEN** the system SHALL read `<path>` as the mesh update YAML input and attempt to update the named resource.

#### Scenario: Update selects the stored mesh by name
- **WHEN** the update input contains `metadata.name`
- **THEN** the system SHALL use that value to select the stored mesh being updated.

#### Scenario: Missing mesh on update
- **WHEN** the user updates a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Update validation failure is atomic
- **WHEN** any validation error occurs while processing an update
- **THEN** the system SHALL reject the whole update and SHALL NOT persist any field from that update.

### Requirement: Mesh update merge behavior
The system SHALL merge valid update input into the stored resource before post-merge validation.

#### Scenario: Provided leaf replaces stored leaf
- **WHEN** an update provides a leaf field that already exists on the stored resource
- **THEN** the system SHALL replace the stored leaf value with the provided value.

#### Scenario: Omitted field keeps stored value
- **WHEN** an update omits a field that exists on the stored resource
- **THEN** the system SHALL keep the stored value for that field.

#### Scenario: Nested objects merge field by field
- **WHEN** an update provides a nested object
- **THEN** the system SHALL merge that object with the stored object field by field.

#### Scenario: Create defaults are not reapplied during update
- **WHEN** an update omits a field that has a create-time default
- **THEN** the system SHALL NOT re-run the create-time default for that omitted field.

#### Scenario: Storage class update preserves storage size and replication factor
- **WHEN** an update sets `spec.network.storage.className` and omits `spec.network.storage.size` and `spec.network.replicationFactor`
- **THEN** the system SHALL preserve the stored `spec.network.storage.size` and `spec.network.replicationFactor`.

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
- **WHEN** lifecycle reconciliation clears a condition
- **THEN** the system SHALL remove that condition from `status.conditions`.

### Requirement: Mesh instance lifecycle transitions
The system SHALL derive lifecycle status transitions from changes to `spec.instances`.

#### Scenario: Scale up update returns starting instances
- **WHEN** `spec.instances` changes from a lower positive count to a higher positive count
- **THEN** the update response SHALL include a `Scaling` condition with status `"True"` and a non-empty message, `status.instances.ready` equal to the previous count, and `status.instances.starting` equal to the new count minus the old count.

#### Scenario: Scale up completes on next describe
- **WHEN** the next describe reads a mesh after a scale-up update response
- **THEN** the describe response SHALL set `status.instances.ready` to the new count, set `status.instances.starting` to `0`, and omit the transient `Scaling` condition.

#### Scenario: Scale down update reports scaling
- **WHEN** `spec.instances` changes from a higher positive count to a lower positive count
- **THEN** the update response SHALL include a transient `Scaling` condition with status `"True"`.

#### Scenario: Scale down completes on next describe
- **WHEN** the next describe reads a mesh after a scale-down update response
- **THEN** the describe response SHALL omit the transient `Scaling` condition.

#### Scenario: Stop update records graceful shutdown
- **WHEN** `spec.instances` changes from a positive count to `0`
- **THEN** the update response SHALL include `GracefulShutdown` with status `"True"` and an empty message, set `status.desiredInstancesOnResume` to the previous instance count, set `status.instances.ready` and `status.instances.starting` to `0`, set `status.instances.stopped` to the previous count, and set `status.state` to `"Stopped"`.

#### Scenario: Stopped mesh keeps shutdown state
- **WHEN** a stopped mesh is described before resume
- **THEN** the system SHALL keep `GracefulShutdown` and `status.desiredInstancesOnResume` in the returned resource.

#### Scenario: Resume update uses explicit target count
- **WHEN** a stopped mesh with `GracefulShutdown` changes from `0` instances to a positive `spec.instances`
- **THEN** the update response SHALL remove `GracefulShutdown`, remove `status.desiredInstancesOnResume`, set `status.instances.ready` to `0`, set `status.instances.starting` to the target count, set `status.instances.stopped` to `0`, and set `status.state` to `"Running"`.

#### Scenario: Resume update uses stored target count
- **WHEN** a stopped mesh with `GracefulShutdown` is updated with `spec.instances` omitted or null
- **THEN** the system SHALL use `status.desiredInstancesOnResume` as the target count for the resume.

#### Scenario: Resume completes on next describe
- **WHEN** the next describe reads a mesh after a resume update response
- **THEN** the describe response SHALL set `status.instances.ready` to the target count and set `status.instances.starting` to `0`.

### Requirement: Mesh network storage
The system SHALL support `spec.network.storage` with immutable size and mutable storage mode fields.

#### Scenario: Storage defaults on create
- **WHEN** a valid create input omits `spec.network.storage.size` and `spec.network.storage.ephemeral`
- **THEN** the created resource SHALL store `spec.network.storage.size` as `"1Gi"` and `spec.network.storage.ephemeral` as `false`.

#### Scenario: Storage size validates as memory quantity
- **WHEN** `spec.network.storage.size` is present and is not a non-negative integer with optional `Ki`, `Mi`, `Gi`, or `Ti` suffix
- **THEN** the system SHALL report field `spec.network.storage.size` with type `invalid`.

#### Scenario: Storage size is immutable
- **WHEN** an update changes the stored `spec.network.storage.size`
- **THEN** the system SHALL report field `spec.network.storage.size` with type `immutable` and SHALL NOT persist the update.

#### Scenario: Ephemeral storage still stores size
- **WHEN** a mesh has `spec.network.storage.ephemeral` equal to `true`
- **THEN** the system SHALL keep the canonical `spec.network.storage.size` value for validation and future updates.

#### Scenario: Persistent storage output includes size
- **WHEN** a returned mesh has `spec.network.storage.ephemeral` equal to `false`
- **THEN** the output SHALL include `spec.network.storage.ephemeral` and `spec.network.storage.size`.

#### Scenario: Ephemeral storage output hides size
- **WHEN** a returned mesh has `spec.network.storage.ephemeral` equal to `true`
- **THEN** the output SHALL include `spec.network.storage.ephemeral` and SHALL omit `spec.network.storage.size`.

#### Scenario: Storage class is mutable
- **WHEN** an update changes only `spec.network.storage.className`
- **THEN** the system SHALL persist the new class name without changing storage size.

### Requirement: Mesh replication factor
The system SHALL support `spec.network.replicationFactor` as a positive integer topology field with a computed create-time default.

#### Scenario: Replication factor defaults from instance count
- **WHEN** a valid create input omits `spec.network.replicationFactor`
- **THEN** the system SHALL compute and store a default based on `spec.instances`.

#### Scenario: Replication factor must be positive
- **WHEN** `spec.network.replicationFactor` is present and is not an integer of at least `1`
- **THEN** the system SHALL report field `spec.network.replicationFactor` with type `invalid`.

#### Scenario: Replication factor must not exceed running instances
- **WHEN** a mesh has a positive `spec.instances` count and `spec.network.replicationFactor` exceeds `spec.instances`
- **THEN** the system SHALL report field `spec.network.replicationFactor` with type `invalid` and name the actual value and limit in the message.

### Requirement: Mesh status fields
The system SHALL return `status.state`, `status.stable`, `status.instances`, conditions, and stopped resume metadata for create, update, and describe responses.

#### Scenario: Running state for positive instances
- **WHEN** a returned mesh has `spec.instances` greater than `0`
- **THEN** `status.state` SHALL be `"Running"`.

#### Scenario: Stopped state for zero instances
- **WHEN** a returned mesh has `spec.instances` equal to `0`
- **THEN** `status.state` SHALL be `"Stopped"`.

#### Scenario: Stable status for steady state
- **WHEN** a returned mesh has no transient lifecycle work
- **THEN** `status.stable` SHALL be `true`.

#### Scenario: Unstable status for transition state
- **WHEN** a returned mesh has transient lifecycle work
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

## MODIFIED Requirements

### Requirement: Mesh CLI command surface
The system SHALL expose `mesh create`, `mesh list`, `mesh describe`, `mesh delete`, and `mesh update` operations through `meshctl.py`.

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

### Requirement: Mesh defaulting
The system SHALL apply documented defaults to successful create output and persisted resources while leaving fields without defaults absent when omitted.

#### Scenario: Defaults applied to omitted fields
- **WHEN** a valid create input omits `spec.instances`, `spec.resources.memory`, `spec.access.authentication.enabled`, `spec.migration.strategy`, `spec.network.storage.size`, `spec.network.storage.ephemeral`, and `spec.network.replicationFactor`
- **THEN** the created resource SHALL include `spec.instances` as `1`, `spec.resources.memory` as `{"limit": "1Gi", "request": "1Gi"}`, `spec.access.authentication.enabled` as `true`, `spec.migration.strategy` as `"FullStop"`, `spec.network.storage.size` as `"1Gi"`, `spec.network.storage.ephemeral` as `false`, and a computed `spec.network.replicationFactor`.

#### Scenario: Fields without defaults remain absent
- **WHEN** a valid create input omits `spec.runtime`, `spec.resources.cpu`, `spec.network.storage.className`, or any other field without a documented default
- **THEN** the created resource SHALL omit those fields from the returned and persisted resource.

### Requirement: Mesh field validation
The system SHALL validate mesh scalar fields and map each failed condition to the documented field and error type.

#### Scenario: Invalid instance count
- **WHEN** `spec.instances` is present and is not a non-negative integer
- **THEN** the system SHALL report field `spec.instances` with type `invalid`.

#### Scenario: Invalid runtime version
- **WHEN** `spec.runtime` is present and does not parse as semantic version `major.minor.patch` with non-negative integer parts
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: Invalid migration strategy
- **WHEN** `spec.migration.strategy` is present and is not `"FullStop"`
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid`.

### Requirement: Successful mesh output
The system SHALL print successful command results as JSON to stdout, print nothing to stderr, and include all defaulted fields and required status fields.

#### Scenario: Create returns full resource
- **WHEN** a mesh is created successfully
- **THEN** the system SHALL print the full resource with `metadata.name`, the defaulted `spec`, `status.state`, `status.stable`, `status.instances`, and `status.conditions`.

#### Scenario: Describe returns full resource
- **WHEN** an existing mesh is described
- **THEN** the system SHALL print the full persisted resource after applying any pending transient lifecycle reconciliation and public output projection.

#### Scenario: Update returns full resource
- **WHEN** an existing mesh is updated successfully
- **THEN** the system SHALL print the full updated resource after applying merge semantics, validation, lifecycle status, conditions, and public output projection.

#### Scenario: Delete returns confirmation object
- **WHEN** an existing mesh is deleted
- **THEN** the system SHALL print a JSON object containing a non-empty `message` and `metadata.name`.

### Requirement: Error output
The system SHALL print errors as JSON to stdout with an `errors` array and SHALL print nothing to stderr.

#### Scenario: Error object shape
- **WHEN** any validation, parse, duplicate, not-found, immutable, or post-merge constraint error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.

#### Scenario: Error order is not contractual
- **WHEN** multiple errors are returned
- **THEN** callers SHALL NOT rely on the order of errors in the `errors` array.

#### Scenario: Immutable error message
- **WHEN** an immutable field is changed
- **THEN** the system SHALL report the changed field path with type `immutable` and message `field '<field>' is immutable after creation`.

#### Scenario: Post-merge invalid error message
- **WHEN** replication or another post-merge constraint fails
- **THEN** the system SHALL report the failing field path with type `invalid` and a message that names the actual value and the limit.
