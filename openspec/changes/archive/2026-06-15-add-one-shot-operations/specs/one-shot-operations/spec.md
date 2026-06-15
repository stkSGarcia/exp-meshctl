## ADDED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology
> Extends: vault-resource-management/add-vault-resource-management
> Extends: mesh-resource-management/add-vault-resource-management

### Requirement: One-shot command surface
The system SHALL expose `task`, `snapshot`, and `recovery` operations through `meshctl.py` with `create -f <path>`, `list`, `describe <name>`, `update -f <path>`, `delete <name>`, and `run <name>` commands for each kind (adapts `mesh-resource-management/add-mesh-lifecycle-topology/mesh-cli-command-surface`).

#### Scenario: List resources in name order
- **GIVEN** multiple resources exist for a one-shot kind
- **WHEN** the user runs `meshctl <kind> list`
- **THEN** the command prints a JSON array sorted by `metadata.name` ascending

#### Scenario: Describe resource
- **GIVEN** a one-shot resource exists
- **WHEN** the user runs `meshctl <kind> describe <name>`
- **THEN** the command prints the full JSON resource

### Requirement: Shared one-shot metadata and status
The system SHALL validate `metadata.name` for `task`, `snapshot`, and `recovery` using the same rules and not-found behavior as existing mesh resources, and SHALL set `status.state` to `Initializing` on successful create.

#### Scenario: Create initializes status
- **GIVEN** a valid YAML document for `task`, `snapshot`, or `recovery`
- **WHEN** the user runs `meshctl <kind> create -f <path>`
- **THEN** the stored resource has `status.state` set to `Initializing`

### Requirement: Task spec validation
The system SHALL require `task.spec.meshRef` to reference an existing mesh and SHALL require exactly one non-empty source field from `task.spec.inline` or `task.spec.bundleRef`.

#### Scenario: Missing mesh reference is rejected
- **GIVEN** a task YAML document with a missing or invalid `spec.meshRef`
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the command fails with an error containing `field = "spec.meshRef"` and `type = "invalid"`

#### Scenario: Task source exclusivity is enforced
- **GIVEN** a task YAML document with neither source, both sources, or an empty source value
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the command fails with an error containing `field = "spec"`, `type = "invalid"`, and `message = "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`

### Requirement: Snapshot spec validation and defaulting
The system SHALL require `snapshot.spec.meshRef` to reference an existing mesh, SHALL validate snapshot CPU and memory resource quantities using the same formats as mesh resource quantities, and SHALL default `snapshot.spec.resources.memory` to `{"limit": "1Gi", "request": "1Gi"}` when omitted.

#### Scenario: Snapshot default memory
- **GIVEN** a valid snapshot YAML document without `spec.resources.memory`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the stored resource has `spec.resources.memory` set to `{"limit": "1Gi", "request": "1Gi"}`

#### Scenario: Snapshot scope is optional
- **GIVEN** a valid snapshot YAML document without `spec.scope`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the snapshot represents all mesh data

### Requirement: Recovery spec validation and defaulting
The system SHALL require `recovery.spec.meshRef` to reference an existing mesh, SHALL require `recovery.spec.snapshotRef` to reference an existing snapshot, SHALL reject snapshots that belong to a different mesh, and SHALL default `recovery.spec.resources.memory` to `{"limit": "1Gi", "request": "1Gi"}` when omitted.

#### Scenario: Missing snapshot reference is rejected
- **GIVEN** a recovery YAML document with a missing or invalid `spec.snapshotRef`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the command fails with an error containing `field = "spec.snapshotRef"` and `type = "invalid"`

#### Scenario: Snapshot mesh mismatch is rejected
- **GIVEN** a recovery YAML document whose `spec.snapshotRef` points to snapshot `<name>` with `spec.meshRef = "<X>"`
- **AND** the recovery document has `spec.meshRef = "<Y>"`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the command fails with an error containing `field = "spec.snapshotRef"`, `type = "invalid"`, and `message = "snapshot '<name>' belongs to mesh '<X>', not '<Y>'"`

### Requirement: Scope field semantics
The system SHALL support optional `scope` objects for snapshots and recoveries with the keys `stores`, `blueprints`, `tallies`, `definitions`, and `procedures`; omitted scope SHALL mean capture or restore all snapshot data.

#### Scenario: Scoped snapshot captures named items
- **GIVEN** a valid snapshot YAML document with `spec.scope`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the snapshot captures only the named items from the scope

#### Scenario: Recovery without scope restores all data
- **GIVEN** a valid recovery YAML document without `spec.scope`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the recovery restores all snapshot data

