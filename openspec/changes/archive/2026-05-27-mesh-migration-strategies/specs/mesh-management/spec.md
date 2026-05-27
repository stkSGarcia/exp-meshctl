## MODIFIED Requirements

### Requirement: Migration strategy validation and default
`spec.migration.strategy` SHALL default to `"FullStop"`. It SHALL accept `"FullStop"`, `"LiveMigration"`, and `"RollingPatch"`. Any other value SHALL produce an invalid error.

#### Scenario: Migration strategy defaults to FullStop
- **WHEN** `spec.migration.strategy` is not specified
- **THEN** output has `spec.migration.strategy = "FullStop"`

#### Scenario: FullStop accepted
- **WHEN** `spec.migration.strategy` is `"FullStop"`
- **THEN** the value is accepted

#### Scenario: LiveMigration accepted
- **WHEN** `spec.migration.strategy` is `"LiveMigration"`
- **THEN** the value is accepted

#### Scenario: RollingPatch accepted
- **WHEN** `spec.migration.strategy` is `"RollingPatch"`
- **THEN** the value is accepted

#### Scenario: Invalid migration strategy rejected
- **WHEN** `spec.migration.strategy` is any value other than `"FullStop"`, `"LiveMigration"`, or `"RollingPatch"`
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"<msg>"}`

---

### Requirement: Stability formula
`status.stable` SHALL be `true` only when ALL of the following are true:
- `Healthy` condition has `status = "True"`
- `PrechecksPassed` condition has `status = "True"`
- `GracefulShutdown` condition is absent or has `status = "False"`
- `Scaling` condition is absent or has `status = "False"`
- `Migration` condition is absent or has `status = "False"`

#### Scenario: Stable when no transient conditions active
- **WHEN** `Healthy` and `PrechecksPassed` are `"True"`, and `GracefulShutdown`, `Scaling`, and `Migration` are absent or `"False"`
- **THEN** `status.stable = true`

#### Scenario: Unstable during active migration
- **WHEN** the `Migration` condition has `status = "True"`
- **THEN** `status.stable = false`

#### Scenario: Unstable during scaling
- **WHEN** the `Scaling` condition has `status = "True"`
- **THEN** `status.stable = false`

#### Scenario: Unstable when Healthy is False
- **WHEN** the `Healthy` condition has `status = "False"`
- **THEN** `status.stable = false`
