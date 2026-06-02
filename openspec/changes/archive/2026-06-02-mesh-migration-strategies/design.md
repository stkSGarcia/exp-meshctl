## Context

The mesh management CLI currently validates `spec.runtime` only as a semver-formatted string and supports a single migration strategy (`FullStop`). Operators need safe, controlled runtime upgrades with multiple migration profiles. This change introduces a catalog-based version registry, three migration strategies with distinct constraints, a dedicated `mesh migrate` command to advance migrations stage by stage, and warnings for deprecated targets.

The implementation lives in a single Python file (`meshctl.py`) backed by a file-based JSON store. All new state (`status.migration`, `Migration` condition) persists in the same store as the rest of the mesh resource.

## Goals / Non-Goals

**Goals:**
- Enforce a catalog-based allowlist for `spec.runtime` on create/update
- Emit deprecation warnings without failing the operation
- Accept `LiveMigration` and `RollingPatch` strategies with their specific validation rules
- Track migration state (`status.migration`, `Migration` condition) through its lifecycle
- Expose `mesh migrate <name>` to advance a migration one stage at a time

**Non-Goals:**
- Actual runtime provisioning or orchestration — lifecycle is bookkeeping only
- Persistent catalog storage — catalog is hardcoded in application code for now
- Concurrent/distributed migration safety — single-process file store

## Decisions

### 1. Catalog as in-process constant

The runtime catalog is defined as a dict constant in the application. Alternatives (external config file, database) were rejected as over-engineering for a CLI tool; the catalog is small and rarely changes.

### 2. Warning accumulation separate from error accumulation

Warnings and errors are accumulated independently. Warnings are appended to the response JSON only when the error list is empty. This keeps the success/failure contract clean: if `errors` is present, `warnings` is never emitted.

### 3. Migration state stored directly in the mesh resource

`status.migration` and the `Migration` condition are stored as part of the mesh JSON blob. No separate migration store. This keeps the describe/list outputs self-contained and avoids cross-resource joins.

### 4. Stage sequences as ordered lists per strategy

Each strategy maps to a fixed ordered list of stage names:
- `FullStop` → `["Migrate"]`
- `RollingPatch` → `["Migrate"]`
- `LiveMigration` → multi-stage list

`mesh migrate` pops the current stage. When the list is exhausted, the migration completes. Alternatives (state machine, enum transitions) were skipped in favor of a simple index-based advance.

### 5. RollingPatch errors reported independently

The two `RollingPatch` constraints (same major.minor, target major ≥ 4) are checked and reported as separate errors so operators see both violations at once.

### 6. `spec.regions` as the multi-region signal

`LiveMigration` uses presence of `spec.regions` as the multi-region indicator. The field is already available in the mesh spec; no additional topology detection needed.

## Risks / Trade-offs

- **Catalog drift** → catalog is hardcoded; adding new versions requires code changes. Mitigation: catalog is a single dict, easy to update.
- **Migration state inconsistency on partial write** → single-process JSON store has no transactions; a crash mid-write could corrupt state. Mitigation: out of scope for this CLI tool's durability requirements.
- **Stage list for LiveMigration is not specified in the checkpoint** → the checkpoint lists "Multiple stages" without naming them. Mitigation: treat as implementation detail; use sensible stage names (`Drain`, `Migrate`, `Verify`) and document them.