### Requirement: One-shot spec immutability
The system SHALL reject `task`, `snapshot`, and `recovery` updates that change the `spec` section, including changing an existing field or adding a previously omitted field, with error `type = "immutable"` (adapts `vault-resource-management/add-vault-resource-management/vault-immutable-fields`).

#### Scenario: Changed spec field is rejected
- **GIVEN** a one-shot resource exists
- **WHEN** the user runs `meshctl <kind> update -f <path>` with any changed `spec` field
- **THEN** the command fails with an error containing `type = "immutable"`

#### Scenario: Added spec field is rejected
- **GIVEN** a one-shot resource exists with an omitted optional `spec` field
- **WHEN** the user runs `meshctl <kind> update -f <path>` with that `spec` field added
- **THEN** the command fails with an error containing `type = "immutable"`

### Requirement: Run state validation
The system SHALL allow `task`, `snapshot`, and `recovery` resources to run only from `status.state = "Initializing"` and SHALL reject run attempts from any other state with a `status.state` validation error.

#### Scenario: Run from non-initializing state is rejected
- **GIVEN** a one-shot resource has `status.state = "<current>"` where `<current>` is not `Initializing`
- **WHEN** the user runs `meshctl <kind> run <name>`
- **THEN** the command fails with an error containing `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state '<current>', expected 'Initializing'"`

### Requirement: Task run execution
The system SHALL run inline task content by treating each line as one command, SHALL execute lines in order without rolling back earlier successful commands, SHALL transition through `Running`, and SHALL finish in `Succeeded` or `Failed`.

#### Scenario: Inline task succeeds
- **GIVEN** a task with inline content that has no line starting with `FAIL:`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the task transitions through `Running` and finishes with `status.state = "Succeeded"`

#### Scenario: Inline task fails on FAIL line
- **GIVEN** a task with inline line `<index>` starting with `FAIL:<reason>`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the task finishes with `status.state = "Failed"` and `status.detail = "command <index> failed: <reason>"`

### Requirement: Snapshot run execution
The system SHALL transition snapshots through `Running` and finish in `Succeeded`, `Failed`, or `Unknown`; when the referenced mesh has `status.stable = false` at run time, the snapshot SHALL finish in `Unknown` with a non-empty `status.detail`.

#### Scenario: Stable mesh snapshot succeeds
- **GIVEN** a snapshot references a mesh whose `status.stable` is not false at run time
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the snapshot finishes with `status.state = "Succeeded"` and a stable non-empty `status.storageRef`

#### Scenario: Unstable mesh snapshot is unknown
- **GIVEN** a snapshot references a mesh with `status.stable = false` at run time
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the snapshot finishes with `status.state = "Unknown"` and a non-empty `status.detail`

### Requirement: Recovery run execution
The system SHALL transition recoveries through `Running` and finish in `Succeeded`, `Failed`, or `Unknown`; when the referenced mesh has `status.stable = false` at run time, the recovery SHALL finish in `Unknown` with a non-empty `status.detail`.

#### Scenario: Stable mesh recovery succeeds
- **GIVEN** a recovery references a mesh whose `status.stable` is not false at run time
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the recovery finishes with `status.state = "Succeeded"`

#### Scenario: Unstable mesh recovery is unknown
- **GIVEN** a recovery references a mesh with `status.stable = false` at run time
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the recovery finishes with `status.state = "Unknown"` and a non-empty `status.detail`

### Requirement: Snapshot dependency protection
The system SHALL reject `snapshot delete` when one or more recovery resources reference that snapshot, with `field = "metadata.name"`, `type = "conflict"`, and a message naming the dependent recovery resources.

#### Scenario: Referenced snapshot delete is rejected
- **GIVEN** one or more recovery resources reference snapshot `<name>`
- **WHEN** the user runs `meshctl snapshot delete <name>`
- **THEN** the command fails with an error containing `field = "metadata.name"`, `type = "conflict"`, and a message naming the dependent recoveries

### Requirement: One-shot status output fields
The system SHALL include `status.state` as the current phase, SHALL include `status.detail` only for `Failed` or `Unknown` states, and SHALL include `status.storageRef` only on a succeeded snapshot.

#### Scenario: Failed task has detail
- **GIVEN** a task run fails
- **WHEN** the user describes the task
- **THEN** the output includes `status.state = "Failed"` and `status.detail`

#### Scenario: Succeeded recovery omits storageRef
- **GIVEN** a recovery run succeeds
- **WHEN** the user describes the recovery
- **THEN** the output includes `status.state = "Succeeded"` and omits `status.storageRef`
