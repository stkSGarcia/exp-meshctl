## Why

Operators need a consistent way to model one-shot work that targets an existing mesh: executable tasks, point-in-time snapshots, and recoveries from those snapshots. Adding these resource kinds extends the existing `meshctl` resource model beyond long-lived mesh and vault resources while preserving the same JSON output, validation, and lifecycle conventions.

## What Changes

- Add `task`, `snapshot`, and `recovery` resource kinds with create, list, describe, update, delete, and run commands.
- Initialize each one-shot resource in `Initializing`, make terminal states irreversible, and allow `run` only from `Initializing`.
- Validate mesh references, task inline versus bundle inputs, snapshot and recovery resource quantities, recovery snapshot references, and snapshot/recovery mesh consistency.
- Enforce full `spec` immutability for task, snapshot, and recovery updates.
- Execute inline tasks line-by-line with deterministic failure handling for `FAIL:` lines.
- Produce snapshot and recovery run outcomes, including `Unknown` when the target mesh is unstable and stable `storageRef` values for successful snapshots.
- Prevent snapshot deletion while recoveries depend on that snapshot.

## Related Work

### Related Changes

- `mesh-resource-management/add-mesh-lifecycle-topology`: Introduced mesh update semantics, topology-related state, and validation rules for existing mesh resources. This change complements that lifecycle work by adding short-lived operational resources that depend on a mesh and observe mesh stability at run time.
- `mesh-resource-management/add-meshctl-mesh-crud`: Established the `mesh` command surface for create, list, describe, and delete operations through `meshctl.py`. This change extends the same CRUD-style CLI pattern to `task`, `snapshot`, and `recovery`, then adds a `run` action for execution.
- `vault-resource-management/add-vault-resource-management`: Added another resource family with create, list, describe, update, and delete operations through `meshctl`. This change reuses that multi-kind resource-management shape while adding one-shot lifecycle execution and dependency protection.

### Related Specs

- `mesh-resource-management/add-mesh-lifecycle-topology`: Defines mesh lifecycle updates and stability-related behavior that one-shot snapshot and recovery runs build on when deciding whether to succeed or become `Unknown`.
- `mesh-resource-management/add-meshctl-mesh-crud`: Defines the JSON command surface and resource lookup conventions that one-shot operations should follow for create, list, describe, update, and delete.
- `vault-resource-management/add-vault-resource-management`: Defines a reusable pattern for additional resource kinds, quantity validation, and update/delete behavior that informs snapshot and recovery validation.

## Capabilities

### New Capabilities

- `one-shot-operations`: Covers `task`, `snapshot`, and `recovery` resources, their command surface, validation, execution state transitions, immutable specs, and snapshot dependency protection.

### Modified Capabilities

- None.

## Impact

- CLI command parsing and dispatch for `meshctl task`, `meshctl snapshot`, and `meshctl recovery`.
- Resource persistence and lookup for three new resource kinds.
- YAML validation, JSON output, and structured error handling.
- Runtime state transitions for one-shot executions.
- Deletion safeguards for snapshots referenced by recoveries.
