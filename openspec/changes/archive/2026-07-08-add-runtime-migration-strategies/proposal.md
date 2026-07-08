## Why

Mesh runtime upgrades need an explicit contract so operators can tell when a runtime version is valid, which migration strategy is allowed, and how an in-progress migration advances or blocks conflicting updates. Today the checkpointed behavior requires catalog-driven validation, warnings, staged migration status, and a dedicated `mesh migrate` command to make runtime changes predictable.

## What Changes

- Add catalog validation for `spec.runtime` on `mesh create` and `mesh update`, while allowing `spec.runtime` to remain optional.
- Accept supported runtime versions, accept deprecated versions with sorted warnings on successful operations, and reject skipped or unknown versions with the documented validation shape.
- Add `spec.migration.strategy` values `FullStop`, `LiveMigration`, and `RollingPatch`, with `FullStop` as the default and strategy-specific validation for runtime changes.
- Start a migration when an existing catalog runtime changes, persist source/target/stage state, and expose `meshctl mesh migrate <name>` to advance or complete the active migration.
- Block runtime and migration strategy changes while a migration is active, while still allowing unrelated spec updates.
- Incorporate `Migration` into `status.conditions` and `status.stable` so in-progress migrations make the mesh unstable until completion.

## Capabilities

### New Capabilities
- `mesh-runtime-migrations`: Runtime catalog validation, warnings, migration strategy validation, migration lifecycle state, `mesh migrate`, and stability behavior for runtime changes.

### Modified Capabilities
- None.

## Related Work

### Related Changes
- `add-mesh-lifecycle-topology`: Introduced lifecycle-aware mesh behavior around update semantics, topology validation, and status. This change complements it by making runtime updates lifecycle-aware through migration state, warning output, and stability rules rather than treating version changes as ordinary field edits.

### Related Specs
- `mesh-resource-management/add-mesh-lifecycle-topology`: Covers `mesh update -f <path>`, topology validation, and lifecycle-aware status. This change reuses that update/status foundation for runtime catalog checks, active migration guards, and `status.stable` calculation.

## Impact

- CLI behavior for `mesh create`, `mesh update`, `mesh describe`, and the new `mesh migrate` subcommand.
- Mesh resource schema for `spec.runtime`, `spec.migration.strategy`, `status.conditions`, `status.migration`, and `status.stable`.
- Validation and error/warning response shapes.
- Persistence logic for runtime changes and migration lifecycle transitions.
