## Context

Mesh resources are implemented in `meshctl.py` with create/update normalization, merged-resource validation, status reconciliation, and JSON output helpers. Existing behavior already defaults `spec.migration.strategy` to `FullStop`, computes lifecycle conditions, and exposes mesh CRUD commands, but runtime values are only syntax-checked and migration state is not modeled.

Checkpoint 6 turns runtime changes into a first-class mesh lifecycle event. The implementation must preserve the current single-file CLI shape, keep validation errors accumulated, and add warnings without changing the successful exit behavior.

## Related Work

**`mesh-resource-management/add-meshctl-mesh-crud`**: Defines the mesh command surface and resource management baseline — informs the decision to add migration behavior inside the existing `mesh create`, `mesh update`, and mesh subcommand routing rather than creating a separate top-level command, because the related intent established mesh CRUD as the operator entry point for resource lifecycle work.

## Goals / Non-Goals

**Goals:**

- Validate optional `spec.runtime` against a small runtime catalog on mesh create and update.
- Add warning output for deprecated runtime targets only when the operation succeeds.
- Support `FullStop`, `LiveMigration`, and `RollingPatch` strategy values and their version-change restrictions.
- Persist active migration state in `status.conditions` and `status.migration`.
- Add `mesh migrate <name>` to advance or complete active migrations.
- Keep unrelated spec updates possible while migration is active.
- Make `status.stable` reflect active `Migration` conditions.

**Non-Goals:**

- No external runtime catalog service or dependency.
- No asynchronous migration worker; stage transitions are explicit CLI operations.
- No implementation of real infrastructure migration side effects.

## Decisions

1. Keep the runtime catalog as an in-process constant in `meshctl.py`.

   The checkpoint gives a fixed catalog shape and this CLI currently keeps validators as local constants and functions. A constant mapping from version to status keeps validation deterministic and testable. Alternative considered: read a catalog file from disk; that would add IO and configuration behavior outside the checkpoint.

2. Add warning-aware success output alongside existing error output.

   Existing commands return JSON to stdout and use `print_errors` for failed validations. Successful create/update responses should continue printing the full public resource unless warnings exist, in which case the response can include a top-level `warnings` array next to the resource payload fields. Warnings must be sorted and suppressed whenever errors exist.

3. Split runtime validation into syntax, catalog status, and version-change checks.

   `validate_runtime` should continue handling semantic validity for `major.minor.patch`, while new catalog helpers validate known versions and status. Update-only helpers should compare stored and candidate runtime values, reject downgrades, and apply strategy-specific constraints. This keeps create behavior from accidentally starting migrations. _(see `mesh-resource-management/add-meshctl-mesh-crud`)_

4. Model migration state directly on the mesh resource.

   On a runtime change, `mesh_update` should persist the target in `spec.runtime`, set a `Migration` condition, and write `status.migration` with `sourceRuntime`, `targetRuntime`, and `stage`. `FullStop` and `RollingPatch` start at `Migrate`; `LiveMigration` uses an ordered stage list constant so `mesh migrate` can advance deterministically.

5. Make migration transitions explicit through mesh subcommand routing.

   Add a `migrate` parser entry under `mesh` and route it from `main` to a new `mesh_migrate(name)` function. That function should load the stored mesh, validate active migration presence, advance one stage or complete final stage, save the store, and print `public_resource`.

6. Recompute stable status from blocking conditions.

   Current status reconciliation sets `status.stable` in branch-specific ways. Add a helper that derives stability from `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration`, then call it after status changes, migration starts, migration advances/completes, rollback, and public upgrade paths.

## Risks / Trade-offs

- [Risk] Existing tests may expect create output to be exactly the mesh resource. -> Mitigation: only add the `warnings` member when warnings exist; no-warning successful output remains unchanged.
- [Risk] Validation order could hide multiple checkpoint-required errors. -> Mitigation: append all independent validation errors before checking `if errors`, and avoid early returns inside strategy-specific validation except for malformed versions.
- [Risk] Runtime changes interact with existing scaling/shutdown status logic. -> Mitigation: isolate migration start/completion helpers and apply the stability helper after existing reconciliation logic.
- [Risk] LiveMigration stage names are not specified in detail. -> Mitigation: define a clear ordered stage list in code and tests, while preserving the contract that `mesh migrate` advances one stage and final stage completes.

## Migration Plan

1. Add runtime catalog, strategy constants, migration stage constants, warning helpers, and version parsing helpers to `meshctl.py`.
2. Extend mesh create/update validation to collect warnings and apply catalog validation.
3. Extend update reconciliation to start migration state for runtime changes and to block runtime/strategy changes during active migration.
4. Add `mesh migrate` command routing and transition handling.
5. Add tests in `tests/test_meshctl_cli.py` for catalog status, warnings, strategy validation, migration lifecycle, active migration restrictions, rollback, stability, and error accumulation.

## Open Questions

- The checkpoint states that LiveMigration has multiple stages but does not name them. The implementation should choose stable internal names and cover only the externally required transition behavior in tests.
- The checkpoint mentions LiveMigration rollback but does not specify the request shape. The implementation should use the smallest existing-compatible update shape, such as a boolean rollback field under `spec.migration`, and document it in tests.
