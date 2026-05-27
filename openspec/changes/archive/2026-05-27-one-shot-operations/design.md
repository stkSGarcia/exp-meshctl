## Context

meshctl.py is a single Python script that manages mesh and vault resources. Resources are persisted to JSON files (`store.json` for meshes, `vault_store.json` for vaults). The CLI uses argparse with two levels of subcommands: `<kind> <operation>`. Validation, persistence, and output are all handled inline in command functions following the pattern: load YAML → validate → load store → persist → print JSON.

Three new one-shot resource kinds need to be added: `task`, `snapshot`, and `recovery`. Unlike meshes and vaults (which are long-lived), these resources execute once and transition through a fixed phase lifecycle.

## Goals / Non-Goals

**Goals:**
- Add `task`, `snapshot`, and `recovery` subcommands with full CRUD + `run` support
- Enforce the phase lifecycle (`Initializing` → `Running` → terminal) with run-time validation
- Enforce full spec immutability after create
- Protect snapshots from deletion while referenced by recoveries
- Keep the implementation consistent with existing code patterns (no new dependencies)

**Non-Goals:**
- Real async execution (run transitions happen synchronously in a single call)
- Persistent run logs or audit history
- Cross-resource transactions

## Decisions

### Storage layout: one file per kind

**Decision:** Use separate JSON files — `task_store.json`, `snapshot_store.json`, `recovery_store.json` — one per resource kind.

**Rationale:** Mirrors the existing `store.json` / `vault_store.json` split. Each file is a flat dict keyed by `metadata.name`. Avoids coupling different resource kinds in a single file and keeps load/save helpers simple and independent.

**Alternative considered:** A single `ops_store.json` with nested keys per kind. Rejected: requires all three kinds to be loaded even when only one is needed, and makes concurrent file writes riskier.

### Spec immutability: full snapshot comparison

**Decision:** On update, store the original spec verbatim at create time and compare the entire merged spec against it. Any field that changes (including newly added fields) triggers an `immutable` error.

**Rationale:** The spec is a unit of intent for a one-shot operation. Partial immutability (field-by-field allow-listing) is harder to maintain as fields are added. Full comparison is simple and unambiguous.

**Alternative considered:** Allow-listing mutable fields. Rejected: adds ongoing maintenance burden with no benefit since the spec for these kinds has no legitimately mutable fields.

### Inline task execution: synchronous line-by-line

**Decision:** Parse `spec.inline` by splitting on newlines. Execute lines in order. A line starting with `FAIL:` fails immediately with the remainder of the line as the reason. No rollback of earlier lines.

**Rationale:** The spec defines the exact failure rule. Synchronous execution keeps run simple and deterministic; the `run` command completes in a single invocation.

### Snapshot storageRef: deterministic generated string

**Decision:** On a successful snapshot run, set `status.storageRef` to a deterministic string derived from the snapshot name (e.g., `snapshot/<name>`).

**Rationale:** The spec requires a stable, non-empty `storageRef` on success. There is no real storage backend; a generated string satisfies the contract without external dependencies.

### Resource kind routing: extend the existing argparse tree

**Decision:** Add three new top-level subparsers (`task`, `snapshot`, `recovery`) alongside `mesh` and `vault`. Each gets the same five sub-operations: `create`, `list`, `describe`, `update`, `delete`, plus `run`.

**Rationale:** Consistent with the existing CLI shape. A `run` subparser takes a positional `name` argument, matching the spec's `meshctl <kind> run <name>` surface.

## Risks / Trade-offs

- **File proliferation** → Mitigated by a clear naming convention (`<kind>_store.json`). Three new files are manageable at this scale.
- **Synchronous run semantics** → Real tasks/snapshots/recoveries are async operations; the simulated synchronous model is sufficient for testing purposes but diverges from production intent. This is acceptable for the current scope.
- **Full spec comparison on update** → If a YAML loader normalizes values (e.g., int vs. string), comparison may produce false positives. Mitigated by storing the validated/normalized spec at create time so comparisons are always normalized-to-normalized.
