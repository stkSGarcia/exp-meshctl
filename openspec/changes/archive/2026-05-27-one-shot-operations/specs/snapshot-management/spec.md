## ADDED Requirements

### Requirement: Snapshot resource CRUD operations
The system SHALL support `meshctl snapshot create -f <path>`, `meshctl snapshot list`, `meshctl snapshot describe <name>`, `meshctl snapshot update -f <path>`, and `meshctl snapshot delete <name>` commands with the same name validation and not-found error shape used by mesh resources.

#### Scenario: Create snapshot with valid spec
- **WHEN** user runs `meshctl snapshot create -f snapshot.yaml` with a valid YAML containing a unique name and an existing meshRef
- **THEN** the system SHALL persist the snapshot with `status.state = "Initializing"` and print the full resource as JSON

#### Scenario: Create snapshot fails on missing meshRef
- **WHEN** user runs `meshctl snapshot create -f snapshot.yaml` with a meshRef that does not reference an existing mesh
- **THEN** the system SHALL return an error with `field = "spec.meshRef"` and `type = "invalid"`

#### Scenario: Create snapshot applies default memory resources
- **WHEN** user runs `meshctl snapshot create -f snapshot.yaml` without `spec.resources.memory`
- **THEN** the system SHALL default `spec.resources.memory` to `{"limit": "1Gi", "request": "1Gi"}`

#### Scenario: List snapshots returns sorted array
- **WHEN** user runs `meshctl snapshot list`
- **THEN** the system SHALL print a JSON array of all snapshots sorted by `name` ascending

#### Scenario: Describe returns full snapshot resource
- **WHEN** user runs `meshctl snapshot describe <name>` for an existing snapshot
- **THEN** the system SHALL print the full snapshot resource as JSON

#### Scenario: Delete snapshot succeeds when no recovery references it
- **WHEN** user runs `meshctl snapshot delete <name>` and no recovery resource references that snapshot
- **THEN** the system SHALL remove the snapshot and print a confirmation message

#### Scenario: Delete snapshot is rejected when a recovery references it
- **WHEN** user runs `meshctl snapshot delete <name>` and one or more recovery resources reference that snapshot
- **THEN** the system SHALL return an error with `field = "metadata.name"`, `type = "conflict"`, and a message naming the dependent recovery resources

### Requirement: Snapshot spec is fully immutable after create
The system SHALL reject any update to a snapshot that changes any field in `spec`, including adding a field that was previously absent.

#### Scenario: Update snapshot spec field is rejected
- **WHEN** user runs `meshctl snapshot update -f snapshot.yaml` with any `spec` field changed from the stored value
- **THEN** the system SHALL return one or more errors with `type = "immutable"`

### Requirement: Snapshot run lifecycle
The system SHALL transition a snapshot through `Initializing` → `Running` → terminal state when `meshctl snapshot run <name>` is executed.

#### Scenario: Run snapshot succeeds when mesh is stable
- **WHEN** user runs `meshctl snapshot run <name>` on a snapshot with `status.state = "Initializing"` and the referenced mesh has `status.stable = true`
- **THEN** the system SHALL set `status.state = "Succeeded"` and `status.storageRef` to a stable non-empty string, and print the updated snapshot

#### Scenario: Run snapshot sets Unknown when mesh is unstable
- **WHEN** user runs `meshctl snapshot run <name>` on a snapshot with `status.state = "Initializing"` and the referenced mesh has `status.stable = false`
- **THEN** the system SHALL set `status.state = "Unknown"` and `status.detail` to a non-empty string

#### Scenario: Run snapshot from non-Initializing state is rejected
- **WHEN** user runs `meshctl snapshot run <name>` on a snapshot whose `status.state` is not `"Initializing"`
- **THEN** the system SHALL return an error with `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state '<current>', expected 'Initializing'"`
