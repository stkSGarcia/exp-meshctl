## ADDED Requirements

### Requirement: One-shot operation command surface
The system SHALL expose `task`, `snapshot`, and `recovery` operations through `meshctl.py`.

#### Scenario: Task command group supports CRUD and run
- **WHEN** the user runs `uv run --project /app meshctl.py task create -f <path>`, `task list`, `task describe <name>`, `task update -f <path>`, `task delete <name>`, or `task run <name>`
- **THEN** the system SHALL route the command to the task resource handler.

#### Scenario: Snapshot command group supports CRUD and run
- **WHEN** the user runs `uv run --project /app meshctl.py snapshot create -f <path>`, `snapshot list`, `snapshot describe <name>`, `snapshot update -f <path>`, `snapshot delete <name>`, or `snapshot run <name>`
- **THEN** the system SHALL route the command to the snapshot resource handler.

#### Scenario: Recovery command group supports CRUD and run
- **WHEN** the user runs `uv run --project /app meshctl.py recovery create -f <path>`, `recovery list`, `recovery describe <name>`, `recovery update -f <path>`, `recovery delete <name>`, or `recovery run <name>`
- **THEN** the system SHALL route the command to the recovery resource handler.

### Requirement: One-shot resource naming and lookup
The system SHALL validate `metadata.name` for tasks, snapshots, and recoveries using the mesh metadata naming rule and SHALL use the mesh resource not-found error shape for missing named resources.

#### Scenario: Missing null or empty name
- **WHEN** a task, snapshot, or recovery create input omits `metadata.name` or provides it as null or an empty string
- **THEN** the system SHALL report field `metadata.name` with type `required`.

#### Scenario: Invalid name format
- **WHEN** a task, snapshot, or recovery create input provides `metadata.name` that does not satisfy the mesh naming rule
- **THEN** the system SHALL report field `metadata.name` with type `invalid`.

#### Scenario: Duplicate resource name on create
- **WHEN** a task, snapshot, or recovery create request uses a `metadata.name` that already exists for the same kind
- **THEN** the system SHALL report field `metadata.name` with type `duplicate` and SHALL NOT overwrite the existing resource.

#### Scenario: Missing named resource
- **WHEN** the user describes, updates, deletes, or runs a task, snapshot, or recovery name that does not exist for that kind
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

### Requirement: One-shot create input format
The system SHALL accept exactly one YAML document whose root value is a mapping with supported top-level `metadata` and `spec` content for task, snapshot, and recovery create and update input.

#### Scenario: YAML read or parse failure
- **WHEN** the input file cannot be read or parsed as YAML
- **THEN** the system SHALL print a JSON error object containing an error with field `""` and type `parse`.

#### Scenario: YAML document is not a mapping
- **WHEN** the input parses but the YAML document root is not a mapping
- **THEN** the system SHALL print a JSON error object and SHALL NOT persist the resource.

### Requirement: One-shot list output
The system SHALL list task, snapshot, and recovery summaries sorted by `name` ascending using lexicographic, case-sensitive ordering.

#### Scenario: List returns sorted task summaries
- **WHEN** tasks named `beta`, `alpha`, and `gamma` exist
- **THEN** `task list` SHALL print summaries in the order `alpha`, `beta`, `gamma`.

#### Scenario: List returns sorted snapshot summaries
- **WHEN** snapshots named `beta`, `alpha`, and `gamma` exist
- **THEN** `snapshot list` SHALL print summaries in the order `alpha`, `beta`, `gamma`.

#### Scenario: List returns sorted recovery summaries
- **WHEN** recoveries named `beta`, `alpha`, and `gamma` exist
- **THEN** `recovery list` SHALL print summaries in the order `alpha`, `beta`, `gamma`.

### Requirement: One-shot lifecycle states
The system SHALL create tasks, snapshots, and recoveries in `Initializing`, SHALL use `Running` as the execution phase, and SHALL treat terminal states as irreversible.

#### Scenario: Create starts in Initializing
- **WHEN** a task, snapshot, or recovery is created successfully
- **THEN** the returned and persisted resource SHALL include `status.state` equal to `"Initializing"`.

#### Scenario: Run rejects non-Initializing resource
- **WHEN** the user runs a task, snapshot, or recovery whose `status.state` is not `"Initializing"`
- **THEN** the system SHALL report field `status.state` with type `invalid` and message `resource is in state '<current>', expected 'Initializing'`.

#### Scenario: Task terminal states
- **WHEN** a task run completes
- **THEN** the task `status.state` SHALL be either `"Succeeded"` or `"Failed"`.

#### Scenario: Snapshot terminal states
- **WHEN** a snapshot run completes
- **THEN** the snapshot `status.state` SHALL be one of `"Succeeded"`, `"Failed"`, or `"Unknown"`.

#### Scenario: Recovery terminal states
- **WHEN** a recovery run completes
- **THEN** the recovery `status.state` SHALL be one of `"Succeeded"`, `"Failed"`, or `"Unknown"`.

