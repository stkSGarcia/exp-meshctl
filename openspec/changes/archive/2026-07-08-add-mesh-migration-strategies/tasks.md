## 1. Runtime Catalog and Diagnostics

- [x] 1.1 In `meshctl.py`, add runtime catalog constants for `3.0.0`, `3.1.0`, `3.1.1`, `4.0.0`, migration strategy constants, and version parsing helpers. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 In `meshctl.py`, extend `normalize_runtime`, `validate_runtime`, and `validate_merged_resource` so create/update skip absent runtimes, reject unlisted or skipped runtimes, and accept supported/deprecated runtimes. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.3 In `meshctl.py`, add warning collection/output helpers that emit sorted deprecated-runtime warnings only for successful operations and suppress warnings when errors exist.
- [x] 1.4 In `tests/test_meshctl_cli.py`, cover supported, deprecated, skipped, unlisted, and absent runtime cases, including warning sorting and warning suppression on validation errors.

## 2. Strategy and Version Change Rules

- [x] 2.1 In `meshctl.py`, update `normalize_migration`, `validate_migration_strategy`, and `validate_migration_object` to accept `FullStop`, `LiveMigration`, and `RollingPatch`, default to `FullStop`, and reject invalid values. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.2 In `meshctl.py`, add update-only version-change validation for downgrades, `RollingPatch` major/minor and target-major constraints, and `LiveMigration` multi-region rejection.
- [x] 2.3 In `meshctl.py`, ensure independent version-change failures are accumulated, including multiple errors with the same `field` and `type`.
- [x] 2.4 In `tests/test_meshctl_cli.py`, cover downgrade rejection, `FullStop` upgrade behavior, `RollingPatch` multiple-error reporting, invalid strategy values, and `LiveMigration` multi-region rejection.

## 3. Migration Lifecycle

- [x] 3.1 In `meshctl.py`, add helpers that detect first runtime assignment versus runtime changes between catalog versions.
- [x] 3.2 In `meshctl.py`, update `mesh_update` and `reconcile_update_status` so runtime changes start migration state by persisting target `spec.runtime`, setting the `Migration` condition, and writing `status.migration`.
- [x] 3.3 In `meshctl.py`, define stage sequences for `FullStop`, `RollingPatch`, and `LiveMigration`, with `FullStop` and `RollingPatch` starting at `Migrate`.
- [x] 3.4 In `tests/test_meshctl_cli.py`, cover first runtime assignment without migration and runtime changes that start migration state with source, target, and initial stage.

## 4. Migrate Command and Active Migration Updates

- [x] 4.1 In `meshctl.py`, add `mesh migrate <name>` parser routing and a `mesh_migrate(name)` handler that loads, validates, transitions, saves, and prints the full mesh resource. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 4.2 In `meshctl.py`, implement migration advancement by one stage and final-stage completion by clearing the `Migration` condition and `status.migration`.
- [x] 4.3 In `meshctl.py`, return the specified errors for missing meshes and meshes without active migrations.
- [x] 4.4 In `meshctl.py`, reject changes to `spec.runtime` and `spec.migration.strategy` while migration is active, allow unrelated spec updates, and implement the selected rollback request shape for active `LiveMigration`.
- [x] 4.5 In `tests/test_meshctl_cli.py`, cover migrate advancement, final-stage completion, missing mesh errors, no-active-migration errors, active-migration update restrictions, unrelated updates, and LiveMigration rollback.

## 5. Stability and Regression Coverage

- [x] 5.1 In `meshctl.py`, add a status stability helper that requires `Healthy=True`, `PrechecksPassed=True`, and no active `GracefulShutdown`, `Scaling`, or `Migration` condition.
- [x] 5.2 In `meshctl.py`, call the stability helper after create, update reconciliation, migration start, migration advancement/completion, rollback, and stored-resource upgrade paths.
- [x] 5.3 In `tests/test_meshctl_cli.py`, cover `status.stable` for active migration, stable non-migration meshes, and interactions with existing scaling or graceful-shutdown conditions.
- [x] 5.4 Run `uv run pytest` and ensure the full CLI test suite passes.
