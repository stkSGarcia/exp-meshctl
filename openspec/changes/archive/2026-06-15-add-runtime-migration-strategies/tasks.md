## 1. Runtime Catalog and Warning Output

- [x] 1.1 In `meshctl.py`, add runtime catalog constants for supported, deprecated, and skipped versions, plus helpers for catalog lookup and sorted warning creation. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 1.2 In `meshctl.py`, update `mesh_create`, `mesh_update`, `validate_runtime`, and validation flow so optional `spec.runtime` is checked against the catalog when present and skipped when absent. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 1.3 In `meshctl.py`, add successful-operation warning output that includes `warnings` only when warnings exist, suppresses warnings when errors exist, and preserves exit code behavior.
- [x] 1.4 In `tests/test_meshctl_cli.py`, add create and update coverage for supported, deprecated, skipped, absent, and unsupported runtime catalog behavior.

## 2. Strategy and Version Change Validation

- [x] 2.1 In `meshctl.py`, extend `validate_migration_strategy` and related normalization so `FullStop`, `LiveMigration`, and `RollingPatch` are accepted and invalid values use the required `spec.migration.strategy` invalid error shape.
- [x] 2.2 In `meshctl.py`, add version comparison helpers and enforce downgrade rejection for all strategies.
- [x] 2.3 In `meshctl.py`, enforce `RollingPatch` same-major-minor and target-major-at-least-4 rules, reporting both applicable errors independently.
- [x] 2.4 In `meshctl.py`, reject `LiveMigration` when `spec.regions` is configured with the required multi-region topology error.
- [x] 2.5 In `tests/test_meshctl_cli.py`, add strategy validation tests for defaulting, invalid values, downgrades, RollingPatch combined failures, and LiveMigration multi-region rejection.

## 3. Migration Lifecycle State

- [x] 3.1 In `meshctl.py`, update `reconcile_update_status` and supporting helpers so first runtime assignment does not start migration but runtime changes between catalog versions do. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.2 In `meshctl.py`, persist migration start state with target `spec.runtime`, `Migration` condition, and `status.migration.sourceRuntime`, `status.migration.targetRuntime`, and first strategy `stage`.
- [x] 3.3 In `meshctl.py`, define strategy stage sequences with single-stage `FullStop` and `RollingPatch` and a deterministic multi-stage `LiveMigration` sequence.
- [x] 3.4 In `tests/test_meshctl_cli.py`, add lifecycle tests for first runtime assignment, migration start, stored migration status fields, and strategy-specific first stage.

## 4. Migrate Command and Active Migration Updates

- [x] 4.1 In `meshctl.py`, extend `build_parser` and `main` to route `mesh migrate <name>` beside the existing mesh CRUD commands. [extends one-shot-operations/add-one-shot-operations]
- [x] 4.2 In `meshctl.py`, implement `mesh_migrate` to load the mesh, return the standard not-found shape for missing names, reject missing active migration, advance one stage, complete on final stage, save the store, and print the full public mesh.
- [x] 4.3 In `meshctl.py`, reject changes to `spec.runtime` and `spec.migration.strategy` while migration is active, while allowing unrelated spec updates.
- [x] 4.4 In `meshctl.py`, implement the selected rollback convention for active `LiveMigration` migrations and clear the `Migration` condition and `status.migration`.
- [x] 4.5 In `tests/test_meshctl_cli.py`, add tests for migrate advancement, final-stage completion, missing mesh, no active migration, active migration update restrictions, unrelated updates during migration, and LiveMigration rollback.

## 5. Stability and Regression Coverage

- [x] 5.1 In `meshctl.py`, update status derivation and public-resource upgrade paths so `status.stable` requires `Healthy = "True"`, `PrechecksPassed = "True"`, and absent-or-false `GracefulShutdown`, `Scaling`, and `Migration`. [extends one-shot-operations/add-one-shot-operations]
- [x] 5.2 In `tests/test_meshctl_cli.py`, add stability tests proving active migration makes a mesh unstable and all passing conditions make it stable.
- [x] 5.3 In `tests/test_meshctl_cli.py`, add error accumulation tests for multiple applicable runtime errors, including same `field` and `type` ties.
- [x] 5.4 Run `uv run pytest` or the repo's configured test command and fix regressions.
