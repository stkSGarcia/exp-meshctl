## Why

The CLI currently models long-lived mesh resources and dependent vault resources, but it does not have a formal contract for one-shot operational work such as running tasks, taking snapshots, or recovering from snapshots. This change adds those operation resources so automation can create, inspect, execute, and validate them using the same resource-oriented command surface as existing meshctl resources.

## Related Work

### Related Changes

- `add-vault-resource-management`: Added a second persisted resource type and dependency-aware delete behavior. This change extends that resource-management model to three operational resource kinds and reuses the same conflict style for snapshot deletion when recoveries depend on it.
- `add-mesh-lifecycle-topology`: Expanded mesh management with update semantics, lifecycle-aware status, and validation rules. This change builds on those lifecycle and validation patterns for operation state transitions and run-time stability checks.
- `add-meshctl-mesh-crud`: Established the basic meshctl create, list, describe, and delete resource contract. This change complements it by adding create/list/describe/update/delete plus run for one-shot operation resources.

### Related Specs

- `mesh-resource-management/add-vault-resource-management`: Defines dependency conflict behavior for deleting resources referenced by another resource. This change adapts that pattern for `snapshot delete` when one or more `recovery` resources reference the snapshot.
- `mesh-resource-management/add-mesh-lifecycle-topology`: Defines mesh update behavior, immutable fields, and status-derived lifecycle semantics. This change reuses those validation and lifecycle concepts for immutable one-shot specs and run transitions.
- `vault-resource-management/add-vault-resource-management`: Defines a non-mesh resource command surface and immutable fields after creation. This change expands the same command-surface style to `task`, `snapshot`, and `recovery`.

## What Changes

- Add `meshctl task`, `meshctl snapshot`, and `meshctl recovery` resource commands for create, list, describe, update, delete, and run.
- Add validation/defaulting for task, snapshot, and recovery specs, including mesh and snapshot reference checks.
- Add immutable `spec` behavior for all three resource kinds after creation.
- Add run-state transitions through `Initializing`, `Running`, and the allowed terminal states for each kind.
- Add inline task execution semantics, snapshot storage references, unstable-mesh `Unknown` outcomes, and snapshot dependency protection.

## Capabilities

### New Capabilities

- `one-shot-operations`: Defines task, snapshot, and recovery resource management, validation, immutable spec behavior, run semantics, terminal phases, dependency protection, and JSON output/error contracts.

### Modified Capabilities

- None.

## Impact

- Affects `meshctl.py` command parsing and dispatch.
- Affects persistence and validation logic for resource kinds beyond meshes and vaults.
- Adds tests for operation CRUD, update immutability, run transitions, dependency protection, and JSON output/error formatting.
