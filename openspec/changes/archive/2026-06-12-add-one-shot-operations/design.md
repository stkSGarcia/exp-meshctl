## Context

`meshctl.py` currently manages mesh and vault resources from YAML, stores them in the JSON file selected by `MESHCTL_STORE`, and prints all success and error responses as JSON. One-shot operations add three persisted resource kinds with their own lifecycle and references: tasks execute commands against meshes, snapshots capture mesh data, and recoveries restore from snapshots.

## Related Work

> **`mesh-resource-management/add-vault-resource-management`**: Mesh deletion dependency conflicts reject deletion when other resources reference a mesh — informs snapshot dependency checks because this change needs the same reference-protection behavior for recoveries that point at snapshots.

> **`mesh-resource-management/add-mesh-lifecycle-topology`**: Mesh command surface, update behavior, validation, and lifecycle status handling define the CLI and status vocabulary — informs command parser and state-transition design because one-shot resources must feel like first-class `meshctl` resources.

> **`vault-resource-management/add-vault-resource-management`**: Vault CRUD, immutable fields, mesh references, and JSON errors define the second-resource pattern — informs generic one-shot resource helpers because tasks, snapshots, and recoveries reuse mesh references and JSON error conventions.

## Goals / Non-Goals

**Goals:**

- Add `task`, `snapshot`, and `recovery` as persisted resource kinds in `meshctl.py`.
- Preserve existing JSON output, name validation, error shape, and zero exit-code behavior for domain validation errors.
- Keep the implementation local to the current single-file CLI and test suite.
- Reuse mesh resource quantity validation for snapshot and recovery resources.
- Make run lifecycle deterministic and fully testable without external systems.

**Non-Goals:**

- Execute real shell commands, create real backups, or perform actual restore operations.
- Add asynchronous processing, background workers, or external storage services.
- Change existing mesh or vault command behavior.
- Define a new storage backend or migrate users away from the current JSON store.

## Decisions

1. Store one-shot resources in top-level `tasks`, `snapshots`, and `recoveries` maps.

   `empty_store()` and `load_store()` will add these collections while continuing to tolerate older store files that contain only `meshes` and `vaults`. This follows the existing resource-map model and keeps list/describe/delete operations straightforward _(see `vault-resource-management/add-vault-resource-management`)_.

   Alternative considered: store every non-mesh resource in a single typed collection. That would reduce top-level keys but complicate kind-specific validation and sorted list behavior.

2. Add parser branches for each new kind rather than building a dynamic command registry.

   The current parser declares mesh and vault subcommands explicitly. Extending that pattern for `task`, `snapshot`, and `recovery` keeps the change readable and avoids a refactor that is not necessary for three resource kinds _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_.

   Alternative considered: generate subparsers from a table of kinds and operations. That may become useful later, but it would mix refactoring with new behavior.

3. Use shared one-shot helpers for common CRUD and validation plumbing.

   The three kinds share name validation, not-found handling, store access, spec immutability, sorted lists, JSON printing, and run-state guard checks. Implementing these as narrow helpers reduces repeated code while leaving kind-specific normalization in explicit task/snapshot/recovery functions _(see `vault-resource-management/add-vault-resource-management`)_.

   Alternative considered: copy mesh/vault handlers for every operation. That would be simple initially but would make the run and immutability rules easier to drift.

4. Model `run` as a synchronous deterministic transition.

   Each run handler will validate `status.state == "Initializing"`, set `Running` in memory, immediately compute the terminal state, persist it, and print the resulting resource. This satisfies the required phase progression without introducing async execution.

   Alternative considered: persist an intermediate `Running` state and require a later command to complete it. The checkpoint requires transition through `Running`, but not delayed completion.

5. Treat mesh stability as a read-time status property.

   Snapshot and recovery runs will inspect the referenced mesh at run time and consider the mesh unstable when `status.stable` is exactly `false`. In that case the operation finishes as `Unknown` with a non-empty detail; otherwise it succeeds. This keeps behavior compatible with existing mesh resources whose status may not include `stable`.

   Alternative considered: require every mesh to carry `status.stable`. That would risk changing existing mesh output and tests outside this change.

6. Reuse existing quantity normalization for one-shot resource `spec.resources`.

   Snapshot and recovery resource specs will call the same memory and CPU quantity validation paths used by mesh specs so formats and request/limit checks stay consistent _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_.

   Alternative considered: add a second minimal parser for one-shot quantities. That would create avoidable divergence.

7. Implement snapshot dependency protection by scanning recoveries before delete.

   `snapshot delete` will inspect `recoveries` for `spec.snapshotRef == <name>` and reject the delete with a `metadata.name` conflict that names dependents. This mirrors the existing mesh delete dependency scan for vaults _(see `mesh-resource-management/add-vault-resource-management`)_.

   Alternative considered: maintain reverse indexes in the store. That is unnecessary for the small local JSON store and would add migration complexity.

## Risks / Trade-offs

- Existing store files lack one-shot collections -> `load_store()` must default missing collections to empty maps.
- `status.stable` is not guaranteed on existing meshes -> treat only explicit `false` as unstable to avoid surprising Unknown results.
- Inline task execution is simulated rather than real -> document and test the checkpoint rules exactly, including `FAIL:` handling and no rollback semantics.
- Entire-spec immutability may reject harmless normalization differences -> compare normalized candidate specs against stored specs to avoid false positives where possible.

## Migration Plan

No explicit data migration is required. Loading an older store will synthesize empty `tasks`, `snapshots`, and `recoveries` collections, and the next save will persist the expanded shape.

Rollback is limited to code rollback. Stores containing one-shot resource keys should remain readable by the new code path; older code may ignore or drop those keys if it rewrites the store, so rollback should avoid running old write commands against expanded stores.

## Open Questions

- None for the checkpoint contract.
