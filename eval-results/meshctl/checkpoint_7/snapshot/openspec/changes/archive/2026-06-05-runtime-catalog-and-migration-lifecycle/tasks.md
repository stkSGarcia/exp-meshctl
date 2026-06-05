## 1. Runtime Catalog

- [x] 1.1 Add `RUNTIME_CATALOG` dict at module level mapping version strings to `"supported"`, `"deprecated"`, or `"skipped"` statuses (at minimum: `3.0.0`→deprecated, `3.1.0`→skipped, `3.1.1`→supported, `4.0.0`→supported)
- [x] 1.2 In `validate_and_build`, after the format check for `spec.runtime`, add catalog membership check: reject versions not in `RUNTIME_CATALOG` with `field="spec.runtime"`, `type="invalid"`
- [x] 1.3 In `validate_and_build`, reject `skipped` catalog status with message `"runtime version '<version>' is skipped and cannot be targeted"`
- [x] 1.4 In `validate_and_build`, collect a deprecation warning for `deprecated` catalog status: `{"field":"spec.runtime","message":"runtime version '<version>' is deprecated"}` and return it alongside the built resource

## 2. Warning Output

- [x] 2.1 Add warning accumulation to `validate_and_build` return signature (e.g. return `(resource, errors, warnings)` or pass warnings via a mutable list parameter)
- [x] 2.2 In `cmd_create`, after successful validation, emit warnings by merging `{"warnings": sorted_warnings}` into the output dict (not the stored dict) when warnings are non-empty; sort by `(field, message)`
- [x] 2.3 In `cmd_update`, apply the same warning emission logic on success

## 3. Migration Strategy Expansion

- [x] 3.1 In `validate_and_build`, change strategy validation from a single-value check (`!= "FullStop"`) to a set membership check against `{"FullStop", "LiveMigration", "RollingPatch"}`
- [x] 3.2 Add `LiveMigration` region restriction check: if strategy is `"LiveMigration"` and `spec.regions` is present and non-empty, emit `{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}`

## 4. Version-Change Rules

- [x] 4.1 Add a semver tuple parser helper (e.g. `parse_semver(v) -> (major, minor, patch)`) for comparing version strings
- [x] 4.2 In `cmd_update`, after merge and validation, detect a version change (stored has `spec.runtime` and merged `spec.runtime` differs); skip if no prior runtime (first-time assignment)
- [x] 4.3 Implement downgrade check: if target semver < source semver, emit `{"field":"spec.runtime","type":"invalid","message":"version downgrade from '<current>' to '<target>' is not allowed"}`
- [x] 4.4 Implement `RollingPatch` rule 1: source and target must share same major+minor; emit `field="spec.runtime"`, `type="invalid"` if they differ
- [x] 4.5 Implement `RollingPatch` rule 2: target major must be ≥ 4; emit `field="spec.runtime"`, `type="invalid"` if not — evaluate independently from rule 1 so both errors are reported when both fail
- [x] 4.6 Verify `FullStop` has no extra version-change constraints beyond the downgrade check

## 5. Migration Lifecycle — Start

- [x] 5.1 Add `MIGRATION_STAGES` dict at module level: `{"FullStop": ["Migrate"], "RollingPatch": ["Migrate"], "LiveMigration": ["Prepare", "Migrate"]}`
- [x] 5.2 In `cmd_update`, when a version change is detected (and no version-change errors exist), start a migration: add `Migration` condition with `status="True"`, `message=""` to `status.conditions`
- [x] 5.3 Set `status.migration` on the resource with `sourceRuntime`, `targetRuntime`, and `stage` = first entry in `MIGRATION_STAGES[strategy]`

## 6. Active-Migration Guards

- [x] 6.1 In `cmd_update`, before the merge step, check if the stored mesh has an active `Migration` condition (`status="True"`); if so, check if the update attempts to change `spec.runtime` and reject with the in-progress runtime error
- [x] 6.2 In `cmd_update`, under the same active-migration check, reject changes to `spec.migration.strategy` with the in-progress strategy error
- [x] 6.3 Ensure non-guarded fields (e.g. `spec.instances`) pass through normally during active migration

## 7. mesh migrate Command

- [x] 7.1 Implement `cmd_migrate(args)` handler: look up mesh by name, return not-found error if absent
- [x] 7.2 In `cmd_migrate`, return error `{"field":"status.migration","type":"invalid","message":"no active migration for mesh '<name>'"}` if `status.migration` is absent
- [x] 7.3 In `cmd_migrate`, advance the migration: look up current stage in `MIGRATION_STAGES[strategy]`, find next stage; if current is final stage, complete the migration (remove `Migration` condition, remove `status.migration`); otherwise update `status.migration.stage` to next stage
- [x] 7.4 Print the full mesh resource after the transition
- [x] 7.5 Wire `mesh migrate <name>` subcommand in `main`: add `migrate_p = mesh_sub.add_parser("migrate")`, `migrate_p.add_argument("name")`, and route to `cmd_migrate`

## 8. Stability Update

- [x] 8.1 Update `status.stable` computation: wherever `stable` is set to `True` (in `build_initial_status` and in `apply_lifecycle`), add a check that the `Migration` condition is absent or `"False"`; `stable` must be `False` when `Migration` is `"True"`

## 9. LiveMigration Rollback

- [x] 9.1 Implement rollback path: when the stored migration strategy is `"LiveMigration"` and a rollback is triggered (define the trigger — e.g. a flag or subcommand as determined by design), remove the `Migration` condition and `status.migration` from the resource
