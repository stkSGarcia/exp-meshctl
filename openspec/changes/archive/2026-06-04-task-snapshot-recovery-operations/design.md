## Context

The tool currently handles mesh and vault resources. This change introduces three new "one-shot operational" resource kinds: `task`, `snapshot`, and `recovery`. Unlike long-lived resources (mesh, vault), these resources are created once, optionally run once, and reach a terminal state — they are never re-run from a terminal state.

The existing codebase already has patterns for CRUD operations, YAML parsing, JSON error output, and `spec.meshRef` cross-resource validation established by mesh-management and vault-management. This design reuses those patterns rather than creating new ones.

## Related Work

**`vault-management`**: Manages vault resources scoped to a mesh, including CRUD operations, validation, and immutability constraints — informs the CRUD structure, error format, and immutability contract because it is the most recent and complete resource implementation. _(see `vault-management`)_

## Goals / Non-Goals

**Goals:**
- Introduce `task`, `snapshot`, and `recovery` resource kinds with full CRUD + `run` lifecycle
- Implement a shared `Initializing → Running → terminal` state machine for all three kinds
- Enforce full spec immutability after creation
- Protect snapshots from deletion when referenced by recoveries
- Implement inline task execution with `FAIL:` line detection

**Non-Goals:**
- Persistent on-disk storage (same approach as existing resources)
- Real subprocess execution for tasks (inline simulation is sufficient per spec)
- Real storage backends for snapshots (storageRef is a synthetic string)
- Background/async execution of run operations

## Decisions

### D1: Shared state machine across all three kinds

All three kinds use the same phase names (`Initializing`, `Running`, `Succeeded`, `Failed`, `Unknown`) and the same guard: run is only valid from `Initializing`. The run-state error message format is identical across kinds.

_Rationale_: Consistency reduces implementation surface and makes the CLI predictable. A shared helper function validates the pre-run state and emits the standardized error.

_Alternative considered_: Per-kind state transition logic — rejected because the checkpoint spec explicitly calls out identical error shape and message format.

### D2: Full spec immutability via field-level diff on update

On any `update` call, the system diffs every field in the incoming YAML `spec` against the stored resource's `spec`. Any change (added, removed, or modified field) triggers an `immutable` error.

_Rationale_: The spec says "the entire spec section is immutable" and "reject adding a field that was previously omitted." A simple equality check on the serialized spec object handles all cases. The contract explicitly does not require one exact field path or one exact error count, so returning one `immutable` error is sufficient.

_Alternative considered_: Allowlist of mutable fields — not applicable here since no spec fields are mutable.

### D3: Snapshot dependency check at delete time

When `meshctl snapshot delete <name>` is called, the system scans the recovery store for any recovery whose `spec.snapshotRef` matches. If any exist, delete is rejected with a `conflict` error naming the dependent recoveries.

_Rationale_: Referential integrity must be enforced at the application layer since there is no database foreign-key mechanism. The check is O(n) over recoveries, which is acceptable for the expected resource counts.

### D4: Inline task execution as line-by-line simulation

Task `run` splits `spec.inline` on newlines, iterates the lines, and fails immediately if a line starts with `FAIL:`. The reason text is the content after `FAIL: ` (trimmed). Line indexing starts at 0.

_Rationale_: The spec defines this precisely. No real subprocess execution is needed — this is a simulation/testing tool.

### D5: Resource quantity validation reused from vault-management

Memory and CPU quantities for snapshot and recovery use the same format and validation rules as mesh resource quantities. The existing quantity validator is reused without modification.

_Rationale_: Code reuse, consistent error messages. _(see `vault-management`)_

## Risks / Trade-offs

- **In-memory store is ephemeral** → All state is lost on process restart. Acceptable: consistent with existing resource behavior.
- **Snapshot storageRef is synthetic** → No real storage backend; `storageRef` is a deterministic or random string. Acceptable: the spec only requires it to be "stable, non-empty."
- **Recovery does not verify snapshot is in Succeeded state** → The spec does not require this check, so it is intentionally omitted. Risk: a recovery could run against a snapshot that never succeeded. Mitigation: out of scope per current spec.

## Migration Plan

No migration required. New resource kinds are additive. Existing mesh and vault functionality is unchanged.

## Open Questions

- Should `storageRef` be deterministic (e.g., based on snapshot name + timestamp) or random? Either satisfies the spec; a deterministic format is friendlier for testing.
