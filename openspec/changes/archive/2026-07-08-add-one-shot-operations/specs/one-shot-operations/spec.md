## ADDED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology
> Extends: mesh-resource-management/add-meshctl-mesh-crud
> Extends: vault-resource-management/add-vault-resource-management

### Requirement: One-shot CLI command surface (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-cli-command-surface)
The system SHALL expose `task`, `snapshot`, and `recovery` create, list, describe, update, delete, and run operations through `meshctl.py`.

#### Scenario: Supported commands are available for each kind
- **WHEN** an operator invokes `meshctl <kind> create -f <path>`, `meshctl <kind> list`, `meshctl <kind> describe <name>`, `meshctl <kind> update -f <path>`, `meshctl <kind> delete <name>`, or `meshctl <kind> run <name>` for `<kind>` equal to `task`, `snapshot`, or `recovery`
- **THEN** the command is routed to the matching one-shot resource operation

#### Scenario: List output is sorted by resource name
- **WHEN** an operator lists tasks, snapshots, or recoveries
- **THEN** the command prints a JSON array sorted by `metadata.name` ascending

#### Scenario: Describe output returns the full resource
- **WHEN** an operator describes an existing task, snapshot, or recovery by name
- **THEN** the command prints the full resource as JSON

### Requirement: Common one-shot resource identity
The system SHALL validate `metadata.name` for tasks, snapshots, and recoveries with the same validation and not-found behavior used by mesh resources.

#### Scenario: Invalid name is rejected
- **WHEN** a task, snapshot, or recovery create request uses a `metadata.name` that is invalid for mesh resources
- **THEN** the request fails with the same structured validation shape used for mesh resource names

#### Scenario: Missing resource uses common not-found behavior
- **WHEN** an operator describes, updates, deletes, or runs a task, snapshot, or recovery name that does not exist
- **THEN** the command fails with the same not-found shape used for missing mesh resources

### Requirement: Task creation validation
The system SHALL create task resources only when `spec.meshRef` references an existing mesh and exactly one non-empty task source is provided in `spec.inline` or `spec.bundleRef`.

#### Scenario: Task starts initializing
- **GIVEN** an existing mesh
- **WHEN** an operator creates a task with `spec.meshRef` set to that mesh and exactly one non-empty source in `spec.inline` or `spec.bundleRef`
- **THEN** the created task has `status.state` equal to `Initializing`

#### Scenario: Task mesh reference is required
- **WHEN** an operator creates a task with a missing or invalid `spec.meshRef`
- **THEN** validation fails with `field` equal to `spec.meshRef` and `type` equal to `invalid`

#### Scenario: Task source is exclusive
- **WHEN** an operator creates a task with neither source, both sources, or an empty source value
- **THEN** validation fails with `field` equal to `spec`, `type` equal to `invalid`, and `message` equal to `exactly one of 'spec.inline' or 'spec.bundleRef' must be set`

### Requirement: Task execution lifecycle
The system SHALL run tasks only from `Initializing` and SHALL transition each run through `Running` to either `Succeeded` or `Failed`.

#### Scenario: Task succeeds when inline commands do not fail
- **GIVEN** a task in `Initializing` with inline content containing no line that starts with `FAIL:`
- **WHEN** an operator runs the task
- **THEN** the task transitions through `Running` and ends with `status.state` equal to `Succeeded`

#### Scenario: Task fails on matching inline command
- **GIVEN** a task in `Initializing` with inline content containing a line that starts with `FAIL:`
- **WHEN** an operator runs the task
- **THEN** the task ends with `status.state` equal to `Failed` and `status.detail` equal to `command <index> failed: <reason>`

#### Scenario: Task does not roll back prior commands
- **GIVEN** a task with multiple inline command lines where a later line starts with `FAIL:`
- **WHEN** an operator runs the task
- **THEN** command lines before the failing line remain successfully executed and are not rolled back

#### Scenario: Task run rejects non-initializing state
- **GIVEN** a task whose `status.state` is not `Initializing`
- **WHEN** an operator runs the task
- **THEN** validation fails with `field` equal to `status.state`, `type` equal to `invalid`, and `message` equal to `resource is in state '<current>', expected 'Initializing'`

