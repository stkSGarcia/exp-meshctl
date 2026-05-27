## Context

`meshctl` is a Python CLI backed by a flat JSON store (`store.json`). The existing `spec.migration.strategy` field only accepts `"FullStop"` and there is no concept of a runtime version catalog, active migration state, or a `migrate` command. Runtime versions are validated only for format (`major.minor.patch`); there is no catalog of valid versions.

This change extends the mesh lifecycle to include:
- A catalog of known runtime versions (with `supported`/`deprecated`/`skipped` states)
- Three migration strategies with version-change constraints
- An active migration state machine persisted in `status.migration` and `status.conditions`
- A `mesh migrate` command to advance or complete an active migration
- A warnings output channel on successful responses

## Goals / Non-Goals

**Goals:**
- Implement runtime catalog lookup and enforce `supported`/`deprecated`/`skipped` semantics on `create` and `update`
- Emit structured warnings for deprecated runtime versions
- Expand `spec.migration.strategy` to accept `"LiveMigration"` and `"RollingPatch"` with their respective version-change rules
- Track active migrations in `status.migration` and `status.conditions`
- Implement `mesh migrate <name>` to advance or complete an active migration
- Reject `spec.runtime` and `spec.migration.strategy` changes while a migration is active
- Implement rollback for `LiveMigration`

**Non-Goals:**
- External catalog service; catalog is embedded in code
- Rollback for `FullStop` or `RollingPatch` strategies
- Concurrent or distributed migration coordination
- Automatic migration advancement (no background worker)

## Decisions

### 1. Catalog embedded in source, not external

The runtime catalog is a static dict in `meshctl.py`. No file, DB, or API. This matches the store-file pattern already used; adding an external catalog service would be premature.

Alternatives considered: YAML config file (more config surface), dynamic API call (adds network dependency).

### 2. Warnings appended as a top-level key in the success response

Successful `create`, `update`, and `mesh migrate` responses include a `warnings` key alongside `metadata`/`spec`/`status` when warnings are present. Warnings are only emitted when there are no errors. The `warnings` key is omitted (not `[]`) when there are none.

Alternatives considered: Separate stderr output (harder to parse in tests), separate JSON line (breaks existing consumers).

### 3. Migration state in store.json under `status`

Active migration is tracked via:
- `status.conditions` entry `{"type":"Migration","status":"True","message":""}` 
- `status.migration` object with `sourceRuntime`, `targetRuntime`, `stage`

This keeps migration state co-located with the mesh resource, consistent with the existing conditions pattern.

### 4. Stage sequences

`FullStop` and `RollingPatch` use a single stage: `["Migrate"]`. `LiveMigration` uses multiple stages; the exact stage names are an open question (see below). On the last stage, `mesh migrate` completes the migration rather than advancing.

### 5. Version comparison uses semver tuple comparison

Runtime versions are parsed as `(major, minor, patch)` integer tuples. Downgrade = target tuple is less than source tuple. `RollingPatch` "same major.minor" means `target.major == source.major and target.minor == source.minor`.

### 6. First assignment does not start a migration

Setting `spec.runtime` when it was previously absent is an initial assignment, not a version change. No `status.migration` is created. This distinguishes "first set" from "change" semantics.

## Risks / Trade-offs

- **Catalog is static** → Adding or changing catalog entries requires a code change and redeploy. Mitigation: Acceptable for this stage; the catalog is small and well-defined.
- **LiveMigration stage list is open** → See Open Questions; an incorrect stage list would require a follow-up patch.
- **Rollback trigger is unspecified** → The checkpoint does not define how rollback is triggered. Assuming `mesh migrate --rollback <name>`; see Open Questions.

## Open Questions

1. **LiveMigration stage sequence**: The checkpoint states "Multiple stages" without naming them. What are the stage names and how many stages does `LiveMigration` have? (e.g., `Prepare → Migrate → Cutover`, or something else?)

2. **Rollback trigger**: How is LiveMigration rollback initiated? Is it `mesh migrate --rollback <name>`, a separate `mesh rollback` command, or a flag on `mesh update`?
