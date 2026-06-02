# mesh-management Delta Specification

## MODIFIED Requirements

### Requirement: Migration strategy validation and default
`spec.migration.strategy` SHALL default to `"FullStop"`. It SHALL accept `"FullStop"`, `"LiveMigration"`, and `"RollingPatch"`. Any other value SHALL produce an invalid error.

#### Scenario: Migration strategy defaults to FullStop
- **WHEN** `spec.migration.strategy` is not specified
- **THEN** output has `spec.migration.strategy = "FullStop"`

#### Scenario: FullStop strategy accepted
- **WHEN** `spec.migration.strategy` is `"FullStop"`
- **THEN** the strategy is accepted without errors

#### Scenario: LiveMigration strategy accepted
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and `spec.regions` is not configured
- **THEN** the strategy is accepted without errors

#### Scenario: RollingPatch strategy accepted
- **WHEN** `spec.migration.strategy` is `"RollingPatch"`
- **THEN** the strategy is accepted (subject to version-change rules)

#### Scenario: Invalid migration strategy rejected
- **WHEN** `spec.migration.strategy` is `"RollingUpdate"` or any other unrecognized value
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"<msg>"}`

---

### Requirement: Enriched status model
`status.stable` SHALL be `true` only when ALL of the following hold:

- `Healthy` condition has `status = "True"`
- `PrechecksPassed` condition has `status = "True"`
- `GracefulShutdown` condition is absent or has `status = "False"`
- `Scaling` condition is absent or has `status = "False"`
- `Migration` condition is absent or has `status = "False"`

Otherwise `status.stable` SHALL be `false`.

#### Scenario: status.stable on steady state
- **WHEN** `Healthy` and `PrechecksPassed` are `"True"` and `GracefulShutdown`, `Scaling`, and `Migration` are absent
- **THEN** `status.stable = true`

#### Scenario: status.stable during transition
- **WHEN** a transient condition (`Scaling`, `Migration`) is active
- **THEN** `status.stable = false`

#### Scenario: status.instances on create
- **WHEN** a mesh is created with `spec.instances > 0`
- **THEN** `status.instances = {"ready":spec.instances,"starting":0,"stopped":0}`

#### Scenario: status.desiredInstancesOnResume absent when running
- **WHEN** the mesh is in `Running` state
- **THEN** `status.desiredInstancesOnResume` is absent from the output

#### Scenario: Stable false when Migration is active
- **WHEN** `Migration` condition is present with `status = "True"`
- **THEN** `status.stable = false`

