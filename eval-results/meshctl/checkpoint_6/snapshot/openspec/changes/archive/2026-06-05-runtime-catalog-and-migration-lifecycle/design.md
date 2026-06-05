## Context

`meshctl.py` is a single-file Python CLI that manages mesh, vault, task, snapshot, and recovery resources through JSON stores. The `validate_and_build` function handles all mesh field validation; `cmd_create` and `cmd_update` are the two entry points that trigger it. The current `spec.runtime` check only validates format; `spec.migration.strategy` accepts only `"FullStop"`.

All resource state lives in flat JSON files (`store.json`, etc.) with atomic write-via-rename. The status model already handles `Scaling` and `GracefulShutdown` conditions with a transient-resolution pattern in `describe` and `update`.

## Related Work

**`implement-meshctl/mesh-management/runtime-version-validation`**: Validates `spec.runtime` as `major.minor.patch`. — Informs that catalog lookup must sit *after* this format check, not replace it, because `implement-meshctl/mesh-management/runtime-version-validation` already handles malformed strings cleanly.

**`implement-meshctl/mesh-management/migration-strategy-validation-and-default`**: Accepts only `"FullStop"`. — Informs that the existing strategy-validation code path must be widened from a single-value check to a set membership check, then augmented with per-strategy rules post-validation. _(see `implement-meshctl/mesh-management/migration-strategy-validation-and-default`)_

**`mesh-lifecycle-and-topology/mesh-management`**: Provides condition helpers (`set_condition`, `remove_condition`), `status.stable` computation, and the update merge path. — Informs all migration condition management; `Migration` condition follows the same add/remove pattern as `Scaling` and `GracefulShutdown`. _(see `mesh-lifecycle-and-topology/mesh-management`)_

## Goals / Non-Goals

**Goals:**
- Add a hardcoded runtime catalog and use it to gate `spec.runtime` values on create/update.
- Emit `warnings` alongside the resource on successful calls with deprecated runtimes.
- Expand `spec.migration.strategy` to three values with per-strategy version-change rules.
- Implement migration lifecycle: start on version change, advance/complete via `mesh migrate`, guard updates during active migration.
- Update `status.stable` to consider the `Migration` condition.

**Non-Goals:**
- Dynamic catalog loading from external sources.
- Rollback for `FullStop` or `RollingPatch`.
- Exposing migration history beyond the current `status.migration` object.
- Changing vault, task, snapshot, or recovery resource shapes.

## Decisions

### Decision 1: Hardcoded catalog as a module-level dict

A `RUNTIME_CATALOG` dict (`{"3.0.0": "deprecated", "3.1.0": "skipped", "3.1.1": "supported", "4.0.0": "supported"}`) lives at module level alongside `VALID_DIGEST_ALGORITHMS` and similar constants. Alternatives considered: loading from a YAML file (adds I/O surface, unnecessary for a simulated tool), computing from a range (not generalizable to non-contiguous status assignments).

### Decision 2: Warnings returned as a top-level key on the resource dict

The existing `print_json` path already serializes the full resource dict. Warnings are added as a `"warnings"` key on that dict before printing, then removed for storage. This avoids a separate response wrapper and keeps the store clean. Sorting is `sorted(warnings, key=lambda w: (w["field"], w["message"]))`.

### Decision 3: Migration guards in `cmd_update`, not in `validate_and_build`

Catalog and catalog-status errors belong in `validate_and_build` because they are input constraints. Active-migration guards (cannot change `spec.runtime` / strategy while migrating) are checked in `cmd_update` *after* the store lookup but *before* the merge, so the error message can name the specific field being changed without polluting the stateless validator.

### Decision 4: Stage sequences as a module-level dict keyed by strategy

```python
MIGRATION_STAGES = {
    "FullStop": ["Migrate"],
    "RollingPatch": ["Migrate"],
    "LiveMigration": ["Prepare", "Migrate"],
}
```

`mesh migrate` advances `status.migration.stage` to the next entry in the list. When the current stage is the last, it completes the migration (remove condition and `status.migration`).

### Decision 5: Version-change detection happens in `cmd_update`

A version change occurs when both the stored mesh has `spec.runtime` and the merged spec has a different `spec.runtime`. First-time assignment (stored lacks `spec.runtime`) is explicitly not a migration start. The comparison is a simple string equality check after both values pass catalog validation.

### Decision 6: Semver downgrade check via tuple comparison

Parse `major.minor.patch` into `(int, int, int)` tuples and compare. No external semver library needed; the format is already guaranteed by `RUNTIME_RE`.

## Risks / Trade-offs

- **Hardcoded catalog may lag reality** → Acceptable: this is a simulated tool; the catalog exists to model the validation behavior, not to track real releases.
- **RollingPatch dual-error accumulation** → Both rules must be independently evaluated before returning; early-exit would suppress the second error. The implementation must not short-circuit.
- **LiveMigration rollback surface** → Rollback is not yet wired to a CLI subcommand; the spec only requires it to be triggerable. A `mesh rollback <name>` subcommand is a natural follow-on but is explicitly out of scope here to keep the change focused.
- **`status.stable` now blocks on Migration** → Any code that checks `stable` for vault readiness will correctly observe `stable = false` during a migration, which is the desired behavior.

## Migration Plan

1. Update `validate_and_build` to add catalog check and warnings accumulation; expand strategy validation.
2. Update `cmd_create` and `cmd_update` to handle warnings in output.
3. Add version-change detection and migration start logic in `cmd_update`.
4. Add active-migration guards in `cmd_update`.
5. Add `cmd_migrate` handler and wire `mesh migrate <name>` subcommand in `main`.
6. Update `build_initial_status` stability check (or wherever `status.stable` is computed) to gate on `Migration`.
7. Verify all existing tests still pass; add new scenario-driven tests from the spec.

Rollback: revert `meshctl.py`; store entries with `status.migration` are backward-compatible (the field is simply ignored by the old code).

## Open Questions

- Should `LiveMigration`'s stage list be configurable or is `["Prepare", "Migrate"]` sufficient? (Assumed fixed for this change.)
- Is `mesh rollback` a subcommand or a flag on `mesh migrate`? (Deferred to a follow-on change.)
