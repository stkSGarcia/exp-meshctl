## ADDED Requirements

### Requirement: Task CRUD surface
The system SHALL support `meshctl task create -f <path>`, `meshctl task list`, `meshctl task describe <name>`, `meshctl task update -f <path>`, and `meshctl task delete <name>` with the same output shapes and error conventions as mesh resources.

#### Scenario: List returns JSON array sorted by name
- **WHEN** one or more tasks exist
- **THEN** output a JSON array of task summaries sorted by `metadata.name` ascending

#### Scenario: List empty store
- **WHEN** no tasks exist
- **THEN** output `[]`

#### Scenario: Describe existing task
- **WHEN** the named task exists
- **THEN** output the full resource JSON

#### Scenario: Describe unknown task
- **WHEN** the named task does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

#### Scenario: Delete existing task
- **WHEN** the named task exists
- **THEN** remove it and output `{"message":"<non-empty>","metadata":{"name":"<string>"}}`

#### Scenario: Delete unknown task
- **WHEN** the named task does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Task create — meshRef validation
The system SHALL reject a create request when `spec.meshRef` is absent or does not reference an existing mesh.

#### Scenario: Missing meshRef
- **WHEN** `spec.meshRef` is absent or empty in the create YAML
- **THEN** output `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"<msg>"}]}`

#### Scenario: Non-existent meshRef
- **WHEN** `spec.meshRef` names a mesh that does not exist
- **THEN** output `{"errors":[{"field":"spec.meshRef","type":"invalid","message":"<msg>"}]}`

---

### Requirement: Task create — exclusive inline/bundleRef
The system SHALL accept exactly one of `spec.inline` or `spec.bundleRef`. Both absent, both present, or either set to an empty string SHALL be rejected.

#### Scenario: Both absent
- **WHEN** neither `spec.inline` nor `spec.bundleRef` is set
- **THEN** output `{"errors":[{"field":"spec","type":"invalid","message":"exactly one of 'spec.inline' or 'spec.bundleRef' must be set"}]}`

#### Scenario: Both present
- **WHEN** both `spec.inline` and `spec.bundleRef` are set
- **THEN** output `{"errors":[{"field":"spec","type":"invalid","message":"exactly one of 'spec.inline' or 'spec.bundleRef' must be set"}]}`

#### Scenario: Empty inline value rejected
- **WHEN** `spec.inline` is set to an empty string
- **THEN** output `{"errors":[{"field":"spec","type":"invalid","message":"exactly one of 'spec.inline' or 'spec.bundleRef' must be set"}]}`

#### Scenario: Empty bundleRef value rejected
- **WHEN** `spec.bundleRef` is set to an empty string
- **THEN** output `{"errors":[{"field":"spec","type":"invalid","message":"exactly one of 'spec.inline' or 'spec.bundleRef' must be set"}]}`

#### Scenario: Only inline provided
- **WHEN** `spec.inline` is non-empty and `spec.bundleRef` is absent
- **THEN** the task is accepted and `status.state = "Initializing"` is set

#### Scenario: Only bundleRef provided
- **WHEN** `spec.bundleRef` is non-empty and `spec.inline` is absent
- **THEN** the task is accepted and `status.state = "Initializing"` is set

---

### Requirement: Task create — initial state
The system SHALL set `status.state = "Initializing"` on successful create.

#### Scenario: Create success sets Initializing
- **WHEN** a valid task YAML is provided and persisted
- **THEN** the response includes `status.state = "Initializing"`

---

### Requirement: Task run — state gate
The system SHALL only permit `meshctl task run <name>` from `status.state = "Initializing"`. Attempts from any other state SHALL be rejected.

#### Scenario: Run from non-Initializing state
- **WHEN** `meshctl task run <name>` is called and the task is not in `"Initializing"` state
- **THEN** output `{"errors":[{"field":"status.state","type":"invalid","message":"resource is in state '<current>', expected 'Initializing'"}]}`

#### Scenario: Run unknown task
- **WHEN** `meshctl task run <name>` is called with a name that does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Task run — inline execution
The system SHALL execute `spec.inline` by treating each line as one command in order. A line that starts with `FAIL:` causes the task to fail at that line.

#### Scenario: All lines succeed
- **WHEN** `spec.inline` contains no line starting with `FAIL:`
- **THEN** `status.state = "Succeeded"`

#### Scenario: Line N starts with FAIL
- **WHEN** line at index `<index>` (0-based) starts with `FAIL:` followed by a reason
- **THEN** `status.state = "Failed"` and `status.detail = "command <index> failed: <reason>"`

#### Scenario: Earlier successful lines not rolled back
- **WHEN** a later line fails
- **THEN** the task result is `"Failed"` without reverting prior commands

#### Scenario: bundleRef task run succeeds
- **WHEN** the task uses `spec.bundleRef` (no `spec.inline`) and run is invoked from `"Initializing"`
- **THEN** `status.state = "Succeeded"`

---

### Requirement: Task run — state transition
The system SHALL transition through `"Running"` before settling at `"Succeeded"` or `"Failed"`.

#### Scenario: Terminal state after run
- **WHEN** `meshctl task run <name>` completes
- **THEN** `status.state` is either `"Succeeded"` or `"Failed"`

---

### Requirement: Task spec immutability
The system SHALL reject any `update` that changes, adds, or removes any field in the `spec` section after creation.

#### Scenario: Spec field change rejected
- **WHEN** an update YAML changes any spec field
- **THEN** output errors with `type: "immutable"` and do not persist

#### Scenario: New spec field addition rejected
- **WHEN** an update YAML adds a spec field that was not set at creation
- **THEN** output errors with `type: "immutable"` and do not persist

#### Scenario: Metadata-only update accepted
- **WHEN** an update YAML changes only metadata fields and leaves spec identical
- **THEN** the update is persisted

---

### Requirement: Task output shape
The system SHALL include `status.state` and, when in `"Failed"` state, `status.detail` in all task responses. `status.detail` SHALL be absent in non-failed states.

#### Scenario: Succeeded task output
- **WHEN** a task is in `"Succeeded"` state
- **THEN** output includes `status.state = "Succeeded"` and no `status.detail` field

#### Scenario: Failed task output
- **WHEN** a task is in `"Failed"` state
- **THEN** output includes `status.state = "Failed"` and a non-empty `status.detail`
