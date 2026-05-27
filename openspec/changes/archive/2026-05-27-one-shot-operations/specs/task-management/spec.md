## ADDED Requirements

### Requirement: Task resource CRUD operations
The system SHALL support `meshctl task create -f <path>`, `meshctl task list`, `meshctl task describe <name>`, `meshctl task update -f <path>`, and `meshctl task delete <name>` commands with the same name validation and not-found error shape used by mesh resources.

#### Scenario: Create task with valid spec
- **WHEN** user runs `meshctl task create -f task.yaml` with a valid YAML containing a unique name, an existing meshRef, and exactly one of inline or bundleRef
- **THEN** the system SHALL persist the task with `status.state = "Initializing"` and print the full resource as JSON

#### Scenario: Create task fails on missing meshRef
- **WHEN** user runs `meshctl task create -f task.yaml` with a meshRef that does not reference an existing mesh
- **THEN** the system SHALL return an error with `field = "spec.meshRef"` and `type = "invalid"`

#### Scenario: Create task fails when both inline and bundleRef are set
- **WHEN** user runs `meshctl task create -f task.yaml` with both `spec.inline` and `spec.bundleRef` present and non-empty
- **THEN** the system SHALL return an error with `field = "spec"`, `type = "invalid"`, and `message = "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`

#### Scenario: Create task fails when neither inline nor bundleRef is set
- **WHEN** user runs `meshctl task create -f task.yaml` with both `spec.inline` and `spec.bundleRef` absent or empty
- **THEN** the system SHALL return an error with `field = "spec"`, `type = "invalid"`, and `message = "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`

#### Scenario: List tasks returns sorted array
- **WHEN** user runs `meshctl task list`
- **THEN** the system SHALL print a JSON array of all tasks sorted by `name` ascending

#### Scenario: Describe returns full task resource
- **WHEN** user runs `meshctl task describe <name>` for an existing task
- **THEN** the system SHALL print the full task resource as JSON

#### Scenario: Delete removes the task
- **WHEN** user runs `meshctl task delete <name>` for an existing task
- **THEN** the system SHALL remove the task and print a confirmation message

### Requirement: Task spec is fully immutable after create
The system SHALL reject any update to a task that changes any field in `spec`, including adding a field that was previously absent.

#### Scenario: Update task spec field is rejected
- **WHEN** user runs `meshctl task update -f task.yaml` with any `spec` field changed from the stored value
- **THEN** the system SHALL return one or more errors with `type = "immutable"`

### Requirement: Task run lifecycle
The system SHALL transition a task through `Initializing` → `Running` → terminal state when `meshctl task run <name>` is executed.

#### Scenario: Run succeeds from Initializing state
- **WHEN** user runs `meshctl task run <name>` on a task with `status.state = "Initializing"` and no failing inline lines
- **THEN** the system SHALL set `status.state = "Succeeded"` and print the updated task

#### Scenario: Run from non-Initializing state is rejected
- **WHEN** user runs `meshctl task run <name>` on a task whose `status.state` is not `"Initializing"`
- **THEN** the system SHALL return an error with `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state '<current>', expected 'Initializing'"`

### Requirement: Inline command execution with per-line failure semantics
When a task uses `spec.inline`, the system SHALL execute each line in order, treating any line starting with `FAIL:` as a failure that terminates execution without rolling back earlier lines.

#### Scenario: Inline task with no failing lines succeeds
- **WHEN** a task with `spec.inline` containing no lines starting with `FAIL:` is run
- **THEN** the system SHALL set `status.state = "Succeeded"`

#### Scenario: Inline task fails on FAIL: line
- **WHEN** a task with `spec.inline` containing a line at index `<index>` starting with `FAIL:` is run
- **THEN** the system SHALL set `status.state = "Failed"`, `status.detail = "command <index> failed: <reason>"` where `<reason>` is the text after `FAIL:`
