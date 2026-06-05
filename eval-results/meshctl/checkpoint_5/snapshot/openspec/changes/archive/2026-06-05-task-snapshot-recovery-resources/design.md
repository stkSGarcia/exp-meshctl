## Context

`meshctl` already supports two resource kinds (`mesh`, `vault`) with a consistent CRUD pattern: YAML-driven create/update, JSON list/describe/delete, and a shared error envelope. The lifecycle state machine established for mesh resources (`Running`, `Scaling`, `Stopped`) provides the template for the three new one-shot operational kinds introduced here.

## Related Work

**`mesh-lifecycle-and-topology`**: Extended meshes with a lifecycle state machine (Running → scaling transitions → Stopped), enriched status (`stable`, `conditions`, `instances`), and immutable-field error typing — informs the state machine and immutability patterns for task/snapshot/recovery because the same `stable` flag gates snapshot and recovery execution.

## Goals / Non-Goals

**Goals:**
- Add `task`, `snapshot`, and `recovery` as first-class resource kinds with the same CLI surface as existing kinds.
- Define a shared `run` command that drives each kind through `Initializing → Running → terminal`.
- Enforce spec immutability after creation across all three kinds.
- Protect snapshots from deletion when referenced by recoveries.

**Non-Goals:**
- Actual distributed execution, storage I/O, or network operations (simulation only).
- Auth/RBAC for who can run resources.
- Streaming output or progress events during run.

## Decisions

### 1. Shared `run` transition model

All three kinds use the same entry-gate rule: `run` is only valid from `Initializing`. Any other state produces a `status.state` / `invalid` error with the `"resource is in state '<current>', expected 'Initializing'"` message. This keeps the state machine learnable and consistent.

**Alternatives considered:** Allowing re-run from `Failed`. Rejected — terminal states are irreversible per spec; re-running requires creating a new resource.

### 2. Spec immutability via full-section rejection

On `update`, any diff against the stored `spec` block (field change, field addition, or field removal) is rejected as `type: "immutable"`. The check is holistic rather than per-field because all three kinds treat spec as a sealed contract once accepted.

**Alternatives considered:** Per-field tracking. Rejected — overkill for one-shot resources; the checkpoint explicitly says the contract does not require one exact field path or message count.

### 3. Snapshot/recovery share `scope` shape

Both snapshot and recovery accept an optional `spec.scope` object with the same keys (`stores`, `blueprints`, `tallies`, `definitions`, `procedures`). When omitted, the full data set is captured/restored. This avoids a separate "scope" resource type.

### 4. Recovery cross-validation at create time

A recovery validates its `spec.snapshotRef` on create (snapshot must exist, and `snapshot.spec.meshRef` must match `recovery.spec.meshRef`). This front-loads referential integrity rather than deferring to run time, where failures are more disruptive.

### 5. Dependency protection for snapshot delete

`snapshot delete` checks for referencing recovery resources before removing. The error names the blocking recoveries. _(See mesh delete's vault-dependency check for the established pattern.)_

### 6. Mesh stability gate at run time

Snapshot and recovery `run` checks `mesh.status.stable` at the moment of execution. An unstable mesh yields `status.state = "Unknown"` with a non-empty `detail`. Task `run` does not gate on mesh stability — tasks are lower-level and may be used diagnostically against unstable meshes.

## Risks / Trade-offs

- **Terminal state irreversibility** — operators cannot retry a `Failed` task inline; they must create a new resource. This is intentional but may surprise users accustomed to re-run semantics.
- **Inline command simulation** — `FAIL:` prefix detection is a test-facing protocol, not a real execution model. Real command execution would need sandboxing not yet scoped here.
- **Snapshot/recovery mesh mismatch at run** — mesh may be deleted between create and run, leaving a dangling `meshRef`. The run checks mesh existence and stability; if the mesh is gone the state transitions to `Failed` or `Unknown`.
