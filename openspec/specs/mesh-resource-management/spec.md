# mesh-resource-management

## Purpose

Define the mesh CLI resource model, operations, validation, defaulting, persistence behavior, lifecycle state, topology fields, and JSON output contract.
## Requirements
### Requirement: Mesh CLI command surface
The system SHALL expose `mesh create`, `mesh list`, `mesh describe`, `mesh delete`, `mesh update`, `mesh migrate`, and `mesh shell` operations through `meshctl.py`.

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

#### Scenario: Shell command returns mesh connection details
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell <name>`
- **THEN** the system SHALL attempt to return the named mesh connection details.

### Requirement: Mesh create input format
The system SHALL accept exactly one YAML document whose root value is a mapping with supported top-level `metadata` and `spec` content.

#### Scenario: YAML read or parse failure
- **WHEN** the create input file cannot be read or parsed as YAML
- **THEN** the system SHALL print a JSON error object containing an error with field `""` and type `parse`.

#### Scenario: YAML document is not a mapping
- **WHEN** the create input parses but the YAML document root is not a mapping
- **THEN** the system SHALL print a JSON error object and SHALL NOT persist a mesh.

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

### Requirement: Mesh name validation
The system SHALL require `metadata.name` to be a non-empty string of at least two characters matching `^[a-z0-9][a-z0-9-]*[a-z0-9]$`.

#### Scenario: Missing null or empty name
- **WHEN** a create input omits `metadata.name` or provides it as null or an empty string
- **THEN** the system SHALL report field `metadata.name` with type `required`.

#### Scenario: Invalid name format
- **WHEN** a create input provides a `metadata.name` that does not match the required format
- **THEN** the system SHALL report field `metadata.name` with type `invalid`.

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

#### Scenario: Missing mesh on shell
- **WHEN** the user shells into a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

### Requirement: Mesh deletion dependency conflicts
The system SHALL reject `mesh delete` when one or more vaults reference the mesh through `spec.meshRef`.

#### Scenario: Mesh delete blocked by dependent vault
- **WHEN** the user deletes a mesh that is referenced by at least one vault through `spec.meshRef`
- **THEN** the system SHALL NOT delete the mesh and SHALL report field `metadata.name` with type `conflict`.

#### Scenario: Conflict message names dependent vaults
- **WHEN** a mesh delete is blocked by dependent vaults
- **THEN** the error message SHALL name the dependent vaults.

#### Scenario: Conflict vault order is not contractual
- **WHEN** multiple vaults block a mesh delete
- **THEN** callers SHALL NOT rely on the order of vault names in the conflict message.

### Requirement: Mesh defaulting
The system SHALL apply documented defaults to successful create output and persisted resources while leaving fields without defaults absent when omitted.

#### Scenario: Defaults applied to omitted fields
- **WHEN** a valid create input omits `spec.instances`, `spec.resources.memory`, `spec.access`, `spec.migration.strategy`, `spec.network.storage.size`, `spec.network.storage.ephemeral`, `spec.network.replicationFactor`, and `spec.management.enabled`
- **THEN** the created resource SHALL include `spec.instances` as `1`, `spec.resources.memory` as `{"limit": "1Gi", "request": "1Gi"}`, `spec.access.authentication.enabled` as `true`, `spec.access.authentication.digestAlgorithm` as `"SHA-256"`, `spec.access.encryption.source` as `"None"`, `spec.access.encryption.clientMode` as `"None"`, `spec.access.permissions.enabled` as `false`, `spec.migration.strategy` as `"FullStop"`, `spec.network.storage.size` as `"1Gi"`, `spec.network.storage.ephemeral` as `false`, a computed `spec.network.replicationFactor`, and `spec.management.enabled` as `false`.

#### Scenario: Fields without defaults remain absent
- **WHEN** a valid create input omits `spec.runtime`, `spec.resources.cpu`, `spec.network.storage.className`, `spec.exposure`, or any other field without a documented default
- **THEN** the created resource SHALL omit those fields from the returned and persisted resource.

### Requirement: Mesh access authentication
The system SHALL support authentication settings under `spec.access.authentication` and an optional `spec.access.credentialRef`.

#### Scenario: Authentication defaults to enabled with SHA-256
- **WHEN** a valid create input omits `spec.access.authentication.enabled` and `spec.access.authentication.digestAlgorithm`
- **THEN** the created resource SHALL include `spec.access.authentication.enabled` as `true` and `spec.access.authentication.digestAlgorithm` as `"SHA-256"`.

#### Scenario: Credential reference is preserved when authentication is enabled
- **WHEN** a valid create input includes `spec.access.credentialRef` while authentication is enabled
- **THEN** the created resource SHALL include `spec.access.credentialRef` with the provided value.

#### Scenario: Digest algorithm allows documented values
- **WHEN** `spec.access.authentication.digestAlgorithm` is present and is one of `"SHA-256"`, `"SHA-384"`, or `"SHA-512"`
- **THEN** the system SHALL accept the digest algorithm.

#### Scenario: Invalid digest algorithm is rejected
- **WHEN** `spec.access.authentication.digestAlgorithm` is present and is not one of `"SHA-256"`, `"SHA-384"`, or `"SHA-512"`
- **THEN** the system SHALL report field `spec.access.authentication.digestAlgorithm` with type `invalid`.

#### Scenario: Disabled authentication omits digest algorithm
- **WHEN** a mesh has `spec.access.authentication.enabled` equal to `false`
- **THEN** the returned resource SHALL include `spec.access.authentication` with only `enabled` equal to `false`.

#### Scenario: Digest algorithm is forbidden when authentication is disabled
- **WHEN** authentication is disabled and `spec.access.authentication.digestAlgorithm` is present
- **THEN** the system SHALL report field `spec.access.authentication.digestAlgorithm` with type `forbidden`.

#### Scenario: Credential reference is forbidden when authentication is disabled
- **WHEN** authentication is disabled and `spec.access.credentialRef` is present
- **THEN** the system SHALL report field `spec.access.credentialRef` with type `forbidden`.

### Requirement: Mesh access permissions
The system SHALL support optional permission role validation under `spec.access.permissions`.

#### Scenario: Permissions default to disabled
- **WHEN** a valid create input omits `spec.access.permissions.enabled`
- **THEN** the created resource SHALL include `spec.access.permissions.enabled` as `false`.

#### Scenario: Roles are required when permissions are enabled
- **WHEN** `spec.access.permissions.enabled` is `true` and `spec.access.permissions.roles` is missing or empty
- **THEN** the system SHALL report field `spec.access.permissions.roles` with type `required`.

#### Scenario: Role name is required
- **WHEN** `spec.access.permissions.roles` contains a role with missing or empty `name`
- **THEN** the system SHALL report field `spec.access.permissions.roles[<index>].name` with type `required`.

#### Scenario: Role permissions are required
- **WHEN** `spec.access.permissions.roles` contains a role with missing or empty `permissions`
- **THEN** the system SHALL report field `spec.access.permissions.roles[<index>].permissions` with type `required`.

#### Scenario: Duplicate role names are rejected
- **WHEN** `spec.access.permissions.roles` contains more than one role with the same `name`
- **THEN** the system SHALL report field `spec.access.permissions.roles` with type `duplicate`.

#### Scenario: Roles appear only when permissions are enabled
- **WHEN** a returned mesh has `spec.access.permissions.enabled` equal to `false`
- **THEN** the returned resource SHALL omit `spec.access.permissions.roles`.

### Requirement: Mesh access encryption
The system SHALL support encryption certificate source selection under `spec.access.encryption`.

#### Scenario: Encryption defaults to none
- **WHEN** a valid create input omits `spec.access.encryption`
- **THEN** the created resource SHALL include `spec.access.encryption.source` as `"None"` and `spec.access.encryption.clientMode` as `"None"`.

#### Scenario: Encryption source validates allowed values
- **WHEN** `spec.access.encryption.source` is present and is not `"None"`, `"Secret"`, or `"Service"`
- **THEN** the system SHALL report field `spec.access.encryption.source` with type `invalid`.

#### Scenario: Encryption client mode validates allowed values
- **WHEN** `spec.access.encryption.clientMode` is present and is not `"None"`, `"Authenticate"`, or `"Validate"`
- **THEN** the system SHALL report field `spec.access.encryption.clientMode` with type `invalid`.

#### Scenario: Secret source requires certificate reference
- **WHEN** `spec.access.encryption.source` is `"Secret"` and `spec.access.encryption.certRef` is missing
- **THEN** the system SHALL report field `spec.access.encryption.certRef` with type `required`.

#### Scenario: Secret source forbids certificate service reference
- **WHEN** `spec.access.encryption.source` is `"Secret"` and `spec.access.encryption.certServiceRef` is present
- **THEN** the system SHALL report field `spec.access.encryption.certServiceRef` with type `forbidden`.

#### Scenario: Service source requires certificate service reference
- **WHEN** `spec.access.encryption.source` is `"Service"` and `spec.access.encryption.certServiceRef` is missing
- **THEN** the system SHALL report field `spec.access.encryption.certServiceRef` with type `required`.

#### Scenario: Service source forbids certificate reference
- **WHEN** `spec.access.encryption.source` is `"Service"` and `spec.access.encryption.certRef` is present
- **THEN** the system SHALL report field `spec.access.encryption.certRef` with type `forbidden`.

#### Scenario: None source forbids certificate references
- **WHEN** `spec.access.encryption.source` is `"None"` and `spec.access.encryption.certRef` or `spec.access.encryption.certServiceRef` is present
- **THEN** the system SHALL report each provided certificate reference field with type `forbidden`.

#### Scenario: None source allows only none client mode
- **WHEN** `spec.access.encryption.source` is `"None"` and `spec.access.encryption.clientMode` is `"Authenticate"` or `"Validate"`
- **THEN** the system SHALL report field `spec.access.encryption.clientMode` with type `invalid`.

### Requirement: Mesh access output
The system SHALL include `spec.access` with all applicable defaults in successful mesh create and describe output.

#### Scenario: Omitted access outputs full default section
- **WHEN** a valid create input omits `spec.access`
- **THEN** create and describe output SHALL include defaulted authentication, permissions, and encryption fields under `spec.access`.

#### Scenario: Optional access fields appear only when set and applicable
- **WHEN** optional access fields without defaults are omitted or are not applicable to the selected access mode
- **THEN** create and describe output SHALL omit those optional fields.

#### Scenario: Object key order is not contractual
- **WHEN** a mesh output contains `spec.access`
- **THEN** callers SHALL NOT rely on object key order.

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

### Requirement: Mesh resource quantity validation
The system SHALL validate memory and CPU resource quantities and ensure requests do not exceed limits.

#### Scenario: Memory limit required when memory object is present
- **WHEN** `spec.resources.memory` is present but `spec.resources.memory.limit` is missing or null
- **THEN** the system SHALL report field `spec.resources.memory.limit` with type `required`.

#### Scenario: CPU limit required when CPU object is present
- **WHEN** `spec.resources.cpu` is present but `spec.resources.cpu.limit` is missing or null
- **THEN** the system SHALL report field `spec.resources.cpu.limit` with type `required`.

#### Scenario: Invalid memory quantity
- **WHEN** a memory `limit` or `request` is not a non-negative integer with optional `Ki`, `Mi`, `Gi`, or `Ti` suffix
- **THEN** the system SHALL report the corresponding `spec.resources.memory.<field>` with type `invalid`.

#### Scenario: Invalid CPU quantity
- **WHEN** a CPU `limit` or `request` is not a non-negative integer core count or non-negative integer with `m` suffix
- **THEN** the system SHALL report the corresponding `spec.resources.cpu.<field>` with type `invalid`.

#### Scenario: Memory request exceeds limit
- **WHEN** `spec.resources.memory.request` represents a quantity greater than `spec.resources.memory.limit`
- **THEN** the system SHALL report field `spec.resources.memory.request` with type `invalid`.

#### Scenario: CPU request exceeds limit
- **WHEN** `spec.resources.cpu.request` represents a quantity greater than `spec.resources.cpu.limit`
- **THEN** the system SHALL report field `spec.resources.cpu.request` with type `invalid`.

#### Scenario: Resource request defaults to limit
- **WHEN** `spec.resources.memory.request` or `spec.resources.cpu.request` is omitted from a present resource object with a valid limit
- **THEN** the system SHALL default the omitted request to the corresponding limit.

### Requirement: Autoscaling fields are forbidden
The system SHALL reject any field named `autoScaling` that appears under `spec`.

#### Scenario: Top-level autoscaling under spec
- **WHEN** create input contains `spec.autoScaling`
- **THEN** the system SHALL report field `spec.autoScaling` with type `forbidden`.

#### Scenario: Nested autoscaling under spec
- **WHEN** create input contains a nested field named `autoScaling` anywhere under `spec`
- **THEN** the system SHALL report the full dot path to that field with type `forbidden`.

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

### Requirement: Mesh list output
The system SHALL list mesh summaries sorted by `name` ascending using lexicographic, case-sensitive ordering.

#### Scenario: List returns sorted summaries
- **WHEN** meshes named `beta`, `alpha`, and `gamma` exist
- **THEN** `mesh list` SHALL print summaries in the order `alpha`, `beta`, `gamma`.

#### Scenario: List summary shape
- **WHEN** `mesh list` returns a mesh
- **THEN** each array item SHALL contain only the mesh `name` and `status.state` summary fields.

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

### Requirement: Mesh exposure configuration
The system SHALL support optional `spec.exposure` configuration for external mesh access.

#### Scenario: Omitted exposure configures no external access
- **WHEN** a valid mesh create input omits `spec.exposure`
- **THEN** the returned and persisted resource SHALL omit `spec.exposure` and SHALL omit `status.connectionDetails`.

#### Scenario: Exposure type is required
- **WHEN** `spec.exposure` is present and `spec.exposure.type` is missing, null, or an empty string
- **THEN** the system SHALL report field `spec.exposure.type` with type `required`.

#### Scenario: Exposure type validates allowed values
- **WHEN** `spec.exposure.type` is present and is not `"Gateway"`, `"DirectPort"`, or `"Balancer"`
- **THEN** the system SHALL report field `spec.exposure.type` with type `invalid`.

#### Scenario: Gateway exposure preserves hostname and annotations
- **WHEN** a valid mesh uses `spec.exposure.type` equal to `"Gateway"` with `hostname` and `annotations`
- **THEN** the returned and persisted resource SHALL preserve `spec.exposure.hostname` and the `spec.exposure.annotations` string mapping.

#### Scenario: Gateway exposure forbids port fields
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.port` or `spec.exposure.directPort` is present
- **THEN** the system SHALL report each provided forbidden field using its full dot path and type `forbidden`.

