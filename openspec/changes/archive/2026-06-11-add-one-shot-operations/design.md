## Context

`meshctl.py` manages resource-like objects through an argparse CLI backed by the JSON store selected by `MESHCTL_STORE`. Mesh and vault commands already establish the local conventions for YAML loading, JSON success output, JSON error output, metadata name validation, deterministic list ordering, update atomicity, and dependency checks.

Checkpoint 5 adds three executable resource kinds: `task`, `snapshot`, and `recovery`. They are persisted resources with ordinary CRUD commands, plus a `run` command that advances status through a one-shot lifecycle. Each resource starts in `Initializing`, may move through `Running`, and eventually reaches an irreversible terminal state.

## Goals / Non-Goals

**Goals:**

- Add `task`, `snapshot`, and `recovery` command groups with create, list, describe, update, delete, and run operations.
- Persist one-shot resources in the same local store model as existing resources without regressing mesh or vault behavior.
- Validate mesh and snapshot references, resource quantities, exclusive task command sources, snapshot/recovery scope objects, and recovery snapshot consistency.
- Enforce full `spec` immutability after create for all one-shot resources.
- Implement deterministic run behavior for inline tasks, snapshots, and recoveries, including `Unknown` outcomes when snapshots or recoveries run against unstable meshes.
- Prevent deleting snapshots while recoveries reference them.
- Keep JSON output, error envelopes, stderr behavior, and exit codes aligned with existing mesh/vault commands.

**Non-Goals:**

- Execute real shell commands, connect to external storage, or perform real backup/restore work.
- Implement asynchronous controllers, retries, cancellation, progress streaming, or background reconciliation.
- Support bundled task execution beyond accepting a valid `spec.bundleRef`.
- Mutate mesh or vault resources as a side effect of running task, snapshot, or recovery resources.

## Decisions

1. Store each new kind in a separate collection.

   Rationale: Distinct `tasks`, `snapshots`, and `recoveries` collections keep resource-kind boundaries explicit, make same-name resources across kinds possible, and simplify per-kind list sorting and duplicate checks.

   Alternative considered: Use one generic operations collection with a `kind` field. That would centralize lifecycle code, but every lookup and dependency check would need extra filtering and would be easier to get wrong in a compact CLI.

2. Reuse the existing resource CRUD helpers where possible, with per-kind normalization hooks.

   Rationale: The new resources share name validation, YAML parsing, duplicate/not-found handling, deterministic list output, JSON errors, and update atomicity with mesh and vault resources. A small per-kind configuration avoids three separate copies of the same command flow.

   Alternative considered: Implement each command group independently. That is direct, but it invites subtle drift in error formatting and update behavior.

3. Treat create as the only place where `spec` defaults are applied.

   Rationale: Snapshot and recovery memory defaults must become part of the persisted spec. Update compares the incoming merged candidate against the stored spec and rejects any change, including adding an omitted field.

   Alternative considered: Recompute defaults on every read. That risks making omitted fields appear mutable and makes immutable comparisons less obvious.

4. Implement `run` as a synchronous state transition.

   Rationale: The CLI has no background worker. A synchronous command can set `Running` during execution and persist the terminal state before printing the resource, which satisfies the observable contract without adding process management.

   Alternative considered: Persist `Running` and require a later command to finish. That adds an unresolved reconciliation model beyond the checkpoint.

5. Model task inline execution with deterministic line inspection.

   Rationale: The checkpoint defines inline behavior in terms of lines and `FAIL:` prefixes, so implementation can avoid invoking a shell while still producing predictable success and failure states.

   Alternative considered: Execute inline text through the host shell. That is unnecessary for the contract and would make tests environment-dependent.

6. Resolve snapshot and recovery run outcomes from the referenced mesh at run time.

   Rationale: The contract specifically depends on current mesh stability when the operation runs. Reading the current mesh before the terminal transition keeps the status accurate when a mesh changed after the operation was created.

   Alternative considered: Validate mesh stability only at create time. That would miss unstable meshes at execution time.

7. Enforce snapshot delete dependency protection by scanning recoveries.

   Rationale: A recovery owns a `spec.snapshotRef`; deleting that snapshot would leave a dangling operational dependency. A pre-delete scan keeps delete atomic and can name dependent recoveries in the conflict message.

   Alternative considered: Allow deletion and let recovery run fail later. That contradicts the checkpoint's dependency protection rule.

## Risks / Trade-offs

- Store shape changes can regress older tests or existing local stores -> Keep store loading tolerant of existing mesh/vault shapes and write all successful saves through centralized collection helpers.
- Full-spec immutability can be accidentally bypassed by partial-update merge code -> Compare the fully merged candidate `spec` against the stored `spec` before validation-side effects or persistence.
- Quantity validation may diverge from mesh validation -> Reuse the existing mesh memory/CPU quantity validator and field mapping for snapshot/recovery resources.
- `Running` may not be externally observable because `run` completes synchronously -> This is acceptable for a single-process CLI, but tests should assert terminal output and invalid rerun behavior rather than requiring an intermediate persisted read.
- Conflict messages can become brittle if tests assert exact formatting -> Sort dependent recovery names for deterministic output while keeping the contract focused on field/type and name inclusion.

## Migration Plan

No explicit user-facing migration command is required. The store loader should default missing `tasks`, `snapshots`, and `recoveries` collections to empty dictionaries and preserve compatibility with existing mesh/vault data. After any successful command, save using the multi-collection shape.

Rollback is limited to reverting the implementation and tests. Stores saved with one-shot collections should remain readable by the updated loader; older code may ignore or fail on the new collections.
