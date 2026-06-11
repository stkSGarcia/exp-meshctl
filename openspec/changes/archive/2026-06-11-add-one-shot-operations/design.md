## Context

`meshctl.py` currently manages persisted mesh and vault resources through a single JSON store selected by `MESHCTL_STORE`. Meshes already provide the parent resource and stability signal needed by one-shot operations, and the codebase has reusable validation helpers for names, YAML parsing, JSON errors, quantity formats, deep updates, and public output shaping.

The new one-shot operation resources should feel like existing meshctl resources: users create a YAML-backed object, inspect it, update allowed fields, delete it, and receive JSON output for every command. The difference is that `task`, `snapshot`, and `recovery` also expose `run`, which performs a deterministic lifecycle transition from `Initializing` into a terminal outcome.

## Goals / Non-Goals

**Goals:**
- Add `task`, `snapshot`, and `recovery` commands with create/list/describe/update/delete/run operations.
- Persist each new resource kind in the existing JSON store alongside meshes and vaults.
- Reuse existing metadata name validation, JSON error shape, YAML parsing, and resource quantity validation behavior.
- Enforce create-time defaults, parent-reference validation, spec immutability, snapshot dependency protection, and run-state transitions.
- Keep run behavior deterministic and local for the exercise: inline task failure rules, mesh stability checks, and stable snapshot storage references.

**Non-Goals:**
- Execute real shell commands or integrate with external task, storage, backup, or recovery systems.
- Add asynchronous workers, polling, retries, cancellation, or rollbacks.
- Change existing mesh or vault command behavior except where shared store loading must tolerate the new collections.

## Decisions

### Store one-shot resources in dedicated top-level collections

Add `tasks`, `snapshots`, and `recoveries` collections to the JSON store. `empty_store()` and `load_store()` should default missing collections to `{}` and preserve compatibility with stores that only contain `meshes` and `vaults`.

Alternative considered: store all one-shot resources in a single collection with a `kind` discriminator. Separate collections match existing mesh/vault patterns, make list/delete lookup simple, and avoid cross-kind name collision policy questions that the checkpoint does not require.

### Use shared generic handlers with kind-specific policy tables

Implement common helpers for create/list/describe/update/delete/run where the behavior is identical across operation kinds, then provide kind-specific normalization, validation, public summary, delete guard, and run functions. This keeps the command surface broad without triplicating all CLI plumbing.

Alternative considered: copy the existing mesh/vault function style for each new kind. That is straightforward but would multiply subtle validation and persistence differences across three similar resources.

### Treat task inline execution as simulated command processing

For `spec.inline`, split content into lines and process them in order. A line beginning with `FAIL:` fails the task with the documented detail; otherwise the task succeeds. The design intentionally does not invoke a shell or external process.

Alternative considered: execute inline lines as shell commands. That would introduce security, environment, rollback, and platform concerns beyond the checkpoint contract.

### Determine snapshot and recovery unknown states at run time

Snapshot and recovery runs should inspect the referenced mesh at run time. If `status.stable` is not `true`, the operation reaches `Unknown` with non-empty detail. Otherwise snapshot succeeds with a deterministic non-empty `status.storageRef`, and recovery succeeds.

Alternative considered: reject creation against unstable meshes. The checkpoint explicitly describes the instability behavior under run semantics, so creation should only validate that references exist.

### Enforce whole-spec immutability after create

Updates should merge incoming YAML over the stored resource for name selection, then compare the entire stored and candidate `spec` values. Any difference, including adding a previously omitted field, is rejected with `type = "immutable"`.

Alternative considered: reject any update containing a `spec` key. Comparing the final spec preserves ordinary update parsing and provides correct behavior even if a user resubmits an identical spec.

## Risks / Trade-offs

- Existing store compatibility may drop new collections if load/save is only updated partially -> Add tests that create resources across all new collections and verify they survive subsequent commands.
- Generic handlers can obscure kind-specific validation errors -> Keep policy functions small and directly test each contractual field/type/message.
- Simulated task execution may be mistaken for real command execution -> Name tests and code paths around inline simulation, and do not invoke subprocesses.
- Run transitions are immediate rather than asynchronous -> This matches the exercise scope but leaves no observable persisted `Running` intermediate state unless implementation records it before the terminal state in-memory.
