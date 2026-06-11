## 1. Runtime Catalog and Warning Output

- [x] 1.1 Add an isolated runtime catalog helper with catalog entries, semantic version parsing/comparison, and status lookup for supported, deprecated, skipped, and unknown versions.
- [x] 1.2 Apply catalog validation to mesh create and update when `spec.runtime` is present, while preserving omitted-runtime behavior.
- [x] 1.3 Emit deprecated runtime warnings only for successful create/update operations, sorted by `field` then `message`, without changing the success exit code.
- [x] 1.4 Extend successful mesh JSON output to include top-level `warnings` only when warnings are present.

## 2. Migration Strategy and Version Change Validation

- [x] 2.1 Update migration strategy validation to accept `FullStop`, `LiveMigration`, and `RollingPatch`, and reject all other values with `spec.migration.strategy` invalid errors.
- [x] 2.2 Detect first runtime assignment versus catalog-to-catalog runtime version changes during mesh update.
- [x] 2.3 Reject runtime downgrades for every strategy with the required `spec.runtime` invalid error message.
- [x] 2.4 Implement RollingPatch checks for same major/minor and target major version at least `4`, reporting both independent errors when both fail.
- [x] 2.5 Implement LiveMigration rejection for configured `spec.regions` with the required `spec.migration.strategy` invalid error message.

## 3. Migration Lifecycle and Command Handling

- [x] 3.1 Persist migration start state with target `spec.runtime`, a `Migration` condition, and `status.migration.sourceRuntime`, `targetRuntime`, and first `stage`.
- [x] 3.2 Define stage sequencing for `FullStop`, `RollingPatch`, and `LiveMigration` and expose helpers to advance or complete the current stage.
- [x] 3.3 Add `mesh migrate <name>` argument parsing and command handling for missing mesh, no active migration, stage advancement, and final-stage completion.
- [x] 3.4 Add `mesh migrate <name> --rollback` handling for active LiveMigration rollback, and reject rollback for inactive or non-LiveMigration migrations.
- [x] 3.5 Ensure migration completion and rollback remove `status.migration`, remove the `Migration` condition, update `spec.runtime` appropriately, and print the full public mesh resource.

## 4. Active Migration Update and Stability Rules

- [x] 4.1 Reject `spec.runtime` changes during active migration with the required `cannot change runtime version while a migration is in progress` message.
- [x] 4.2 Reject `spec.migration.strategy` changes during active migration with the required `cannot change migration strategy while a migration is in progress` message.
- [x] 4.3 Allow unrelated spec updates during active migration when all other validation succeeds.
- [x] 4.4 Recompute `status.stable` from `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration` conditions for create, update, migrate, and describe output.
- [x] 4.5 Preserve deterministic condition uniqueness, condition ordering, error accumulation, and same-field same-type error reporting.

## 5. Tests and Verification

- [x] 5.1 Add CLI tests for runtime catalog supported, deprecated, skipped, unknown, and omitted runtime cases on create/update.
- [x] 5.2 Add CLI tests for warning output shape, sorting, success exit behavior, and suppression when validation errors exist.
- [x] 5.3 Add CLI tests for strategy validation, downgrade rejection, RollingPatch constraints, and LiveMigration multi-region rejection.
- [x] 5.4 Add CLI tests for migration start persistence, stage advancement, final completion, missing mesh, no active migration, and LiveMigration rollback.
- [x] 5.5 Add CLI tests for active migration update constraints, allowed unrelated updates, migration-aware `status.stable`, and error ordering with duplicate field/type errors.
- [x] 5.6 Run the full test suite and `openspec validate add-mesh-migration-strategies`.
