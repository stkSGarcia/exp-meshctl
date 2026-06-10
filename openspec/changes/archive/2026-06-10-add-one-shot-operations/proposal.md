## Why

The CLI can manage long-lived mesh and vault resources, but it does not yet model one-shot operational workflows such as command tasks, snapshots, and recoveries. Adding these resources gives operators a consistent CRUD and execution contract for operational actions while preserving the existing JSON output and validation style.

## What Changes

- Add `task`, `snapshot`, and `recovery` resource kinds with `create`, `list`, `describe`, `update`, `delete`, and `run` commands.
- Require all three kinds to use mesh-style metadata name validation, JSON output, structured errors, and lexicographic list ordering.
- Define task inputs with required `spec.meshRef` and exactly one of `spec.inline` or `spec.bundleRef`.
- Define snapshot inputs with required `spec.meshRef`, optional storage, optional scope, and resource quantity validation/defaulting.
- Define recovery inputs with required `spec.meshRef`, required `spec.snapshotRef`, optional scope, snapshot/mesh consistency validation, and resource quantity validation/defaulting.
- Add run behavior for all three resources, including valid starting phase, state transitions, terminal state rules, task inline failure handling, unstable mesh handling for snapshots and recoveries, and snapshot storage references.
- Make the entire `spec` immutable after create for task, snapshot, and recovery resources.
- Block `snapshot delete` when one or more recovery resources reference the snapshot.

## Capabilities

### New Capabilities
- `one-shot-operations`: Defines task, snapshot, and recovery CLI resource operations, specs, validation, lifecycle execution, status output, immutability, and snapshot dependency protection.

### Modified Capabilities

## Impact

- Affected code: `meshctl.py` and any helpers for CLI routing, validation, defaulting, persistence, status transitions, dependency lookup, and JSON output.
- Affected interface: new `uv run --project /app meshctl.py task ...`, `snapshot ...`, and `recovery ...` command surfaces.
- Affected tests: CLI coverage for task/snapshot/recovery CRUD, sorted list output, mesh and snapshot reference validation, task source exclusivity, run transitions, failure and unknown states, spec immutability, snapshot dependency conflicts, and output shape.
- Dependencies: no new external dependencies are expected beyond existing YAML parsing and JSON support.
