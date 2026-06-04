## ADDED Requirements

> Extends: `vault-management`

### Requirement: Task CLI Entry Point

The tool SHALL be invokable as `meshctl task <operation> [arguments]` and SHALL route to the correct task operation handler.

#### Scenario: Routing task create
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system reads the YAML file and creates a task resource

#### Scenario: Routing task run
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the system executes the named task resource

---

### Requirement: Task Create

The system SHALL read a YAML document from the file path given by `-f`, validate all fields, and — if valid — persist the task resource with `status.state = "Initializing"` and print the full resource as JSON to stdout.

#### Scenario: Successful task creation
- **GIVEN** a YAML file with a valid `metadata.name`, an existing `spec.meshRef`, and exactly one of `spec.inline` or `spec.bundleRef` set
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system persists the resource and prints the full task JSON with `status.state = "Initializing"`

#### Scenario: Missing mesh reference
- **GIVEN** a YAML file where `spec.meshRef` is absent or references a non-existent mesh
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns a validation error with `field = "spec.meshRef"` and `type = "invalid"`

#### Scenario: Neither inline nor bundleRef set
- **GIVEN** a YAML file where neither `spec.inline` nor `spec.bundleRef` is set
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns an error with `field = "spec"`, `type = "invalid"`, and `message = "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`

#### Scenario: Both inline and bundleRef set
- **GIVEN** a YAML file where both `spec.inline` and `spec.bundleRef` are set
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns an error with `field = "spec"`, `type = "invalid"`, and `message = "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`

#### Scenario: Inline set to empty string
- **GIVEN** a YAML file where `spec.inline` is set to an empty string
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system returns a validation error with `field = "spec"` and `type = "invalid"`

---

### Requirement: Task List

The system SHALL print a JSON array of all task resources sorted by `name` ascending lexicographically. (adapts `vault-management/vault-list`)

#### Scenario: List with no tasks
- **WHEN** the user runs `meshctl task list` and no tasks exist
- **THEN** the system prints `[]`

#### Scenario: List with multiple tasks
- **GIVEN** tasks named `alpha`, `gamma`, and `beta` exist
- **WHEN** the user runs `meshctl task list`
- **THEN** the system prints the array sorted as `alpha`, `beta`, `gamma`

---

### Requirement: Task Describe

The system SHALL print the full resource JSON for the task identified by `<name>`. (adapts `vault-management/vault-describe`)

#### Scenario: Describe existing task
- **GIVEN** a task named `my-task` exists
- **WHEN** the user runs `meshctl task describe my-task`
- **THEN** the system prints the full task resource JSON

#### Scenario: Describe non-existent task
- **GIVEN** no task named `missing` exists
- **WHEN** the user runs `meshctl task describe missing`
- **THEN** the system returns a not-found error with `field = "metadata.name"` and `type = "not_found"`

---

### Requirement: Task Update

The system SHALL read a YAML document from the file path given by `-f` and reject any update that changes any field in the `spec` section or adds a field that was previously omitted. The entire `spec` is immutable after creation.

#### Scenario: Attempt to change spec field
- **GIVEN** a task named `my-task` exists with `spec.inline = "echo hello"`
- **WHEN** the user runs `meshctl task update -f <path>` where the file sets `spec.inline = "echo world"`
- **THEN** the system returns an error with `type = "immutable"`

#### Scenario: Attempt to add previously-omitted spec field
- **GIVEN** a task created without `spec.bundleRef`
- **WHEN** the user runs `meshctl task update -f <path>` where the file adds `spec.bundleRef`
- **THEN** the system returns an error with `type = "immutable"`

---

### Requirement: Task Delete

The system SHALL remove the named task from the store and print a confirmation JSON object. (adapts `vault-management/vault-delete`)

#### Scenario: Delete existing task
- **GIVEN** a task named `my-task` exists
- **WHEN** the user runs `meshctl task delete my-task`
- **THEN** the system removes the task and prints a confirmation JSON

---

### Requirement: Task Run

The system SHALL execute the task identified by `<name>` only when `status.state = "Initializing"`. On any other state, the run SHALL be rejected. During execution the state transitions through `"Running"` to a terminal state.

#### Scenario: Run from Initializing state
- **GIVEN** a task with `status.state = "Initializing"` and `spec.inline` containing no `FAIL:` lines
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the state transitions `Initializing → Running → Succeeded`

#### Scenario: Run from non-Initializing state
- **GIVEN** a task with `status.state = "Succeeded"`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the system returns an error with `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state 'Succeeded', expected 'Initializing'"`

---

### Requirement: Task Inline Execution

When executing an inline task, the system SHALL treat each line in `spec.inline` as one command, execute them in order without rolling back earlier successful commands, and detect failure by a line starting with `FAIL:`.

#### Scenario: All lines succeed
- **GIVEN** a task with `spec.inline = "cmd1\ncmd2\ncmd3"` (no FAIL: lines)
- **WHEN** `meshctl task run <name>` executes
- **THEN** `status.state = "Succeeded"` and no `status.detail` is set

#### Scenario: Line at index 1 fails
- **GIVEN** a task with `spec.inline = "cmd1\nFAIL: disk full\ncmd3"` where line index 1 starts with `FAIL:`
- **WHEN** `meshctl task run <name>` executes
- **THEN** `status.state = "Failed"` and `status.detail = "command 1 failed: disk full"`

---

### Requirement: Task Error Output Format

All task validation and operational errors SHALL use the JSON error shape: `{"errors":[{"field":"<path>","type":"<type>","message":"<msg>"}]}` printed to stdout. (adapts `vault-management/vault-error-output-format`)

#### Scenario: Validation error format
- **GIVEN** a task create with an invalid spec
- **WHEN** the error is returned
- **THEN** it is printed as `{"errors":[{"field":"...","type":"...","message":"..."}]}`
