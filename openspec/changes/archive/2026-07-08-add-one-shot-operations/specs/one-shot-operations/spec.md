## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud
> Extends: mesh-resource-management/add-mesh-lifecycle-topology
> Extends: vault-resource-management/add-vault-resource-management

### Requirement: One-shot CLI command surface (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-cli-command-surface)
The system SHALL expose `task`, `snapshot`, and `recovery` `create -f <path>`, `list`, `describe <name>`, `update -f <path>`, `delete <name>`, and `run <name>` operations through `meshctl.py`.

#### Scenario: List one-shot resources
- **GIVEN** stored one-shot resources of a kind exist with unsorted names
- **WHEN** the user runs `meshctl <kind> list` for `task`, `snapshot`, or `recovery`
- **THEN** the system prints a JSON array sorted by `metadata.name` ascending

#### Scenario: Describe one-shot resource
- **GIVEN** a stored one-shot resource exists
- **WHEN** the user runs `meshctl <kind> describe <name>`
- **THEN** the system prints the full resource as JSON

### Requirement: Task creation validation
The system SHALL create task resources only when `spec.meshRef` references an existing mesh and exactly one non-empty command source is set.

#### Scenario: Create task with inline commands
- **GIVEN** a valid task YAML sets `spec.meshRef` to an existing mesh and sets non-empty `spec.inline`
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system stores the task with `status.state` set to `Initializing`

#### Scenario: Reject task with missing mesh
- **GIVEN** a task YAML has missing or invalid `spec.meshRef`
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system rejects the request with an error whose `field` is `spec.meshRef` and whose `type` is `invalid`

#### Scenario: Reject task with invalid command source
- **GIVEN** a task YAML sets neither `spec.inline` nor `spec.bundleRef`, sets both fields, or sets an empty selected value
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system rejects the request with an error whose `field` is `spec`, whose `type` is `invalid`, and whose `message` is `exactly one of 'spec.inline' or 'spec.bundleRef' must be set`

### Requirement: Task run execution
The system SHALL run task resources only from `Initializing`, transition through `Running`, and finish in `Succeeded` or `Failed`.

#### Scenario: Run successful inline task
- **GIVEN** a task is in `Initializing` and `spec.inline` contains no line starting with `FAIL:`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the system sets `status.state` to `Succeeded`

#### Scenario: Run failing inline task
- **GIVEN** a task is in `Initializing` and line `<index>` of `spec.inline` starts with `FAIL:`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the system sets `status.state` to `Failed`
- **AND** sets `status.detail` to `command <index> failed: <reason>`

#### Scenario: Reject task run from terminal state
- **GIVEN** a task is not in `Initializing`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the system rejects the request with an error whose `field` is `status.state`, whose `type` is `invalid`, and whose `message` is `resource is in state '<current>', expected 'Initializing'`

### Requirement: Snapshot creation validation
The system SHALL create snapshot resources only when `spec.meshRef` references an existing mesh and resource requests use the same quantity validation as mesh resources.

#### Scenario: Create snapshot with defaults
- **GIVEN** a valid snapshot YAML sets `spec.meshRef` to an existing mesh and omits `spec.resources.memory`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system stores the snapshot with `spec.resources.memory` defaulted to `{"limit": "1Gi", "request": "1Gi"}`
- **AND** sets `status.state` to `Initializing`

#### Scenario: Create scoped snapshot
- **GIVEN** a valid snapshot YAML includes `spec.scope` with any of `stores`, `blueprints`, `tallies`, `definitions`, or `procedures`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system stores a snapshot that captures only the named items at run time

#### Scenario: Reject snapshot with invalid mesh
- **GIVEN** a snapshot YAML has missing or invalid `spec.meshRef`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system rejects the request with an error whose `field` is `spec.meshRef` and whose `type` is `invalid`

### Requirement: Snapshot run execution
The system SHALL run snapshot resources only from `Initializing`, transition through `Running`, and finish in `Succeeded`, `Failed`, or `Unknown`.

#### Scenario: Run snapshot for stable mesh
- **GIVEN** a snapshot is in `Initializing` and the referenced mesh has `status.stable` set to `true`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the system sets `status.state` to `Succeeded`
- **AND** sets a stable, non-empty `status.storageRef`

#### Scenario: Run snapshot for unstable mesh
- **GIVEN** a snapshot is in `Initializing` and the referenced mesh has `status.stable` set to `false`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the system sets `status.state` to `Unknown`
- **AND** sets `status.detail` to a non-empty string

