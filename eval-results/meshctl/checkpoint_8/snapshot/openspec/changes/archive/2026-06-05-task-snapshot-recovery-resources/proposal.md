## Why

`meshctl` currently manages mesh and vault resources but has no mechanism for one-shot operational actions — running ad-hoc tasks against a mesh, capturing a snapshot of its data, or recovering from a previous snapshot. These are essential day-two operations for any production cluster management tool, and their absence forces operators to use out-of-band tooling.

### Related Changes

**`mesh-lifecycle-and-topology`** — Extended the mesh resource model with a lifecycle state machine (Running, Scaling, Stopped) and enriched status model including `stable` and `conditions`. This change reuses that state machine pattern and `stable` flag for the three new operational resource kinds.

## What Changes

- Add `task` resource kind: create, list, describe, update, delete, and run tasks that execute inline commands or bundle references against a mesh.
- Add `snapshot` resource kind: create, list, describe, update, delete, and run snapshots that capture mesh data to storage.
- Add `recovery` resource kind: create, list, describe, update, delete, and run recoveries that restore mesh data from a snapshot.
- All three kinds share a common `run` command that drives a state machine through `Initializing → Running → terminal`.
- Entire `spec` section is immutable after creation for all three kinds.
- `snapshot delete` is protected when referenced by a recovery (dependency protection).

## Capabilities

### New Capabilities

- `task-management`: CRUD + run lifecycle for task resources with inline command execution and `inline`/`bundleRef` mutual exclusion.
- `snapshot-management`: CRUD + run lifecycle for snapshot resources with scoped data capture, storage resource configuration, and mesh stability gating.
- `recovery-management`: CRUD + run lifecycle for recovery resources with snapshot cross-reference validation, scoped restore, and mesh stability gating.

### Modified Capabilities

*(none)*

## Impact

- New storage layer entries for `task`, `snapshot`, and `recovery` resource kinds.
- New CLI command groups: `meshctl task`, `meshctl snapshot`, `meshctl recovery`.
- `snapshot delete` must check for referencing recovery resources before proceeding.
- Output format follows existing JSON conventions: success prints full resource JSON, errors print `{"errors": [...]}`.
