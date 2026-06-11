## ADDED Requirements

### Requirement: One-shot operation command surface
The system SHALL expose `task`, `snapshot`, and `recovery` resource commands through `meshctl.py`.

#### Scenario: Task commands are available
- **WHEN** the user runs `uv run --project /app meshctl.py task create -f <path>`, `task list`, `task describe <name>`, `task update -f <path>`, `task delete <name>`, or `task run <name>`
- **THEN** the system SHALL route the request to the corresponding task operation.

#### Scenario: Snapshot commands are available
- **WHEN** the user runs `uv run --project /app meshctl.py snapshot create -f <path>`, `snapshot list`, `snapshot describe <name>`, `snapshot update -f <path>`, `snapshot delete <name>`, or `snapshot run <name>`
- **THEN** the system SHALL route the request to the corresponding snapshot operation.

#### Scenario: Recovery commands are available
- **WHEN** the user runs `uv run --project /app meshctl.py recovery create -f <path>`, `recovery list`, `recovery describe <name>`, `recovery update -f <path>`, `recovery delete <name>`, or `recovery run <name>`
- **THEN** the system SHALL route the request to the corresponding recovery operation.

### Requirement: One-shot operation common resource behavior
The system SHALL persist task, snapshot, and recovery resources by `metadata.name`, use the mesh resource name validation rule, and print JSON command output.

#### Scenario: Create initializes operation status
- **WHEN** a task, snapshot, or recovery is created successfully
- **THEN** the persisted resource SHALL include `status.state` equal to `"Initializing"`.

#### Scenario: List returns sorted operation summaries
- **WHEN** a list command returns task, snapshot, or recovery resources
- **THEN** the system SHALL print a JSON array sorted by `name` ascending.

#### Scenario: Describe returns full operation resource
- **WHEN** the user describes an existing task, snapshot, or recovery
- **THEN** the system SHALL print the full persisted resource.

#### Scenario: Delete removes operation resource
- **WHEN** the user deletes an existing task, snapshot, or recovery
- **THEN** the system SHALL remove that resource and print a JSON confirmation object.

#### Scenario: Missing named operation resource
- **WHEN** the user describes, updates, deletes, or runs a task, snapshot, or recovery name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Operation name validation matches meshes
- **WHEN** a task, snapshot, or recovery input provides `metadata.name` that does not satisfy the mesh naming rule
- **THEN** the system SHALL report field `metadata.name` with type `invalid`.

### Requirement: Task spec validation and creation
The system SHALL support task resources with required `spec.meshRef` and exactly one non-empty source field: `spec.inline` or `spec.bundleRef`.

#### Scenario: Task rejects missing parent mesh
- **WHEN** a task create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Task requires exactly one source
- **WHEN** a task create input omits both `spec.inline` and `spec.bundleRef` or provides both fields
- **THEN** the system SHALL report field `spec` with type `invalid` and message `exactly one of 'spec.inline' or 'spec.bundleRef' must be set`.

#### Scenario: Task rejects empty inline source
- **WHEN** a task create input provides `spec.inline` as an empty value
- **THEN** the system SHALL report field `spec` with type `invalid` and message `exactly one of 'spec.inline' or 'spec.bundleRef' must be set`.

#### Scenario: Task rejects empty bundle reference
- **WHEN** a task create input provides `spec.bundleRef` as an empty value
- **THEN** the system SHALL report field `spec` with type `invalid` and message `exactly one of 'spec.inline' or 'spec.bundleRef' must be set`.

#### Scenario: Task create succeeds
- **WHEN** a task create input provides an existing `spec.meshRef` and exactly one valid source field
- **THEN** the system SHALL persist the task with `status.state` equal to `"Initializing"`.

### Requirement: Task run lifecycle
The system SHALL run tasks only from `"Initializing"` and SHALL transition them to `"Succeeded"` or `"Failed"`.

#### Scenario: Task run rejects non-initializing state
- **WHEN** the user runs a task whose `status.state` is not `"Initializing"`
- **THEN** the system SHALL report field `status.state` with type `invalid` and message `resource is in state '<current>', expected 'Initializing'`.

