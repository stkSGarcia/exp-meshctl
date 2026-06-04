# mesh-management Specification

## Purpose
TBD - created by archiving change implement-meshctl. Update Purpose after archive.
## Requirements
### Requirement: CLI entry point
The tool SHALL be invokable as `uv run --project /app meshctl.py mesh <operation> [arguments]` and SHALL route to the correct operation handler.

#### Scenario: Valid subcommand dispatched
- **WHEN** the user runs `meshctl.py mesh create -f <path>`
- **THEN** the create handler is invoked with the given file path

#### Scenario: Unknown subcommand
- **WHEN** the user runs `meshctl.py mesh <unknown>`
- **THEN** the tool exits with a non-success indicator (implementation detail)

---

### Requirement: Mesh create
The system SHALL read a YAML document from the file path given by `-f`, apply all defaults, validate all fields, and — if valid and the name is not already taken — persist the resource and print the full resource as JSON to stdout.

#### Scenario: Valid create
- **WHEN** a valid YAML file is provided with a unique mesh name
- **THEN** the resource is persisted with defaults applied and the full resource JSON is printed

#### Scenario: Duplicate name rejected
- **WHEN** `create` is called with a name that already exists
- **THEN** output `{"errors":[{"field":"metadata.name","type":"duplicate","message":"<msg>"}]}` and do not persist

#### Scenario: Invalid YAML file
- **WHEN** the file cannot be read or is not valid YAML
- **THEN** output `{"errors":[{"field":"","type":"parse","message":"<msg>"}]}`

---

### Requirement: Mesh list
The system SHALL print a JSON array of all stored mesh summaries, sorted by `name` ascending lexicographically (case-sensitive).

#### Scenario: Non-empty store
- **WHEN** one or more meshes exist
- **THEN** output a JSON array of `{"name":"<string>","status":{"state":"<string>"}}` objects sorted by name

#### Scenario: Empty store
- **WHEN** no meshes exist
- **THEN** output `[]`

---

### Requirement: Mesh describe
The system SHALL print the full resource JSON for the mesh identified by `<name>`.

#### Scenario: Existing mesh
- **WHEN** the named mesh exists
- **THEN** output the full resource JSON including all defaulted spec fields and `status`

#### Scenario: Unknown mesh
- **WHEN** the named mesh does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Mesh delete
The system SHALL remove the named mesh from the store and print a confirmation JSON object. Before deleting, the system SHALL check whether any vaults reference the mesh through `spec.meshRef`. If one or more dependent vaults exist, the system SHALL reject the deletion with a `conflict` error and SHALL NOT remove the mesh.

#### Scenario: Existing mesh deleted when no dependent vaults exist
- **WHEN** the named mesh exists and no vault has `spec.meshRef` equal to that mesh name
- **THEN** remove it from the store and output `{"message":"<non-empty>","metadata":{"name":"<string>"}}`

#### Scenario: Unknown mesh
- **WHEN** the named mesh does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

#### Scenario: Delete blocked when dependent vaults exist
- **WHEN** the named mesh exists and one or more vaults have `spec.meshRef` equal to that mesh name
- **THEN** output `{"errors":[{"field":"metadata.name","type":"conflict","message":"<msg>"}]}` naming the dependent vaults, and do not delete the mesh

### Requirement: YAML input schema
**Updated:** The system SHALL accept `spec.exposure` (optional) and `spec.management` (optional) as recognized top-level keys under `spec`. All existing fields remain unchanged.

#### Scenario: Exposure and management fields accepted
- **WHEN** the input YAML includes `spec.exposure` and `spec.management`
- **THEN** they are parsed and validated without a parse error

---

