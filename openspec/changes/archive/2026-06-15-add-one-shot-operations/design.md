## Context

`meshctl.py` currently implements mesh and vault resource management in a single CLI module with JSON persistence through `MESHCTL_STORE`, YAML input parsing, shared error formatting, and helper-based validation/defaulting. The one-shot operation resources should fit that structure so `task`, `snapshot`, and `recovery` behave like first-class persisted resources without introducing a new runtime service or storage layer.

## Related Work

> **`mesh-resource-management/add-vault-resource-management`**: Defines dependency conflict behavior for deleting resources referenced by another resource — informs snapshot dependency protection because this change must reject deletion when recoveries reference a snapshot.

> **`mesh-resource-management/add-mesh-lifecycle-topology`**: Defines update behavior, immutable fields, and lifecycle/status semantics — informs run transition validation and unstable-mesh checks because one-shot resources have explicit state machines and rely on mesh stability at execution time.

> **`vault-resource-management/add-vault-resource-management`**: Defines a non-mesh resource command surface and immutable fields after creation — informs the reusable command dispatch and spec immutability approach because this change adds three additional non-mesh resource kinds.

## Goals / Non-Goals

**Goals:**

- Add persisted `task`, `snapshot`, and `recovery` collections to the existing store.
- Add CLI dispatch for all required commands and keep JSON output/error formatting consistent with current mesh/vault behavior.
- Validate references, resource quantities, task source exclusivity, snapshot/recovery scopes, immutable specs, run-state preconditions, and snapshot dependency conflicts.
- Implement deterministic local run simulation for inline tasks, snapshots, and recoveries.
- Cover the new behavior in `tests/test_meshctl_cli.py`.

**Non-Goals:**

- Execute real shell commands for task inline content.
- Create real snapshot storage or restore data from storage.
- Add external services, background workers, or asynchronous execution.
- Change existing mesh or vault command behavior except where store upgrade code must preserve older store shapes.

## Decisions

### Extend the Existing Store Shape

Add top-level store collections for `tasks`, `snapshots`, and `recoveries` alongside `meshes` and `vaults`. `empty_store()` and `load_store()` should default missing collections to empty dictionaries so older stores remain readable.

Alternative considered: store one-shot resources in a generic `operations` collection keyed by kind. Separate top-level collections are simpler for dependency checks, list sorting, and compatibility with the current mesh/vault collection style.

### Use Shared Generic Resource Helpers

Introduce small helpers for common one-shot CRUD behavior: collection lookup by kind, resource not-found errors, sorted list output, spec immutability comparison, `Initializing` status setup, and run-state validation. Keep kind-specific normalization and run logic separate where validation diverges.

Alternative considered: copy mesh/vault command functions for each new kind. That would be faster initially but would triple the same CRUD and state validation code.

### Preserve Current Error Contract

Use `print_errors()`, `error()`, `validate_name()`, `normalize_required_string()`, and the quantity validators already used by mesh resources. Snapshot and recovery memory/CPU validation should call the existing quantity normalization paths so units and request/limit behavior stay consistent _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_.

Alternative considered: validate one-shot quantities with looser string checks. Reusing the existing validators avoids a second quantity dialect.

### Treat Run as Synchronous State Mutation

`run` should validate the resource is `Initializing`, set `Running` internally, immediately compute the terminal state, persist the result, and print the final resource. Inline task execution is simulated by scanning each line for `FAIL:`; snapshot/recovery execution checks the referenced mesh status at run time.

Alternative considered: persist `Running` and require a later command to complete. The checkpoint requires transitions, but the current CLI has no worker loop; synchronous mutation keeps tests deterministic.

### Keep Public Output Kind-Specific

Add public projection helpers for one-shot resources so `status.detail` appears only for `Failed` or `Unknown`, and `status.storageRef` appears only for a succeeded snapshot. This is safer than printing raw stored resources because run logic may keep intermediate or implementation-only fields.

Alternative considered: store only public fields. A projection helper matches the existing `public_resource()` and `public_vault()` pattern and leaves room for internal state if needed.

## Risks / Trade-offs

- Store compatibility regression -> Mitigate by updating `load_store()` to always return all five collections and by testing legacy store loading.
- Incomplete immutability comparison for omitted fields -> Mitigate by comparing the complete normalized candidate spec with the stored spec, not just fields present in the update document.
- Ambiguous scope validation depth -> Mitigate by accepting only object-shaped `scope` values with the specified keys and list/string named-item values as implementation detail, while preserving the required capture/restore semantics.
- Run output may hide the `Running` transition -> Mitigate by persisting final state synchronously while tests assert final status and invalid reruns; the transition is internal to the run operation.

## Migration Plan

1. Extend store loading/defaulting to include `tasks`, `snapshots`, and `recoveries`.
2. Add parser dispatch and one-shot CRUD/run functions.
3. Add normalization, validation, public output, and run helpers.
4. Add tests for each resource kind and error path.
5. Rollback is removing the new commands and collections; older mesh/vault stores remain compatible because missing one-shot collections default to empty.

## Open Questions

- None. The checkpoint provides exact command names, fields, phases, and required error shapes.