#### Scenario: DirectPort exposure accepts port fields
- **WHEN** a valid mesh uses `spec.exposure.type` equal to `"DirectPort"` with `port` or `directPort`
- **THEN** the returned and persisted resource SHALL preserve the provided integer port fields.

#### Scenario: DirectPort exposure forbids gateway fields
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.hostname` or `spec.exposure.annotations` is present
- **THEN** the system SHALL report each provided forbidden field using its full dot path and type `forbidden`.

#### Scenario: Balancer exposure accepts service port
- **WHEN** a valid mesh uses `spec.exposure.type` equal to `"Balancer"` with `port`
- **THEN** the returned and persisted resource SHALL preserve `spec.exposure.port`.

#### Scenario: Balancer exposure forbids gateway and direct port fields
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.hostname`, `spec.exposure.annotations`, or `spec.exposure.directPort` is present
- **THEN** the system SHALL report each provided forbidden field using its full dot path and type `forbidden`.

#### Scenario: Exposure scalar field validation
- **WHEN** `spec.exposure.hostname` is present and is not a string, `spec.exposure.port` is present and is not an integer, or `spec.exposure.directPort` is present and is not an integer
- **THEN** the system SHALL report each invalid field with type `invalid`.

#### Scenario: Exposure annotations validation
- **WHEN** `spec.exposure.annotations` is present and is not a map from string keys to string values
- **THEN** the system SHALL report field `spec.exposure.annotations` with type `invalid`.