### Requirement: Name validation
`metadata.name` SHALL be required, non-null, non-empty, and SHALL match `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (minimum length 2).

#### Scenario: Valid name
- **WHEN** `metadata.name` is `"my-mesh"`
- **THEN** name validation passes

#### Scenario: Missing name
- **WHEN** `metadata.name` is absent or null
- **THEN** output error `{"field":"metadata.name","type":"required","message":"<msg>"}`

#### Scenario: Invalid name format
- **WHEN** `metadata.name` is `"My_Mesh"` or `"a"` (too short) or `"-bad"` (starts with hyphen)
- **THEN** output error `{"field":"metadata.name","type":"invalid","message":"<msg>"}`

---

### Requirement: Instance count validation and default
`spec.instances` SHALL be a positive integer. If absent, it SHALL default to `1`.

#### Scenario: Absent instances defaults to 1
- **WHEN** `spec.instances` is not specified
- **THEN** the persisted resource has `spec.instances = 1`

#### Scenario: Invalid instances
- **WHEN** `spec.instances` is `0`, negative, or non-integer
- **THEN** output error `{"field":"spec.instances","type":"invalid","message":"<msg>"}`

---

### Requirement: Runtime version validation
`spec.runtime`, when present, SHALL parse as `major.minor.patch` where each part is a non-negative integer. If absent, it SHALL be omitted from output.

#### Scenario: Valid runtime
- **WHEN** `spec.runtime` is `"1.2.3"`
- **THEN** runtime validation passes and value is preserved

#### Scenario: Invalid runtime format
- **WHEN** `spec.runtime` is `"1.2"` or `"v1.2.3"` or `"1.2.x"`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}`

#### Scenario: Absent runtime omitted
- **WHEN** `spec.runtime` is not in the input
- **THEN** `spec.runtime` is absent from the output JSON

---

### Requirement: Memory resource validation and defaults
When `spec.resources.memory` is absent, the system SHALL default it to `{"limit":"1Gi","request":"1Gi"}`. When present, `limit` SHALL be required and `request` SHALL default to `limit`. Memory quantities SHALL be a non-negative integer optionally suffixed with `Ki`, `Mi`, `Gi`, or `Ti`. `request` SHALL NOT exceed `limit`.

#### Scenario: Absent memory defaults applied
- **WHEN** `spec.resources.memory` is not specified
- **THEN** output has `spec.resources.memory = {"limit":"1Gi","request":"1Gi"}`

#### Scenario: Memory limit required when memory object present
- **WHEN** `spec.resources.memory` is present but `limit` is absent
- **THEN** output error `{"field":"spec.resources.memory.limit","type":"required","message":"<msg>"}`

#### Scenario: Memory request defaults to limit
- **WHEN** `spec.resources.memory.limit` is `"2Gi"` and `request` is absent
- **THEN** output has `spec.resources.memory.request = "2Gi"`

#### Scenario: Memory request exceeds limit rejected
- **WHEN** `spec.resources.memory.request` parses to a value greater than `limit`
- **THEN** output error `{"field":"spec.resources.memory.request","type":"invalid","message":"<msg>"}`

#### Scenario: Invalid memory quantity
- **WHEN** `spec.resources.memory.limit` is `"abc"` or `"-1Gi"`
- **THEN** output error `{"field":"spec.resources.memory.limit","type":"invalid","message":"<msg>"}`

---

### Requirement: CPU resource validation and defaults
When `spec.resources.cpu` is absent, it SHALL be omitted from output. When present, `limit` SHALL be required and `request` SHALL default to `limit`. CPU quantities SHALL be a non-negative integer optionally suffixed with `m`. `request` SHALL NOT exceed `limit`.

#### Scenario: Absent CPU omitted from output
- **WHEN** `spec.resources.cpu` is not specified
- **THEN** `spec.resources.cpu` is absent from the output JSON

#### Scenario: CPU limit required when cpu object present
- **WHEN** `spec.resources.cpu` is present but `limit` is absent
- **THEN** output error `{"field":"spec.resources.cpu.limit","type":"required","message":"<msg>"}`

#### Scenario: CPU request defaults to limit
- **WHEN** `spec.resources.cpu.limit` is `"500m"` and `request` is absent
- **THEN** output has `spec.resources.cpu.request = "500m"`

#### Scenario: CPU request exceeds limit rejected
- **WHEN** `spec.resources.cpu.request` parses to a value greater than `limit`
- **THEN** output error `{"field":"spec.resources.cpu.request","type":"invalid","message":"<msg>"}`

#### Scenario: Invalid CPU quantity
- **WHEN** `spec.resources.cpu.limit` is `"1.5"` or `"abc"`
- **THEN** output error `{"field":"spec.resources.cpu.limit","type":"invalid","message":"<msg>"}`

---