#### Scenario: Reject snapshot run from terminal state
- **GIVEN** a snapshot is not in `Initializing`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the system rejects the request with an error whose `field` is `status.state`, whose `type` is `invalid`, and whose `message` is `resource is in state '<current>', expected 'Initializing'`

### Requirement: Recovery creation validation
The system SHALL create recovery resources only when `spec.meshRef` references an existing mesh, `spec.snapshotRef` references an existing snapshot, and the snapshot belongs to the same mesh.

#### Scenario: Create recovery with defaults
- **GIVEN** a valid recovery YAML sets `spec.meshRef` to an existing mesh, sets `spec.snapshotRef` to a snapshot for that mesh, and omits `spec.resources.memory`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system stores the recovery with `spec.resources.memory` defaulted to `{"limit": "1Gi", "request": "1Gi"}`
- **AND** sets `status.state` to `Initializing`

#### Scenario: Reject recovery with missing snapshot
- **GIVEN** a recovery YAML has missing or invalid `spec.snapshotRef`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system rejects the request with an error whose `field` is `spec.snapshotRef` and whose `type` is `invalid`

#### Scenario: Reject recovery snapshot mesh mismatch
- **GIVEN** a recovery YAML sets `spec.meshRef` to `<Y>` and `spec.snapshotRef` to a snapshot whose `spec.meshRef` is `<X>`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system rejects the request with an error whose `field` is `spec.snapshotRef`, whose `type` is `invalid`, and whose `message` is `snapshot '<name>' belongs to mesh '<X>', not '<Y>'`

### Requirement: Recovery run execution
The system SHALL run recovery resources only from `Initializing`, transition through `Running`, and finish in `Succeeded`, `Failed`, or `Unknown`.

#### Scenario: Run recovery for stable mesh
- **GIVEN** a recovery is in `Initializing` and the referenced mesh has `status.stable` set to `true`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the system sets `status.state` to `Succeeded`

#### Scenario: Run recovery for unstable mesh
- **GIVEN** a recovery is in `Initializing` and the referenced mesh has `status.stable` set to `false`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the system sets `status.state` to `Unknown`
- **AND** sets `status.detail` to a non-empty string

#### Scenario: Reject recovery run from terminal state
- **GIVEN** a recovery is not in `Initializing`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the system rejects the request with an error whose `field` is `status.state`, whose `type` is `invalid`, and whose `message` is `resource is in state '<current>', expected 'Initializing'`

### Requirement: One-shot spec immutability
The system SHALL reject any update to a task, snapshot, or recovery that changes any `spec` field or adds a previously omitted `spec` field.

#### Scenario: Reject changed spec field
- **GIVEN** an existing task, snapshot, or recovery resource
- **WHEN** the user runs `meshctl <kind> update -f <path>` with a changed `spec` value
- **THEN** the system rejects the request with an error whose `type` is `immutable`

#### Scenario: Reject added spec field
- **GIVEN** an existing task, snapshot, or recovery resource whose `spec` omitted an optional field
- **WHEN** the user runs `meshctl <kind> update -f <path>` with that field added
- **THEN** the system rejects the request with an error whose `type` is `immutable`

### Requirement: Snapshot dependency protection
The system SHALL reject deleting a snapshot while one or more recovery resources reference it.

#### Scenario: Reject referenced snapshot delete
- **GIVEN** one or more recovery resources reference a snapshot
- **WHEN** the user runs `meshctl snapshot delete <name>`
- **THEN** the system rejects the request with an error whose `field` is `metadata.name` and whose `type` is `conflict`
- **AND** the error message names the dependent recovery resources

### Requirement: One-shot status output
The system SHALL include only valid one-shot status fields for task, snapshot, and recovery output.

#### Scenario: Include detail only for failed or unknown resources
- **GIVEN** a task, snapshot, or recovery is described or listed
- **WHEN** `status.state` is `Failed` or `Unknown`
- **THEN** `status.detail` may be present
- **AND** `status.detail` is absent for other states

#### Scenario: Include storage reference only for succeeded snapshots
- **GIVEN** a snapshot is described or listed
- **WHEN** `status.state` is `Succeeded`
- **THEN** `status.storageRef` may be present
- **AND** `status.storageRef` is absent for non-snapshot resources and non-succeeded snapshots
