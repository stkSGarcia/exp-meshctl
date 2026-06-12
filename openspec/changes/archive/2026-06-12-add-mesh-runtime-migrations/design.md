## Context

`meshctl.py` already handles mesh CRUD, update merging, field-scoped validation errors, JSON output, default `FullStop` migration strategy, and status condition helpers. Runtime validation currently checks only semantic-version shape, migration validation currently accepts only `FullStop`, and status stability is computed through lifecycle-specific status transitions.

## Related Work

> **`one-shot-operations/add-one-shot-operations`**: Defines command surfaces that execute resource transitions and print the full resulting resource — informs `meshctl mesh migrate <name>` output because the migration command is also a resource transition command. _(see `one-shot-operations/add-one-shot-operations`)_

> **`mesh-resource-management/add-mesh-lifecycle-topology`**: Defines mesh update behavior, lifecycle conditions, and stable status semantics — informs active migration update guards, migration condition handling, and stability recalculation because runtime changes are lifecycle transitions. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

> **`mesh-resource-management/add-access-security-model`**: Defines additional mesh spec validation with field-specific errors — informs runtime and migration strategy validation because those errors should follow the same field/type/message shape. _(see `mesh-resource-management/add-access-security-model`)_

## Goals / Non-Goals

**Goals:**

- Add a runtime catalog with supported, deprecated, and skipped statuses.
- Validate `spec.runtime` and `spec.migration.strategy` on create and update.
- Emit warnings only for successful deprecated-runtime operations.
- Start, advance, complete, and roll back migration state.
- Keep `status.stable` consistent with existing lifecycle conditions plus `Migration`.

**Non-Goals:**

- No external runtime catalog service or dependency.
- No asynchronous migration execution.
- No change to unrelated resource kinds beyond their existing dependency on mesh stability.

## Decisions

### In-process runtime catalog

Define a small constant catalog in `meshctl.py`, keyed by runtime version and status. This keeps validation deterministic for the checkpoint and matches the project’s current single-file architecture. An external file was considered, but it would add parsing, path, and deployment behavior that the checkpoint does not require.

### Warning collection alongside validation

Introduce a warning shape separate from validation errors, then pass warnings to JSON output only after the operation succeeds. This avoids leaking warnings on failed operations and preserves the existing `print_errors` behavior. Sorting by `field` and `message` should happen in a helper before output.

### Version-change handling in update flow

Compute runtime changes after `deep_merge(stored, update_patch(document))` and before persisting. First runtime assignment updates the resource without migration state. Catalog-version-to-catalog-version changes validate downgrade and strategy-specific constraints, then start migration state in `reconcile_update_status` or a dedicated helper called next to it. This keeps create behavior separate from update-only migration lifecycle rules. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

### Migration stages as strategy metadata

Represent stage sequences in a constant map by strategy. `FullStop` and `RollingPatch` use `["Migrate"]`. `LiveMigration` uses a multi-stage sequence and the first entry becomes the initial `status.migration.stage`. The exact LiveMigration stage names can be internal as long as order is stable and `mesh migrate` advances one step.

### `mesh migrate` command surface

Add `meshctl mesh migrate <name>` for stage advancement and completion, and `meshctl mesh migrate <name> --rollback` for explicit LiveMigration rollback. A separate `rollback` subcommand was considered, but a flag keeps all migration lifecycle operations under one command and leaves existing command names undisturbed.

### Stability helper

Replace ad hoc `status["stable"]` assignments that assume non-transition means stable with a helper that derives stability from `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration`. Existing transition code can still set conditions first, then call the helper. This keeps one source of truth for stability.

## Risks / Trade-offs

- Runtime catalog hard-coded in `meshctl.py` -> acceptable for the checkpoint; extract only if catalog size or source changes later.
- Warning output changes successful response shape -> tests should assert existing resource fields remain available and warnings are additive.
- Migration status and scale/resume transitions can interact -> update tests should cover runtime migration plus existing lifecycle transitions.
- Rollback flag is an inferred interface -> keep it limited to `mesh migrate --rollback` and document it in tests so the behavior is explicit.

## Migration Plan

1. Add constants and helpers for runtime catalog, strategy values, version comparison, warnings, stage sequences, migration state, and stability calculation.
2. Extend mesh parser dispatch with `mesh migrate <name>` and `--rollback`.
3. Update create/update validation and output paths.
4. Add focused CLI tests for catalog statuses, warning suppression/sorting, strategy constraints, migration start/advance/complete/rollback, active migration update guards, and stability.

## Open Questions

- None. The design treats rollback as `meshctl mesh migrate <name> --rollback` to make the checkpoint’s rollback behavior actionable.
