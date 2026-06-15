## ADDED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology
> Extends: vault-resource-management/add-vault-resource-management

### Requirement: One-shot resource command surface
The system SHALL expose `create -f <path>`, `list`, `describe <name>`, `update -f <path>`, `delete <name>`, and `run <name>` operations for `task`, `snapshot`, and `recovery` resources through `meshctl` (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-cli-command-surface).

#### Scenario: Create one-shot resource from YAML
- **GIVEN** a valid YAML definition for a `task`, `snapshot`, or `recovery`
- **WHEN** the user runs `meshctl <kind> create -f <path>`
- **THEN** the system stores the resource and prints the full resource as JSON.

#### Scenario: List one-shot resources by name
- **GIVEN** multiple resources exist for a one-shot kind
- **WHEN** the user runs `meshctl <kind> list`
- **THEN** the system prints a JSON array sorted by `metadata.name` ascending.

#### Scenario: Describe one-shot resource
- **GIVEN** a resource exists for a one-shot kind
- **WHEN** the user runs `meshctl <kind> describe <name>`
- **THEN** the system prints the full resource as JSON.

### Requirement: Shared one-shot resource identity and errors
The system SHALL validate `metadata.name` for `task`, `snapshot`, and `recovery` using the same name rules and not-found error shape as mesh resources, and SHALL use the established JSON error format for validation failures (adapts vault-resource-management/add-vault-resource-management/vault-error-output).

#### Scenario: Reject invalid one-shot name
- **GIVEN** a one-shot resource definition has an invalid `metadata.name`
- **WHEN** the user runs `meshctl <kind> create -f <path>`
- **THEN** the system prints a JSON error using the documented field/type format.

#### Scenario: Report missing one-shot resource
- **GIVEN** no resource exists with the requested name
- **WHEN** the user runs `meshctl <kind> describe <name>`, `meshctl <kind> update -f <path>`, `meshctl <kind> delete <name>`, or `meshctl <kind> run <name>`
- **THEN** the system prints a `metadata.name` error with type `not_found`.

### Requirement: Task creation validation
The system SHALL require `task.spec.meshRef` to reference an existing mesh and SHALL require exactly one non-empty value from `task.spec.inline` or `task.spec.bundleRef` before creating a task (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-field-validation).

#### Scenario: Reject task with invalid mesh reference
- **GIVEN** a task definition has a missing or invalid `spec.meshRef`
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system prints an error with `field = "spec.meshRef"` and `type = "invalid"`.

#### Scenario: Reject task without exactly one command source
- **GIVEN** a task definition sets neither `spec.inline` nor `spec.bundleRef`, sets both fields, or sets an empty value
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the system prints an error with `field = "spec"`, `type = "invalid"`, and `message = "exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`.

#### Scenario: Create valid task
- **GIVEN** a task definition references an existing mesh and sets exactly one non-empty command source
- **WHEN** the user runs `meshctl task create -f <path>`
- **THEN** the stored task has `status.state = "Initializing"`.

### Requirement: Snapshot creation validation
The system SHALL require `snapshot.spec.meshRef` to reference an existing mesh, SHALL validate `spec.resources.memory` and `spec.resources.cpu` with the same resource quantity rules as mesh resources, and SHALL default `spec.resources.memory` to `{"limit": "1Gi", "request": "1Gi"}` when omitted (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-field-validation).

#### Scenario: Reject snapshot with invalid mesh reference
- **GIVEN** a snapshot definition has a missing or invalid `spec.meshRef`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system prints an error with `field = "spec.meshRef"` and `type = "invalid"`.

#### Scenario: Create snapshot with default memory
- **GIVEN** a valid snapshot definition omits `spec.resources.memory`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the stored snapshot includes `spec.resources.memory = {"limit": "1Gi", "request": "1Gi"}` and `status.state = "Initializing"`.

#### Scenario: Create scoped snapshot
- **GIVEN** a valid snapshot definition includes `spec.scope` with any of `stores`, `blueprints`, `tallies`, `definitions`, or `procedures`
- **WHEN** the user runs `meshctl snapshot create -f <path>`
- **THEN** the system stores the scope so the snapshot captures only the named items.

### Requirement: Recovery creation validation
The system SHALL require `recovery.spec.meshRef` to reference an existing mesh, `recovery.spec.snapshotRef` to reference an existing snapshot, and the referenced snapshot's `spec.meshRef` to match the recovery's `spec.meshRef`.

#### Scenario: Reject recovery with invalid mesh reference
- **GIVEN** a recovery definition has a missing or invalid `spec.meshRef`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system prints an error with `field = "spec.meshRef"` and `type = "invalid"`.

#### Scenario: Reject recovery with missing snapshot reference
- **GIVEN** a recovery definition has a missing or invalid `spec.snapshotRef`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system prints an error with `field = "spec.snapshotRef"` and `type = "invalid"`.

#### Scenario: Reject recovery with mismatched snapshot mesh
- **GIVEN** a recovery references mesh `<Y>` and snapshot `<name>` belongs to mesh `<X>`
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the system prints an error with `field = "spec.snapshotRef"`, `type = "invalid"`, and `message = "snapshot '<name>' belongs to mesh '<X>', not '<Y>'"`.

#### Scenario: Create valid recovery
- **GIVEN** a recovery definition references an existing mesh and a snapshot from that same mesh
- **WHEN** the user runs `meshctl recovery create -f <path>`
- **THEN** the stored recovery has `status.state = "Initializing"`.