### Requirement: Mesh connection details
The system SHALL compute `status.connectionDetails` for exposed meshes in successful create and describe output.

#### Scenario: Gateway connection details
- **WHEN** a mesh has `spec.exposure.type` equal to `"Gateway"`
- **THEN** `status.connectionDetails` SHALL contain `host` equal to `spec.exposure.hostname` when set or a default host when omitted, `port` equal to `443`, and `protocol` equal to `"https"`.

#### Scenario: DirectPort connection details
- **WHEN** a mesh named `<name>` has `spec.exposure.type` equal to `"DirectPort"`
- **THEN** `status.connectionDetails` SHALL contain `host` equal to `<name>`, `port` equal to `spec.exposure.directPort` when set or the default direct port when omitted, and `protocol` equal to `"https"`.

#### Scenario: Balancer connection details
- **WHEN** a mesh named `<name>` has `spec.exposure.type` equal to `"Balancer"`
- **THEN** `status.connectionDetails` SHALL contain `host` equal to `<name>-external`, `port` equal to `spec.exposure.port` when set or the default balancer port when omitted, and `protocol` equal to `"https"`.

#### Scenario: Connection details are absent without exposure
- **WHEN** a mesh omits `spec.exposure`
- **THEN** create and describe output SHALL omit `status.connectionDetails`.

