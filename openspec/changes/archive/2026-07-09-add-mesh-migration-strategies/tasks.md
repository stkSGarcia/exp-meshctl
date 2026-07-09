## 1. Behavior Coverage

- [x] 1.1 Add runtime catalog create/update tests in `tests/test_meshctl_cli.py` for supported, deprecated, skipped, unlisted, and absent `spec.runtime` values. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 Add warning response tests in `tests/test_meshctl_cli.py` for deprecated runtime success, warning suppression when errors exist, and warning sort order. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.3 Add migration strategy and version-change tests in `tests/test_meshctl_cli.py` for `FullStop`, `LiveMigration`, `RollingPatch`, downgrades, RollingPatch rule accumulation, and LiveMigration multi-region rejection. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.4 Add migration lifecycle tests in `tests/test_meshctl_cli.py` for first runtime assignment, migration start state, `mesh migrate` advancement, final-stage completion, missing mesh, and inactive migration errors. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.5 Add active migration and rollback tests in `tests/test_meshctl_cli.py` for runtime/strategy update rejection, unrelated spec update success, LiveMigration rollback clearing state, and non-LiveMigration rollback rejection. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.6 Add stability regression tests in `tests/test_meshctl_cli.py` proving active `Migration` makes `status.stable` false and cleared migration state restores stable computation. [extends mesh-resource-management/add-meshctl-mesh-crud]

## 2. Catalog, Warnings, and Strategy Validation

- [x] 2.1 Add a module-level runtime catalog, catalog status constants, strategy constants, and stage-sequence constants in `meshctl.py`.
- [x] 2.2 Update `normalize_runtime`, `validate_runtime`, and `validate_merged_resource` in `meshctl.py` so catalog validation runs on create/update when `spec.runtime` is present and skips when absent.
- [x] 2.3 Add warning collection and success serialization helpers in `meshctl.py`, then thread warnings through `mesh_create` and `mesh_update`.
- [x] 2.4 Update `normalize_migration`, `validate_migration_strategy`, and `validate_migration_object` in `meshctl.py` to accept `FullStop`, `LiveMigration`, and `RollingPatch` while preserving the `FullStop` default.
- [x] 2.5 Add runtime tuple parsing and version-change validation helpers in `meshctl.py` for downgrade rejection, RollingPatch constraints, and LiveMigration multi-region rejection.

## 3. Migration State

- [x] 3.1 Add active migration detection and status mutation helpers in `meshctl.py` that set/clear the `Migration` condition and maintain `status.migration`.
- [x] 3.2 Update `mesh_update` and `reconcile_update_status` in `meshctl.py` so runtime version changes start migrations after validation and first runtime assignment does not.
- [x] 3.3 Add active migration update guards in `meshctl.py` that reject `spec.runtime` and `spec.migration.strategy` changes while allowing unrelated spec changes.
- [x] 3.4 Ensure migration conditions use existing `set_condition`, `clear_condition`, and `sort_conditions` helpers in `meshctl.py`.

## 4. Migration Commands

- [x] 4.1 Extend `build_parser` and `main` in `meshctl.py` with `mesh migrate <name>`. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 4.2 Implement `mesh_migrate` in `meshctl.py` to load a mesh, reject missing/inactive migrations, advance one stage, complete final-stage migrations, save the store, and print `public_resource`.
- [x] 4.3 Add the chosen rollback CLI surface in `build_parser` and `main` in `meshctl.py`, defaulting to `mesh rollback <name>` unless apply-time requirements choose a different surface.
- [x] 4.4 Implement rollback handling in `meshctl.py` so only active `LiveMigration` migrations clear migration state and other strategies are rejected.

## 5. Stability and Error Ordering

- [x] 5.1 Centralize `status.stable` computation in `meshctl.py` so `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration` conditions are all considered.
- [x] 5.2 Update public rendering or status reconciliation in `meshctl.py` so active migration state remains visible and stable computation is applied consistently before output.
- [x] 5.3 Preserve existing error sorting in `meshctl.py` while allowing multiple same-field and same-type errors to remain in the serialized response.
- [x] 5.4 Confirm mesh delete dependency behavior in `meshctl.py` remains unchanged for vault-referenced meshes. [extends mesh-resource-management/add-vault-resource-management]

## 6. Verification

- [x] 6.1 Run `uv run pytest tests/test_meshctl_cli.py` and fix failures related to mesh migration strategies.
- [x] 6.2 Run `openspec status --change "add-mesh-migration-strategies"` and confirm proposal, specs, design, and tasks are complete.
