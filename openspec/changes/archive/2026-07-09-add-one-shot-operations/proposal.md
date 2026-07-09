## Why

Mesh users need a first-class way to model operational work that runs against existing meshes. The CLI already manages persisted mesh-style resources, and this change extends that contract to one-shot operations for tasks, snapshots, and recoveries.

## Related Work

### Related Changes

- `add-mesh-lifecycle-topology`: Established lifecycle-aware mesh resource behavior, including create/list/describe/delete/update flows and status semantics. This change extends the same resource-management shape to operational resources that can be executed with `run`.
- `add-vault-resource-management`: Added a dependent resource type that references meshes and uses dependency conflict validation. This change complements that pattern with additional mesh-referenced resources and snapshot-to-recovery dependency protection.

### Related Specs

- `mesh-resource-management/add-vault-resource-management`: Defines dependency conflicts for resources that reference meshes. This change reuses that conflict pattern for `snapshot delete` when recoveries depend on a snapshot.
- `mesh-resource-management/add-mesh-lifecycle-topology`: Defines lifecycle-aware resource management and update behavior. This change adapts that command surface for `task`, `snapshot`, and `recovery`, including immutable specs and state transitions.

## What Changes

- Add `task`, `snapshot`, and `recovery` resource kinds.
- Add create, list, describe, update, delete, and run commands for each new kind.
- Validate mesh references, snapshot references, exclusive task source fields, resource quantity fields, and operation-specific scope fields.
- Start newly created one-shot resources in `Initializing`.
- Execute `run` only from `Initializing`, transitioning through `Running` to the resource-specific terminal states.
- Treat `spec` as immutable after create for all three new resource kinds.
- Reject snapshot deletion while one or more recoveries reference the snapshot.
- Emit JSON output and the existing error format for success and validation/conflict failures.

## Capabilities

### New Capabilities

- `one-shot-operations`: Defines task, snapshot, and recovery resources, their command surface, validation rules, execution lifecycle, immutability, dependency protection, and status output.

### Modified Capabilities

- None.

## Impact

- CLI command parsing and dispatch for `task`, `snapshot`, and `recovery`.
- Resource persistence and lookup for the three new kinds.
- Validation logic for resource references, mutually exclusive fields, quantities, scope objects, immutable specs, and deletion conflicts.
- Run execution logic and status transitions.
- Test coverage for creation, listing, describing, updating, deleting, running, and failure cases.
