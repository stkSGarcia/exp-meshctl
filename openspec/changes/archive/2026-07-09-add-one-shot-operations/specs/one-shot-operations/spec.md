## ADDED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology
> Extends: mesh-resource-management/add-vault-resource-management

### Requirement: One-shot command surface
The system SHALL expose `create -f <path>`, `list`, `describe <name>`, `update -f <path>`, `delete <name>`, and `run <name>` commands for each of `task`, `snapshot`, and `recovery`.

#### Scenario: Resource commands are available
- **WHEN** a user invokes a supported command for `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL route the command for that resource kind and operation.

#### Scenario: Listed resources are sorted
- **WHEN** a user lists `task`, `snapshot`, or `recovery` resources
- **THEN** the system SHALL print a JSON array sorted by `metadata.name` ascending.

#### Scenario: Described resource is complete
- **WHEN** a user describes an existing `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL print the full resource as JSON.

### Requirement: Shared one-shot resource metadata
The system SHALL validate `metadata.name` for `task`, `snapshot`, and `recovery` resources using the same rules and not-found error shape as mesh resources.

#### Scenario: Missing one-shot resource
- **WHEN** a user describes, updates, deletes, or runs a missing `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL report the same not-found error shape used for missing mesh resources.

### Requirement: Task creation
The system SHALL create `task` resources with required `spec.meshRef`, exactly one non-empty command source from `spec.inline` or `spec.bundleRef`, and `status.state` set to `Initializing`.

#### Scenario: Task references missing mesh
- **WHEN** a user creates a task whose `spec.meshRef` does not reference an existing mesh
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Task command source is invalid
- **WHEN** a user creates a task without exactly one non-empty value among `spec.inline` and `spec.bundleRef`
- **THEN** the system SHALL report field `spec` with type `invalid` and message `exactly one of 'spec.inline' or 'spec.bundleRef' must be set`.

#### Scenario: Task create initializes status
- **WHEN** a user creates a valid task
- **THEN** the system SHALL persist the task with `status.state` set to `Initializing`.

### Requirement: Task execution lifecycle
The system SHALL run tasks only from `Initializing`, transition through `Running`, and finish in `Succeeded` or `Failed`.

#### Scenario: Task run rejects non-initializing state
- **WHEN** a user runs a task whose `status.state` is not `Initializing`
- **THEN** the system SHALL report field `status.state` with type `invalid` and message `resource is in state '<current>', expected 'Initializing'`.

#### Scenario: Inline task succeeds
- **WHEN** a user runs a task whose `spec.inline` contains no line starting with `FAIL:`
- **THEN** the system SHALL set `status.state` to `Succeeded`.

#### Scenario: Inline task fails
- **WHEN** a user runs a task whose `spec.inline` has line `<index>` starting with `FAIL:`
- **THEN** the system SHALL set `status.state` to `Failed` and `status.detail` to `command <index> failed: <reason>`.

#### Scenario: Inline task preserves prior effects
- **WHEN** a user runs a task and a later inline command fails
- **THEN** the system SHALL NOT roll back earlier successful command lines.

### Requirement: Snapshot creation
The system SHALL create `snapshot` resources with required `spec.meshRef`, optional storage fields, optional scope fields, validated resource quantities, default memory resources, and `status.state` set to `Initializing`.

#### Scenario: Snapshot references missing mesh
- **WHEN** a user creates a snapshot whose `spec.meshRef` does not reference an existing mesh
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Snapshot validates resources
- **WHEN** a user creates a snapshot with memory or CPU resource quantities
- **THEN** the system SHALL validate the quantities using the same formats and validation rules as mesh resource quantities.

#### Scenario: Snapshot defaults memory resources
- **WHEN** a user creates a snapshot without `spec.resources.memory`
- **THEN** the system SHALL persist `spec.resources.memory` as `{"limit": "1Gi", "request": "1Gi"}`.

#### Scenario: Snapshot scope is omitted
- **WHEN** a user creates a snapshot without `spec.scope`
- **THEN** the snapshot SHALL capture all data.

#### Scenario: Snapshot scope is present
- **WHEN** a user creates a snapshot with `spec.scope`
- **THEN** the snapshot SHALL capture only the named `stores`, `blueprints`, `tallies`, `definitions`, and `procedures` entries.

### Requirement: Snapshot execution lifecycle
The system SHALL run snapshots only from `Initializing`, transition through `Running`, and finish in `Succeeded`, `Failed`, or `Unknown`.

#### Scenario: Snapshot run rejects non-initializing state
- **WHEN** a user runs a snapshot whose `status.state` is not `Initializing`
- **THEN** the system SHALL report field `status.state` with type `invalid` and message `resource is in state '<current>', expected 'Initializing'`.

#### Scenario: Snapshot run succeeds for stable mesh
- **WHEN** a user runs a snapshot whose referenced mesh has `status.stable` set to `true`
- **THEN** the system SHALL set `status.state` to `Succeeded` and set a stable, non-empty `status.storageRef`.

#### Scenario: Snapshot run is unknown for unstable mesh
- **WHEN** a user runs a snapshot whose referenced mesh has `status.stable` set to `false`
- **THEN** the system SHALL set `status.state` to `Unknown` and `status.detail` to a non-empty string.

### Requirement: Recovery creation
The system SHALL create `recovery` resources with required `spec.meshRef`, required `spec.snapshotRef`, optional scope fields, validated resource quantities, default memory resources, matching snapshot ownership, and `status.state` set to `Initializing`.

#### Scenario: Recovery references missing mesh
- **WHEN** a user creates a recovery whose `spec.meshRef` does not reference an existing mesh
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Recovery references missing snapshot
- **WHEN** a user creates a recovery whose `spec.snapshotRef` does not reference an existing snapshot
- **THEN** the system SHALL report field `spec.snapshotRef` with type `invalid`.

#### Scenario: Recovery snapshot belongs to different mesh
- **WHEN** a user creates a recovery with `spec.meshRef` `<Y>` and `spec.snapshotRef` `<name>` whose snapshot has `spec.meshRef` `<X>`
- **THEN** the system SHALL report field `spec.snapshotRef` with type `invalid` and message `snapshot '<name>' belongs to mesh '<X>', not '<Y>'`.

#### Scenario: Recovery defaults memory resources
- **WHEN** a user creates a recovery without `spec.resources.memory`
- **THEN** the system SHALL persist `spec.resources.memory` as `{"limit": "1Gi", "request": "1Gi"}`.

#### Scenario: Recovery scope is omitted
- **WHEN** a user creates a recovery without `spec.scope`
- **THEN** the recovery SHALL restore all snapshot data.

### Requirement: Recovery execution lifecycle
The system SHALL run recoveries only from `Initializing`, transition through `Running`, and finish in `Succeeded`, `Failed`, or `Unknown`.

#### Scenario: Recovery run rejects non-initializing state
- **WHEN** a user runs a recovery whose `status.state` is not `Initializing`
- **THEN** the system SHALL report field `status.state` with type `invalid` and message `resource is in state '<current>', expected 'Initializing'`.

#### Scenario: Recovery run succeeds for stable mesh
- **WHEN** a user runs a recovery whose referenced mesh has `status.stable` set to `true`
- **THEN** the system SHALL set `status.state` to `Succeeded`.

#### Scenario: Recovery run is unknown for unstable mesh
- **WHEN** a user runs a recovery whose referenced mesh has `status.stable` set to `false`
- **THEN** the system SHALL set `status.state` to `Unknown` and `status.detail` to a non-empty string.

### Requirement: One-shot spec immutability
The system SHALL reject updates to `task`, `snapshot`, and `recovery` resources that change any existing `spec` field or add any previously omitted `spec` field. (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-network-storage)

#### Scenario: Existing spec field changes
- **WHEN** an update changes any persisted `spec` field for a `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL report type `immutable` and SHALL NOT persist the update.