#### Scenario: Inline task succeeds
- **WHEN** the user runs an initializing task whose `spec.inline` has no line beginning with `FAIL:`
- **THEN** the system SHALL set `status.state` to `"Succeeded"`.

#### Scenario: Inline task fails at failing line
- **WHEN** the user runs an initializing task whose `spec.inline` line `<index>` begins with `FAIL:`
- **THEN** the system SHALL set `status.state` to `"Failed"` and `status.detail` to `command <index> failed: <reason>`.

#### Scenario: Task does not roll back earlier successful inline commands
- **WHEN** a task inline command after one or more successful lines begins with `FAIL:`
- **THEN** the system SHALL keep the failure result for that line and SHALL NOT report rollback behavior.

#### Scenario: Bundle task succeeds
- **WHEN** the user runs an initializing task with `spec.bundleRef`
- **THEN** the system SHALL set `status.state` to `"Succeeded"`.

### Requirement: Snapshot spec validation and creation
The system SHALL support snapshot resources with required `spec.meshRef`, optional `spec.storage`, optional `spec.scope`, and optional `spec.resources`.

#### Scenario: Snapshot rejects missing parent mesh
- **WHEN** a snapshot create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Snapshot defaults memory resources
- **WHEN** a valid snapshot create input omits `spec.resources.memory`
- **THEN** the created snapshot SHALL include `spec.resources.memory` equal to `{"limit": "1Gi", "request": "1Gi"}`.

#### Scenario: Snapshot validates resource quantities
- **WHEN** a snapshot create input provides invalid memory or CPU quantity values under `spec.resources`
- **THEN** the system SHALL report the corresponding resource field with type `invalid`.

#### Scenario: Snapshot preserves optional storage fields
- **WHEN** a valid snapshot create input provides `spec.storage.size` or `spec.storage.className`
- **THEN** the created snapshot SHALL include the provided storage fields.

#### Scenario: Snapshot scope can be omitted
- **WHEN** a valid snapshot create input omits `spec.scope`
- **THEN** the snapshot SHALL represent a request to capture all mesh data.

#### Scenario: Snapshot scope can limit captured data
- **WHEN** a valid snapshot create input provides `spec.scope` keys for stores, blueprints, tallies, definitions, or procedures
- **THEN** the created snapshot SHALL preserve those scope selections.

### Requirement: Snapshot run lifecycle
The system SHALL run snapshots only from `"Initializing"` and SHALL transition them to `"Succeeded"`, `"Failed"`, or `"Unknown"`.

#### Scenario: Snapshot run rejects non-initializing state
- **WHEN** the user runs a snapshot whose `status.state` is not `"Initializing"`
- **THEN** the system SHALL report field `status.state` with type `invalid` and message `resource is in state '<current>', expected 'Initializing'`.

#### Scenario: Snapshot run is unknown for unstable mesh
- **WHEN** the user runs an initializing snapshot whose referenced mesh has `status.stable` equal to `false`
- **THEN** the system SHALL set `status.state` to `"Unknown"` and set `status.detail` to a non-empty string.

#### Scenario: Snapshot run succeeds for stable mesh
- **WHEN** the user runs an initializing snapshot whose referenced mesh has `status.stable` equal to `true`
- **THEN** the system SHALL set `status.state` to `"Succeeded"` and set `status.storageRef` to a stable non-empty string.

### Requirement: Recovery spec validation and creation
The system SHALL support recovery resources with required `spec.meshRef`, required `spec.snapshotRef`, optional `spec.scope`, and optional `spec.resources`.

#### Scenario: Recovery rejects missing parent mesh
- **WHEN** a recovery create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Recovery rejects missing snapshot reference
- **WHEN** a recovery create input has `spec.snapshotRef` that does not match an existing snapshot name
- **THEN** the system SHALL report field `spec.snapshotRef` with type `invalid`.

#### Scenario: Recovery rejects snapshot from another mesh
- **WHEN** a recovery create input references snapshot `<name>` whose `spec.meshRef` is `<X>` while recovery `spec.meshRef` is `<Y>`
- **THEN** the system SHALL report field `spec.snapshotRef` with type `invalid` and message `snapshot '<name>' belongs to mesh '<X>', not '<Y>'`.

