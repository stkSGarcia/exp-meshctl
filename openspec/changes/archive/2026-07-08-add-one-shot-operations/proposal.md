## Why

Operators need run-once operational resources for imperative work, backups, and restores without inventing ad hoc commands outside the mesh resource model. Adding task, snapshot, and recovery resources gives the CLI a consistent way to create, inspect, execute, and protect one-shot operations.

## What Changes

- Add `task`, `snapshot`, and `recovery` resource kinds with YAML-backed `create`, `list`, `describe`, `update`, `delete`, and `run` commands.
- Add validation for required mesh and snapshot references, exclusive task command sources, quantity formats, scoped snapshot/recovery data, and snapshot/recovery mesh ownership.
- Add run-time state transitions from `Initializing` through `Running` into the allowed terminal phases for each resource.
- Add immutable specs for all one-shot operation resources after creation.
- Add dependency protection that blocks deleting snapshots referenced by recoveries.
- Add JSON output and existing error formatting for resource output and validation failures.

## Related Work

### Related Changes

- `add-mesh-lifecycle-topology`: This prior change expanded mesh management beyond CRUD into update semantics, topology validation, and lifecycle-aware status. This change complements it by applying lifecycle-aware state transitions to operational resources that act on meshes.
- `add-vault-resource-management`: This prior change introduced a second persisted resource type with its own validation and dependency rules. This change extends that pattern to one-shot resources, including references across resource kinds.

### Related Specs

- `mesh-resource-management/add-meshctl-mesh-crud`: Establishes the CLI pattern for YAML-backed resource create, list, describe, and delete flows. This change reuses that command shape for task, snapshot, and recovery resources.
- `mesh-resource-management/add-mesh-lifecycle-topology`: Establishes update behavior, lifecycle validation, status fields, and resource quantity validation. This change adapts those conventions for immutable one-shot specs and run-time status transitions.
- `vault-resource-management/add-vault-resource-management`: Establishes persisted dependent resources with validation and update/delete semantics. This change builds on that model for snapshot and recovery references.

## Capabilities

### New Capabilities

- `one-shot-operations`: Covers task, snapshot, and recovery resources, including CRUD commands, run commands, validation, lifecycle states, immutable specs, dependency protection, and JSON output.

### Modified Capabilities

- None.

## Impact

- CLI command routing in `meshctl.py` must accept three additional resource kinds and their `run` operation.
- Resource persistence, validation, update, delete, and output paths must support the new kinds.
- Tests must cover happy paths, validation errors, immutable updates, run transitions, snapshot/recovery safety checks, and sorted JSON list output.
