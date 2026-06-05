## ADDED Requirements

### Requirement: Recovery CRUD surface
The system SHALL support `meshctl recovery create -f <path>`, `meshctl recovery list`, `meshctl recovery describe <name>`, `meshctl recovery update -f <path>`, and `meshctl recovery delete <name>` with the same output shapes and error conventions as mesh resources.

#### Scenario: List returns JSON array sorted by name
- **WHEN** one or more recoveries exist
- **THEN** output a JSON array of recovery summaries sorted by `metadata.name` ascending

#### Scenario: List empty store
- **WHEN** no recoveries exist
- **THEN** output `[]`

#### Scenario: Describe existing recovery
- **WHEN** the named recovery exists
- **THEN** output the full resource JSON

#### Scenario: Describe unknown recovery
- **WHEN** the named recovery does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

#### Scenario: Delete existing recovery
- **WHEN** the named recovery exists
- **THEN** remove it and output `{"message":"<non-empty>","metadata":{"name":"<string>"}}`

#### Scenario: Delete unknown recovery
- **WHEN** the named recovery does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Recovery create — meshRef validation
The system SHALL reject a create request when `spec.meshRef` is absent or does not reference an existing mesh.

#### Scenario: Missing meshRef
- **WHEN** `spec.meshRef` is absent or empty
- **THEN** output `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"<msg>"}]}`

#### Scenario: Non-existent meshRef
- **WHEN** `spec.meshRef` names a mesh that does not exist
- **THEN** output `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"<msg>"}]}`

---

### Requirement: Recovery create — snapshotRef validation
The system SHALL require `spec.snapshotRef` to reference an existing snapshot. The snapshot's `spec.meshRef` SHALL match the recovery's `spec.meshRef`.

#### Scenario: Missing snapshotRef
- **WHEN** `spec.snapshotRef` is absent or empty
- **THEN** output `{"errors":[{"field":"spec.snapshotRef","type":"invalid","message":"<msg>"}]}`

#### Scenario: Non-existent snapshotRef
- **WHEN** `spec.snapshotRef` names a snapshot that does not exist
- **THEN** output `{"errors":[{"field":"spec.snapshotRef","type":"invalid","message":"<msg>"}]}`

#### Scenario: Snapshot meshRef mismatch
- **WHEN** the named snapshot exists but its `spec.meshRef` does not match the recovery's `spec.meshRef`
- **THEN** output `{"errors":[{"field":"spec.snapshotRef","type":"invalid","message":"snapshot '<name>' belongs to mesh '<X>', not '<Y>'"}]}`

---

### Requirement: Recovery create — resource quantity validation
The system SHALL validate `spec.resources.memory` and `spec.resources.cpu` using the same quantity formats as mesh resource quantities. `spec.resources.memory` SHALL default to `{"limit":"1Gi","request":"1Gi"}` when omitted.

#### Scenario: Default memory applied when omitted
- **WHEN** `spec.resources.memory` is absent in the create YAML
- **THEN** the resource is persisted with `spec.resources.memory = {"limit":"1Gi","request":"1Gi"}`

#### Scenario: Invalid memory quantity rejected
- **WHEN** `spec.resources.memory.limit` or `spec.resources.memory.request` is not a valid memory quantity
- **THEN** output an error with `type: "invalid"` for the offending field

---

### Requirement: Recovery create — scope
The system SHALL accept an optional `spec.scope` object with the same shape as snapshot scope. When omitted, the recovery restores all snapshot data. When present, it restores only the named items.

#### Scenario: Scope omitted restores all
- **WHEN** `spec.scope` is absent
- **THEN** the recovery is created and will restore all snapshot data on run

#### Scenario: Scope present restores named items only
- **WHEN** `spec.scope` names specific items
- **THEN** only those items are restored on run

---

### Requirement: Recovery create — initial state
The system SHALL set `status.state = "Initializing"` on successful create.

#### Scenario: Create success sets Initializing
- **WHEN** a valid recovery YAML is provided and persisted
- **THEN** the response includes `status.state = "Initializing"`

---

### Requirement: Recovery run — state gate
The system SHALL only permit `meshctl recovery run <name>` from `status.state = "Initializing"`. Attempts from any other state SHALL be rejected.

#### Scenario: Run from non-Initializing state
- **WHEN** `meshctl recovery run <name>` is called and the recovery is not in `"Initializing"` state
- **THEN** output `{"errors":[{"field":"status.state","type":"invalid","message":"resource is in state '<current>', expected 'Initializing'"}]}`

#### Scenario: Run unknown recovery
- **WHEN** `meshctl recovery run <name>` is called with a name that does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Recovery run — mesh stability gate
The system SHALL check whether the referenced mesh has `status.stable = false` at run time. An unstable mesh causes the recovery to enter `"Unknown"` state.

#### Scenario: Mesh not stable at run time
- **WHEN** `meshctl recovery run <name>` is called and the referenced mesh has `status.stable = false`
- **THEN** `status.state = "Unknown"` and `status.detail` is a non-empty string

#### Scenario: Stable mesh allows recovery to succeed
- **WHEN** the referenced mesh has `status.stable = true` at run time
- **THEN** the recovery transitions to `"Succeeded"`

---

### Requirement: Recovery run — state transition
The system SHALL transition through `"Running"` before settling at `"Succeeded"`, `"Failed"`, or `"Unknown"`.

#### Scenario: Terminal state after run
- **WHEN** `meshctl recovery run <name>` completes
- **THEN** `status.state` is one of `"Succeeded"`, `"Failed"`, or `"Unknown"`

---

### Requirement: Recovery spec immutability
The system SHALL reject any `update` that changes, adds, or removes any field in the `spec` section after creation.

#### Scenario: Spec field change rejected
- **WHEN** an update YAML changes any spec field
- **THEN** output errors with `type: "immutable"` and do not persist

#### Scenario: New spec field addition rejected
- **WHEN** an update YAML adds a spec field that was not present at creation
- **THEN** output errors with `type: "immutable"` and do not persist

---

### Requirement: Recovery output shape
The system SHALL include `status.state` in all recovery responses and `status.detail` only in `"Failed"` or `"Unknown"` states.

#### Scenario: Succeeded recovery output
- **WHEN** a recovery is in `"Succeeded"` state
- **THEN** output includes `status.state = "Succeeded"` and no `status.detail`

#### Scenario: Failed or Unknown recovery output
- **WHEN** a recovery is in `"Failed"` or `"Unknown"` state
- **THEN** output includes a non-empty `status.detail`