### Requirement: Authentication default
`spec.access.authentication.enabled` SHALL default to `true` when absent. When authentication is enabled (the default), `spec.access.authentication.digestAlgorithm` SHALL default to `"SHA-256"`. When authentication is disabled, the `authentication` object in output SHALL contain only `"enabled": false` — `digestAlgorithm` SHALL be absent from output. `spec.access.credentialRef`, when provided, SHALL be stored and output as given; it has no default.

#### Scenario: Authentication defaults to true
- **WHEN** `spec.access.authentication.enabled` is not specified
- **THEN** output has `spec.access.authentication.enabled = true`

#### Scenario: Explicit false accepted
- **WHEN** `spec.access.authentication.enabled` is `false`
- **THEN** output has `spec.access.authentication.enabled = false`

#### Scenario: digestAlgorithm defaults to SHA-256 when auth enabled
- **WHEN** `spec.access.authentication.enabled` is `true` (or absent) and `digestAlgorithm` is not specified
- **THEN** output has `spec.access.authentication.digestAlgorithm = "SHA-256"`

#### Scenario: digestAlgorithm absent from output when auth disabled
- **WHEN** `spec.access.authentication.enabled` is `false`
- **THEN** `spec.access.authentication.digestAlgorithm` is absent from output

#### Scenario: credentialRef stored as given
- **WHEN** `spec.access.credentialRef` is provided
- **THEN** output has `spec.access.credentialRef` equal to the provided value

---

### Requirement: Migration strategy validation and default
`spec.migration.strategy` SHALL default to `"FullStop"`. It SHALL only accept the value `"FullStop"`; any other value SHALL produce an invalid error.

#### Scenario: Migration strategy defaults to FullStop
- **WHEN** `spec.migration.strategy` is not specified
- **THEN** output has `spec.migration.strategy = "FullStop"`

#### Scenario: Invalid migration strategy rejected
- **WHEN** `spec.migration.strategy` is `"RollingUpdate"`
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"<msg>"}`

---

### Requirement: Forbidden autoScaling field
Any field named `autoScaling` anywhere under `spec` SHALL be rejected.

#### Scenario: autoScaling at spec root
- **WHEN** the input has `spec.autoScaling: ...`
- **THEN** output error `{"field":"spec.autoScaling","type":"forbidden","message":"<msg>"}`

#### Scenario: autoScaling nested under spec
- **WHEN** the input has `spec.resources.autoScaling: ...`
- **THEN** output error `{"field":"spec.resources.autoScaling","type":"forbidden","message":"<msg>"}`

---

### Requirement: Error output format
All validation and operational errors SHALL be printed as `{"errors":[...]}` to stdout with nothing to stderr. Each error object SHALL have `field` (dot-path string), `message` (human-readable string), and `type` (one of: `required`, `invalid`, `forbidden`, `duplicate`, `not_found`, `parse`, `immutable`). When multiple errors are present, the array SHALL be sorted by `field` ascending, with ties broken by `type` ascending.

#### Scenario: Single error
- **WHEN** one validation rule fails
- **THEN** output `{"errors":[{"field":"<path>","type":"<type>","message":"<msg>"}]}`

#### Scenario: Multiple errors sorted by field then type
- **WHEN** multiple validation rules fail simultaneously
- **THEN** output `{"errors":[...]}` containing all violations, sorted by `field` ascending then `type` ascending

---

### Requirement: Success output — create and describe
**Updated:** The full resource JSON for create and describe SHALL include `status.connectionDetails` when `spec.exposure` is configured, and `status.managementConnectionDetails` when `spec.management.enabled` is `true`. Both fields are absent when not applicable.

(adapts mesh-management/success-output-create-and-describe)

#### Scenario: Create with exposure includes connectionDetails
- **WHEN** a mesh is created with a valid `spec.exposure` block
- **THEN** the response JSON includes `status.connectionDetails`

#### Scenario: Create without exposure omits connectionDetails
- **WHEN** a mesh is created without `spec.exposure`
- **THEN** `status.connectionDetails` is absent from the response

### Requirement: Success output — delete
Successful `delete` SHALL print `{"message":"<non-empty>","metadata":{"name":"<string>"}}`. The exact message wording is not part of the contract.

#### Scenario: Delete confirmation printed
- **WHEN** delete succeeds
- **THEN** output contains a non-empty `message` and `metadata.name` matching the deleted resource

### Requirement: Mesh update
The system SHALL read a YAML document from the file path given by `-f`, merge its fields into the stored mesh using field-level merge rules, validate all constraints, and — if valid — persist the updated resource and print the full resource JSON to stdout.

#### Scenario: Valid update persists and prints
- **WHEN** a valid YAML file is provided whose `metadata.name` matches a stored mesh
- **THEN** the merged resource is persisted and the full resource JSON is printed

#### Scenario: Missing mesh rejected
- **WHEN** `update` is called with a name that does not exist in the store
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}` and do not persist

