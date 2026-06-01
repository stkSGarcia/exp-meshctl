## ADDED Requirements

> Extends: `mesh-management`

### Requirement: task-cli-surface

The system SHALL support `meshctl task create -f <path>`, `meshctl task list`, `meshctl task describe <name>`, `meshctl task update -f <path>`, `meshctl task delete <name>`, and `meshctl task run <name>` commands. (adapts `mesh-management/cli-entry-point`)

#### Scenario: task create command is routed

- **WHEN** the user runs `meshctl task create -f task.yaml`
- **THEN** the system reads the YAML, validates it, and persists the task resource

#### Scenario: task list command returns sorted array

- **WHEN** the user runs `meshctl task list`
- **THEN** the system prints a JSON array of all tasks sorted by `name` ascending

#### Scenario: task describe command returns full resource

- **WHEN** the user runs `meshctl task describe <name>`
- **THEN** the system prints the full task resource as JSON

#### Scenario: task delete command removes the resource

- **WHEN** the user runs `meshctl task delete <name>`
- **THEN** the system removes the task and prints a confirmation JSON object

---

### Requirement: task-yaml-input-schema

The system SHALL accept a YAML document with top-level keys `metadata` and `spec`. `metadata.name` SHALL follow the same validation rules as mesh name: required, non-null, non-empty, matching `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (minimum length 2). (adapts `mesh-management/yaml-input-schema`, `mesh-management/name-validation`)

#### Scenario: valid task YAML is accepted

- **GIVEN** a YAML file with `metadata.name` and valid `spec`
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system persists the resource and returns it as JSON

#### Scenario: invalid name is rejected

- **GIVEN** a YAML file with `metadata.name` that does not match `^[a-z0-9][a-z0-9-]*[a-z0-9]$`
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns an error with `field = "metadata.name"` and `type = "invalid"`

#### Scenario: not-found returns error

- **WHEN** the user runs `meshctl task describe <name>` and no task with that name exists
- **THEN** the system returns an error with `field = "metadata.name"` and `type = "not_found"`

---

### Requirement: task-spec-fields

The task spec SHALL have:
- `spec.meshRef` (string, required): must reference an existing mesh
- `spec.inline` (string): exactly one of `inline` or `bundleRef` must be set; empty values are invalid
- `spec.bundleRef` (string): exactly one of `inline` or `bundleRef` must be set; empty values are invalid

#### Scenario: missing meshRef is rejected

- **GIVEN** a task YAML without `spec.meshRef`
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"..."}]}`

#### Scenario: meshRef referencing non-existent mesh is rejected

- **GIVEN** a task YAML with `spec.meshRef` pointing to a mesh that does not exist
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"..."}]}`

#### Scenario: both inline and bundleRef set is rejected

- **GIVEN** a task YAML with both `spec.inline` and `spec.bundleRef` set
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns an error with `field = "spec"`, `type = "invalid"`, `message = "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`

#### Scenario: neither inline nor bundleRef set is rejected

- **GIVEN** a task YAML with neither `spec.inline` nor `spec.bundleRef`
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns an error with `field = "spec"`, `type = "invalid"`, `message = "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`

#### Scenario: empty inline value is rejected

- **GIVEN** a task YAML with `spec.inline` set to an empty string
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns an error with `field = "spec"` and `type = "invalid"`

---

### Requirement: task-create-initial-state

On successful create, the system SHALL set `status.state = "Initializing"`.

#### Scenario: created task has Initializing state

- **GIVEN** a valid task YAML
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the returned resource has `status.state = "Initializing"`

---

### Requirement: task-spec-immutability

After creation, the entire `spec` section of a task SHALL be immutable. The system SHALL reject any update that changes any spec field or adds a field that was previously omitted, using `type = "immutable"`. (adapts `mesh-management/immutable-field-error-type`)

#### Scenario: updating spec field is rejected

- **GIVEN** an existing task
- **WHEN** the user runs `meshctl task update -f <path>` with a changed `spec.inline` value
- **THEN** the system returns an error with `type = "immutable"`

#### Scenario: adding omitted spec field is rejected

- **GIVEN** an existing task created without `spec.bundleRef`
- **WHEN** the user runs `meshctl task update -f <path>` that includes `spec.bundleRef`
- **THEN** the system returns an error with `type = "immutable"`

---

### Requirement: task-run

`meshctl task run <name>` SHALL execute the task's inline content.

Run is valid only from `"Initializing"`. On any other state, the system SHALL return:
- `field = "status.state"`
- `type = "invalid"`
- `message = "resource is in state '<current>', expected 'Initializing'"`

The system SHALL transition through `"Running"` to a terminal state.

#### Scenario: run from Initializing succeeds on clean inline

- **GIVEN** a task in `"Initializing"` state with `spec.inline` containing no `FAIL:` lines
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** `status.state` transitions to `"Succeeded"`

#### Scenario: run from non-Initializing state is rejected

- **GIVEN** a task in `"Succeeded"` state
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the system returns an error with `field = "status.state"`, `type = "invalid"`, `message = "resource is in state 'Succeeded', expected 'Initializing'"`

---

### Requirement: task-inline-failure-rules

The system SHALL treat each line in `spec.inline` as one command and execute them in order.
- A line starting with `FAIL:` causes immediate failure.
- If line `<index>` (0-based) starts with `FAIL:`, the system SHALL set `status.state = "Failed"` and `status.detail = "command <index> failed: <reason>"` where `<reason>` is the text after `FAIL:`.
- Earlier successful commands SHALL NOT be rolled back.
- If no line starts with `FAIL:`, the run succeeds.

#### Scenario: FAIL line causes Failed state

- **GIVEN** a task with `spec.inline` = `"ok\nFAIL: disk full\nok"`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** `status.state = "Failed"` and `status.detail = "command 1 failed: disk full"`

#### Scenario: no FAIL line causes Succeeded state

- **GIVEN** a task with `spec.inline` containing no `FAIL:` lines
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** `status.state = "Succeeded"`

---

### Requirement: task-output-format

Task output SHALL use the same JSON formatting and error format as mesh resources. `status` SHALL include `state`. `status.detail` SHALL be present only in `"Failed"` state. (adapts `mesh-management/error-output-format`, `mesh-management/success-output-create-and-describe`)

#### Scenario: failed task includes detail

- **GIVEN** a task that ran and reached `"Failed"` state
- **WHEN** the user runs `meshctl task describe <name>`
- **THEN** the output includes `status.detail` with a non-empty string

#### Scenario: succeeded task omits detail

- **GIVEN** a task that ran and reached `"Succeeded"` state
- **WHEN** the user runs `meshctl task describe <name>`
- **THEN** the output does not include `status.detail`
