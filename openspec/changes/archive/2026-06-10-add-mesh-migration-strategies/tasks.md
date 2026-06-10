## 1. CLI Surface and Output Helpers

- [x] 1.1 Add `mesh migrate <name>` argument parsing and route it from `main`.
- [x] 1.2 Add reusable success-output handling that can include `warnings` beside the public resource when warnings exist.
- [x] 1.3 Ensure warning output is omitted whenever any errors are printed.
- [x] 1.4 Keep all successful mesh command output on stdout as JSON and keep stderr empty.

## 2. Runtime Catalog and Strategy Validation

- [x] 2.1 Add the runtime catalog with `3.0.0` deprecated, `3.1.0` skipped, `3.1.1` supported, and `4.0.0` supported.
- [x] 2.2 Validate present `spec.runtime` values against semantic-version shape and catalog membership on create and update, while skipping catalog validation when absent.
- [x] 2.3 Reject skipped and uncataloged runtime targets with `spec.runtime` invalid errors and the required skipped-version message.
- [x] 2.4 Generate deprecated runtime warnings with the required warning shape and ordering only after validation succeeds.
- [x] 2.5 Expand `spec.migration.strategy` validation to accept `FullStop`, `LiveMigration`, and `RollingPatch`.

## 3. Runtime Version Change Rules

- [x] 3.1 Detect post-merge runtime version changes by comparing stored and candidate `spec.runtime` values.
- [x] 3.2 Treat first runtime assignment as a normal assignment that does not start a migration.
- [x] 3.3 Reject downgrades for all strategies with the required `spec.runtime` invalid message.
- [x] 3.4 Enforce `RollingPatch` same-major-minor and target-major-at-least-four rules independently, preserving both errors when both fail.
- [x] 3.5 Reject `LiveMigration` when `spec.regions` is configured with the required `spec.migration.strategy` invalid message.

## 4. Migration State and Transitions

- [x] 4.1 Start migrations on valid catalog-to-catalog runtime changes by storing target runtime in `spec.runtime`.
- [x] 4.2 Add and persist a `Migration` condition with status `"True"` and empty message when migration starts.
- [x] 4.3 Add and persist `status.migration.sourceRuntime`, `status.migration.targetRuntime`, and `status.migration.stage`.
- [x] 4.4 Define stage sequences for `FullStop`, `RollingPatch`, and multi-stage `LiveMigration`, with `Migrate` as the first stage for `FullStop` and `RollingPatch`.
- [x] 4.5 Implement `mesh migrate <name>` to advance one stage, print the full resource, and complete migrations at the final stage.
- [x] 4.6 On migration completion, remove the `Migration` condition and remove `status.migration`.
- [x] 4.7 Implement missing-mesh and no-active-migration errors for `mesh migrate`.
- [x] 4.8 Implement the chosen local trigger for active `LiveMigration` rollback and clear migration condition/status on rollback.

## 5. Active Migration Update Rules and Stability

- [x] 5.1 Reject `spec.runtime` changes while migration is active with the required `spec.runtime` invalid message.
- [x] 5.2 Reject `spec.migration.strategy` changes while migration is active with the required `spec.migration.strategy` invalid message.
- [x] 5.3 Allow unrelated spec updates during active migration when no other validation errors exist.
- [x] 5.4 Update `status.stable` so it is `true` only when `Healthy` and `PrechecksPassed` are `"True"` and `GracefulShutdown`, `Scaling`, and `Migration` are absent or `"False"`.
- [x] 5.5 Preserve duplicate errors that share the same `field` and `type`, including multiple `spec.runtime` invalid errors.

## 6. Tests and Verification

- [x] 6.1 Add CLI tests for runtime catalog acceptance, skipped/unknown rejection, and omitted-runtime behavior.
- [x] 6.2 Add CLI tests for deprecated runtime warnings, warning ordering, warning suppression on errors, and unchanged success exit code.
- [x] 6.3 Add CLI tests for accepted strategy values, invalid strategy values, downgrade rejection, `RollingPatch` constraints, and `LiveMigration` multi-region rejection.
- [x] 6.4 Add CLI tests for first runtime assignment, migration start state, condition/status persistence, and stability during migration.
- [x] 6.5 Add CLI tests for `mesh migrate` stage advancement, final-stage completion, missing mesh, and no-active-migration errors.
- [x] 6.6 Add CLI tests for active-migration update restrictions, allowed unrelated updates, and `LiveMigration` rollback.
- [x] 6.7 Run the full test suite and `openspec validate add-mesh-migration-strategies`.
