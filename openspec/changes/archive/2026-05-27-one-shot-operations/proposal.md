## Why

meshctl currently manages long-lived mesh and vault resources but has no way to execute one-shot operations (tasks), capture point-in-time snapshots, or restore state from snapshots. Adding these three resource kinds closes the gap between resource management and operational workflows.

## What Changes

- Introduce three new resource kinds: `task`, `snapshot`, and `recovery`
- Each kind supports a full command surface: `create`, `list`, `describe`, `update`, `delete`, and `run`
- All three kinds follow a phase lifecycle: `Initializing` → `Running` → terminal state
- `spec` sections are fully immutable after creation
- `snapshot delete` is blocked while a recovery references the snapshot

## Capabilities

### New Capabilities

- `task-management`: CRUD + run lifecycle for task resources, including inline command execution with per-line failure semantics
- `snapshot-management`: CRUD + run lifecycle for snapshot resources, capturing mesh state into a storage reference
- `recovery-management`: CRUD + run lifecycle for recovery resources, restoring mesh state from a snapshot with mesh/snapshot cross-reference validation

### Modified Capabilities

## Impact

- `meshctl.py`: new command handlers for `task`, `snapshot`, and `recovery` subcommands
- `store.json` / in-memory store: new collections for tasks, snapshots, and recoveries
- Existing mesh and snapshot resources become dependencies for task/snapshot/recovery create and run