#### Scenario: Validation error rolls back entire update
- **WHEN** the update YAML produces any validation error after merging
- **THEN** output all errors and persist nothing

---

### Requirement: Field-level merge semantics
The system SHALL merge update fields into the stored resource using leaf-level replacement, leaving omitted fields unchanged.

#### Scenario: Provided leaf replaces stored leaf
- **WHEN** the update YAML includes a field that exists in the stored mesh
- **THEN** the stored value is replaced with the provided value

#### Scenario: Omitted field is kept
- **WHEN** the update YAML omits a field
- **THEN** the stored value for that field is unchanged

#### Scenario: Nested objects merged field by field
- **WHEN** the update YAML provides a partial nested object (e.g., only `spec.resources.memory.limit`)
- **THEN** sibling fields not mentioned retain their stored values

#### Scenario: Create-time defaults not re-applied on update
- **WHEN** an omitted field has a create-time default and that field is already stored
- **THEN** the stored value is kept unchanged, not replaced by the default

#### Scenario: Setting storage className does not affect storage size
- **WHEN** the update YAML sets `spec.network.storage.className`
- **THEN** `spec.network.storage.size` and `spec.network.replicationFactor` retain their stored values

---

### Requirement: Status conditions
The system SHALL maintain a `status.conditions` array on each mesh. Each element SHALL have `type` (string), `status` (string, `"True"` or `"False"`), and `message` (string, empty when unused). The array SHALL be sorted by `type` ascending and each `type` SHALL appear at most once.

#### Scenario: New mesh has Healthy and PrechecksPassed conditions
- **WHEN** a mesh is created
- **THEN** `status.conditions` contains exactly `[{"type":"Healthy","status":"True","message":""},{"type":"PrechecksPassed","status":"True","message":""}]`

#### Scenario: Conditions sorted by type
- **WHEN** conditions are set in any order
- **THEN** `status.conditions` is returned sorted by `type` ascending

#### Scenario: Condition type appears at most once
- **WHEN** a condition of a given type is set
- **THEN** no duplicate type exists in the array

#### Scenario: Clearing a condition removes it
- **WHEN** a condition is cleared
- **THEN** that `type` is absent from `status.conditions`

---

### Requirement: Scale up lifecycle
The system SHALL detect when `spec.instances` increases in an update and reflect the transition in the response and on the next describe.

#### Scenario: Scale up update response
- **WHEN** `spec.instances` increases from N to M (M > N > 0) in an update
- **THEN** the update response has `status.instances.ready = N`, `status.instances.starting = M - N`, and `status.conditions` includes `{"type":"Scaling","status":"True","message":"<non-empty>"}`

#### Scenario: Scale up stabilizes on next describe
- **WHEN** a describe is performed after a scale-up update
- **THEN** `status.instances.ready = M`, `status.instances.starting = 0`, and `Scaling` is absent from `status.conditions`

---

### Requirement: Scale down lifecycle
The system SHALL detect when `spec.instances` decreases (but stays above 0) in an update and reflect the transition.

#### Scenario: Scale down update response
- **WHEN** `spec.instances` decreases from N to M (0 < M < N) in an update
- **THEN** `status.conditions` includes `{"type":"Scaling","status":"True","message":"<any>"}` in the update response

#### Scenario: Scale down stabilizes on next describe
- **WHEN** a describe is performed after a scale-down update
- **THEN** `Scaling` is absent from `status.conditions`

---

### Requirement: Stop lifecycle
The system SHALL treat a stop as occurring when `spec.instances` changes from a positive value to `0`.

