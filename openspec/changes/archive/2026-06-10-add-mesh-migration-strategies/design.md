## Context

The CLI currently stores mesh resources in a local JSON store and derives public status during create, update, and describe operations. Existing mesh behavior already includes partial update merge semantics, defaulted `spec.migration.strategy`, lifecycle conditions, `status.stable`, topology validation, and structured JSON error output.

Checkpoint 6 extends that resource model with catalog-backed runtime compatibility, warning output, version-change rules, persisted migration state, and a new `mesh migrate` operation. The implementation should stay in the single-file CLI shape unless the existing code already has helper boundaries that can absorb this behavior cleanly.

## Goals / Non-Goals

**Goals:**

- Validate `spec.runtime` against the runtime catalog on create and update only when present.
- Emit deterministic warnings for deprecated runtime versions only on successful operations.
- Accept and validate `FullStop`, `LiveMigration`, and `RollingPatch` migration strategies.
- Start, persist, advance, complete, and roll back migrations using explicit status fields.
- Preserve update atomicity while allowing unrelated updates during active migrations.
- Keep `status.stable` derived from the full condition set, including `Migration`.
- Add focused CLI tests for success output, warning output, validation errors, migration transitions, and active-migration restrictions.

**Non-Goals:**

- Add real orchestration, timers, or external runtime compatibility services.
- Implement a complete runtime release history beyond the catalog values required by the checkpoint.
- Change store backends or introduce package restructuring unrelated to the feature.
- Make warnings affect exit codes.

## Decisions

1. Represent the runtime catalog as a deterministic in-code mapping from version string to status.

   Rationale: The checkpoint requires a fixed runtime catalog and the project is a local CLI. A small mapping keeps validation transparent and avoids file-loading concerns.

   Alternative considered: Store the catalog in a separate data file. That would be useful for frequent catalog changes, but it adds path and packaging concerns without current benefit.

2. Validate runtime versions in two layers: semantic shape first, catalog membership/status second.

   Rationale: Existing validation already treats malformed runtime values as `spec.runtime` invalid errors. Keeping shape validation separate lets unknown catalog-listed and skipped cases produce clear catalog-specific messages while preserving existing invalid-field behavior.

   Alternative considered: Replace semantic-version parsing entirely with catalog lookup. That would accept only exact strings but would make malformed values indistinguishable from unsupported versions.

3. Compute warnings from the accepted candidate resource only after all errors are known.

   Rationale: Warnings must appear only for successful operations and must never accompany errors. Deferring warning assembly until after validation avoids leaking deprecated-version warnings when another field fails.

   Alternative considered: Emit warnings during field validation. That would require later filtering and is easier to get wrong.

4. Persist active migration state under `status.migration` and model active migration through a `Migration` condition.

   Rationale: The checkpoint defines public state that must survive between commands. Storing the source runtime, target runtime, and current stage in status makes `mesh migrate` deterministic and keeps `status.stable` derivable from conditions.

   Alternative considered: Track active migrations in hidden store metadata. That would reduce public status churn but conflicts with the required `status.migration` output.

5. Treat runtime changes as post-merge update transitions.

   Rationale: Update inputs are partial. Comparing the stored runtime to the post-merge target runtime lets unrelated updates preserve runtime and lets explicit runtime changes start migrations or fail strategy constraints atomically.

   Alternative considered: Validate only the incoming patch. That would miss changes caused by merge/default interactions and make active-migration rules harder to enforce.

6. Implement `mesh migrate <name>` as a synchronous state transition.

   Rationale: The CLI has no background reconciler. Advancing one stage per command and completing on the final stage directly matches the checkpoint and keeps tests deterministic.

   Alternative considered: Simulate asynchronous progress on `describe`. That would make migration advancement depend on reads, while the checkpoint explicitly assigns advancement to `mesh migrate`.

## Risks / Trade-offs

- Catalog logic can be duplicated across create and update -> Centralize runtime catalog lookup, warning generation, and skipped/unsupported error creation.
- Active migration restrictions can conflict with partial update merge semantics -> Compare stored and candidate values after merge so omitted fields are not treated as changes.
- Multiple validation failures can be lost if strategy checks return early -> Accumulate all applicable errors, including multiple `spec.runtime` invalid errors.
- Public status can drift from persisted status -> Use one status normalization/output projection path for create, update, describe, and migrate.
- LiveMigration rollback is underspecified as a CLI gesture -> Implement it through an update that expresses rollback while preserving the checkpoint's required state removal, and cover the chosen trigger in tests.

## Migration Plan

No store migration is required for fresh test stores. Existing meshes without `status.migration` have no active migration. Existing meshes without `spec.runtime` skip runtime catalog validation until a runtime is assigned.

Rollback is code-only: reverting the feature removes `mesh migrate` and catalog enforcement. Stores that contain `status.migration` remain JSON objects, though older code may ignore or expose those fields differently.

## Open Questions

- The checkpoint requires LiveMigration rollback but does not define the exact CLI input that requests rollback. The implementation should choose the smallest local convention and document it in tests, unless a later checkpoint supplies a dedicated rollback command.
