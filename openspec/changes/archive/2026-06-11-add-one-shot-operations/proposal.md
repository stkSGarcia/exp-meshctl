## Why

Operators need first-class CLI resources for one-shot operational work: executing ad hoc tasks, capturing mesh snapshots, and recovering mesh data from snapshots. Modeling these as resources gives the existing meshctl workflow a consistent create/list/describe/update/delete/run lifecycle with persisted status and structured validation.

## What Changes

- Add `task`, `snapshot`, and `recovery` resource kinds to the `meshctl.py` command surface.
- Support create, list, describe, update, delete, and run operations for each new kind.
- Persist one-shot operation specs and lifecycle status, starting each created resource in `Initializing`.
- Validate mesh and snapshot references, mutually exclusive task source fields, snapshot/recovery resource quantities, and immutable specs after create.
- Add run-time transitions and terminal state handling for task, snapshot, and recovery resources.
- Protect snapshots from deletion while recoveries reference them.

## Capabilities

### New Capabilities
- `one-shot-operations`: Defines task, snapshot, and recovery resource models, CLI operations, validation, lifecycle transitions, dependency protection, and JSON output.

### Modified Capabilities

## Impact

- Affects `meshctl.py` command parsing, persistence, validation helpers, lifecycle/status handling, and JSON output paths.
- Requires tests for the new resource command surfaces, validation failures, run transitions, immutable spec updates, and snapshot dependency conflicts.