#### Scenario: Stop update response
- **WHEN** `spec.instances` changes from N (N > 0) to `0` in an update
- **THEN** `status.instances = {"ready":0,"starting":0,"stopped":N}`, `status.state = "Stopped"`, `status.desiredInstancesOnResume = N`, and `status.conditions` includes `{"type":"GracefulShutdown","status":"True","message":""}`

#### Scenario: GracefulShutdown persists through describes
- **WHEN** a describe is performed on a stopped mesh
- **THEN** `GracefulShutdown` remains in `status.conditions` and `status.desiredInstancesOnResume` is present

---

### Requirement: Resume lifecycle
The system SHALL treat a resume as occurring when a stopped mesh (with `GracefulShutdown` present) sets `spec.instances` to a positive value or omits it.

#### Scenario: Resume with explicit instance count
- **WHEN** a stopped mesh is updated with a positive `spec.instances`
- **THEN** `GracefulShutdown` is removed, `status.desiredInstancesOnResume` is removed, `status.instances = {"ready":0,"starting":spec.instances,"stopped":0}`, and `status.state = "Running"`

#### Scenario: Resume with omitted instances uses stored desiredInstancesOnResume
- **WHEN** a stopped mesh is updated and `spec.instances` is omitted or null
- **THEN** the target count is taken from `status.desiredInstancesOnResume` and `status.instances.starting` equals that count

#### Scenario: Resume stabilizes on next describe
- **WHEN** a describe is performed after a resume update
- **THEN** `status.instances.ready` equals the target count and `status.instances.starting = 0`

---

### Requirement: Network storage field
The mesh spec SHALL support `spec.network.storage` with sub-fields `size` (string, memory quantity format), `ephemeral` (boolean, default `false`), and `className` (string, optional). `size` SHALL default to `"1Gi"` on create when omitted.

#### Scenario: Storage defaults on create
- **WHEN** `spec.network.storage` is absent on create
- **THEN** `spec.network.storage.size = "1Gi"` and `spec.network.storage.ephemeral = false`

#### Scenario: Valid storage accepted
- **WHEN** `spec.network.storage.size` is a valid memory quantity
- **THEN** the value is accepted and persisted

#### Scenario: Invalid storage size rejected
- **WHEN** `spec.network.storage.size` is not a valid memory quantity (e.g., `"abc"` or `"-1Gi"`)
- **THEN** output error `{"field":"spec.network.storage.size","type":"invalid","message":"<msg>"}`

#### Scenario: Storage size immutable
- **WHEN** an update provides a `spec.network.storage.size` that differs from the stored value
- **THEN** output error `{"field":"spec.network.storage.size","type":"immutable","message":"field 'spec.network.storage.size' is immutable after creation"}`

#### Scenario: Storage size immutable even when ephemeral is true
- **WHEN** an update provides a different `spec.network.storage.size` and `ephemeral` is `true`
- **THEN** output the same immutable error

---

### Requirement: Network storage output format
The system SHALL conditionally include `spec.network.storage` fields in output based on the `ephemeral` flag.

#### Scenario: Non-ephemeral storage output
- **WHEN** `spec.network.storage.ephemeral` is `false`
- **THEN** output includes both `ephemeral` and `size` fields

#### Scenario: Ephemeral storage output
- **WHEN** `spec.network.storage.ephemeral` is `true`
- **THEN** output includes only `ephemeral` (omit `size`)

---

### Requirement: Replication factor
`spec.network.replicationFactor` SHALL be a positive integer. It SHALL have a computed default equal to `spec.instances` (capped at 3, minimum 1) when omitted on create. It SHALL be at least `1` and SHALL NOT exceed `spec.instances`.

#### Scenario: Replication factor defaults to instance count (capped at 3)
- **WHEN** `spec.network.replicationFactor` is absent on create and `spec.instances = 2`
- **THEN** `spec.network.replicationFactor = 2`

#### Scenario: Replication factor defaults to 3 when instances exceed 3
- **WHEN** `spec.network.replicationFactor` is absent on create and `spec.instances = 5`
- **THEN** `spec.network.replicationFactor = 3`

#### Scenario: Replication factor below 1 rejected
- **WHEN** `spec.network.replicationFactor` is `0` or negative
- **THEN** output error `{"field":"spec.network.replicationFactor","type":"invalid","message":"<msg>"}`

