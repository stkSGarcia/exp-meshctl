## Context

`meshctl.py` currently owns command routing, YAML parsing, JSON store persistence, validation helpers, and output formatting for mesh and vault resources. The one-shot operation resources should fit that same single-file CLI shape: typed collections in the store, normalized resources on create, JSON output, and validation errors returned in the existing `errors` envelope.

## Related Work

**`mesh-resource-management/add-meshctl-mesh-crud`**: Implements the baseline mesh create/list/describe/delete command surface — informs the decision to add the same resource-oriented verbs for `task`, `snapshot`, and `recovery` because this change needs consistent resource management for new kinds.

**`mesh-resource-management/add-mesh-lifecycle-topology`**: Implements update behavior, quantity validation, status projection, and lifecycle status fields — informs the decision to reuse existing resource quantity helpers and explicit status transitions because one-shot operations introduce their own lifecycle phases.

**`vault-resource-management/add-vault-resource-management`**: Implements a second persisted resource kind with mesh references, validation, and immutable identity fields — informs the decision to store new collections alongside meshes and vaults and validate cross-resource references because snapshot/recovery resources depend on other resources.

## Goals / Non-Goals

**Goals:**

- Add `task`, `snapshot`, and `recovery` resources with CRUD plus `run` commands.
- Preserve the current JSON/error CLI behavior and zero-stderr test style.
- Reuse existing YAML parsing, name validation, quantity validation, persistence, and public output helpers where practical.
- Keep run execution deterministic and local: inline task lines are simulated, snapshots/recoveries transition based on referenced mesh stability.

**Non-Goals:**

- Execute shell commands, external bundles, or real backup/restore systems.
- Add asynchronous workers, polling, or background process management.
- Change mesh or vault requirements except where helper reuse requires non-behavioral refactoring.

## Decisions

### Store one-shot resources as first-class collections

Add `tasks`, `snapshots`, and `recoveries` keys to the JSON store and update `empty_store()`/`load_store()` to tolerate old stores that only have `meshes` and `vaults`. This mirrors vault storage and keeps list/describe/delete operations simple _(see `vault-resource-management/add-vault-resource-management`)_.

Alternative considered: one generic `operations` collection with a `kind` field. That would reduce keys, but every command would need filtering and kind-specific validation branches. Separate collections match the existing resource model better.

### Use generic helpers for shared resource verbs

Introduce small helpers for collection lookup, duplicate/not-found errors, sorted list output, immutable spec checks, and run-state validation. Keep kind-specific normalization and run behavior in separate functions so the command handlers stay readable _(see `mesh-resource-management/add-meshctl-mesh-crud`)_.

Alternative considered: copy mesh/vault functions for each new kind. That would be quick but would triple the same CRUD logic and make future consistency fixes harder.

### Normalize create-time specs and preserve immutable specs

On create, normalize `metadata.name`, required references, optional scope, resources, and defaults. On update, merge the incoming document with the stored resource only after checking that no `spec` path changes or adds a previously omitted field; return `type = "immutable"` for those errors. Metadata/status updates are not part of the checkpoint contract, so updates should remain conservative.

Alternative considered: reject every update for one-shot resources. The command surface requires `update -f <path>`, and allowing metadata/status-preserving no-op updates keeps the command useful without weakening spec immutability.

### Model run operations as deterministic state transitions

Each `run` command loads the stored resource, rejects non-`Initializing` resources with the exact `status.state` error, writes `Running` internally, then immediately persists the terminal phase. Task inline content succeeds unless a line starts with `FAIL:`; snapshot and recovery return `Unknown` with detail when the mesh is unstable, otherwise they succeed. Snapshot success generates a stable non-empty storage reference from the snapshot name _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_.

Alternative considered: expose the intermediate `Running` state to users. The CLI is synchronous today, so persisting only the final state after passing through `Running` keeps behavior deterministic for tests.

### Keep output projection explicit per kind

Return full resources for create/describe/update/run and sorted summary arrays for list. Status output should omit `detail` unless the terminal state is `Failed` or `Unknown`, and omit `storageRef` except for succeeded snapshots. This keeps status fields from leaking stale data after later operations.

Alternative considered: print stored resources directly. Explicit projection is safer because run operations add state-specific fields that must be absent in other states.

## Risks / Trade-offs

- [Risk] Generic CRUD helpers could obscure kind-specific validation failures. -> Mitigation: keep validators named per kind and cover exact error field/type/message cases in tests.
- [Risk] Deep immutable-spec comparisons can be noisy for omitted optional fields after defaults. -> Mitigation: compare against normalized stored specs and treat any changed or newly supplied normalized spec path as immutable.
- [Risk] Synchronous `Running` transitions are not externally observable. -> Mitigation: tests should assert final states and invalid reruns; the spec only requires transition through `Running`, not an observable pause.
- [Risk] Store migration could drop legacy data if old files lack new keys. -> Mitigation: extend `load_store()` to always preserve `meshes` and `vaults` while defaulting missing one-shot collections to empty dictionaries.

## Migration Plan

No manual migration is required. Existing stores load with empty `tasks`, `snapshots`, and `recoveries` collections, and subsequent saves write the expanded shape.

Rollback is code-only: removing the new command handlers leaves existing mesh/vault data compatible, though stores may retain unused one-shot collection keys.

## Open Questions

- None for the proposal. Bundle task execution can remain a stored reference until a later checkpoint defines concrete behavior.
