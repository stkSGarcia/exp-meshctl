## ADDED Requirements

### Requirement: Extended migration strategy values
`spec.migration.strategy` SHALL accept `"FullStop"` (default), `"LiveMigration"`, and `"RollingPatch"`. Any other value SHALL produce an error on `{"field":"spec.migration.strategy","type":"invalid"}`. (adapts `implement-meshctl/mesh-management/migration-strategy-validation-and-default`)

> Extends: `implement-meshctl/mesh-management/migration-strategy-validation-and-default`

#### Scenario: LiveMigration accepted as strategy
- **WHEN** `spec.migration.strategy` is `"LiveMigration"`
- **THEN** no strategy validation error is emitted

#### Scenario: RollingPatch accepted as strategy
- **WHEN** `spec.migration.strategy` is `"RollingPatch"`
- **THEN** no strategy validation error is emitted

#### Scenario: Unknown strategy still rejected
- **WHEN** `spec.migration.strategy` is `"BlueGreen"`
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"<msg>"}`

---

### Requirement: Downgrade forbidden for all strategies
Changing `spec.runtime` to a version that is lower (by semver ordering) than the current stored `spec.runtime` SHALL be rejected regardless of strategy. The error SHALL use `field = "spec.runtime"`, `type = "invalid"`, and `message = "version downgrade from '<current>' to '<target>' is not allowed"`.

#### Scenario: Downgrade rejected with FullStop
- **WHEN** stored `spec.runtime` is `"4.0.0"` and the update sets it to `"3.1.1"`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"version downgrade from '4.0.0' to '3.1.1' is not allowed"}`

#### Scenario: Same version is not a downgrade
- **WHEN** stored `spec.runtime` equals the target `spec.runtime`
- **THEN** no downgrade error is emitted (not a version change)

---

### Requirement: RollingPatch version-change constraints
When `spec.migration.strategy` is `"RollingPatch"`, the system SHALL independently check two rules on a version change:
1. Source and target MUST share the same major and minor version.
2. Target major version MUST be at least `4`.

Both rules SHALL be evaluated independently. When both fail, both errors SHALL be reported. Each error uses `field = "spec.runtime"` and `type = "invalid"`.

#### Scenario: RollingPatch — different major/minor rejected
- **WHEN** strategy is `"RollingPatch"`, source is `"4.0.0"`, target is `"4.1.0"` (different minor)
- **THEN** output error with `field = "spec.runtime"` about major/minor mismatch

#### Scenario: RollingPatch — major < 4 rejected
- **WHEN** strategy is `"RollingPatch"`, source is `"3.0.0"`, target is `"3.0.1"` (same major/minor, but major < 4)
- **THEN** output error with `field = "spec.runtime"` about major version requirement

#### Scenario: RollingPatch — both rules fail, both errors reported
- **WHEN** strategy is `"RollingPatch"`, source is `"3.0.0"`, target is `"4.0.0"` (different minor, and source major < 4)
- **THEN** two errors are emitted: one for major/minor mismatch, one for major version requirement

#### Scenario: RollingPatch — valid patch upgrade
- **WHEN** strategy is `"RollingPatch"`, source is `"4.0.0"`, target is `"4.0.1"` (same major.minor, major >= 4)
- **THEN** no RollingPatch constraint errors are emitted

---

### Requirement: LiveMigration region restriction
`"LiveMigration"` strategy SHALL be rejected when `spec.regions` is configured. The error SHALL use `field = "spec.migration.strategy"`, `type = "invalid"`, and `message = "LiveMigration strategy is not supported with multi-region topology"`.