### Requirement: Task run lifecycle
The system SHALL run tasks only from `status.state = "Initializing"` and SHALL transition a task through `Running` to `Succeeded` or `Failed`.

#### Scenario: Reject task run from non-initial state
- **GIVEN** a task has `status.state` other than `Initializing`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the system prints an error with `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state '<current>', expected 'Initializing'"`.

#### Scenario: Succeed inline task
- **GIVEN** a task in `Initializing` has `spec.inline` with no line starting with `FAIL:`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the task transitions through `Running` to `Succeeded`.

#### Scenario: Fail inline task at failing command
- **GIVEN** a task in `Initializing` has `spec.inline` and line `<index>` starts with `FAIL:`
- **WHEN** the user runs `meshctl task run <name>`
- **THEN** the task transitions through `Running` to `Failed` and sets `status.detail = "command <index> failed: <reason>"`.

### Requirement: Snapshot run lifecycle
The system SHALL run snapshots only from `status.state = "Initializing"` and SHALL transition a snapshot through `Running` to `Succeeded`, `Failed`, or `Unknown`.

#### Scenario: Reject snapshot run from non-initial state
- **GIVEN** a snapshot has `status.state` other than `Initializing`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the system prints an error with `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state '<current>', expected 'Initializing'"`.

#### Scenario: Succeed snapshot for stable mesh
- **GIVEN** a snapshot in `Initializing` references a mesh with `status.stable = true`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the snapshot transitions through `Running` to `Succeeded` and sets a stable, non-empty `status.storageRef`.

#### Scenario: Mark snapshot unknown for unstable mesh
- **GIVEN** a snapshot in `Initializing` references a mesh with `status.stable = false`
- **WHEN** the user runs `meshctl snapshot run <name>`
- **THEN** the snapshot transitions through `Running` to `Unknown` and sets a non-empty `status.detail`.

### Requirement: Recovery run lifecycle
The system SHALL run recoveries only from `status.state = "Initializing"` and SHALL transition a recovery through `Running` to `Succeeded`, `Failed`, or `Unknown`.

#### Scenario: Reject recovery run from non-initial state
- **GIVEN** a recovery has `status.state` other than `Initializing`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the system prints an error with `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state '<current>', expected 'Initializing'"`.

#### Scenario: Succeed recovery for stable mesh
- **GIVEN** a recovery in `Initializing` references a mesh with `status.stable = true`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the recovery transitions through `Running` to `Succeeded`.

#### Scenario: Mark recovery unknown for unstable mesh
- **GIVEN** a recovery in `Initializing` references a mesh with `status.stable = false`
- **WHEN** the user runs `meshctl recovery run <name>`
- **THEN** the recovery transitions through `Running` to `Unknown` and sets a non-empty `status.detail`.

### Requirement: One-shot spec immutability
The system SHALL reject any `task`, `snapshot`, or `recovery` update that changes the resource `spec`, including adding a previously omitted spec field, using error type `immutable` (adapts vault-resource-management/add-vault-resource-management/vault-immutable-fields).

#### Scenario: Reject one-shot spec change
- **GIVEN** a one-shot resource already exists
- **WHEN** the user runs `meshctl <kind> update -f <path>` with any changed, added, or removed `spec` field
- **THEN** the system prints one or more errors with `type = "immutable"`.

#### Scenario: Accept one-shot metadata or status update without spec change
- **GIVEN** a one-shot resource already exists
- **WHEN** the user runs `meshctl <kind> update -f <path>` without changing `spec`
- **THEN** the system applies the allowed changes and prints the updated resource as JSON.

### Requirement: Snapshot dependency protection
The system SHALL reject `snapshot delete` when one or more recoveries reference that snapshot, using `field = "metadata.name"` and `type = "conflict"` (adapts mesh-resource-management/add-vault-resource-management/mesh-deletion-dependency-conflicts).

#### Scenario: Reject deleting referenced snapshot
- **GIVEN** one or more recoveries reference snapshot `<name>` through `spec.snapshotRef`
- **WHEN** the user runs `meshctl snapshot delete <name>`
- **THEN** the system prints an error with `field = "metadata.name"` and `type = "conflict"` whose message names the dependent recoveries.

#### Scenario: Delete unreferenced snapshot
- **GIVEN** a snapshot exists and no recovery references it
- **WHEN** the user runs `meshctl snapshot delete <name>`
- **THEN** the system deletes the snapshot and prints a JSON confirmation.

### Requirement: One-shot status output
The system SHALL use exact phase names `Initializing`, `Running`, `Succeeded`, `Failed`, and `Unknown`, SHALL include `status.detail` only for `Failed` or `Unknown`, and SHALL include `status.storageRef` only for a succeeded snapshot.

#### Scenario: Print terminal task status
- **GIVEN** a task has finished running
- **WHEN** the user describes the task
- **THEN** the JSON output uses `Succeeded` or `Failed`, with `status.detail` present only for `Failed`.

#### Scenario: Print snapshot storage reference
- **GIVEN** a snapshot run succeeded
- **WHEN** the user describes the snapshot
- **THEN** the JSON output includes a stable, non-empty `status.storageRef`.

#### Scenario: Omit detail outside failure and unknown states
- **GIVEN** a one-shot resource is in `Initializing`, `Running`, or `Succeeded`
- **WHEN** the system prints the resource
- **THEN** `status.detail` is absent.