### Requirement: Task spec validation
The system SHALL support task `spec.meshRef`, `spec.inline`, and `spec.bundleRef`.

#### Scenario: Mesh reference is required
- **WHEN** a task create input omits `spec.meshRef` or provides it as null or an empty string
- **THEN** the system SHALL report field `spec.meshRef` with type `required`.

#### Scenario: Mesh reference must exist
- **WHEN** a task create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Inline or bundle reference is required
- **WHEN** a task create input omits both `spec.inline` and `spec.bundleRef`
- **THEN** the system SHALL report field `spec` with type `invalid` and message `exactly one of 'spec.inline' or 'spec.bundleRef' must be set`.

#### Scenario: Inline and bundle reference are exclusive
- **WHEN** a task create input includes both `spec.inline` and `spec.bundleRef`
- **THEN** the system SHALL report field `spec` with type `invalid` and message `exactly one of 'spec.inline' or 'spec.bundleRef' must be set`.

#### Scenario: Empty inline value is invalid
- **WHEN** a task create input provides `spec.inline` as an empty value
- **THEN** the system SHALL reject the resource.

#### Scenario: Empty bundle reference is invalid
- **WHEN** a task create input provides `spec.bundleRef` as an empty value
- **THEN** the system SHALL reject the resource.

### Requirement: Task run behavior
The system SHALL execute task inline content deterministically by treating each line as one command and SHALL NOT roll back earlier successful lines after a later failure.

#### Scenario: Inline content without failing line succeeds
- **WHEN** the user runs a task in `Initializing` whose `spec.inline` has no line starting with `FAIL:`
- **THEN** the system SHALL transition the task through `"Running"` to `"Succeeded"`.

#### Scenario: Inline content with failing line fails
- **WHEN** the user runs a task in `Initializing` and line `<index>` of `spec.inline` starts with `FAIL:`
- **THEN** the system SHALL set `status.state` to `"Failed"` and `status.detail` to `command <index> failed: <reason>`.

#### Scenario: Bundle task succeeds
- **WHEN** the user runs a task in `Initializing` with `spec.bundleRef` and no inline content
- **THEN** the system SHALL transition the task through `"Running"` to `"Succeeded"`.

### Requirement: Snapshot spec validation and defaults
The system SHALL support snapshot `spec.meshRef`, optional `spec.storage.size`, optional `spec.storage.className`, optional `spec.scope`, defaulted `spec.resources.memory`, and optional `spec.resources.cpu`.

#### Scenario: Mesh reference is required
- **WHEN** a snapshot create input omits `spec.meshRef` or provides it as null or an empty string
- **THEN** the system SHALL report field `spec.meshRef` with type `required`.

#### Scenario: Mesh reference must exist
- **WHEN** a snapshot create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Memory defaults when omitted
- **WHEN** a valid snapshot create input omits `spec.resources.memory`
- **THEN** the created snapshot SHALL include `spec.resources.memory` equal to `{"limit": "1Gi", "request": "1Gi"}`.

#### Scenario: CPU and memory quantities use mesh validation
- **WHEN** a snapshot create input includes `spec.resources.memory` or `spec.resources.cpu`
- **THEN** the system SHALL validate those quantities using the same formats and validation rules as mesh resource quantities.

#### Scenario: Omitted scope captures all data
- **WHEN** a valid snapshot create input omits `spec.scope`
- **THEN** running the snapshot SHALL capture all mesh data.

#### Scenario: Provided scope captures named items only
- **WHEN** a snapshot includes `spec.scope` keys for `stores`, `blueprints`, `tallies`, `definitions`, or `procedures`
- **THEN** running the snapshot SHALL capture only the named items in the provided scope.

### Requirement: Snapshot run behavior
The system SHALL run snapshots from `Initializing` and SHALL set a stable storage reference only for successful snapshots.

#### Scenario: Stable mesh snapshot succeeds
- **WHEN** the user runs a snapshot in `Initializing` and the referenced mesh has `status.stable` equal to `true`
- **THEN** the system SHALL transition the snapshot through `"Running"` to `"Succeeded"` and set a stable, non-empty `status.storageRef`.

#### Scenario: Unstable mesh snapshot becomes unknown
- **WHEN** the user runs a snapshot in `Initializing` and the referenced mesh has `status.stable` equal to `false`
- **THEN** the system SHALL set `status.state` to `"Unknown"` and `status.detail` to a non-empty string.

#### Scenario: Storage reference only appears on succeeded snapshot
- **WHEN** a snapshot has not succeeded
- **THEN** the system SHALL omit `status.storageRef`.

### Requirement: Recovery spec validation and defaults
The system SHALL support recovery `spec.meshRef`, required `spec.snapshotRef`, optional `spec.scope`, defaulted `spec.resources.memory`, and optional `spec.resources.cpu`.

#### Scenario: Mesh reference is required
- **WHEN** a recovery create input omits `spec.meshRef` or provides it as null or an empty string
- **THEN** the system SHALL report field `spec.meshRef` with type `required`.

