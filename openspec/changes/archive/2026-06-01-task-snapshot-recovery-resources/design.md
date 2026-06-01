## Related Work

**`mesh-management`**: Established mesh CRUD commands, YAML input schema, name validation, resource quantity formats (`Ki`/`Mi`/`Gi` memory, `m` CPU), error output format, and immutable field error type — informs all design decisions for the three new resource kinds because the same patterns are reused wholesale. _(see `mesh-management`)_

## Context

meshctl manages mesh and vault resources. Three operational resource kinds are needed to complete the administrative surface: `task` (run custom commands against a mesh), `snapshot` (capture point-in-time data), and `recovery` (restore from a snapshot). These are "one-shot" resources: created once, run once, and their terminal state is permanent.

The project is a single-file Python CLI (`meshctl.py`) backed by a JSON file store. All three new kinds will extend that same store and routing structure.

## Goals / Non-Goals

**Goals:**
- Add `task`, `snapshot`, and `recovery` resource kinds with full CRUD and a `run` command
- Reuse existing YAML input schema, name validation, quantity validation, and error format (see `mesh-management`)
- Enforce spec immutability for all three kinds after creation
- Block snapshot deletion when referenced by a recovery
- Implement task inline execution with per-line failure tracking
- Return `status.storageRef` on a succeeded snapshot run
- Handle unstable mesh at run time for snapshot and recovery with `"Unknown"` state

**Non-Goals:**
- Distributed or remote task execution — inline only
- Snapshot storage implementation — `storageRef` is a string field, not a real storage layer
- Scheduled or recurring operations
- Changes to the existing mesh or vault resource kinds

## Decisions

### 1. Same store file, separate kind keys

Each resource kind (`task`, `snapshot`, `recovery`) is stored under its own top-level key in the JSON store (e.g., `store["tasks"]`, `store["snapshots"]`, `store["recoveries"]`). This avoids collisions without adding new files.

_Alternatives:_ Separate files per kind — rejected as unnecessary complexity for a single-file store.

### 2. Spec immutability enforced at update time

On `update -f <path>`, the system loads the stored spec, compares it field-by-field (including absent fields) to the incoming spec, and rejects any difference with `type = "immutable"`. The contract does not require one exact field path or message, so a single `spec` path error is acceptable.

_Alternatives:_ Store a hash of the spec — rejected as opaque and hard to debug.

### 3. Task inline execution model

`spec.inline` is split on newlines. Each line is executed in sequence. A line beginning with `FAIL:` immediately terminates with `status.state = "Failed"` and `status.detail = "command <index> failed: <reason>"` where `<reason>` is the remainder of the `FAIL:` line and `<index>` is the 0-based line number. No rollback.

_Alternatives:_ Shell execution — rejected as out of scope; spec defines a simulated model.

### 4. Mesh stability check for snapshot and recovery run

At `run` time, the system reads the referenced mesh's `status.stable` field. If `false`, it sets state to `"Unknown"` with a non-empty `status.detail`. This mirrors real-world backup/restore guards without requiring a real stability service.

### 5. Dependency protection via pre-delete scan

Before deleting a snapshot, the system scans all stored recoveries for any whose `spec.snapshotRef` equals the snapshot name. If any exist, it returns a `conflict` error naming them. This is the same pattern used by mesh delete checking vault references _(see `mesh-management/mesh-delete`)_.

## Risks / Trade-offs

- **Immutability comparison edge cases** → Fields that default at create time (e.g., memory defaults) will be stored in their defaulted form; comparisons happen on the stored value, so an update that re-sends the default won't be rejected.
- **No real task execution** → The inline model is simulated; actual command output is not captured beyond pass/fail.
- **Single-file store contention** → Not a concern at this scale; noted for future if store is split.