### Requirement: Mesh management endpoint
The system SHALL support `spec.management.enabled` as a boolean management endpoint toggle with a default of `false`.

#### Scenario: Management defaults to disabled
- **WHEN** a valid create input omits `spec.management.enabled`
- **THEN** the returned and persisted resource SHALL include `spec.management.enabled` as `false` and SHALL omit `status.managementConnectionDetails`.

#### Scenario: Management enabled emits connection details
- **WHEN** a mesh named `<name>` has `spec.management.enabled` equal to `true`
- **THEN** create and describe output SHALL include `status.managementConnectionDetails` with `host` equal to `<name>-admin`, `port` equal to `9990`, and `protocol` equal to `"https"`.

#### Scenario: Management enabled validates as boolean
- **WHEN** `spec.management.enabled` is present and is not a boolean
- **THEN** the system SHALL report field `spec.management.enabled` with type `invalid`.

#### Scenario: Management enabled is immutable after create
- **WHEN** an update changes the stored `spec.management.enabled`
- **THEN** the system SHALL report field `spec.management.enabled` with type `immutable`, message `field 'spec.management.enabled' is immutable after creation`, and SHALL NOT persist the update.

### Requirement: Mesh shell command
The system SHALL expose `mesh shell <name>` to return connection details for an exposed mesh.

#### Scenario: Shell returns connection details object
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell <name>` for a mesh with exposure configured
- **THEN** the system SHALL print only the mesh `status.connectionDetails` object without a resource envelope.

#### Scenario: Shell missing mesh
- **WHEN** the user runs `mesh shell <name>` for a mesh that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found` using the standard not-found shape.

#### Scenario: Shell rejects mesh without exposure
- **WHEN** the user runs `mesh shell <name>` for a mesh with no `spec.exposure`
- **THEN** the system SHALL report field `spec.exposure` with type `invalid` and message `mesh '<name>' has no exposure configured`.