#### Scenario: Replication factor exceeds instance count rejected
- **WHEN** `spec.network.replicationFactor` exceeds `spec.instances` after merge
- **THEN** output error `{"field":"spec.network.replicationFactor","type":"invalid","message":"<msg> (got <rf>, max <instances>)"}`

---

### Requirement: Enriched status model
The system SHALL include additional status fields on create, update, and describe responses.

#### Scenario: status.stable on steady state
- **WHEN** no transient conditions (e.g., `Scaling`) are active
- **THEN** `status.stable = true`

#### Scenario: status.stable during transition
- **WHEN** a transient condition is active
- **THEN** `status.stable = false`

#### Scenario: status.instances on create
- **WHEN** a mesh is created with `spec.instances > 0`
- **THEN** `status.instances = {"ready":spec.instances,"starting":0,"stopped":0}`

#### Scenario: status.desiredInstancesOnResume absent when running
- **WHEN** the mesh is in `Running` state
- **THEN** `status.desiredInstancesOnResume` is absent from the output

---

### Requirement: Immutable field error type
The system SHALL reject any update that attempts to change a field marked immutable after creation, using the `immutable` error type.

#### Scenario: Immutable field change produces correct error shape
- **WHEN** an update changes an immutable field
- **THEN** output `{"errors":[{"field":"<path>","type":"immutable","message":"field '<path>' is immutable after creation"}]}`

---

### Requirement: Post-merge constraint error messages
The system SHALL produce `invalid` errors with messages that name the actual value and the relevant limit when post-merge constraints fail.

#### Scenario: Replication factor constraint message includes values
- **WHEN** `spec.network.replicationFactor` exceeds `spec.instances` after merge
- **THEN** the error message names the actual replication factor value and the instance count limit

### Requirement: Authentication digest algorithm validation
`spec.access.authentication.digestAlgorithm`, when present, SHALL be one of `"SHA-256"`, `"SHA-384"`, or `"SHA-512"`. Any other value SHALL produce an `invalid` error.

#### Scenario: Valid digestAlgorithm accepted
- **WHEN** `spec.access.authentication.digestAlgorithm` is `"SHA-256"`, `"SHA-384"`, or `"SHA-512"`
- **THEN** the value is accepted and stored

#### Scenario: Invalid digestAlgorithm rejected
- **WHEN** `spec.access.authentication.digestAlgorithm` is any other value (e.g., `"MD5"`)
- **THEN** output error `{"field":"spec.access.authentication.digestAlgorithm","type":"invalid","message":"<msg>"}`

---

### Requirement: Authentication forbidden fields when disabled
When `spec.access.authentication.enabled` is `false`, the fields `digestAlgorithm` and `credentialRef` SHALL be absent. If either is present, the system SHALL produce a `forbidden` error for each.

#### Scenario: digestAlgorithm forbidden when auth disabled
- **WHEN** `spec.access.authentication.enabled` is `false` and `spec.access.authentication.digestAlgorithm` is present
- **THEN** output error `{"field":"spec.access.authentication.digestAlgorithm","type":"forbidden","message":"<msg>"}`

#### Scenario: credentialRef forbidden when auth disabled
- **WHEN** `spec.access.authentication.enabled` is `false` and `spec.access.credentialRef` is present
- **THEN** output error `{"field":"spec.access.credentialRef","type":"forbidden","message":"<msg>"}`

---

### Requirement: Permissions
The mesh spec SHALL support `spec.access.permissions.enabled` (boolean, default `false`). When `permissions.enabled` is `true`, `spec.access.permissions.roles` SHALL be required and SHALL contain at least one entry. Each role SHALL have a non-empty `name` (string) and a non-empty `permissions` array of strings. Role names SHALL be unique within the list. When `permissions.enabled` is `false`, `roles` SHALL be omitted from output.

#### Scenario: Permissions disabled by default
- **WHEN** `spec.access.permissions.enabled` is not specified
- **THEN** output has `spec.access.permissions.enabled = false` and `roles` is absent from output

#### Scenario: Roles required when permissions enabled
- **WHEN** `spec.access.permissions.enabled` is `true` and `spec.access.permissions.roles` is absent or empty
- **THEN** output error `{"field":"spec.access.permissions.roles","type":"required","message":"<msg>"}`

