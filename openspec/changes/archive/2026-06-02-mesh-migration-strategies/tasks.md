## 1. Runtime Catalog

- [x] 1.1 Define the runtime catalog constant (version → status mapping) in `meshctl.py`
- [x] 1.2 Replace format-only `spec.runtime` validation with catalog lookup on create and update
- [x] 1.3 Implement `skipped` rejection with message `"runtime version '<version>' is skipped and cannot be targeted"`
- [x] 1.4 Implement `deprecated` acceptance with warning `{"field":"spec.runtime","message":"runtime version '<version>' is deprecated"}`
- [x] 1.5 Skip catalog validation when `spec.runtime` is absent

## 2. Warning Emission

- [x] 2.1 Add a warnings accumulator alongside the errors accumulator in the validation/response pipeline
- [x] 2.2 Append `"warnings"` array to successful response JSON when warnings exist and errors are empty
- [x] 2.3 Sort warnings by `field` ascending then `message` ascending before output
- [x] 2.4 Suppress the `"warnings"` key entirely when the list is empty

## 3. Migration Strategy Expansion

- [x] 3.1 Expand the `spec.migration.strategy` enum to accept `"LiveMigration"` and `"RollingPatch"`
- [x] 3.2 Implement downgrade check for all strategies: reject if target semver < source semver with message `"version downgrade from '<current>' to '<target>' is not allowed"`
- [x] 3.3 Implement `RollingPatch` constraint 1: source and target must share major.minor
- [x] 3.4 Implement `RollingPatch` constraint 2: target major must be ≥ 4
- [x] 3.5 Report both `RollingPatch` errors independently when both fail
- [x] 3.6 Implement `LiveMigration` multi-region rejection: error when `spec.regions` is present with message `"LiveMigration strategy is not supported with multi-region topology"`

## 4. Migration Lifecycle — Start

- [x] 4.1 Detect first runtime assignment (no stored `spec.runtime`) and skip migration start
- [x] 4.2 Detect runtime version change (stored version differs from new version) and trigger migration start
- [x] 4.3 On migration start: store `targetRuntime` in `spec.runtime`, add `Migration` condition (`status="True"`, `message=""`)
- [x] 4.4 On migration start: populate `status.migration` with `sourceRuntime`, `targetRuntime`, and initial `stage`
- [x] 4.5 Define stage sequences: `FullStop` → `["Migrate"]`, `RollingPatch` → `["Migrate"]`, `LiveMigration` → `["Drain","Migrate","Verify"]`
- [x] 4.6 Set initial `stage` from the first entry of the strategy's sequence

## 5. `mesh migrate` Command

- [x] 5.1 Add `migrate` subcommand routing in the CLI dispatcher for `mesh migrate <name>`
- [x] 5.2 Return not-found error when the named mesh does not exist
- [x] 5.3 Return `{"field":"status.migration","type":"invalid","message":"no active migration for mesh '<name>'"}` when no active migration exists
- [x] 5.4 Advance `status.migration.stage` to the next stage in the sequence and persist
- [x] 5.5 When the current stage is the final stage, complete the migration (remove `Migration` condition and `status.migration`)
- [x] 5.6 Print full mesh resource JSON after each migrate operation

## 6. Active Migration Guards

- [x] 6.1 On update, detect active migration (Migration condition `status="True"`)
- [x] 6.2 Reject `spec.runtime` change during active migration with message `"cannot change runtime version while a migration is in progress"`
- [x] 6.3 Reject `spec.migration.strategy` change during active migration with message `"cannot change migration strategy while a migration is in progress"`
- [x] 6.4 Allow all other spec field updates while migration is active

## 7. LiveMigration Rollback

- [x] 7.1 Implement rollback operation for `LiveMigration` active migrations: remove `Migration` condition and `status.migration`
- [x] 7.2 Restrict rollback to `LiveMigration` only (no rollback for `FullStop` or `RollingPatch`)

## 8. Stability Update

- [x] 8.1 Update `status.stable` computation to include `Migration` condition: `false` when `Migration` is present with `status="True"`
- [x] 8.2 Verify existing stability conditions (`Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`) still function correctly after change

## 9. Tests

- [x] 9.1 Test catalog validation: unknown version, skipped version, deprecated version (warning), absent runtime skips check
- [x] 9.2 Test warning output shape: present when deprecated, absent when no warnings, suppressed on error
- [x] 9.3 Test strategy acceptance: `FullStop`, `LiveMigration`, `RollingPatch` all accepted; invalid value rejected
- [x] 9.4 Test downgrade rejection across all strategies
- [x] 9.5 Test `RollingPatch` constraints independently and both failing simultaneously
- [x] 9.6 Test `LiveMigration` multi-region rejection
- [x] 9.7 Test first runtime assignment (no migration) vs. version change (migration starts)
- [x] 9.8 Test `mesh migrate` happy path: stage advance, final stage completion, full resource output
- [x] 9.9 Test `mesh migrate` error cases: not found, no active migration
- [x] 9.10 Test active migration guards: runtime change blocked, strategy change blocked, other fields allowed
- [x] 9.11 Test `status.stable = false` during active migration
- [x] 9.12 Test migration completion clears `status.migration` and `Migration` condition
