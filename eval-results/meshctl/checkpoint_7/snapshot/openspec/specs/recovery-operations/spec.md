# recovery-operations Specification

## Purpose
TBD - created by archiving change task-snapshot-recovery-operations. Update Purpose after archive.
## Requirements
### Requirement: Recovery CLI Entry Point

The tool SHALL be invokable as `meshctl recovery <operation> [arguments]` and SHALL route to the correct recovery operation handler.

#### Scenario: Routing recovery run
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the system executes the named recovery resource

---

### Requirement: Recovery Create

The system SHALL read a YAML document from the file path given by `-f`, validate all fields, apply resource defaults, and — if valid — persist the recovery resource with `status.state = "Initializing"` and print the full resource as JSON to stdout.

#### Scenario: Successful recovery creation
- **GIVEN** a YAML file with a valid `metadata.name`, an existing `spec.meshRef`, and a `spec.snapshotRef` pointing to a snapshot whose `spec.meshRef` matches
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system persists the recovery with `status.state = "Initializing"`

#### Scenario: Missing mesh reference
- **GIVEN** a YAML file where `spec.meshRef` is absent or references a non-existent mesh
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system returns an error with `field = "spec.meshRef"` and `type = "invalid"`

#### Scenario: Missing snapshot reference
- **GIVEN** a YAML file where `spec.snapshotRef` references a non-existent snapshot
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system returns an error with `field = "spec.snapshotRef"` and `type = "invalid"`

#### Scenario: Snapshot belongs to different mesh
- **GIVEN** a YAML file where `spec.meshRef = "mesh-a"` and `spec.snapshotRef` points to a snapshot whose `spec.meshRef = "mesh-b"`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system returns an error with `field = "spec.snapshotRef"`, `type = "invalid"`, and `message = "snapshot '<name>' belongs to mesh 'mesh-b', not 'mesh-a'"`

#### Scenario: Memory default applied
- **GIVEN** a YAML file with no `spec.resources.memory`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the persisted resource has `spec.resources.memory = {"limit": "1Gi", "request": "1Gi"}`

#### Scenario: Scope omitted restores all data
- **GIVEN** a YAML file with no `spec.scope`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the recovery will restore all snapshot data when run

---

### Requirement: Recovery List

The system SHALL print a JSON array of all recovery resources sorted by `name` ascending lexicographically. (adapts `vault-management/vault-list`)

#### Scenario: List with multiple recoveries
- **GIVEN** recoveries named `rec-b` and `rec-a` exist
- **WHEN** the user runs `meshctl recovery list`
- **THEN** the system prints them sorted as `rec-a`, `rec-b`

---

### Requirement: Recovery Describe

The system SHALL print the full resource JSON for the recovery identified by `<name>`. (adapts `vault-management/vault-describe`)

#### Scenario: Describe existing recovery
- **GIVEN** a recovery named `rec-1` exists
- **WHEN** the user runs `meshctl recovery describe rec-1`
- **THEN** the system prints the full recovery resource JSON

#### Scenario: Describe non-existent recovery
- **GIVEN** no recovery named `missing` exists
- **WHEN** the user runs `meshctl recovery describe missing`
- **THEN** the system returns a not-found error with `field = "metadata.name"` and `type = "not_found"`

---

### Requirement: Recovery Spec Immutability

The entire `spec` section of a recovery is immutable after creation. Any update that changes a spec field or adds a previously-omitted field SHALL be rejected.

#### Scenario: Attempt to change snapshotRef after creation
- **GIVEN** a recovery with `spec.snapshotRef = "snap-1"`
- **WHEN** the user runs `meshctl recovery update -f <path>` with `spec.snapshotRef = "snap-2"`
- **THEN** the system returns an error with `type = "immutable"`

---

### Requirement: Recovery Delete

The system SHALL remove the named recovery from the store and print a confirmation JSON object. (adapts `vault-management/vault-delete`)

#### Scenario: Delete existing recovery
- **GIVEN** a recovery named `rec-1` exists
- **WHEN** the user runs `meshctl recovery delete rec-1`
- **THEN** the system removes the recovery and prints confirmation JSON

---

### Requirement: Recovery Run

The system SHALL execute the recovery identified by `<name>` only when `status.state = "Initializing"`. On any other state the run SHALL be rejected. During execution the state transitions through `"Running"` to a terminal state.

#### Scenario: Run from Initializing — mesh is stable
- **GIVEN** a recovery with `status.state = "Initializing"` and the referenced mesh has `status.stable = true`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the state transitions `Initializing → Running → Succeeded`

#### Scenario: Run from Initializing — mesh is not stable
- **GIVEN** a recovery with `status.state = "Initializing"` and the referenced mesh has `status.stable = false`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** `status.state = "Unknown"` and `status.detail` is a non-empty string

#### Scenario: Run from non-Initializing state
- **GIVEN** a recovery with `status.state = "Failed"`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the system returns an error with `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state 'Failed', expected 'Initializing'"`

---

### Requirement: Recovery Output Fields

`status` SHALL include `state` always and `detail` only in `"Failed"` or `"Unknown"` states. `storageRef` is not present on recovery resources.

#### Scenario: Failed recovery has detail
- **GIVEN** a recovery in `"Failed"` state
- **WHEN** the user runs `meshctl recovery describe <name>`
- **THEN** `status.detail` is present and non-empty

#### Scenario: Succeeded recovery has no detail
- **GIVEN** a recovery in `"Succeeded"` state
- **WHEN** the user runs `meshctl recovery describe <name>`
- **THEN** `status.detail` is absent

---

### Requirement: Recovery Error Output Format

All recovery validation and operational errors SHALL use the JSON error shape: `{"errors":[{"field":"<path>","type":"<type>","message":"<msg>"}]}` printed to stdout. (adapts `vault-management/vault-error-output-format`)

#### Scenario: Snapshot ownership mismatch error format
- **GIVEN** a recovery create where the snapshot's meshRef does not match
- **WHEN** the error is returned
- **THEN** it is printed as `{"errors":[{"field":"spec.snapshotRef","type":"invalid","message":"snapshot '...' belongs to mesh '...', not '...'"}]}`

