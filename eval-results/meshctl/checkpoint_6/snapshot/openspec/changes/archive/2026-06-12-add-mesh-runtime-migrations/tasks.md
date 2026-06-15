## 1. Runtime Catalog and Warning Output

- [x] 1.1 In `meshctl.py`, add runtime catalog constants for `3.0.0`, `3.1.0`, `3.1.1`, and `4.0.0`, plus helper functions for catalog lookup and semantic version comparison. [extends mesh-resource-management/add-access-security-model]
- [x] 1.2 In `meshctl.py`, update `validate_runtime`, `normalize_runtime`, and `validate_merged_resource` so create and update accept only catalog-listed runtimes, reject skipped runtimes with the required message, and skip catalog validation when `spec.runtime` is absent. [extends mesh-resource-management/add-access-security-model]
- [x] 1.3 In `meshctl.py`, add warning helpers and update `mesh_create` and `mesh_update` so deprecated runtime warnings are emitted only on successful operations and sorted by `field` then `message`. [extends mesh-resource-management/add-access-security-model]
- [x] 1.4 In `tests/test_meshctl_cli.py`, add CLI coverage for supported, deprecated, skipped, unknown, and absent runtime values, including warning suppression when any validation error exists.

## 2. Migration Strategy Validation

- [x] 2.1 In `meshctl.py`, update `validate_migration_strategy` and `validate_migration_object` to accept `FullStop`, `LiveMigration`, and `RollingPatch`, while preserving `FullStop` as the default strategy. [extends mesh-resource-management/add-access-security-model]
- [x] 2.2 In `meshctl.py`, add runtime version-change validation for downgrades, RollingPatch major/minor and target-major constraints, and LiveMigration multi-region rejection in the mesh update path. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 2.3 In `meshctl.py`, ensure version-change validation accumulates all applicable errors, including multiple errors with the same `field` and `type`. [extends mesh-resource-management/add-access-security-model]
- [x] 2.4 In `tests/test_meshctl_cli.py`, add CLI coverage for valid strategies, invalid strategies, downgrade rejection, RollingPatch failures and success, LiveMigration multi-region rejection, and error accumulation.

## 3. Migration Lifecycle State

- [x] 3.1 In `meshctl.py`, add migration stage sequence constants and helper functions to identify active migrations, start migration state, advance stages, complete migrations, and roll back LiveMigration migrations. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.2 In `meshctl.py`, update `mesh_update` and status reconciliation so first runtime assignment does not start a migration, but catalog-version-to-catalog-version changes store the target runtime, add the `Migration` condition, and populate `status.migration`. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.3 In `meshctl.py`, reject `spec.runtime` and `spec.migration.strategy` changes while a migration is active, while allowing updates to unrelated spec fields. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.4 In `tests/test_meshctl_cli.py`, add CLI coverage for first runtime assignment, migration start state, active migration update guards, and unrelated field updates during active migration.

## 4. Mesh Migrate Command

- [x] 4.1 In `meshctl.py`, extend `build_parser` and `main` with `mesh migrate <name>` and `mesh migrate <name> --rollback`. [extends one-shot-operations/add-one-shot-operations]
- [x] 4.2 In `meshctl.py`, implement `mesh_migrate` to load the mesh, return the standard missing-mesh error, advance an active migration by one stage, complete final-stage migrations, persist changes, and print the full mesh resource. [extends one-shot-operations/add-one-shot-operations]
- [x] 4.3 In `meshctl.py`, implement rollback handling so only active LiveMigration migrations can roll back and rollback removes the `Migration` condition plus `status.migration`. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 4.4 In `tests/test_meshctl_cli.py`, add CLI coverage for missing mesh, no active migration, stage advancement, final-stage completion, successful LiveMigration rollback, and rejected rollback for non-LiveMigration strategies.

## 5. Stability and Regression Coverage

- [x] 5.1 In `meshctl.py`, add a shared `recalculate_mesh_stability` helper and call it after status condition changes so `Migration`, `Scaling`, `GracefulShutdown`, `Healthy`, and `PrechecksPassed` determine `status.stable`. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 5.2 In `meshctl.py`, verify public resource output and stored resource upgrades preserve existing status fields and clear completed migration state consistently. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 5.3 In `tests/test_meshctl_cli.py`, extend status lifecycle tests to assert `status.stable = false` during migration and `true` after migration completion when all other gates pass.
- [x] 5.4 Run `uv run pytest` and fix any regressions in existing mesh, vault, task, snapshot, and recovery CLI behavior.
