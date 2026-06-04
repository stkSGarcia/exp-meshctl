## ADDED Requirements

> Extends: `vault-management`

### Requirement: Snapshot CLI Entry Point

The tool SHALL be invokable as `meshctl snapshot <operation> [arguments]` and SHALL route to the correct snapshot operation handler.

#### Scenario: Routing snapshot run
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the system executes the named snapshot resource

---

### Requirement: Snapshot Create

The system SHALL read a YAML document from the file path given by `-f`, validate all fields, apply resource defaults, and — if valid — persist the snapshot resource with `status.state = "Initializing"` and print the full resource as JSON to stdout.

#### Scenario: Successful snapshot creation with no scope
- **GIVEN** a YAML file with a valid `metadata.name`, an existing `spec.meshRef`, and no `spec.scope`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system persists the snapshot with `status.state = "Initializing"` and the scope captures all data

#### Scenario: Successful snapshot creation with scope
- **GIVEN** a YAML file with `spec.scope` containing selected keys
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system captures only the named items in scope

#### Scenario: Missing mesh reference
- **GIVEN** a YAML file where `spec.meshRef` references a non-existent mesh
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system returns an error with `field = "spec.meshRef"` and `type = "invalid"`

#### Scenario: Memory default applied
- **GIVEN** a YAML file with no `spec.resources.memory`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the persisted resource has `spec.resources.memory = {"limit": "1Gi", "request": "1Gi"}`

#### Scenario: Invalid memory quantity format
- **GIVEN** a YAML file with `spec.resources.memory.limit = "not-a-quantity"`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system returns a validation error for the memory field

---

### Requirement: Snapshot List

The system SHALL print a JSON array of all snapshot resources sorted by `name` ascending lexicographically. (adapts `vault-management/vault-list`)

#### Scenario: List with multiple snapshots
- **GIVEN** snapshots named `snap-b` and `snap-a` exist
- **WHEN** the user runs `meshctl snapshot list`
- **THEN** the system prints them sorted as `snap-a`, `snap-b`

---

### Requirement: Snapshot Describe

The system SHALL print the full resource JSON for the snapshot identified by `<name>`. (adapts `vault-management/vault-describe`)

#### Scenario: Describe existing snapshot
- **GIVEN** a snapshot named `snap-1` exists
- **WHEN** the user runs `meshctl snapshot describe snap-1`
- **THEN** the system prints the full snapshot resource JSON

#### Scenario: Describe non-existent snapshot
- **GIVEN** no snapshot named `missing` exists
- **WHEN** the user runs `meshctl snapshot describe missing`
- **THEN** the system returns a not-found error with `field = "metadata.name"` and `type = "not_found"`

---

### Requirement: Snapshot Spec Immutability

The entire `spec` section of a snapshot is immutable after creation. Any update that changes a spec field or adds a previously-omitted field SHALL be rejected.

#### Scenario: Attempt to change meshRef after creation
- **GIVEN** a snapshot with `spec.meshRef = "mesh-a"`
- **WHEN** the user runs `meshctl snapshot update -f <path>` with `spec.meshRef = "mesh-b"`
- **THEN** the system returns an error with `type = "immutable"`

---

### Requirement: Snapshot Delete

The system SHALL remove the named snapshot from the store and print a confirmation JSON object, unless one or more recoveries reference that snapshot.

#### Scenario: Delete unreferenced snapshot
- **GIVEN** a snapshot named `snap-1` exists and no recovery references it
- **WHEN** the user runs `meshctl snapshot delete snap-1`
- **THEN** the system removes the snapshot and prints confirmation JSON

#### Scenario: Delete snapshot referenced by recovery
- **GIVEN** a snapshot named `snap-1` is referenced by recovery `rec-a`
- **WHEN** the user runs `meshctl snapshot delete snap-1`
- **THEN** the system returns an error with `field = "metadata.name"`, `type = "conflict"`, and a message naming `rec-a`

---

### Requirement: Snapshot Run

The system SHALL execute the snapshot identified by `<name>` only when `status.state = "Initializing"`. On any other state the run SHALL be rejected. During execution the state transitions through `"Running"` to a terminal state.

#### Scenario: Run from Initializing — mesh is stable
- **GIVEN** a snapshot with `status.state = "Initializing"` and the referenced mesh has `status.stable = true`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the state transitions `Initializing → Running → Succeeded` and `status.storageRef` is set to a stable, non-empty string

#### Scenario: Run from Initializing — mesh is not stable
- **GIVEN** a snapshot with `status.state = "Initializing"` and the referenced mesh has `status.stable = false`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** `status.state = "Unknown"` and `status.detail` is a non-empty string

#### Scenario: Run from non-Initializing state
- **GIVEN** a snapshot with `status.state = "Succeeded"`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the system returns an error with `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state 'Succeeded', expected 'Initializing'"`

---

### Requirement: Snapshot Output Fields

`status` SHALL include `state` always, `detail` only in `"Failed"` or `"Unknown"` states, and `storageRef` only on a succeeded snapshot.

#### Scenario: Succeeded snapshot has storageRef
- **GIVEN** a snapshot that ran successfully
- **WHEN** the user runs `meshctl snapshot describe <name>`
- **THEN** `status.storageRef` is present and non-empty, and `status.detail` is absent

#### Scenario: Failed snapshot has detail not storageRef
- **GIVEN** a snapshot in `"Failed"` state
- **WHEN** the user runs `meshctl snapshot describe <name>`
- **THEN** `status.detail` is present and `status.storageRef` is absent

---

### Requirement: Snapshot Error Output Format

All snapshot validation and operational errors SHALL use the JSON error shape: `{"errors":[{"field":"<path>","type":"<type>","message":"<msg>"}]}` printed to stdout. (adapts `vault-management/vault-error-output-format`)

#### Scenario: Conflict error format on protected delete
- **GIVEN** a snapshot referenced by a recovery
- **WHEN** delete is attempted
- **THEN** the error is printed as `{"errors":[{"field":"metadata.name","type":"conflict","message":"..."}]}`
