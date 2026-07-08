## Context

`meshctl.py` currently owns command parsing, persistence, validation, JSON output, and resource-specific behavior for meshes and vaults. The one-shot operations add three new resource families that share the existing local JSON store and CLI conventions, but introduce an explicit execution action and terminal lifecycle states.

## Related Work

**`mesh-resource-management/add-mesh-lifecycle-topology`**: Defines mesh update and lifecycle behavior, including mesh command extensions and stability-related state — informs the run-time mesh stability check for snapshot and recovery because one-shot resources are executed against an existing mesh and must react to the mesh state at run time.

**`mesh-resource-management/add-meshctl-mesh-crud`**: Defines the original `meshctl.py` create, list, describe, and delete command surface — informs command parser and output shape decisions because task, snapshot, and recovery should feel like first-class resource kinds in the same CLI.

**`vault-resource-management/add-vault-resource-management`**: Defines another resource family with create, list, describe, update, delete, mesh reference validation, and resource quantity reuse — informs the shared helper design for additional resource collections because one-shot resources follow the same local resource-management pattern with extra run semantics.

## Goals / Non-Goals

**Goals:**

- Add `task`, `snapshot`, and `recovery` as first-class `meshctl.py` resource kinds with consistent JSON output and error handling.
- Reuse existing name validation, YAML loading, store persistence, resource quantity validation, and mesh reference checks where possible.
- Store one-shot resources durably in the same local store as meshes and vaults.
- Keep execution deterministic and local: inline task commands are simulated by line inspection, snapshot storage references are stable generated identifiers, and unstable meshes produce `Unknown`.
- Protect snapshots from deletion while recoveries reference them.

**Non-Goals:**

- Execute real shell commands or external bundles for tasks.
- Persist actual snapshot payload data or restore mesh data from snapshots.
- Add background jobs, asynchronous polling, or external storage integrations.
- Change existing mesh or vault behavior except where store upgrade logic must preserve backward compatibility.

## Decisions

1. Extend the existing store schema with `tasks`, `snapshots`, and `recoveries`.

   `empty_store()` and `load_store()` should return collections for all five resource kinds. Existing stores that contain only `meshes` and `vaults` should upgrade in memory with empty one-shot collections before use. This keeps persistence simple and avoids a migration step. _(see `vault-resource-management/add-vault-resource-management`)_

   Alternative considered: create separate store files per one-shot kind. That would reduce per-file contention but would duplicate the current persistence model and complicate dependency checks.

2. Add a generic one-shot command dispatcher for parser and CRUD operations.

   `build_parser()` and `main()` should register the same operation set for `task`, `snapshot`, and `recovery`, then dispatch into shared helpers with kind-specific normalization, public projection, and run behavior. The existing `mesh` and `vault` functions can remain intact while one-shot helpers reduce repeated CRUD plumbing. _(see `mesh-resource-management/add-meshctl-mesh-crud`)_

   Alternative considered: copy full CRUD functions for each kind. That is straightforward but makes update immutability, list sorting, and not-found behavior easier to drift.

3. Normalize on create and treat `spec` as immutable after creation.

   Each create path should build a canonical resource with `metadata`, normalized `spec`, and `status.state = "Initializing"`. Update should apply metadata/status-safe changes only if the incoming normalized or merged `spec` is identical to the stored spec; otherwise return an `immutable` error. This mirrors existing normalization while enforcing one-shot terminal semantics.

   Alternative considered: allow partial `spec` updates before run. The checkpoint requires full spec immutability after create, so the design rejects all spec changes including adding omitted optional fields.

4. Model run as a synchronous local state transition.

   `run` should reject any state except `Initializing`, set `Running` during execution, and persist a terminal result before printing the updated resource. Tasks end in `Succeeded` or `Failed`; snapshots and recoveries end in `Succeeded`, `Failed`, or `Unknown`. Terminal states are irreversible because subsequent `run` calls fail the state precondition.

   Alternative considered: expose a long-running `Running` state that completes on later describe. The checkpoint asks for transition through `Running`, not asynchronous completion, and tests can verify final state deterministically.

5. Use mesh stability at execution time for snapshot and recovery.

   Snapshot and recovery `run` should look up the referenced mesh at run time and inspect `status.stable`. If it is `false`, the one-shot resource becomes `Unknown` with non-empty detail; otherwise the run succeeds. A successful snapshot gets a stable deterministic `status.storageRef`, such as one derived from the snapshot name. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

   Alternative considered: validate mesh stability at create time. That would not satisfy the run-time behavior and would allow stale decisions if the mesh changes before execution.

6. Enforce recovery and snapshot dependencies from the store.

   Recovery create validates that `spec.snapshotRef` exists and that the snapshot belongs to the same mesh. Snapshot delete scans recoveries for matching `spec.snapshotRef` and returns a `conflict` error naming the dependent recoveries.

   Alternative considered: store reverse references on snapshots. Scanning the in-memory recovery collection keeps the source of truth in recovery specs and avoids synchronization bugs.

## Risks / Trade-offs

- Store compatibility risk -> Upgrade `load_store()` to tolerate older store shapes and missing one-shot collections.
- Helper abstraction risk -> Keep resource-specific validation explicit where task, snapshot, and recovery differ.
- State transition observability risk -> Persist the terminal resource after run and rely on tests to assert invalid reruns.
- Snapshot storage realism trade-off -> Use deterministic placeholder `storageRef` now; real storage integration remains out of scope.
- Scope validation ambiguity -> Accept only the named scope keys from the checkpoint and reject invalid shape or unknown keys with structured validation.

## Migration Plan

No explicit migration is required. Existing store files load with empty `tasks`, `snapshots`, and `recoveries` collections and are saved in the expanded shape after the next write.

## Open Questions

- Whether `bundleRef` tasks should succeed immediately like non-failing inline tasks, or remain a no-op placeholder until bundle execution exists.
- Whether snapshot `spec.storage.size` should use memory quantity validation or a looser non-empty string rule.