#### Scenario: Omitted spec field is added
- **WHEN** an update adds a `spec` field that was omitted when a `task`, `snapshot`, or `recovery` was created
- **THEN** the system SHALL report type `immutable` and SHALL NOT persist the update.

### Requirement: Snapshot dependency protection
The system SHALL reject `snapshot delete` when one or more recoveries reference that snapshot through `spec.snapshotRef`.

#### Scenario: Snapshot has dependent recoveries
- **WHEN** a user deletes a snapshot referenced by one or more recoveries
- **THEN** the system SHALL report field `metadata.name` with type `conflict` and a message naming the dependent recovery resources.

### Requirement: One-shot status output
The system SHALL use exact phase names `Initializing`, `Running`, `Succeeded`, `Failed`, and `Unknown`, and SHALL include status fields only when valid for the current terminal state.

#### Scenario: Failed or unknown detail
- **WHEN** a `task`, `snapshot`, or `recovery` finishes in `Failed` or `Unknown`
- **THEN** the system MAY include `status.detail` and SHALL only use `Unknown` for snapshot and recovery resources.

#### Scenario: Snapshot storage reference
- **WHEN** a snapshot finishes in `Succeeded`
- **THEN** the system SHALL include `status.storageRef`.

#### Scenario: Non-snapshot storage reference is omitted
- **WHEN** a task or recovery is printed
- **THEN** the system SHALL omit `status.storageRef`.
