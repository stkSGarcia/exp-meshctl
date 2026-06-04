## ADDED Requirements

### Requirement: Enriched status model
The system SHALL include additional status fields on create, update, and describe responses. `status.stable`, `status.migration` (when active), and `status.instances` are part of the response. (adapts mesh-management/enriched-status-model)

#### Scenario: status.stable on steady state
- **WHEN** no transient conditions (`Scaling`, `Migration`) are active
- **THEN** `status.stable = true`

#### Scenario: status.stable during active migration
- **WHEN** a `Migration` condition is active
- **THEN** `status.stable = false`

#### Scenario: status.stable during scaling
- **WHEN** a `Scaling` condition is active
- **THEN** `status.stable = false`

#### Scenario: status.instances on create
- **WHEN** a mesh is created with `spec.instances > 0`
- **THEN** `status.instances = {"ready":spec.instances,"starting":0,"stopped":0}`

#### Scenario: status.desiredInstancesOnResume absent when running
- **WHEN** the mesh is in `Running` state
- **THEN** `status.desiredInstancesOnResume` is absent from the output

### Requirement: Stability definition
`status.stable` SHALL be `true` only when ALL of the following hold: `Healthy` condition is `"True"`, `PrechecksPassed` condition is `"True"`, `GracefulShutdown` is absent or `"False"`, `Scaling` is absent or `"False"`, and `Migration` is absent or `"False"`. Otherwise `status.stable` SHALL be `false`.

#### Scenario: Stable when all conditions nominal
- **WHEN** `Healthy = "True"`, `PrechecksPassed = "True"`, and `GracefulShutdown`, `Scaling`, `Migration` are all absent
- **THEN** `status.stable = true`

#### Scenario: Not stable when Migration is True
- **WHEN** `Migration` condition has `status = "True"`
- **THEN** `status.stable = false`

#### Scenario: Not stable when GracefulShutdown is True
- **WHEN** `GracefulShutdown` condition has `status = "True"`
- **THEN** `status.stable = false`

#### Scenario: Not stable when Healthy is not True
- **WHEN** `Healthy` condition has `status = "False"`
- **THEN** `status.stable = false`

### Requirement: Migration status in output
When a migration is active, the response SHALL include `status.migration` with `sourceRuntime`, `targetRuntime`, and `stage`. When no migration is active, `status.migration` SHALL be absent.

#### Scenario: status.migration present during active migration
- **WHEN** a migration is in progress
- **THEN** the describe/update response includes `status.migration.sourceRuntime`, `status.migration.targetRuntime`, and `status.migration.stage`

#### Scenario: status.migration absent after completion
- **WHEN** a migration has completed
- **THEN** `status.migration` is absent from the response
