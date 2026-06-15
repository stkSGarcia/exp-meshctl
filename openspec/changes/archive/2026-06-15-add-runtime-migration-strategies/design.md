## Context

`meshctl.py` currently owns the mesh command parser, validation, defaulting, persistence, update merging, status reconciliation, and output formatting in a single module. Runtime syntax validation already exists, migration strategy validation already defaults to `FullStop`, and lifecycle status is reconciled during mesh updates, but runtime catalog status, warning output, migration progress, and migration-aware stability are not yet specified as one coherent flow.

## Related Work

> **`mesh-resource-management/add-mesh-lifecycle-topology`**: specifies mesh update and lifecycle status behavior — informs the decision to implement runtime changes inside the existing `mesh_update` merge, validation, and `reconcile_update_status` path because this change extends update-driven lifecycle transitions.

> **`one-shot-operations/add-one-shot-operations`**: consumes `status.stable` for task, snapshot, and recovery execution — informs the decision to derive migration-aware stability on the mesh resource itself because one-shot commands should continue reading the same stability signal.

> **`mesh-resource-management/add-vault-resource-management`**: specifies validation-based rejection for unsafe resource relationships — informs the decision to reuse accumulated validation errors and standard not-found shapes for catalog, strategy, and migration command failures.

## Goals / Non-Goals

**Goals:**

- Validate optional `spec.runtime` values against a fixed runtime catalog while preserving existing semantic-version syntax checks.
- Add warning output for deprecated runtime versions without changing successful command exit behavior.
- Enforce migration strategy rules during runtime changes and persist migration state in mesh status.
- Add `mesh migrate <name>` to advance or complete an active migration.
- Keep `status.stable` authoritative for downstream one-shot operations _(see `one-shot-operations/add-one-shot-operations`)_.

**Non-Goals:**

- No external runtime catalog service or dynamic catalog download.
- No background migration worker, timers, or asynchronous state transition engine.
- No change to the store format beyond adding optional migration status fields and condition entries.
- No new top-level command family outside the existing `mesh` subcommands.

## Decisions

### Use an in-process runtime catalog

Represent the catalog as module-level data in `meshctl.py`, keyed by version with status values `supported`, `deprecated`, and `skipped`. This keeps catalog validation deterministic for tests and consistent with the existing single-file CLI architecture.

Alternative considered: store the catalog in a YAML or JSON fixture. That would make edits data-driven, but it adds file loading behavior that is not required by the checkpoint and would complicate packaging for a small static catalog.

### Preserve syntax validation before catalog validation

Keep `validate_runtime` responsible for field shape and semantic-version syntax, then layer catalog status validation on create/update when `spec.runtime` is present. Catalog validation should not run when the runtime value is absent, and it should avoid duplicate or misleading catalog errors when syntax validation has already rejected the value.

Alternative considered: replace `validate_runtime` with catalog lookup only. That would lose the existing generic invalid handling for malformed versions and make unsupported values harder to distinguish from malformed values.

### Thread warnings through successful create and update output

Have create and update collect warnings separately from errors, suppress warnings when any error exists, sort them by `field` then `message`, and include them in the JSON response for successful operations. The cleanest implementation is a small output helper that can print the public resource alone or wrap it with a `warnings` array when warnings are present.

Alternative considered: print warnings to stderr. The checkpoint defines a JSON `warnings` shape, and tests already parse stdout as JSON, so stdout JSON is the stable interface.

### Model migration as status owned by mesh updates

When a runtime changes from one catalog version to another, store the target in `spec.runtime`, add a `Migration` condition with `status = "True"` and `message = ""`, and write `status.migration` with `sourceRuntime`, `targetRuntime`, and the first strategy stage. This follows the existing update-driven lifecycle pattern _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_.

Alternative considered: store pending target runtime only under `status.migration` until completion. The checkpoint requires persisting the target in `spec.runtime` at migration start, so the spec remains the desired target state while status records migration progress.

### Keep stage sequencing explicit and minimal

Define stage sequences in code by strategy. `FullStop` and `RollingPatch` each use `["Migrate"]`; `LiveMigration` should use a small explicit multi-stage sequence so `mesh migrate` can demonstrate advancement before completion.

Alternative considered: infer stages from strategy names. Explicit sequences are easier to validate and test, especially because only `LiveMigration` has multiple stages.

### Add migrate as a mesh subcommand

Extend `build_parser` and `main` so `mesh migrate <name>` routes beside existing mesh CRUD operations. The handler should load the mesh, return the standard not-found shape for missing meshes, reject resources without active `status.migration`, advance the current stage, and print the full public mesh.

Alternative considered: implement migration advancement as `mesh update`. A dedicated subcommand matches the checkpoint and keeps progress transitions separate from spec mutation.

### Derive stability from condition state

Update the mesh status reconciliation/public upgrade path so `status.stable` is true only when required positive conditions are true and blocking conditions, including `Migration`, are absent or false. This preserves the one-shot command contract that reads `status.stable` without needing command-specific migration logic _(see `one-shot-operations/add-one-shot-operations`)_.

Alternative considered: let one-shot commands inspect migration details directly. That duplicates stability policy outside mesh status and risks divergent behavior.

## Risks / Trade-offs

- [Risk] Warning output may change the shape of successful create/update responses when warnings exist -> Mitigation: only wrap/include warnings when warnings exist, preserve existing plain resource output when none exist, and add tests for both shapes.
- [Risk] Active migration restrictions can conflict with partial update semantics -> Mitigation: compare the stored and candidate `spec.runtime` and `spec.migration.strategy` after merge, and only reject actual changes while allowing unrelated fields.
- [Risk] Multiple validation paths can produce duplicate errors -> Mitigation: keep syntax validation, catalog validation, strategy validation, and version-change validation as separate checks, but only run dependent checks when their input values are usable.
- [Risk] Existing stored meshes may not have `status.stable` or migration fields -> Mitigation: keep upgrade/public-resource normalization tolerant of missing fields and derive defaults from existing condition state.

## Migration Plan

1. Add runtime catalog constants, warning helpers, migration stage constants, and migration-state helpers in `meshctl.py`.
2. Extend create/update validation and output handling while preserving existing no-warning output.
3. Add migration start, advancement, completion, rollback, and stability derivation in the existing status helpers.
4. Add CLI parser and dispatch support for `mesh migrate <name>`.
5. Cover the checkpoint scenarios in `tests/test_meshctl_cli.py`.

Rollback is code rollback only; persisted resources with `status.migration` should remain readable because the new fields are optional status data and older paths already tolerate extra dictionary keys.

## Open Questions

- The checkpoint does not name the exact multi-stage `LiveMigration` sequence. The implementation should choose a clear deterministic sequence and keep it covered by tests.
- The checkpoint mentions LiveMigration rollback but does not define a CLI surface for requesting rollback. Implementation should either use an existing update shape if present or document a minimal local convention during apply.