#### Scenario: Role missing name rejected
- **WHEN** a role entry has an absent or empty `name`
- **THEN** output error `{"field":"spec.access.permissions.roles[<index>].name","type":"required","message":"<msg>"}`

#### Scenario: Role missing permissions rejected
- **WHEN** a role entry has an absent or empty `permissions` array
- **THEN** output error `{"field":"spec.access.permissions.roles[<index>].permissions","type":"required","message":"<msg>"}`

#### Scenario: Duplicate role names rejected
- **WHEN** two or more roles have the same `name`
- **THEN** output error `{"field":"spec.access.permissions.roles","type":"duplicate","message":"<msg>"}`

#### Scenario: Valid permissions accepted
- **WHEN** `spec.access.permissions.enabled` is `true` and at least one valid role is provided
- **THEN** the permissions section is accepted and output includes `spec.access.permissions.roles`

---

### Requirement: Encryption
The mesh spec SHALL support `spec.access.encryption` with `source` (string, default `"None"`), `certRef` (string, optional), `certServiceRef` (string, optional), and `clientMode` (string, default `"None"`). The `source` field determines which certificate reference fields are required or forbidden. When `source` is `"None"`, `clientMode` SHALL be `"None"`.

Valid values for `source` are `"None"`, `"Secret"`, and `"Service"`. Valid values for `clientMode` are implementation-defined but SHALL produce an `invalid` error for unrecognized values.

| source value | certRef | certServiceRef |
|---|---|---|
| `"None"` | forbidden | forbidden |
| `"Secret"` | required | forbidden |
| `"Service"` | forbidden | required |

#### Scenario: Encryption defaults applied when absent
- **WHEN** `spec.access.encryption` is not specified
- **THEN** output has `spec.access.encryption.source = "None"` and `spec.access.encryption.clientMode = "None"`

#### Scenario: Invalid source rejected
- **WHEN** `spec.access.encryption.source` is not one of the valid values
- **THEN** output error `{"field":"spec.access.encryption.source","type":"invalid","message":"<msg>"}`

#### Scenario: Invalid clientMode rejected
- **WHEN** `spec.access.encryption.clientMode` is not one of the valid values
- **THEN** output error `{"field":"spec.access.encryption.clientMode","type":"invalid","message":"<msg>"}`

#### Scenario: certRef required when source is Secret
- **WHEN** `spec.access.encryption.source` is `"Secret"` and `certRef` is absent
- **THEN** output error `{"field":"spec.access.encryption.certRef","type":"required","message":"<msg>"}`

#### Scenario: certServiceRef required when source is Service
- **WHEN** `spec.access.encryption.source` is `"Service"` and `certServiceRef` is absent
- **THEN** output error `{"field":"spec.access.encryption.certServiceRef","type":"required","message":"<msg>"}`

#### Scenario: certRef forbidden when source is not Secret
- **WHEN** `spec.access.encryption.source` is `"None"` or `"Service"` and `certRef` is present
- **THEN** output error `{"field":"spec.access.encryption.certRef","type":"forbidden","message":"<msg>"}`

#### Scenario: certServiceRef forbidden when source is not Service
- **WHEN** `spec.access.encryption.source` is `"None"` or `"Secret"` and `certServiceRef` is present
- **THEN** output error `{"field":"spec.access.encryption.certServiceRef","type":"forbidden","message":"<msg>"}`

#### Scenario: clientMode None required when source is None
- **WHEN** `spec.access.encryption.source` is `"None"` and `clientMode` is `"Authenticate"` or `"Validate"`
- **THEN** the system SHALL produce an error for `spec.access.encryption.clientMode`

---

### Requirement: Access section defaults when omitted
When `spec.access` is entirely absent from the input, the system SHALL output the full `spec.access` section with all applicable sub-section defaults applied.

#### Scenario: Full access defaults when spec.access omitted
- **WHEN** `spec.access` is not present in the input
- **THEN** output includes `spec.access.authentication.enabled = true`, `spec.access.authentication.digestAlgorithm = "SHA-256"`, `spec.access.permissions.enabled = false`, `spec.access.encryption.source = "None"`, and `spec.access.encryption.clientMode = "None"`

#### Scenario: roles absent when permissions disabled by default
- **WHEN** `spec.access.permissions.enabled` is `false` (or defaulted to false)
- **THEN** `spec.access.permissions.roles` is absent from output

