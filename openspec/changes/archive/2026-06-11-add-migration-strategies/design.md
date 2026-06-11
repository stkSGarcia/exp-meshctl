## Context

`meshctl.py` currently owns the mesh command surface, YAML normalization, JSON store persistence, validation helpers, lifecycle conditions, and public output projection in one module. Meshes already support optional `spec.runtime`, a defaulted `spec.migration.strategy`, transient lifecycle conditions, and `status.stable`, but runtime validation is only semantic-version parsing and the only accepted strategy is `"FullStop"`.

This change makes runtime selection catalog-driven and adds an explicit migration lifecycle. The implementation should fit the current local, deterministic CLI model: commands load the JSON store, validate and mutate one resource, save the store, then print JSON to stdout.

## Goals / Non-Goals

**Goals:**
- Define a runtime catalog with supported, deprecated, and skipped version statuses.
- Validate runtime targets on mesh create and update only when `spec.runtime` is present.
- Emit sorted warnings on successful create/update operations that target deprecated runtimes.
- Accept `"FullStop"`, `"LiveMigration"`, and `"RollingPatch"` migration strategies and enforce their version-change rules.
- Persist active migration state in `status.conditions` and `status.migration`.
- Add `mesh migrate <name>` to advance or complete active migrations.
- Keep one-shot operation stability checks accurate by treating active migrations as unstable.

**Non-Goals:**
- Discover runtime versions from an external service or network source.
- Execute real platform migrations or long-running background work.
- Add partial rollback support beyond the documented LiveMigration rollback behavior.
- Change vault, task, snapshot, or recovery semantics except through mesh stability.

## Decisions

### Keep the runtime catalog in code

Represent the runtime catalog as a module-level mapping from version string to status, initially including `3.0.0` as deprecated, `3.1.0` as skipped, `3.1.1` as supported, and `4.0.0` as supported. Validation first checks semantic-version shape, then catalog membership and status.

Alternative considered: store the catalog in the persisted JSON store. A code-level catalog is simpler, deterministic for tests, and matches the checkpoint's fixed list.

### Return warnings as top-level successful-output metadata

Create/update should accumulate warnings separately from errors. If errors exist, print only the existing error object. If the operation succeeds and warnings exist, include a top-level `warnings` array on the successful JSON resource output, sorted by `field` then `message`.

Alternative considered: print warnings to stderr. Existing CLI contracts use JSON stdout and no stderr for command results, so keeping warnings in the JSON response preserves machine-readability.

### Centralize runtime-change validation and migration start

After deep-merge update validation has a candidate resource, compare stored and candidate `spec.runtime`. A change from one catalog version to another is a version change. Validate downgrade, active-migration immutability, strategy-specific rules, and topology restrictions before mutating status. Once valid, set the target runtime on the candidate and initialize `status.migration` with the stored source runtime, target runtime, and first stage for the selected strategy.

Alternative considered: start migration during field normalization. Update normalization does not have the stored resource context needed for source runtime, active migration, downgrade, or strategy rules.

### Model migration progression as explicit stages

Store `status.migration.stage` as the current stage. `FullStop` and `RollingPatch` use a single `Migrate` stage, so `mesh migrate` completes them when called. `LiveMigration` should use a deterministic multi-stage sequence in code so advancing by one stage is observable before completion.

Alternative considered: immediately complete all migrations on update. The checkpoint requires an active migration and a `mesh migrate` command, so completion must be a separate user action.

### Recompute stability from blocking conditions

Set `status.stable` from the documented condition set: `Healthy=True`, `PrechecksPassed=True`, and no active `GracefulShutdown`, `Scaling`, or `Migration` condition. This should be applied anywhere mesh status is initialized, reconciled, migration state changes, or public output is produced.

Alternative considered: keep `status.stable` as a simple transition flag. That misses the new active migration condition and makes stability drift likely across describe/update paths.

## Risks / Trade-offs

- Warning output can disturb callers expecting the full resource shape only -> Keep warnings top-level and only on successful operations; add focused tests for deprecated create/update output.
- Active migration validation overlaps with ordinary update merge validation -> Accumulate errors in a single list and sort through the existing error printer so users get all applicable failures.
- The LiveMigration stage names are not fully specified by the checkpoint -> Use stable internal stage names and rely on the spec only requiring multiple ordered stages unless a later checkpoint names them.
- Runtime catalog updates will require code changes -> This is acceptable for the exercise and avoids adding file discovery or config parsing surface area.
