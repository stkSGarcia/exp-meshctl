## MODIFIED Requirements

### Requirement: status.stable computation
`status.stable` SHALL be `true` only when ALL of the following conditions hold:
- `Healthy` condition status is `"True"`.
- `PrechecksPassed` condition status is `"True"`.
- `GracefulShutdown` condition is absent or its status is `"False"`.
- `Scaling` condition is absent or its status is `"False"`.
- `Migration` condition is absent or its status is `"False"`.

If any condition fails, `status.stable` SHALL be `false`.

#### Scenario: stable false when Migration is active
- **WHEN** the `Migration` condition has `status = "True"` and all other stability conditions are satisfied
- **THEN** `status.stable` is `false`

#### Scenario: stable true when Migration is absent
- **WHEN** `Healthy` and `PrechecksPassed` are `"True"`, and `Migration`, `Scaling`, `GracefulShutdown` are all absent
- **THEN** `status.stable` is `true`

#### Scenario: stable true when Migration condition is False
- **WHEN** `Migration` condition has `status = "False"` and all other stability conditions are satisfied
- **THEN** `status.stable` is `true`

---

### Requirement: spec.migration.strategy validation — extended
`spec.migration.strategy` SHALL default to `"FullStop"` when absent. Valid values are `"FullStop"`, `"LiveMigration"`, and `"RollingPatch"`. Any other value SHALL produce an error on `{"field":"spec.migration.strategy","type":"invalid"}`. (adapts `implement-meshctl/mesh-management/migration-strategy-validation-and-default`)

#### Scenario: FullStop still accepted and defaults correctly
- **WHEN** `spec.migration.strategy` is absent or explicitly `"FullStop"`
- **THEN** output has `spec.migration.strategy = "FullStop"` and no error

#### Scenario: Invalid strategy still rejected
- **WHEN** `spec.migration.strategy` is `"RollingUpdate"` or any unrecognized string
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"<msg>"}`
