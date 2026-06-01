## Why

The meshctl tool currently manages meshes and vaults but provides no way to execute operations against a mesh, capture its state as a snapshot, or restore data from a snapshot. These one-shot operational primitives are essential for day-to-day mesh administration: running custom tasks, taking backups, and recovering from failures.

### Related Specs

**`mesh-management`** — TBD - created by archiving change implement-meshctl. Update Purpose after archive. _Why it exists: TBD - created by archiving change implement-meshctl. Update Purpose after archive._ This change extends that spec by introducing three new resource kinds (`task`, `snapshot`, `recovery`) that follow the same YAML input schema, name validation, resource quantity formats, error output format, and immutability patterns already established for mesh resources.

These three resource kinds collectively round out the operational surface of meshctl: tasks enable custom execution, snapshots enable point-in-time data capture, and recoveries enable controlled restoration — all scoped to a specific mesh and sharing the same lifecycle and error contract.

## What Changes

- Add `meshctl task create|list|describe|update|delete|run` commands
- Add `meshctl snapshot create|list|describe|update|delete|run` commands
- Add `meshctl recovery create|list|describe|update|delete|run` commands
- All three kinds follow the same YAML input schema (`metadata` + `spec`) and name validation as mesh resources
- All three kinds have an immutable `spec` after creation
- Snapshots block deletion when referenced by a recovery (`conflict` error)
- Task `run` executes inline commands with per-line failure tracking
- Snapshot `run` captures mesh data and sets `status.storageRef`
- Recovery `run` restores data from a referenced snapshot
- All three use the same lifecycle phases: `Initializing` → `Running` → terminal

## Capabilities

### New Capabilities

- `task-management`: CRUD + run for the `task` resource kind, including inline script execution with line-level failure reporting
- `snapshot-management`: CRUD + run for the `snapshot` resource kind, including scoped data capture and storage reference output
- `recovery-management`: CRUD + run for the `recovery` resource kind, including snapshot cross-reference validation and scoped restore

### Modified Capabilities

_(none — existing mesh-management and vault-management specs are unchanged)_

## Impact

- `meshctl.py`: new CLI routes for `task`, `snapshot`, `recovery` sub-commands
- Storage layer: three new resource stores (tasks, snapshots, recoveries)
- Validation: reuses existing quantity parsers and name-validation logic from mesh-management
- Dependency check: `snapshot delete` must query the recovery store before proceeding
