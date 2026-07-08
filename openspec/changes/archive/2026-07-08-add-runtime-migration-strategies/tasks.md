## 1. Runtime Catalog and Warning Output

- [x] 1.1 In `meshctl.py`, add runtime catalog constants/helpers for supported, deprecated, skipped, and unknown versions. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 1.2 In `meshctl.py`, update `validate_runtime()`/merged validation to keep semantic-version shape validation and add catalog validation only when `spec.runtime` is present. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 1.3 In `meshctl.py`, add warning collection and sorted successful-output handling so deprecated runtimes emit `warnings` while error responses suppress warnings.
- [x] 1.4 In `tests/test_meshctl_cli.py`, add create/update coverage for supported runtime, absent runtime, skipped runtime, unknown runtime, deprecated warning output, warning sorting, warning suppression on errors, and success exit code.

## 2. Migration Strategy Validation

- [x] 2.1 In `meshctl.py`, extend `validate_migration_strategy()` and `validate_migration_object()` to accept `FullStop`, `LiveMigration`, and `RollingPatch`, preserving the `FullStop` default.
- [x] 2.2 In `meshctl.py`, add version comparison helpers and validate downgrade rejection for all migration strategies during merged mesh updates.
- [x] 2.3 In `meshctl.py`, add RollingPatch validation for same major/minor compatibility and target major version at least `4`, accumulating both errors when both fail.
- [x] 2.4 In `meshctl.py`, add LiveMigration validation that rejects runtime changes when `spec.regions` is configured.
- [x] 2.5 In `tests/test_meshctl_cli.py`, add strategy validation tests for invalid strategy values, default strategy, downgrade rejection, RollingPatch allowed/rejected changes, accumulated RollingPatch errors, and LiveMigration multi-region rejection.

## 3. Migration Lifecycle State

- [x] 3.1 In `meshctl.py`, detect first runtime assignment versus runtime version change after `mesh_update()` deep-merges stored and incoming resources. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.2 In `meshctl.py`, start runtime migrations by storing the target runtime in `spec.runtime`, setting the `Migration` condition, and adding `status.migration.sourceRuntime`, `status.migration.targetRuntime`, and `status.migration.stage`.
- [x] 3.3 In `meshctl.py`, define migration stage sequences with `Migrate` for `FullStop` and `RollingPatch`, and a deterministic multi-stage sequence for `LiveMigration`.
- [x] 3.4 In `meshctl.py`, reject `spec.runtime` and `spec.migration.strategy` changes while a migration is active, while allowing unrelated spec field updates.
- [x] 3.5 In `tests/test_meshctl_cli.py`, add lifecycle tests for first runtime assignment, migration start, persisted migration state, active migration runtime/strategy guards, and unrelated updates during active migration.

## 4. Migration Command and Rollback

- [x] 4.1 In `meshctl.py`, add `mesh migrate <name>` to `build_parser()` and `main()` dispatch.
- [x] 4.2 In `meshctl.py`, implement `mesh_migrate()` to return standard not-found errors, reject missing active migrations, advance one stage, complete final-stage migrations, persist the store, and print the full public mesh resource.
- [x] 4.3 In `meshctl.py`, add the chosen rollback CLI shape for active `LiveMigration` migrations and clear `Migration`/`status.migration` on rollback.
- [x] 4.4 In `tests/test_meshctl_cli.py`, add command tests for missing mesh, no active migration, stage advancement, final-stage completion, printed resource shape, LiveMigration rollback, and non-LiveMigration rollback rejection.

## 5. Stability and Regression Coverage

- [x] 5.1 In `meshctl.py`, centralize `status.stable` computation from `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration` conditions.
- [x] 5.2 In `meshctl.py`, call the centralized stability helper from create, update reconciliation, migration start/advance/completion, rollback, describe transition completion, and public resource preparation where needed. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 5.3 In `tests/test_meshctl_cli.py`, extend status tests to prove active migration makes `status.stable` false and completed/rolled-back migrations restore stability when all other conditions pass.
- [x] 5.4 Run `uv run pytest` and fix any regressions in existing mesh, vault, task, snapshot, and recovery CLI behavior.
