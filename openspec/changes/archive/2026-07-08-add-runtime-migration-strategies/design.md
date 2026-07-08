## Context

The CLI currently stores all mesh resources in the JSON store managed by `meshctl.py`, with create/update flows normalizing input, validating merged resources, reconciling status, and printing JSON resources or validation errors. Runtime validation is currently limited to semantic-version shape, migration strategy validation only accepts `FullStop`, and status stability is driven by lifecycle conditions such as `Scaling` and `GracefulShutdown`.

This change adds catalog-aware runtime validation, warnings, multiple migration strategies, persisted migration state, and a new migration command. It touches CLI parsing, mesh validation, status reconciliation, output envelopes, and tests.

## Related Work

**`mesh-resource-management/add-mesh-lifecycle-topology`**: Adds update semantics, topology validation, and lifecycle-aware status — informs the decision to treat runtime changes as update-driven lifecycle transitions because that related work established merged-resource validation and status reconciliation as the mesh update boundary.

## Goals / Non-Goals

**Goals:**
- Validate `spec.runtime` against a local catalog only when the field is present.
- Preserve successful create/update behavior while adding sorted warnings for deprecated runtimes.
- Support `FullStop`, `LiveMigration`, and `RollingPatch` strategy validation for runtime changes.
- Persist and expose migration state through `status.conditions` and `status.migration`.
- Add `meshctl mesh migrate <name>` to advance or complete active migrations.
- Keep `status.stable` consistent across scaling, graceful shutdown, and migration conditions.

**Non-Goals:**
- Downloading or dynamically updating the runtime catalog.
- Simulating real infrastructure migration work.
- Changing the existing zero exit-code behavior for validation errors.
- Reworking storage beyond the existing JSON store format.

## Decisions

### Runtime Catalog as Local Data

Represent the catalog as an in-process mapping from runtime version to status. This keeps validation deterministic and mirrors existing local validation constants for access, encryption, and one-shot resource rules. The initial catalog includes `3.0.0` as deprecated, `3.1.0` as skipped, and `3.1.1`/`4.0.0` as supported.

Alternative considered: load the catalog from a separate file. That would make updates easier later, but it adds file discovery and error handling that the checkpoint does not require.

### Warnings Travel with Successful JSON Output

Return warnings as a top-level `warnings` array alongside the successful resource JSON when deprecated runtimes are accepted. Validation errors continue using the existing `{"errors": [...]}` shape, and warning generation runs only after all validation errors are known.

Alternative considered: print warnings to stderr. The existing CLI uses stdout JSON for machine-readable results, so keeping warnings in stdout preserves the command contract and test style.

### Runtime Change Validation in the Merged Update Path

Detect version changes after `mesh_update` deep-merges the incoming patch with the stored mesh. This allows strategy checks to see the effective target runtime, current runtime, target strategy, and topology in one place. The implementation should add dedicated helpers for catalog lookup, version comparison, strategy-specific rules, and active migration guards. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

Alternative considered: validate only the incoming patch. That would miss interactions with preserved fields such as existing runtime, regions, and active migration status.

### Migration State Uses Existing Condition Helpers

Use the existing status condition helpers for the `Migration` condition, and add `status.migration` with `sourceRuntime`, `targetRuntime`, and `stage`. `FullStop` and `RollingPatch` use the single `Migrate` stage. `LiveMigration` should use a small ordered sequence so `mesh migrate` can demonstrate multi-stage advancement while remaining deterministic.

Alternative considered: store migration progress only in a private `_transition` field. That would hide required public state and make `mesh migrate` unable to operate from persisted resources.

### Stability Computed from Conditions

Centralize stability calculation so create, update, describe, migration advance, rollback, and transition completion all apply the same rule: healthy/prechecks true, and graceful shutdown/scaling/migration absent or false. This extends the existing lifecycle-aware status behavior rather than adding one-off status assignments. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

Alternative considered: set `status.stable` manually in each branch. That matches some existing code but is brittle once migration can interact with scaling and graceful shutdown.

### Command Dispatch Mirrors Existing Mesh Operations

Add `migrate` as a mesh subcommand in `build_parser()` and dispatch from `main()` next to create/list/describe/delete/update. The handler should load the stored mesh, validate active migration presence, advance or complete migration state, persist the store, and print the full public resource.

Alternative considered: model migration as `mesh update`. A dedicated command matches the checkpoint and keeps stage advancement separate from declarative spec updates.

## Risks / Trade-offs

- Runtime catalog drift -> Keep the catalog isolated behind helper functions so future checkpoints can replace the source without changing validation call sites.
- Warning envelope compatibility -> Existing callers expecting a raw resource may need to tolerate top-level `warnings`; tests should pin the exact successful-warning shape.
- Migration and scaling interactions -> Recompute stability from conditions after every status mutation and add regression tests covering active migration plus existing lifecycle paths.
- Error accumulation complexity -> Strategy validators should append errors instead of returning early, especially for RollingPatch and active migration guards.

## Migration Plan

1. Add runtime catalog and migration-stage helpers in `meshctl.py`.
2. Extend mesh parser/dispatch with `mesh migrate <name>`.
3. Update create/update validation to collect warnings and migration errors.
4. Persist migration status during runtime changes and migrate command transitions.
5. Update `tests/test_meshctl_cli.py` with catalog, warning, strategy, lifecycle, command, rollback, and stability coverage.

Rollback is a code rollback only; existing stored meshes without `status.migration` remain compatible because `upgrade_stored_resource()` can continue defaulting missing fields.

## Open Questions

- The checkpoint names rollback behavior but does not specify the CLI shape for requesting rollback. Implementation should choose a minimal discoverable shape, such as `meshctl mesh migrate <name> --rollback`, unless later instructions define a different command.
- The exact multi-stage sequence for `LiveMigration` is described only as "Multiple stages"; implementation should define stable stage names in tests.
