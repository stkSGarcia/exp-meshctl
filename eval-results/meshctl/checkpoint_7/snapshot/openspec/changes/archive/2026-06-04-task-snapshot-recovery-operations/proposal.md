## Why

The tool currently manages mesh and vault resources but lacks any mechanism for executing operations against a mesh, capturing mesh state, or restoring from a prior state. Users need a way to run arbitrary commands against a mesh, take point-in-time snapshots, and recover from those snapshots — all as first-class, tracked resources with lifecycle state.

### Related Specs

**`vault-management`** — Manages vault resources scoped to a mesh, including CRUD operations, validation, and immutability constraints. _Why it exists: TBD - created by archiving change vault-resource-management. Update Purpose after archive._ This change builds on that spec by following the same CRUD command surface, error output format, and immutability patterns — extending them to three new one-shot operational resource kinds.

The vault-management spec establishes the project's standard for resource validation, immutability enforcement, and JSON error output. This change applies those same contracts to task, snapshot, and recovery resources, ensuring consistency across all resource kinds in the tool.

## What Changes

- Add `task` resource kind: create, list, describe, update, delete, and **run**
- Add `snapshot` resource kind: create, list, describe, update, delete, and **run**
- Add `recovery` resource kind: create, list, describe, update, delete, and **run**
- Each kind transitions through `Initializing → Running → terminal` state machine on `run`
- Entire `spec` section is immutable after creation for all three kinds
- `snapshot delete` is blocked when active recoveries reference the snapshot (dependency protection)
- Task `run` executes inline commands line-by-line with `FAIL:` prefix detection
- Snapshot `run` captures mesh data (scoped or full) and writes a `storageRef`
- Recovery `run` restores mesh state from a referenced snapshot

## Capabilities

### New Capabilities

- `task-operations`: CRUD and run lifecycle for task resources, including inline command execution, `FAIL:` line detection, and `Initializing → Running → Succeeded/Failed` state machine
- `snapshot-operations`: CRUD and run lifecycle for snapshot resources, including scoped capture, resource quantity validation, mesh stability check, and `Initializing → Running → Succeeded/Failed/Unknown` state machine with `storageRef` output
- `recovery-operations`: CRUD and run lifecycle for recovery resources, including snapshot cross-reference validation, mesh ownership check, mesh stability check, and `Initializing → Running → Succeeded/Failed/Unknown` state machine

### Modified Capabilities

## Impact

- New CLI entry points: `meshctl task`, `meshctl snapshot`, `meshctl recovery`
- New in-memory/persistent stores for task, snapshot, and recovery resources
- Snapshot store must be queryable by recovery for dependency protection
- All three kinds share the JSON error format established by mesh-management and vault-management