#### Scenario: LiveMigration with regions rejected
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and `spec.regions` is present and non-empty
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}`

#### Scenario: LiveMigration without regions accepted
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and `spec.regions` is absent
- **THEN** no region-restriction error is emitted

---

### Requirement: Migration lifecycle — first assignment
Setting `spec.runtime` for the first time (stored value was absent) SHALL assign the version without starting a migration. No `status.migration` or `Migration` condition is created for a first-time assignment.

#### Scenario: First runtime assignment does not start migration
- **WHEN** the stored mesh has no `spec.runtime` and an update sets `spec.runtime` to `"4.0.0"`
- **THEN** `spec.runtime` is persisted as `"4.0.0"` and `status.migration` is absent from the response

---

### Requirement: Migration lifecycle — version change starts migration
Changing `spec.runtime` from one catalog version to another SHALL start a migration. The system SHALL:
1. Store the target version in `spec.runtime`.
2. Add a `Migration` condition to `status.conditions` with `status = "True"` and `message = ""`.
3. Add `status.migration` with `sourceRuntime`, `targetRuntime`, and `stage` set to the first stage for the chosen strategy.

Stage sequences:
- `FullStop`: `["Migrate"]`
- `RollingPatch`: `["Migrate"]`
- `LiveMigration`: multiple stages (at minimum two, e.g. `["Prepare", "Migrate"]`)

#### Scenario: FullStop version change starts migration at Migrate stage
- **WHEN** stored `spec.runtime` is `"3.1.1"`, update sets `"4.0.0"`, strategy is `"FullStop"`
- **THEN** response has `status.migration.stage = "Migrate"`, `status.migration.sourceRuntime = "3.1.1"`, `status.migration.targetRuntime = "4.0.0"`, and `status.conditions` includes `{"type":"Migration","status":"True","message":""}`

#### Scenario: RollingPatch version change starts migration at Migrate stage
- **WHEN** strategy is `"RollingPatch"`, version changes
- **THEN** `status.migration.stage = "Migrate"` is set

#### Scenario: LiveMigration version change starts at first stage
- **WHEN** strategy is `"LiveMigration"`, version changes
- **THEN** `status.migration.stage` equals the first stage in LiveMigration's sequence

---

### Requirement: mesh migrate command — advance stage
`meshctl mesh migrate <name>` SHALL advance an active migration by one stage and print the full mesh resource. If the current stage is the final stage, the migration SHALL be completed instead.

#### Scenario: Advance from non-final stage
- **WHEN** the mesh has an active migration with a non-final stage
- **THEN** `status.migration.stage` is updated to the next stage and the full resource is printed

#### Scenario: Complete migration from final stage
- **WHEN** the mesh has an active migration at its final stage
- **THEN** `status.migration` is removed, the `Migration` condition is removed, and the full resource is printed

#### Scenario: Missing mesh
- **WHEN** `mesh migrate` is called with a name that does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

#### Scenario: No active migration
- **WHEN** `mesh migrate` is called and `status.migration` is absent
- **THEN** output `{"errors":[{"field":"status.migration","type":"invalid","message":"no active migration for mesh '<name>'"}]}`

---

### Requirement: Updates blocked during active migration
The system SHALL enforce the following restrictions while a `Migration` condition with `status = "True"` is active:
- Changes to `spec.runtime` SHALL be rejected with `field = "spec.runtime"`, `type = "invalid"`, `message = "cannot change runtime version while a migration is in progress"`.
- Changes to `spec.migration.strategy` SHALL be rejected with `field = "spec.migration.strategy"`, `type = "invalid"`, `message = "cannot change migration strategy while a migration is in progress"`.
- Updates to all other spec fields SHALL be allowed.

#### Scenario: Runtime change blocked during active migration
- **WHEN** an update attempts to change `spec.runtime` while `Migration` condition is `"True"`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"cannot change runtime version while a migration is in progress"}`

#### Scenario: Strategy change blocked during active migration
- **WHEN** an update attempts to change `spec.migration.strategy` while `Migration` condition is `"True"`
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"cannot change migration strategy while a migration is in progress"}`

#### Scenario: Other fields may be updated during active migration
- **WHEN** an update changes `spec.instances` while a migration is active
- **THEN** the update succeeds without a migration-guard error

---

### Requirement: LiveMigration rollback
Only `LiveMigration` supports rollback during an active migration. A rollback SHALL remove the `Migration` condition and `status.migration`. Other strategies do not support rollback.

#### Scenario: LiveMigration rollback removes migration state
- **WHEN** the active migration uses `"LiveMigration"` strategy and a rollback is triggered
- **THEN** the `Migration` condition is removed and `status.migration` is absent from the resource

### Related Scenarios

**`implement-meshctl/mesh-management/migration-strategy-validation-and-default/migration-strategy-defaults-to-fullstop`** — When strategy is unspecified, output has `spec.migration.strategy = "FullStop"`. _(matched on: migration strategy lifecycle stages)_

**`implement-meshctl/mesh-management/migration-strategy-validation-and-default/invalid-migration-strategy-rejected`** — When strategy is `"RollingUpdate"`, output a strategy invalid error. _(matched on: migration strategy lifecycle stages)_
