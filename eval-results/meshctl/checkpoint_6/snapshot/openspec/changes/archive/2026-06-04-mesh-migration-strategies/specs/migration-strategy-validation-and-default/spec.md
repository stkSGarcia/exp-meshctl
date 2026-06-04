## ADDED Requirements

### Requirement: Migration strategy validation and default
`spec.migration.strategy` SHALL default to `"FullStop"`. It SHALL accept `"FullStop"`, `"LiveMigration"`, and `"RollingPatch"`. Any other value SHALL produce an `invalid` error. (adapts mesh-management/migration-strategy-validation-and-default)

#### Scenario: Migration strategy defaults to FullStop
- **WHEN** `spec.migration.strategy` is not specified
- **THEN** output has `spec.migration.strategy = "FullStop"`

#### Scenario: FullStop accepted
- **WHEN** `spec.migration.strategy` is `"FullStop"`
- **THEN** it is accepted and stored

#### Scenario: LiveMigration accepted
- **WHEN** `spec.migration.strategy` is `"LiveMigration"`
- **THEN** it is accepted and stored

#### Scenario: RollingPatch accepted
- **WHEN** `spec.migration.strategy` is `"RollingPatch"`
- **THEN** it is accepted and stored

#### Scenario: Invalid migration strategy rejected
- **WHEN** `spec.migration.strategy` is any other value (e.g., `"RollingUpdate"`)
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"<msg>"}` (see scenario: mesh-management/migration-strategy-validation-and-default/invalid-migration-strategy-rejected)

### Requirement: Downgrade prohibition
All strategies SHALL forbid a version downgrade (setting `spec.runtime` to a lower version than the current stored value).

#### Scenario: Downgrade rejected for FullStop
- **WHEN** the stored `spec.runtime` is `"4.0.0"` and the update sets it to `"3.1.1"` with `FullStop`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"version downgrade from '4.0.0' to '3.1.1' is not allowed"}`

#### Scenario: Downgrade rejected for LiveMigration
- **WHEN** the stored `spec.runtime` is `"4.0.0"` and the update sets it to `"3.1.1"` with `LiveMigration`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"version downgrade from '4.0.0' to '3.1.1' is not allowed"}`

#### Scenario: Downgrade rejected for RollingPatch
- **WHEN** the stored `spec.runtime` is `"4.1.1"` and the update sets it to `"4.1.0"` with `RollingPatch`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"version downgrade from '4.1.1' to '4.1.0' is not allowed"}`

### Requirement: RollingPatch version constraints
`RollingPatch` SHALL require that source and target share the same major and minor version AND that the target major version is at least `4`. Both rules SHALL be checked independently and both errors reported when both fail.

#### Scenario: RollingPatch requires same major and minor
- **WHEN** `RollingPatch` is used and source is `"4.0.0"` and target is `"4.1.1"` (different minor)
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg about major.minor mismatch>"}`

#### Scenario: RollingPatch requires target major at least 4
- **WHEN** `RollingPatch` is used and the target major version is less than `4`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg about minimum major version>"}`

#### Scenario: RollingPatch reports both errors independently
- **WHEN** `RollingPatch` is used and both the major/minor rule and the major-4 rule fail
- **THEN** both errors are included in the errors array for `spec.runtime`

#### Scenario: RollingPatch valid same major/minor upgrade at major 4+
- **WHEN** `RollingPatch` is used with source `"4.1.1"` and target `"4.1.2"`
- **THEN** no RollingPatch constraint errors are produced

### Requirement: LiveMigration multi-region rejection
`LiveMigration` SHALL be rejected when `spec.regions` is configured.

#### Scenario: LiveMigration rejected with regions
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and `spec.regions` is configured
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}`

#### Scenario: LiveMigration accepted without regions
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and `spec.regions` is absent
- **THEN** no multi-region error is produced