### Requirement: Snapshot creation validation (adapts mesh-resource-management/add-meshctl-mesh-crud/mesh-resource-quantity-validation)
The system SHALL create snapshot resources only when `spec.meshRef` references an existing mesh, optional storage and scope fields are accepted, and memory and CPU resource quantities are valid.

#### Scenario: Snapshot starts initializing with defaults
- **GIVEN** an existing mesh
- **WHEN** an operator creates a snapshot with `spec.meshRef` set to that mesh and no `spec.resources.memory`
- **THEN** the created snapshot has `status.state` equal to `Initializing` and `spec.resources.memory` equal to `{"limit": "1Gi", "request": "1Gi"}`

#### Scenario: Snapshot mesh reference is required
- **WHEN** an operator creates a snapshot with a missing or invalid `spec.meshRef`
- **THEN** validation fails with `field` equal to `spec.meshRef` and `type` equal to `invalid`

#### Scenario: Snapshot scope may narrow captured data
- **WHEN** an operator creates a snapshot with `spec.scope` containing any of `stores`, `blueprints`, `tallies`, `definitions`, or `procedures`
- **THEN** the snapshot records that only the named items are captured

#### Scenario: Snapshot scope may be omitted
- **WHEN** an operator creates a snapshot without `spec.scope`
- **THEN** the snapshot records that all data is captured

#### Scenario: Snapshot resource quantities are validated
- **WHEN** an operator creates a snapshot with invalid memory or CPU quantity values or requests greater than limits
- **THEN** validation fails using the same resource quantity rules as mesh resources

### Requirement: Snapshot execution lifecycle
The system SHALL run snapshots only from `Initializing` and SHALL transition each run through `Running` to `Succeeded`, `Failed`, or `Unknown`.

#### Scenario: Snapshot succeeds for stable mesh
- **GIVEN** a snapshot in `Initializing` whose referenced mesh has `status.stable` equal to `true`
- **WHEN** an operator runs the snapshot
- **THEN** the snapshot transitions through `Running`, ends with `status.state` equal to `Succeeded`, and includes a stable non-empty `status.storageRef`

#### Scenario: Snapshot becomes unknown for unstable mesh
- **GIVEN** a snapshot in `Initializing` whose referenced mesh has `status.stable` equal to `false`
- **WHEN** an operator runs the snapshot
- **THEN** the snapshot ends with `status.state` equal to `Unknown` and `status.detail` set to a non-empty string

#### Scenario: Snapshot run rejects non-initializing state
- **GIVEN** a snapshot whose `status.state` is not `Initializing`
- **WHEN** an operator runs the snapshot
- **THEN** validation fails with `field` equal to `status.state`, `type` equal to `invalid`, and `message` equal to `resource is in state '<current>', expected 'Initializing'`

### Requirement: Recovery creation validation (adapts mesh-resource-management/add-meshctl-mesh-crud/mesh-resource-quantity-validation)
The system SHALL create recovery resources only when `spec.meshRef` references an existing mesh, `spec.snapshotRef` references an existing snapshot owned by that mesh, optional scope fields are accepted, and memory and CPU resource quantities are valid.

#### Scenario: Recovery starts initializing with defaults
- **GIVEN** an existing mesh and an existing snapshot whose `spec.meshRef` matches that mesh
- **WHEN** an operator creates a recovery with `spec.meshRef` set to that mesh, `spec.snapshotRef` set to that snapshot, and no `spec.resources.memory`
- **THEN** the created recovery has `status.state` equal to `Initializing` and `spec.resources.memory` equal to `{"limit": "1Gi", "request": "1Gi"}`

#### Scenario: Recovery mesh reference is required
- **WHEN** an operator creates a recovery with a missing or invalid `spec.meshRef`
- **THEN** validation fails with `field` equal to `spec.meshRef` and `type` equal to `invalid`

#### Scenario: Recovery snapshot reference is required
- **WHEN** an operator creates a recovery with a missing or invalid `spec.snapshotRef`
- **THEN** validation fails with `field` equal to `spec.snapshotRef` and `type` equal to `invalid`