#### Scenario: Recovery defaults memory resources
- **WHEN** a valid recovery create input omits `spec.resources.memory`
- **THEN** the created recovery SHALL include `spec.resources.memory` equal to `{"limit": "1Gi", "request": "1Gi"}`.

#### Scenario: Recovery validates resource quantities
- **WHEN** a recovery create input provides invalid memory or CPU quantity values under `spec.resources`
- **THEN** the system SHALL report the corresponding resource field with type `invalid`.

#### Scenario: Recovery scope can be omitted
- **WHEN** a valid recovery create input omits `spec.scope`
- **THEN** the recovery SHALL represent a request to restore all snapshot data.

#### Scenario: Recovery scope can limit restored data
- **WHEN** a valid recovery create input provides the same scope shape as snapshots
- **THEN** the created recovery SHALL preserve those scope selections.

### Requirement: Recovery run lifecycle
The system SHALL run recoveries only from `"Initializing"` and SHALL transition them to `"Succeeded"`, `"Failed"`, or `"Unknown"`.

#### Scenario: Recovery run rejects non-initializing state
- **WHEN** the user runs a recovery whose `status.state` is not `"Initializing"`
- **THEN** the system SHALL report field `status.state` with type `invalid` and message `resource is in state '<current>', expected 'Initializing'`.

#### Scenario: Recovery run is unknown for unstable mesh
- **WHEN** the user runs an initializing recovery whose referenced mesh has `status.stable` equal to `false`
- **THEN** the system SHALL set `status.state` to `"Unknown"` and set `status.detail` to a non-empty string.

#### Scenario: Recovery run succeeds for stable mesh
- **WHEN** the user runs an initializing recovery whose referenced mesh has `status.stable` equal to `true`
- **THEN** the system SHALL set `status.state` to `"Succeeded"`.

### Requirement: One-shot operation spec immutability
The system SHALL treat the entire `spec` section of task, snapshot, and recovery resources as immutable after create.

#### Scenario: Update rejects changed spec field
- **WHEN** a task, snapshot, or recovery update changes any stored `spec` field
- **THEN** the system SHALL reject the update with at least one error whose type is `immutable`.

#### Scenario: Update rejects added spec field
- **WHEN** a task, snapshot, or recovery update adds a `spec` field that was previously omitted
- **THEN** the system SHALL reject the update with at least one error whose type is `immutable`.

#### Scenario: Update allows unchanged spec
- **WHEN** a task, snapshot, or recovery update provides no `spec` changes
- **THEN** the system SHALL preserve the resource and print the full resource.

### Requirement: Snapshot dependency protection
The system SHALL reject snapshot deletion while one or more recoveries reference the snapshot.

#### Scenario: Snapshot delete is blocked by dependent recovery
- **WHEN** the user deletes a snapshot referenced by at least one recovery through `spec.snapshotRef`
- **THEN** the system SHALL NOT delete the snapshot and SHALL report field `metadata.name` with type `conflict`.

#### Scenario: Snapshot conflict message names recoveries
- **WHEN** a snapshot delete is blocked by dependent recoveries
- **THEN** the error message SHALL name the dependent recovery resources.

### Requirement: One-shot operation status output
The system SHALL use exact phase names and status field presence rules for task, snapshot, and recovery resources.

#### Scenario: Operation phase names are exact
- **WHEN** a task, snapshot, or recovery status is returned
- **THEN** `status.state` SHALL use only `"Initializing"`, `"Running"`, `"Succeeded"`, `"Failed"`, or `"Unknown"` as applicable to that resource kind.

#### Scenario: Detail appears only for failed or unknown operations
- **WHEN** a task, snapshot, or recovery status is returned
- **THEN** `status.detail` SHALL be present only when `status.state` is `"Failed"` or `"Unknown"`.

#### Scenario: Snapshot storage reference appears only on success
- **WHEN** a snapshot status is returned
- **THEN** `status.storageRef` SHALL be present only when `status.state` is `"Succeeded"`.

#### Scenario: Error output uses existing JSON shape
- **WHEN** any task, snapshot, or recovery validation, parse, duplicate, not-found, immutable, run-state, or dependency error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.
