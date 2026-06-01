## ADDED Requirements

> Extends: `mesh-management`

### Requirement: recovery-cli-surface

The system SHALL support `meshctl recovery create -f <path>`, `meshctl recovery list`, `meshctl recovery describe <name>`, `meshctl recovery update -f <path>`, `meshctl recovery delete <name>`, and `meshctl recovery run <name>` commands. (adapts `mesh-management/cli-entry-point`)

#### Scenario: recovery create command is routed

- **WHEN** the user runs `meshctl recovery create -f recovery.yaml`
- **THEN** the system reads the YAML, validates it, and persists the recovery resource

#### Scenario: recovery list command returns sorted array

- **WHEN** the user runs `meshctl recovery list`
- **THEN** the system prints a JSON array of all recoveries sorted by `name` ascending

#### Scenario: recovery describe returns full resource

- **WHEN** the user runs `meshctl recovery describe <name>`
- **THEN** the system prints the full recovery resource as JSON

---

### Requirement: recovery-yaml-input-schema

The system SHALL accept a YAML document with top-level keys `metadata` and `spec`. `metadata.name` SHALL follow the same validation rules as mesh name. (adapts `mesh-management/yaml-input-schema`, `mesh-management/name-validation`)

#### Scenario: valid recovery YAML is accepted

- **GIVEN** a YAML file with valid `metadata.name`, `spec.meshRef`, and `spec.snapshotRef`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system persists the resource and returns it as JSON

#### Scenario: not-found returns error

- **WHEN** the user runs `meshctl recovery describe <name>` and no recovery exists
- **THEN** the system returns an error with `field = "metadata.name"` and `type = "not_found"`

---

### Requirement: recovery-spec-fields

The recovery spec SHALL have:
- `spec.meshRef` (string, required): must reference an existing mesh; invalid/missing → `field = "spec.meshRef"`, `type = "invalid"`
- `spec.snapshotRef` (string, required): must reference an existing snapshot; missing/invalid → `field = "spec.snapshotRef"`, `type = "invalid"`
- `spec.scope` (object, optional): same shape as snapshot scope; when omitted, all snapshot data is restored
- `spec.resources.memory` (object): defaults to `{"limit": "1Gi", "request": "1Gi"}` when absent (adapts `mesh-management/memory-resource-validation-and-defaults`)
- `spec.resources.cpu` (object, optional): same format as mesh CPU (adapts `mesh-management/cpu-resource-validation-and-defaults`)

#### Scenario: missing meshRef is rejected

- **GIVEN** a recovery YAML without `spec.meshRef`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system returns `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"..."}]}`

#### Scenario: missing snapshotRef is rejected

- **GIVEN** a recovery YAML without `spec.snapshotRef`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system returns `{"errors":[{"field":"spec.snapshotRef","type":"invalid","message":"..."}]}`

#### Scenario: non-existent snapshotRef is rejected

- **GIVEN** a recovery YAML with `spec.snapshotRef` pointing to a snapshot that does not exist
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system returns an error with `field = "spec.snapshotRef"` and `type = "invalid"`

#### Scenario: snapshotRef mesh mismatch is rejected

- **GIVEN** a recovery YAML where `spec.meshRef = "mesh-a"` but the referenced snapshot has `spec.meshRef = "mesh-b"`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system returns an error with `field = "spec.snapshotRef"`, `type = "invalid"`, `message = "snapshot '<name>' belongs to mesh '<mesh-b>', not '<mesh-a>'"`

#### Scenario: memory defaults when absent

- **GIVEN** a recovery YAML without `spec.resources.memory`
- **WHEN** the user runs `meshctl recovery create -f <path>` with valid input
- **THEN** the stored resource has `spec.resources.memory = {"limit": "1Gi", "request": "1Gi"}`

---

### Requirement: recovery-create-initial-state

On successful create, the system SHALL set `status.state = "Initializing"`.

#### Scenario: created recovery has Initializing state

- **GIVEN** a valid recovery YAML
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the returned resource has `status.state = "Initializing"`

---

### Requirement: recovery-spec-immutability

After creation, the entire `spec` section SHALL be immutable. Any update that changes or adds a spec field SHALL be rejected with `type = "immutable"`. (adapts `mesh-management/immutable-field-error-type`)

#### Scenario: updating spec field is rejected

- **GIVEN** an existing recovery
- **WHEN** the user runs `meshctl recovery update -f <path>` with a changed spec field
- **THEN** the system returns an error with `type = "immutable"`

---

### Requirement: recovery-run

`meshctl recovery run <name>` SHALL execute the recovery restore operation.

Run is valid only from `"Initializing"`. On any other state:
- `field = "status.state"`
- `type = "invalid"`
- `message = "resource is in state '<current>', expected 'Initializing'"`

The system SHALL transition through `"Running"` to `"Succeeded"`, `"Failed"`, or `"Unknown"`.

If the referenced mesh has `status.stable = false` at run time:
- `status.state = "Unknown"`
- `status.detail` is a non-empty string

Otherwise, the system SHALL succeed.

#### Scenario: run from Initializing with stable mesh succeeds

- **GIVEN** a recovery in `"Initializing"` state and its referenced mesh has `status.stable = true`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** `status.state = "Succeeded"`

#### Scenario: run with unstable mesh results in Unknown

- **GIVEN** a recovery in `"Initializing"` state and its referenced mesh has `status.stable = false`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** `status.state = "Unknown"` and `status.detail` is a non-empty string

#### Scenario: run from non-Initializing state is rejected

- **GIVEN** a recovery in `"Succeeded"` state
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the system returns an error with `field = "status.state"`, `type = "invalid"`, `message = "resource is in state 'Succeeded', expected 'Initializing'"`

---

### Requirement: recovery-output-format

Recovery output SHALL use the same JSON and error format as mesh resources. `status` SHALL include `state`. `status.detail` SHALL be present only in `"Failed"` or `"Unknown"` state. (adapts `mesh-management/error-output-format`)

#### Scenario: failed recovery includes detail

- **GIVEN** a recovery that ran and reached `"Failed"` state
- **WHEN** the user runs `meshctl recovery describe <name>`
- **THEN** the output includes `status.detail` with a non-empty string

#### Scenario: succeeded recovery omits detail

- **GIVEN** a recovery that ran and reached `"Succeeded"` state
- **WHEN** the user runs `meshctl recovery describe <name>`
- **THEN** the output does not include `status.detail`
