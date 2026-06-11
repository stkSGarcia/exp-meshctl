## Context

Mesh resources currently accept optional semantic `spec.runtime` values and default `spec.migration.strategy` to `"FullStop"`, but runtime changes do not create migration state. Mesh status already has sorted conditions, lifecycle stability, and local JSON persistence, so runtime migration can be modeled inside the existing mesh resource path without adding a service or background worker.

The checkpoint introduces runtime catalog semantics, warnings, multiple migration strategies, an active migration status object, and a new `mesh migrate` command. The implementation should preserve the existing CLI pattern: deterministic local transitions, JSON on stdout, no stderr output for expected errors, and test-isolatable storage through `MESHCTL_STORE`.

## Goals / Non-Goals

**Goals:**

- Validate `spec.runtime` against an explicit runtime catalog on create and update when the field is present.
- Return deterministic warnings for deprecated catalog versions on otherwise successful create/update operations.
- Support `FullStop`, `RollingPatch`, and `LiveMigration` strategy validation and strategy-specific version-change rules.
- Persist active migration state on runtime changes and expose deterministic advancement through `mesh migrate <name>`.
- Prevent runtime and strategy changes during active migrations while allowing unrelated spec updates.
- Include active migration state in `status.stable` calculation.

**Non-Goals:**

- Implement real data-plane migration, asynchronous workers, timers, or external runtime discovery.
- Add automatic migration completion outside explicit `mesh migrate` calls.
- Add runtime catalog configuration files or network-backed catalog lookup.
- Change vault, task, snapshot, or recovery behavior except where they observe mesh stability through existing references.

## Decisions

1. Store the runtime catalog as an in-code constant with version, status, and ordering metadata.

   Rationale: The project is a compact CLI and the checkpoint defines a small catalog. A constant keeps validation deterministic and avoids adding file discovery or network concerns.

   Alternative considered: Load a catalog file from disk. That would be useful later, but it introduces configuration error handling that is outside this checkpoint.

2. Treat deprecated runtime versions as successful validation plus warnings.

   Rationale: The checkpoint requires deprecated versions to be accepted, warnings to appear only on success, and warnings not to affect the success exit code. Validation should accumulate errors first, then attach sorted warnings only when no errors are returned.

   Alternative considered: Print warnings to stderr. Existing command contracts keep machine-readable JSON on stdout and expected output off stderr.

3. Represent warnings as an optional top-level `warnings` array on successful mesh create/update JSON.

   Rationale: Existing success responses already print the full resource at the top level. Adding `warnings` alongside `metadata`, `spec`, and `status` preserves resource output while giving callers a stable warning shape.

   Alternative considered: Wrap successful results in `{ "resource": ..., "warnings": ... }`. That would be a larger breaking output-shape change.

4. Use deterministic stage lists per migration strategy.

   Rationale: `FullStop` and `RollingPatch` each have one `Migrate` stage. The checkpoint only says `LiveMigration` has multiple stages, so this design defines `Prepare`, `Replicate`, and `Cutover` to make CLI output and tests concrete.

   Alternative considered: Leave LiveMigration stage names implementation-defined. That would make `status.migration.stage` hard to test and less useful to callers.

5. Expose rollback as `mesh migrate <name> --rollback` for active LiveMigration migrations.

   Rationale: The checkpoint defines rollback behavior but not a trigger. Keeping rollback under the migrate command keeps all active migration transitions in one command surface and avoids allowing ordinary update-time runtime changes during active migrations.

   Alternative considered: Use `mesh update` with `spec.runtime` set back to the source runtime. That conflicts with the rule that runtime changes are rejected while a migration is active.

6. Complete a final-stage migration by removing `status.migration` and the `Migration` condition.

   Rationale: The target runtime is stored in `spec.runtime` when migration starts, so completion only needs to remove active migration markers and recompute stability.

   Alternative considered: Store the target runtime only in status until completion. That contradicts the checkpoint requirement to persist the target in `spec.runtime` on migration start.

## Risks / Trade-offs

- The in-code runtime catalog can drift from future real runtime support -> Keep the catalog isolated in a helper so a later change can replace the source.
- Adding `warnings` as a top-level field means successful mesh objects can have one non-resource key -> Tests and documentation should make this explicit for warning-bearing responses.
- Strategy validation depends on both stored and target runtime versions -> Centralize semantic version parsing and comparison for downgrade and RollingPatch checks.
- Active migration state can interact with scaling transitions -> Derive `status.stable` from conditions each time public output is prepared so `Migration`, `Scaling`, and `GracefulShutdown` are handled consistently.

## Migration Plan

No store migration is required. Existing meshes without `status.migration` remain valid and stable according to their current conditions. When a mesh with an existing `spec.runtime` is updated to a different catalog version, the new migration state is added at that point.

Rollback of this code change is limited to reverting code and tests. Stores containing `status.migration` remain JSON objects; older code may expose or ignore the extra status field but should still be able to load the store.

## Open Questions

None.
