## Why

`meshctl` currently models long-lived mesh and vault resources, but operational actions like tasks, snapshots, and recoveries are only described in checkpoint form. Adding one-shot operations gives the CLI a formal contract for executable, stateful resources that depend on meshes and snapshots.

## What Changes

- Add `task`, `snapshot`, and `recovery` command groups with `create -f <path>`, `list`, `describe <name>`, `update -f <path>`, `delete <name>`, and `run <name>` operations.
- Define shared lifecycle behavior for one-shot resources, including `Initializing`, `Running`, terminal states, terminal-state immutability, JSON output, and structured errors.
- Add task validation for required `spec.meshRef`, exclusive `spec.inline`/`spec.bundleRef`, inline execution failure handling, and run-state transitions.
- Add snapshot validation for required `spec.meshRef`, optional scoped capture, resource defaulting/validation, run behavior, unstable-mesh `Unknown` outcomes, and successful `status.storageRef`.
- Add recovery validation for required `spec.meshRef`, required `spec.snapshotRef`, snapshot/mesh consistency, optional scoped restore, resource defaulting/validation, and run behavior.
- Make the full `spec` immutable for `task`, `snapshot`, and `recovery` after create.
- Block `snapshot delete` while one or more recoveries reference the snapshot.

## Capabilities

### New Capabilities
- `one-shot-operations`: Defines task, snapshot, and recovery CLI operations, resource schemas, validation/defaulting, execution lifecycle, immutability, dependency protection, and JSON output contracts.

### Modified Capabilities
None.

## Impact

- Affected code: `meshctl.py` command routing, YAML normalization, validation/defaulting helpers, store helpers, resource lookup, lifecycle execution, dependency checks, and JSON output.
- Affected interface: new `uv run --project /app meshctl.py task ...`, `snapshot ...`, and `recovery ...` commands.
- Affected persistence: the local JSON store must persist `tasks`, `snapshots`, and `recoveries` alongside existing resource collections while preserving current mesh and vault behavior.
- Affected tests: CLI coverage for CRUD, list ordering, validation failures, update immutability, run transitions, unstable-mesh outcomes, snapshot storage refs, recovery snapshot consistency, and delete dependency conflicts.
- Dependencies: no new external dependency is expected beyond the existing YAML and JSON support.