#### Scenario: Recovery snapshot must belong to mesh
- **GIVEN** a snapshot named `<name>` whose `spec.meshRef` is `<X>`
- **WHEN** an operator creates a recovery with `spec.snapshotRef` set to `<name>` and `spec.meshRef` set to `<Y>`
- **THEN** validation fails with `field` equal to `spec.snapshotRef`, `type` equal to `invalid`, and `message` equal to `snapshot '<name>' belongs to mesh '<X>', not '<Y>'`

#### Scenario: Recovery scope may narrow restored data
- **WHEN** an operator creates a recovery with `spec.scope` containing any of `stores`, `blueprints`, `tallies`, `definitions`, or `procedures`
- **THEN** the recovery records that only the named items are restored

#### Scenario: Recovery scope may be omitted
- **WHEN** an operator creates a recovery without `spec.scope`
- **THEN** the recovery records that all snapshot data is restored

### Requirement: Recovery execution lifecycle
The system SHALL run recoveries only from `Initializing` and SHALL transition each run through `Running` to `Succeeded`, `Failed`, or `Unknown`.

#### Scenario: Recovery succeeds for stable mesh
- **GIVEN** a recovery in `Initializing` whose referenced mesh has `status.stable` equal to `true`
- **WHEN** an operator runs the recovery
- **THEN** the recovery transitions through `Running` and ends with `status.state` equal to `Succeeded`

#### Scenario: Recovery becomes unknown for unstable mesh
- **GIVEN** a recovery in `Initializing` whose referenced mesh has `status.stable` equal to `false`
- **WHEN** an operator runs the recovery
- **THEN** the recovery ends with `status.state` equal to `Unknown` and `status.detail` set to a non-empty string

#### Scenario: Recovery run rejects non-initializing state
- **GIVEN** a recovery whose `status.state` is not `Initializing`
- **WHEN** an operator runs the recovery
- **THEN** validation fails with `field` equal to `status.state`, `type` equal to `invalid`, and `message` equal to `resource is in state '<current>', expected 'Initializing'`

### Requirement: One-shot spec immutability
The system SHALL reject updates to tasks, snapshots, and recoveries that change, add, or remove any field under `spec`.

#### Scenario: Spec field update is rejected
- **GIVEN** an existing task, snapshot, or recovery
- **WHEN** an operator updates the resource with any changed `spec` field
- **THEN** validation fails with `type` equal to `immutable`

#### Scenario: Previously omitted spec field addition is rejected
- **GIVEN** an existing task, snapshot, or recovery whose `spec` omits an optional field
- **WHEN** an operator updates the resource by adding that optional field under `spec`
- **THEN** validation fails with `type` equal to `immutable`

### Requirement: Snapshot dependency protection
The system SHALL reject deleting a snapshot while one or more recovery resources reference that snapshot.

#### Scenario: Referenced snapshot cannot be deleted
- **GIVEN** one or more recoveries whose `spec.snapshotRef` references a snapshot
- **WHEN** an operator deletes that snapshot
- **THEN** validation fails with `field` equal to `metadata.name`, `type` equal to `conflict`, and a message naming the dependent recovery resources

#### Scenario: Unreferenced snapshot can be deleted
- **GIVEN** a snapshot with no recovery resources referencing it
- **WHEN** an operator deletes that snapshot
- **THEN** the snapshot is removed

### Requirement: One-shot status output
The system SHALL use the exact phase names `Initializing`, `Running`, `Succeeded`, `Failed`, and `Unknown`, and SHALL include status fields only when valid for the current outcome.

#### Scenario: Failed or unknown status includes detail
- **WHEN** a task, snapshot, or recovery ends in `Failed` or `Unknown`
- **THEN** the resource status includes a non-empty `detail`

#### Scenario: Succeeded snapshot includes storage reference
- **WHEN** a snapshot ends in `Succeeded`
- **THEN** the resource status includes `storageRef`

#### Scenario: Storage reference is snapshot-only
- **WHEN** a task or recovery ends in any terminal state
- **THEN** the resource status does not include `storageRef`
