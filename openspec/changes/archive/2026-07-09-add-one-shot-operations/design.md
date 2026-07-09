## Context

`meshctl.py` currently owns CLI parsing, JSON store persistence, validation, output formatting, and resource operations for meshes and vaults. Meshes already provide name validation, quantity validation, lifecycle status, and dependency protection from vaults; vaults already provide a second persisted resource kind that references meshes.

This change adds three persisted one-shot resource kinds: `task`, `snapshot`, and `recovery`. They use the same command shape as existing resources, plus a `run` operation that moves a resource from `Initializing` through `Running` into a terminal phase.

## Related Work

**`mesh-resource-management/add-vault-resource-management`**: Defines dependency conflicts for resources that reference meshes — informs the snapshot deletion conflict design because the related intent introduced dependent resource management and conflict validation for mesh-referenced resources.

**`mesh-resource-management/add-mesh-lifecycle-topology`**: Defines lifecycle-aware create/list/describe/delete/update behavior and immutable storage size updates — informs command dispatch, update atomicity, status transitions, and spec immutability because the related intent expanded mesh resources into lifecycle-aware status and update semantics.

## Goals / Non-Goals

**Goals:**

- Add `task`, `snapshot`, and `recovery` commands to the existing `argparse` command tree.
- Persist one-shot resources beside existing `meshes` and `vaults` collections.
- Reuse current validation and output helpers for names, quantities, YAML parsing, JSON output, and errors.
- Keep one-shot updates atomic and reject every spec mutation after create.
- Simulate `run` deterministically so CLI behavior is testable without external systems.

**Non-Goals:**

- Execute real shell commands from task inline content.
- Implement bundle loading for `spec.bundleRef`; the field is accepted as a reference only.
- Implement real snapshot storage, backup transport, or restore side effects.
- Split `meshctl.py` into multiple modules during this change.

## Decisions

### Store one-shot resources as top-level collections

Add `tasks`, `snapshots`, and `recoveries` keys to the JSON store. `load_store()` should default missing collections to `{}` so existing stores continue to load, and `save_store()` can persist the expanded shape. This mirrors the current `meshes` and `vaults` collections and keeps lookup simple.

Alternative considered: nest one-shot resources under each mesh. That would make dependency checks and global listing more awkward and would diverge from the existing vault collection shape. _(see `mesh-resource-management/add-vault-resource-management`)_

### Add generic one-shot command helpers

Implement thin command functions for each kind and share helpers for create/list/describe/update/delete/run where behavior is identical. Kind-specific normalization and validation should stay explicit for readability:

- `normalize_task_for_create`
- `normalize_snapshot_for_create`
- `normalize_recovery_for_create`
- `validate_one_shot_spec_immutable`
- `run_task`, `run_snapshot`, and `run_recovery`

Alternative considered: copy full handlers for all three resource kinds. That would be fast to write but would triple not-found, list sorting, update, and immutability logic.

### Preserve existing error and output conventions

Use `print_json`, `print_errors`, `error`, `validate_name`, `normalize_required_string`, and quantity validation helpers. Missing one-shot resources should use `metadata.name` with type `not_found`, and validation failures should return JSON on stdout with no stderr. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

Alternative considered: introduce resource-specific error shapes for one-shot operations. The checkpoint requires the same validation and not-found shape as mesh resources, so shared conventions are preferable.

### Treat one-shot spec as fully immutable

For updates, deep-merge the incoming patch with the stored resource only after confirming the requested `spec` subtree is identical to the stored `spec` subtree. Any changed or newly added spec field should produce an `immutable` error and leave the store untouched. This generalizes the current mesh storage-size immutability pattern to the entire one-shot spec. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

Alternative considered: allow metadata/status-only updates. The current command surface only accepts YAML resource updates and the checkpoint makes the whole `spec` immutable, so the implementation should accept no spec changes while preserving omitted values.

### Simulate run transitions synchronously

`run` should validate that the resource is in `Initializing`, persist a transient `Running` transition internally if useful, then persist the terminal state before printing. Task inline content is deterministic: each line is a command, and the first `FAIL:` line produces `Failed` with the required indexed detail. Snapshot and recovery check the referenced mesh at run time; unstable meshes produce `Unknown` with detail, stable meshes succeed, and snapshots also set a stable non-empty `storageRef`.

Alternative considered: model asynchronous pending transitions like mesh scaling. The checkpoint only requires transition semantics and terminal output, and synchronous execution keeps the CLI tests deterministic.

## Risks / Trade-offs

- Duplicate resource plumbing across meshes, vaults, and one-shot kinds -> Mitigate by extracting narrow helpers only where the new kinds share behavior.
- Store migrations could drop new collections for old stores -> Mitigate by updating `empty_store()` and `load_store()` to always include all five collections.
- Full-spec immutability could produce broad errors without precise field paths -> The contract allows flexible field paths and messages, so tests should assert `type = "immutable"` and atomic persistence.
- Snapshot/recovery `Unknown` depends on mesh stability status being current -> Use the stored mesh state at run time and rely on existing mesh describe/update lifecycle behavior.

## Migration Plan

No explicit migration command is required. Existing stores without one-shot collections should load with empty `tasks`, `snapshots`, and `recoveries`, and subsequent writes should persist the expanded store shape.

## Open Questions

None for the proposal. The implementation can choose stable deterministic `storageRef` text, such as `snapshot:<name>`, as long as it is non-empty and stable.