#### Scenario: Mesh reference must exist
- **WHEN** a recovery create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Snapshot reference is required
- **WHEN** a recovery create input omits `spec.snapshotRef` or provides it as null or an empty string
- **THEN** the system SHALL report field `spec.snapshotRef` with type `required`.

#### Scenario: Snapshot reference must exist
- **WHEN** a recovery create input has `spec.snapshotRef` that does not match an existing snapshot name
- **THEN** the system SHALL report field `spec.snapshotRef` with type `invalid`.

#### Scenario: Snapshot mesh must match recovery mesh
- **WHEN** a recovery create input references snapshot `<name>` whose `spec.meshRef` is `<X>` and the recovery `spec.meshRef` is `<Y>`
- **THEN** the system SHALL report field `spec.snapshotRef` with type `invalid` and message `snapshot '<name>' belongs to mesh '<X>', not '<Y>'`.

#### Scenario: Memory defaults when omitted
- **WHEN** a valid recovery create input omits `spec.resources.memory`
- **THEN** the created recovery SHALL include `spec.resources.memory` equal to `{"limit": "1Gi", "request": "1Gi"}`.

#### Scenario: CPU and memory quantities use mesh validation
- **WHEN** a recovery create input includes `spec.resources.memory` or `spec.resources.cpu`
- **THEN** the system SHALL validate those quantities using the same formats and validation rules as mesh resource quantities.

#### Scenario: Omitted scope restores all snapshot data
- **WHEN** a valid recovery create input omits `spec.scope`
- **THEN** running the recovery SHALL restore all snapshot data.

### Requirement: Recovery run behavior
The system SHALL run recoveries from `Initializing` against their referenced mesh and snapshot.

#### Scenario: Stable mesh recovery succeeds
- **WHEN** the user runs a recovery in `Initializing` and the referenced mesh has `status.stable` equal to `true`
- **THEN** the system SHALL transition the recovery through `"Running"` to `"Succeeded"`.

#### Scenario: Unstable mesh recovery becomes unknown
- **WHEN** the user runs a recovery in `Initializing` and the referenced mesh has `status.stable` equal to `false`
- **THEN** the system SHALL set `status.state` to `"Unknown"` and `status.detail` to a non-empty string.

### Requirement: One-shot spec immutability
The system SHALL treat the entire `spec` section of tasks, snapshots, and recoveries as immutable after create.

#### Scenario: Update changing an existing spec field is rejected
- **WHEN** a task, snapshot, or recovery update changes any stored `spec` field
- **THEN** the system SHALL report an error with type `immutable` and SHALL NOT persist the update.

#### Scenario: Update adding omitted spec field is rejected
- **WHEN** a task, snapshot, or recovery update adds a `spec` field that was previously omitted
- **THEN** the system SHALL report an error with type `immutable` and SHALL NOT persist the update.

#### Scenario: Update preserving spec is accepted
- **WHEN** a task, snapshot, or recovery update provides no `spec` change after merging with the stored resource
- **THEN** the system SHALL persist allowed non-spec changes and return the full resource.

### Requirement: Snapshot dependency protection
The system SHALL reject `snapshot delete` when one or more recoveries reference that snapshot.

#### Scenario: Snapshot delete blocked by dependent recovery
- **WHEN** the user deletes a snapshot that is referenced by at least one recovery through `spec.snapshotRef`
- **THEN** the system SHALL NOT delete the snapshot and SHALL report field `metadata.name` with type `conflict`.

#### Scenario: Conflict message names dependent recoveries
- **WHEN** a snapshot delete is blocked by dependent recoveries
- **THEN** the error message SHALL name the dependent recovery resources.

### Requirement: One-shot status output
The system SHALL print task, snapshot, and recovery status using `status.state` and SHALL include optional status fields only when applicable.

#### Scenario: Detail appears only for failed or unknown resources
- **WHEN** a task, snapshot, or recovery status is not `"Failed"` or `"Unknown"`
- **THEN** the returned resource SHALL omit `status.detail`.

#### Scenario: Detail appears for failed or unknown resources
- **WHEN** a task, snapshot, or recovery status is `"Failed"` or `"Unknown"`
- **THEN** the returned resource SHALL include a non-empty `status.detail`.

#### Scenario: Snapshot storage reference appears only on success
- **WHEN** a snapshot status is `"Succeeded"`
- **THEN** the returned resource SHALL include a non-empty `status.storageRef`.

### Requirement: One-shot error output
The system SHALL use the JSON error shape, exit codes, and formatting rules established for mesh resources for task, snapshot, and recovery errors.

#### Scenario: Error object shape
- **WHEN** any task, snapshot, or recovery validation, parse, duplicate, not-found, immutable, run-state, or dependency error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.

#### Scenario: Error order is not contractual
- **WHEN** multiple one-shot resource errors are returned
- **THEN** callers SHALL NOT rely on the order of errors in the `errors` array.
