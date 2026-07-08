## Why

Mesh resources can currently be created and updated without a runtime compatibility contract or a controlled way to move between runtime versions. Checkpoint 6 adds the validation, warning, migration lifecycle, and operator command behavior needed to make runtime upgrades explicit, auditable, and safe.

## What Changes

- Add catalog-backed validation for optional `spec.runtime` values on mesh create and update.
- Emit sorted warnings for deprecated runtime versions only when the operation otherwise succeeds.
- Extend `spec.migration.strategy` to accept `FullStop`, `LiveMigration`, and `RollingPatch`, with strategy-specific validation for version changes.
- Start and persist migration state when an existing mesh changes from one catalog runtime version to another.
- Add `meshctl mesh migrate <name>` to advance or complete active migrations and print the updated mesh resource.
- Restrict updates during active migrations while still allowing unrelated spec updates.
- Support LiveMigration rollback by clearing active migration state.
- Update `status.stable` so active migration state makes a mesh unstable.
- Accumulate all applicable validation errors and preserve the specified error and warning shapes.

## Related Work

### Related Changes

- `add-mesh-lifecycle-topology`: introduced lifecycle-aware mesh status and topology validation for the mesh CLI. This change extends that lifecycle model with runtime-version transition state, migration conditions, and migration-aware stability.

### Related Specs

- `mesh-resource-management/add-meshctl-mesh-crud`: defines the mesh command surface and resource management baseline. This change builds on those create, update, and describe-style resource flows by adding runtime catalog validation, migration updates, and the new `mesh migrate` transition command.

## Capabilities

### New Capabilities

- `mesh-migration-strategies`: Runtime catalog validation, migration strategy validation, active migration lifecycle, migrate command behavior, rollback handling, warnings, and migration-aware stability.

### Modified Capabilities

- `mesh-resource-management`: Mesh create and update behavior is extended with runtime catalog validation, warnings, migration strategy validation, active migration state, and migration-related update restrictions.

## Impact

- Mesh resource schema and validation for `spec.runtime` and `spec.migration.strategy`.
- Mesh create and update command behavior, including warning output and accumulated validation errors.
- Mesh status persistence for `status.conditions`, `status.migration`, and `status.stable`.
- CLI command routing for `meshctl mesh migrate <name>`.
- Tests covering runtime catalog validation, strategy rules, migration lifecycle transitions, rollback, stable-status calculation, and warning/error output.
