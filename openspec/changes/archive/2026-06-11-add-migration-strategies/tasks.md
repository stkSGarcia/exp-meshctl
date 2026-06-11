## 1. Runtime Catalog and Warning Output

- [x] 1.1 Add a runtime catalog and status constants for supported, deprecated, and skipped runtime versions.
- [x] 1.2 Update runtime validation so create/update reject non-catalog and skipped versions while skipping catalog validation when `spec.runtime` is absent.
- [x] 1.3 Add warning accumulation, sorting, and successful JSON output support for deprecated runtime targets.
- [x] 1.4 Add tests for supported, deprecated, skipped, unsupported, malformed, and omitted runtime values on create and update.

## 2. Migration Strategy Validation

- [x] 2.1 Allow `"FullStop"`, `"LiveMigration"`, and `"RollingPatch"` in `spec.migration.strategy`.
- [x] 2.2 Implement semantic-version comparison helpers for upgrade/downgrade and major/minor checks.
- [x] 2.3 Validate runtime changes for downgrade rejection, RollingPatch constraints, and LiveMigration multi-region rejection.
- [x] 2.4 Add tests for invalid strategies, downgrades, valid FullStop changes, RollingPatch independent failures, and LiveMigration region restrictions.

## 3. Migration Lifecycle State

- [x] 3.1 Detect first runtime assignment separately from catalog-to-catalog runtime changes.
- [x] 3.2 Start migrations by persisting the target runtime, adding the `Migration` condition, and setting `status.migration.sourceRuntime`, `status.migration.targetRuntime`, and `status.migration.stage`.
- [x] 3.3 Define deterministic stage sequences for FullStop, RollingPatch, and LiveMigration.
- [x] 3.4 Recompute `status.stable` from Healthy, PrechecksPassed, GracefulShutdown, Scaling, and Migration conditions.
- [x] 3.5 Add tests for first assignment, migration start status, strategy-specific starting stages, and active-migration stability.

## 4. Mesh Migrate Command

- [x] 4.1 Add `mesh migrate <name>` to the parser and command dispatcher.
- [x] 4.2 Implement migrate behavior to advance non-final stages and complete final stages by clearing `Migration` and `status.migration`.
- [x] 4.3 Implement migrate errors for missing meshes and meshes without active migration.
- [x] 4.4 Add tests for FullStop completion, RollingPatch completion, LiveMigration stage advancement and completion, missing mesh, and no active migration.

## 5. Active Migration Update Rules

- [x] 5.1 Reject `spec.runtime` changes while a migration is active with the documented error field, type, and message.
- [x] 5.2 Reject `spec.migration.strategy` changes while a migration is active with the documented error field, type, and message.
- [x] 5.3 Preserve active migration state while accepting unrelated spec updates that otherwise pass validation.
- [x] 5.4 Implement the documented LiveMigration rollback state clearing if the existing update model exposes rollback input.
- [x] 5.5 Add tests for runtime rejection, strategy rejection, unrelated update acceptance, and rollback behavior where applicable.

## 6. Error Ordering and Regression Coverage

- [x] 6.1 Ensure accumulated errors keep all applicable entries, including multiple errors with the same field and type.
- [x] 6.2 Confirm error sorting remains by field then type, with no contractual ordering among same-field and same-type messages.
- [x] 6.3 Run the existing CLI test suite and add regression tests for one-shot operations observing unstable meshes during active migration.
