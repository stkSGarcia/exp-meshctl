## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Success output — create and describe
The system SHALL print the full resource JSON with `metadata`, `spec` (all defaulted fields including network topology), and a `status` block containing `state`, `stable`, `instances`, `conditions`, and (when stopped) `desiredInstancesOnResume`.

#### Scenario: Create success output includes full status
- **WHEN** create succeeds with `spec.instances > 0`
- **THEN** output includes `status.state = "Running"`, `status.stable = true`, `status.instances = {"ready":spec.instances,"starting":0,"stopped":0}`, and `status.conditions` with `Healthy` and `PrechecksPassed`

#### Scenario: New mesh starts as Running
- **WHEN** a mesh is first created with positive instances
- **THEN** `status.state = "Running"`
