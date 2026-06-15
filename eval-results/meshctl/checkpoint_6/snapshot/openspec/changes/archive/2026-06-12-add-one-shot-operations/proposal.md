## Why

Mesh users need a formal contract for one-shot operational resources that execute work against existing meshes and carry clear terminal status. This change adds task, snapshot, and recovery resources with consistent CRUD behavior, run semantics, validation, and dependency protection.

## Related Work

### Related Changes

- `add-vault-resource-management`: Introduced a second persisted resource type with mesh references and dependency checks. This change extends that pattern to operational resources that reference meshes and, for recoveries, snapshots.
- `add-mesh-lifecycle-topology`: Expanded the mesh command surface with update semantics, field validation, and lifecycle-aware status. This change reuses the same CLI and status contract style for one-shot operations.
- `add-meshctl-mesh-crud`: Established the baseline `meshctl.py` CRUD, YAML input, persistence, JSON output, and error formatting behavior. This change complements that work by adding non-mesh resource kinds with the same user-facing shape.

### Related Specs

- `mesh-resource-management/add-vault-resource-management`: Covers mesh deletion dependency conflicts for resources that reference a mesh. This change adapts that dependency protection model for snapshot deletion when recoveries reference the snapshot.
- `mesh-resource-management/add-mesh-lifecycle-topology`: Covers mesh CLI operations, update behavior, validation, and status handling. This change builds on its command-surface and lifecycle vocabulary for `task`, `snapshot`, and `recovery`.
- `vault-resource-management/add-vault-resource-management`: Covers vault CLI CRUD, immutable fields, mesh references, and JSON error output. This change reuses those resource-management patterns while adding a `run` operation and stricter spec immutability for one-shot resources.

## What Changes

- Add `task`, `snapshot`, and `recovery` resource kinds to `meshctl`.
- Add `create`, `list`, `describe`, `update`, `delete`, and `run` commands for each new kind.
- Validate one-shot specs, including mesh references, task inline/bundle exclusivity, snapshot references, resource quantities, and recovery/snapshot mesh compatibility.
- Start all newly created one-shot resources in `status.state = "Initializing"`.
- Execute `run` only from `Initializing`, transition through `Running`, and finish in the allowed terminal phases.
- Treat the entire `spec` section as immutable after creation for all three new resource kinds.
- Prevent deleting snapshots while recoveries reference them.
- Preserve existing JSON output and error formatting conventions.

## Capabilities

### New Capabilities

- `one-shot-operations`: Defines task, snapshot, and recovery resources, their command surface, validation rules, run lifecycle, status fields, immutability, and snapshot dependency protection.

### Modified Capabilities

- None.

## Impact

- `meshctl.py`: Add parser branches, persistence buckets, validation helpers, run handlers, update immutability checks, and dependency checks.
- `tests/test_meshctl_cli.py`: Add CLI coverage for task, snapshot, and recovery create/list/describe/update/delete/run behavior and validation failures.
- Persistent store shape: Add `tasks`, `snapshots`, and `recoveries` collections alongside existing resource collections.
