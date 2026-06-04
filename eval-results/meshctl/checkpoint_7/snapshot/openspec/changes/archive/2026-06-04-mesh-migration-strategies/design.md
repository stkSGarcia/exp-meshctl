## Context

meshctl currently handles mesh create/update/delete/describe with a basic `spec.migration.strategy` field that only accepts `"FullStop"`. Runtime version is validated for format only (`major.minor.patch`). No migration lifecycle is tracked in `status`; there is no `mesh migrate` command; and warnings are not emitted. The codebase is a single Python file (`meshctl.py`) backed by a simple in-memory or file-based JSON store.

## Related Work

**`mesh-management`**: Manages all mesh resource operations and status conditions — informs the placement of catalog validation (inside the create/update validation pipeline) and migration guards (inside the update merge/validation step). _(see `mesh-management`)_

## Goals / Non-Goals

**Goals:**
- Add runtime catalog validation distinguishing supported, deprecated (warn), and skipped (reject) versions
- Expand `spec.migration.strategy` to accept `"LiveMigration"` and `"RollingPatch"` with per-strategy version-change constraints
- Implement migration lifecycle: `status.migration` block, `Migration` condition, stage sequences, completion
- Add `mesh migrate <name>` command to advance a migration through its stage sequence
- Enforce guards on `spec.runtime` and `spec.migration.strategy` changes during active migrations
- Emit a `warnings` array on successful responses for deprecated runtime versions

**Non-Goals:**
- Automatic or background stage advancement (operator-driven only)
- Integration with real runtime environments or external version registries
- Migration of vault or other resource types

## Decisions

**1. Catalog as in-process constant**

The runtime catalog is defined as a hardcoded dict inside `meshctl.py`. The catalog is small, fixed per release, and has no need for live updates. An external YAML/JSON file would add I/O and operational surface without benefit. Catalog entries map `version → status` (one of `"supported"`, `"deprecated"`, `"skipped"`).

**2. Warning format: top-level sibling key**

Warnings are emitted as a top-level `"warnings"` array alongside the resource body:
```json
{"metadata": ..., "spec": ..., "status": ..., "warnings": [...]}
```
This keeps warnings separable from the resource state and clearly advisory. Embedding warnings in `status` would mix transient advisory output with durable operational signals.

**3. Migration state stored inside the mesh resource**

`status.migration` and the `Migration` condition are stored as part of the mesh record in the same persistent store already used for all other status fields. This is the simplest approach and avoids a separate migration entity or table.

**4. Stage sequences as ordered lists per strategy**

Each strategy maps to a fixed list of stage names. The first element is the initial stage set on migration start. `mesh migrate` advances to the next element; when the current stage is the last element, `mesh migrate` completes the migration instead.

| Strategy | Stages |
|---|---|
| `FullStop` | `["Migrate"]` |
| `RollingPatch` | `["Migrate"]` |
| `LiveMigration` | `["Prepare", "Migrate", "Complete"]` |

**5. Downgrade check via parsed semver tuples**

Versions are compared as `(major, minor, patch)` integer tuples. A target with a lower tuple than the current version is a downgrade and is rejected for all strategies. No external semver library is required.

**6. RollingPatch dual-rule validation**

Both RollingPatch rules (same major/minor AND target major ≥ 4) are checked independently; when both fail, both errors are reported. This is consistent with the existing multi-error accumulation pattern already used throughout the codebase.

## Risks / Trade-offs

- [Risk: Active migration lock prevents fixing unrelated fields] → Mitigation: only `spec.runtime` and `spec.migration.strategy` are locked; all other spec fields remain editable during migration.
- [Risk: Warning suppression on errors hides deprecation info] → Mitigation: consistent with spec contract; warnings are advisory and only meaningful when the operation succeeded.
- [Risk: LiveMigration multi-stage sequence not exhaustively specified] → Mitigation: use `["Prepare", "Migrate", "Complete"]`; the contract only guarantees multiple stages exist.
