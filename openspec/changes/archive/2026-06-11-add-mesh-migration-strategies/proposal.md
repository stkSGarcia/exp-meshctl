## Why

Mesh runtime upgrades need a defined contract for which runtime versions can be targeted, which migration strategies are valid, and how in-progress migrations are represented and advanced. Without this, `spec.runtime` updates are only scalar validation and cannot model deprecated versions, skipped versions, active migration state, rollback, or stability changes.

## What Changes

- Validate `spec.runtime` against a runtime catalog when present on mesh create and update.
- Accept supported catalog versions, reject skipped or unknown versions, and emit non-fatal warnings for deprecated versions on otherwise successful operations.
- Expand `spec.migration.strategy` from only `"FullStop"` to `"FullStop"`, `"LiveMigration"`, and `"RollingPatch"`.
- Start an active migration when an existing mesh changes from one catalog runtime version to another, including persisted `status.migration` details and a `Migration` condition.
- Add `mesh migrate <name>` to advance or complete an active migration and print the full mesh resource.
- Reject runtime and strategy changes while a migration is active, while still allowing unrelated spec updates.
- Treat active migrations as unstable for `status.stable` and keep existing lifecycle stability checks intact.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mesh-resource-management`: Add runtime catalog validation, warning output, migration strategy validation, migration lifecycle state, `mesh migrate`, update constraints during active migration, and migration-aware stability.

## Impact

- `meshctl.py` mesh create/update validation and output projection.
- Mesh persistence shape for `status.migration` and `Migration` conditions.
- Mesh command routing for the new `mesh migrate <name>` operation.
- Existing tests for runtime validation, migration strategy validation, update behavior, status stability, and JSON output shape.
