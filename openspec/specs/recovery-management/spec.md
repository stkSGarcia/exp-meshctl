## Purpose

Defines the requirements for recovery resource management in meshctl, including CRUD operations, immutability constraints, and the run lifecycle.

## Requirements

### Requirement: Recovery resource CRUD operations
The system SHALL support `meshctl recovery create -f <path>`, `meshctl recovery list`, `meshctl recovery describe <name>`, `meshctl recovery update -f <path>`, and `meshctl recovery delete <name>` commands with the same name validation and not-found error shape used by mesh resources.

#### Scenario: Create recovery with valid spec
- **WHEN** user runs `meshctl recovery create -f recovery.yaml` with a valid YAML containing a unique name, an existing meshRef, and a snapshotRef whose mesh matches the recovery's meshRef
- **THEN** the system SHALL persist the recovery with `status.state = "Initializing"` and print the full resource as JSON

#### Scenario: Create recovery fails on missing meshRef
- **WHEN** user runs `meshctl recovery create -f recovery.yaml` with a meshRef that does not reference an existing mesh
- **THEN** the system SHALL return an error with `field = "spec.meshRef"` and `type = "invalid"`

#### Scenario: Create recovery fails on missing snapshotRef
- **WHEN** user runs `meshctl recovery create -f recovery.yaml` with a snapshotRef that does not reference an existing snapshot
- **THEN** the system SHALL return an error with `field = "spec.snapshotRef"` and `type = "invalid"`

#### Scenario: Create recovery fails when snapshot belongs to a different mesh
- **WHEN** user runs `meshctl recovery create -f recovery.yaml` where the referenced snapshot's `spec.meshRef` does not match the recovery's `spec.meshRef`
- **THEN** the system SHALL return an error with `field = "spec.snapshotRef"`, `type = "invalid"`, and `message = "snapshot '<name>' belongs to mesh '<X>', not '<Y>'"`

#### Scenario: Create recovery applies default memory resources
- **WHEN** user runs `meshctl recovery create -f recovery.yaml` without `spec.resources.memory`
- **THEN** the system SHALL default `spec.resources.memory` to `{"limit": "1Gi", "request": "1Gi"}`

#### Scenario: List recoveries returns sorted array
- **WHEN** user runs `meshctl recovery list`
- **THEN** the system SHALL print a JSON array of all recoveries sorted by `name` ascending

#### Scenario: Describe returns full recovery resource
- **WHEN** user runs `meshctl recovery describe <name>` for an existing recovery
- **THEN** the system SHALL print the full recovery resource as JSON

#### Scenario: Delete removes the recovery
- **WHEN** user runs `meshctl recovery delete <name>` for an existing recovery
- **THEN** the system SHALL remove the recovery and print a confirmation message

### Requirement: Recovery spec is fully immutable after create
The system SHALL reject any update to a recovery that changes any field in `spec`, including adding a field that was previously absent.

#### Scenario: Update recovery spec field is rejected
- **WHEN** user runs `meshctl recovery update -f recovery.yaml` with any `spec` field changed from the stored value
- **THEN** the system SHALL return one or more errors with `type = "immutable"`

### Requirement: Recovery run lifecycle
The system SHALL transition a recovery through `Initializing` → `Running` → terminal state when `meshctl recovery run <name>` is executed.

#### Scenario: Run recovery succeeds when mesh is stable
- **WHEN** user runs `meshctl recovery run <name>` on a recovery with `status.state = "Initializing"` and the referenced mesh has `status.stable = true`
- **THEN** the system SHALL set `status.state = "Succeeded"` and print the updated recovery

#### Scenario: Run recovery sets Unknown when mesh is unstable
- **WHEN** user runs `meshctl recovery run <name>` on a recovery with `status.state = "Initializing"` and the referenced mesh has `status.stable = false`
- **THEN** the system SHALL set `status.state = "Unknown"` and `status.detail` to a non-empty string

#### Scenario: Run recovery from non-Initializing state is rejected
- **WHEN** user runs `meshctl recovery run <name>` on a recovery whose `status.state` is not `"Initializing"`
- **THEN** the system SHALL return an error with `field = "status.state"`, `type = "invalid"`, and `message = "resource is in state '<current>', expected 'Initializing'"`
