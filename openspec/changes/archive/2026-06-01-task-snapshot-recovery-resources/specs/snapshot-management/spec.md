## ADDED Requirements

> Extends: `mesh-management`

### Requirement: snapshot-cli-surface

The system SHALL support `meshctl snapshot create -f <path>`, `meshctl snapshot list`, `meshctl snapshot describe <name>`, `meshctl snapshot update -f <path>`, `meshctl snapshot delete <name>`, and `meshctl snapshot run <name>` commands. (adapts `mesh-management/cli-entry-point`)

#### Scenario: snapshot create command is routed

- **WHEN** the user runs `meshctl snapshot create -f snapshot.yaml`
- **THEN** the system reads the YAML, validates it, and persists the snapshot resource

#### Scenario: snapshot list command returns sorted array

- **WHEN** the user runs `meshctl snapshot list`
- **THEN** the system prints a JSON array of all snapshots sorted by `name` ascending

#### Scenario: snapshot describe returns full resource

- **WHEN** the user runs `meshctl snapshot describe <name>`
- **THEN** the system prints the full snapshot resource as JSON

---

### Requirement: snapshot-yaml-input-schema

The system SHALL accept a YAML document with top-level keys `metadata` and `spec`. `metadata.name` SHALL follow the same validation rules as mesh name. (adapts `mesh-management/yaml-input-schema`, `mesh-management/name-validation`)

#### Scenario: valid snapshot YAML is accepted

- **GIVEN** a YAML file with valid `metadata.name` and `spec.meshRef`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system persists the resource and returns it as JSON

#### Scenario: not-found returns error

- **WHEN** the user runs `meshctl snapshot describe <name>` and no snapshot exists
- **THEN** the system returns an error with `field = "metadata.name"` and `type = "not_found"`

---

### Requirement: snapshot-spec-fields

The snapshot spec SHALL have:
- `spec.meshRef` (string, required): must reference an existing mesh; invalid/missing → `field = "spec.meshRef"`, `type = "invalid"`
- `spec.storage.size` (string, optional): memory quantity format
- `spec.storage.className` (string, optional)
- `spec.scope` (object, optional): keys `stores`, `blueprints`, `tallies`, `definitions`, `procedures`; when omitted, all data is captured
- `spec.resources.memory` (object): defaults to `{"limit": "1Gi", "request": "1Gi"}` when absent (adapts `mesh-management/memory-resource-validation-and-defaults`)
- `spec.resources.cpu` (object, optional): same format as mesh CPU (adapts `mesh-management/cpu-resource-validation-and-defaults`)

#### Scenario: missing meshRef is rejected

- **GIVEN** a snapshot YAML without `spec.meshRef`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system returns `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"..."}]}`

#### Scenario: invalid memory quantity is rejected

- **GIVEN** a snapshot YAML with `spec.resources.memory.limit = "badvalue"`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system returns an error for the invalid memory quantity

#### Scenario: memory defaults when absent

- **GIVEN** a snapshot YAML without `spec.resources.memory`
- **WHEN** the user runs `meshctl snapshot create -f <path>` with a valid input
- **THEN** the stored resource has `spec.resources.memory = {"limit": "1Gi", "request": "1Gi"}`

#### Scenario: scope omitted captures all data

- **GIVEN** a snapshot YAML without `spec.scope`
- **WHEN** `meshctl snapshot run <name>` succeeds
- **THEN** the system captures all data (scope is unrestricted)

---

### Requirement: snapshot-create-initial-state

On successful create, the system SHALL set `status.state = "Initializing"`.

#### Scenario: created snapshot has Initializing state

- **GIVEN** a valid snapshot YAML
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the returned resource has `status.state = "Initializing"`

---

### Requirement: snapshot-spec-immutability

After creation, the entire `spec` section SHALL be immutable. Any update that changes or adds a spec field SHALL be rejected with `type = "immutable"`. (adapts `mesh-management/immutable-field-error-type`)

#### Scenario: updating spec field is rejected

- **GIVEN** an existing snapshot
- **WHEN** the user runs `meshctl snapshot update -f <path>` with a changed spec field
- **THEN** the system returns an error with `type = "immutable"`

---

### Requirement: snapshot-run

`meshctl snapshot run <name>` SHALL execute the snapshot capture operation.

Run is valid only from `"Initializing"`. On any other state:
- `field = "status.state"`
- `type = "invalid"`
- `message = "resource is in state '<current>', expected 'Initializing'"`

The system SHALL transition through `"Running"` to `"Succeeded"`, `"Failed"`, or `"Unknown"`.

If the referenced mesh has `status.stable = false` at run time:
- `status.state = "Unknown"`
- `status.detail` is a non-empty string

Otherwise, the system SHALL succeed and set a stable, non-empty `status.storageRef`.

#### Scenario: run from Initializing with stable mesh succeeds

- **GIVEN** a snapshot in `"Initializing"` state and its referenced mesh has `status.stable = true`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** `status.state = "Succeeded"` and `status.storageRef` is a non-empty string

#### Scenario: run with unstable mesh results in Unknown

- **GIVEN** a snapshot in `"Initializing"` state and its referenced mesh has `status.stable = false`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** `status.state = "Unknown"` and `status.detail` is a non-empty string

#### Scenario: run from non-Initializing state is rejected

- **GIVEN** a snapshot in `"Succeeded"` state
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the system returns an error with `field = "status.state"`, `type = "invalid"`, `message = "resource is in state 'Succeeded', expected 'Initializing'"`

---

### Requirement: snapshot-dependency-protection

The system SHALL reject `meshctl snapshot delete <name>` when one or more recoveries reference that snapshot via `spec.snapshotRef`. The error SHALL use:
- `field = "metadata.name"`
- `type = "conflict"`
- message naming the dependent recovery resources

#### Scenario: delete blocked by dependent recovery

- **GIVEN** a snapshot named `snap-a` and a recovery with `spec.snapshotRef = "snap-a"`
- **WHEN** the user runs `meshctl snapshot delete snap-a`
- **THEN** the system returns `{"errors":[{"field":"metadata.name","type":"conflict","message":"..."}]}` naming the dependent recovery

#### Scenario: delete succeeds with no dependents

- **GIVEN** a snapshot with no referencing recoveries
- **WHEN** the user runs `meshctl snapshot delete <name>`
- **THEN** the system removes the snapshot and prints a confirmation JSON object

---

### Requirement: snapshot-output-format

Snapshot output SHALL use the same JSON and error format as mesh resources. `status` SHALL include `state`. `status.detail` SHALL be present only in `"Failed"` or `"Unknown"` state. `status.storageRef` SHALL be present only on a succeeded snapshot. (adapts `mesh-management/error-output-format`)

#### Scenario: succeeded snapshot includes storageRef

- **GIVEN** a snapshot that ran successfully
- **WHEN** the user runs `meshctl snapshot describe <name>`
- **THEN** the output includes `status.storageRef` with a non-empty string

#### Scenario: non-succeeded snapshot omits storageRef

- **GIVEN** a snapshot in `"Initializing"` state
- **WHEN** the user runs `meshctl snapshot describe <name>`
- **THEN** the output does not include `status.storageRef`
