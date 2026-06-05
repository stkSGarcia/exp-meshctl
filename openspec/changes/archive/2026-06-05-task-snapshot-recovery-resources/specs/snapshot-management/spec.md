## ADDED Requirements

### Requirement: Snapshot CRUD surface
The system SHALL support `meshctl snapshot create -f <path>`, `meshctl snapshot list`, `meshctl snapshot describe <name>`, `meshctl snapshot update -f <path>`, and `meshctl snapshot delete <name>` with the same output shapes and error conventions as mesh resources.

#### Scenario: List returns JSON array sorted by name
- **WHEN** one or more snapshots exist
- **THEN** output a JSON array of snapshot summaries sorted by `metadata.name` ascending

#### Scenario: List empty store
- **WHEN** no snapshots exist
- **THEN** output `[]`

#### Scenario: Describe existing snapshot
- **WHEN** the named snapshot exists
- **THEN** output the full resource JSON

#### Scenario: Describe unknown snapshot
- **WHEN** the named snapshot does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

#### Scenario: Delete existing snapshot with no dependents
- **WHEN** the named snapshot exists and no recovery references it
- **THEN** remove it and output `{"message":"<non-empty>","metadata":{"name":"<string>"}}`

#### Scenario: Delete unknown snapshot
- **WHEN** the named snapshot does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Snapshot create — meshRef validation
The system SHALL reject a create request when `spec.meshRef` is absent or does not reference an existing mesh.

#### Scenario: Missing meshRef
- **WHEN** `spec.meshRef` is absent or empty
- **THEN** output `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"<msg>"}]}`

#### Scenario: Non-existent meshRef
- **WHEN** `spec.meshRef` names a mesh that does not exist
- **THEN** output `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"<msg>"}]}`

---

### Requirement: Snapshot create — resource quantity validation
The system SHALL validate `spec.resources.memory` and `spec.resources.cpu` using the same quantity formats as mesh resource quantities. `spec.resources.memory` SHALL default to `{"limit":"1Gi","request":"1Gi"}` when omitted.

#### Scenario: Default memory applied when omitted
- **WHEN** `spec.resources.memory` is absent in the create YAML
- **THEN** the resource is persisted with `spec.resources.memory = {"limit":"1Gi","request":"1Gi"}`

#### Scenario: Invalid memory quantity rejected
- **WHEN** `spec.resources.memory.limit` or `spec.resources.memory.request` is not a valid memory quantity
- **THEN** output an error with `type: "invalid"` for the offending field

---

### Requirement: Snapshot create — scope
The system SHALL accept an optional `spec.scope` object. When omitted, the snapshot captures all data. When present, it captures only the named items under keys `stores`, `blueprints`, `tallies`, `definitions`, and `procedures`.

#### Scenario: Scope omitted captures all
- **WHEN** `spec.scope` is absent
- **THEN** the snapshot is created and will capture all mesh data on run

#### Scenario: Scope present captures named items only
- **WHEN** `spec.scope` names specific items
- **THEN** only those items are captured on run

---

### Requirement: Snapshot create — initial state
The system SHALL set `status.state = "Initializing"` on successful create.

#### Scenario: Create success sets Initializing
- **WHEN** a valid snapshot YAML is provided and persisted
- **THEN** the response includes `status.state = "Initializing"`

---

### Requirement: Snapshot run — state gate
The system SHALL only permit `meshctl snapshot run <name>` from `status.state = "Initializing"`. Attempts from any other state SHALL be rejected.

#### Scenario: Run from non-Initializing state
- **WHEN** `meshctl snapshot run <name>` is called and the snapshot is not in `"Initializing"` state
- **THEN** output `{"errors":[{"field":"status.state","type":"invalid","message":"resource is in state '<current>', expected 'Initializing'"}]}`

#### Scenario: Run unknown snapshot
- **WHEN** `meshctl snapshot run <name>` is called with a name that does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Snapshot run — mesh stability gate
The system SHALL check whether the referenced mesh has `status.stable = false` at run time. An unstable mesh causes the snapshot to enter `"Unknown"` state.

#### Scenario: Mesh not stable at run time
- **WHEN** `meshctl snapshot run <name>` is called and the referenced mesh has `status.stable = false`
- **THEN** `status.state = "Unknown"` and `status.detail` is a non-empty string

#### Scenario: Stable mesh allows snapshot to succeed
- **WHEN** the referenced mesh has `status.stable = true` at run time
- **THEN** the snapshot transitions to `"Succeeded"` and `status.storageRef` is a stable, non-empty string

---

### Requirement: Snapshot run — state transition
The system SHALL transition through `"Running"` before settling at `"Succeeded"`, `"Failed"`, or `"Unknown"`.

#### Scenario: Terminal state after run
- **WHEN** `meshctl snapshot run <name>` completes
- **THEN** `status.state` is one of `"Succeeded"`, `"Failed"`, or `"Unknown"`

---

### Requirement: Snapshot delete — dependency protection
The system SHALL reject `snapshot delete` when one or more recovery resources reference the snapshot via `spec.snapshotRef`.

#### Scenario: Delete blocked by dependent recovery
- **WHEN** one or more recoveries have `spec.snapshotRef` equal to the snapshot's name
- **THEN** output `{"errors":[{"field":"metadata.name","type":"conflict","message":"<msg>"}]}` naming the dependent recoveries and do not delete

---

### Requirement: Snapshot spec immutability
The system SHALL reject any `update` that changes, adds, or removes any field in the `spec` section after creation.

#### Scenario: Spec field change rejected
- **WHEN** an update YAML changes any spec field
- **THEN** output errors with `type: "immutable"` and do not persist

#### Scenario: New spec field addition rejected
- **WHEN** an update YAML adds a spec field that was not present at creation
- **THEN** output errors with `type: "immutable"` and do not persist

---

### Requirement: Snapshot output shape
The system SHALL include `status.state` in all snapshot responses, `status.detail` only in `"Failed"` or `"Unknown"` states, and `status.storageRef` only in `"Succeeded"` state.

#### Scenario: Succeeded snapshot output
- **WHEN** a snapshot is in `"Succeeded"` state
- **THEN** output includes `status.state = "Succeeded"`, a non-empty `status.storageRef`, and no `status.detail`

#### Scenario: Failed or Unknown snapshot output
- **WHEN** a snapshot is in `"Failed"` or `"Unknown"` state
- **THEN** output includes a non-empty `status.detail` and no `status.storageRef`

#### Scenario: Initializing or Running snapshot output
- **WHEN** a snapshot is in `"Initializing"` or `"Running"` state
- **THEN** output includes only `status.state` with no `status.detail` and no `status.storageRef`
