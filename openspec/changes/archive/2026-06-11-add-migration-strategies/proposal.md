## Why

Mesh runtime changes need an explicit contract so callers can tell whether a target runtime is supported, deprecated, skipped, or mid-migration. The CLI also needs a predictable migration lifecycle so updates, one-shot operations, and stability reporting treat runtime transitions consistently.

## What Changes

- Add runtime catalog validation for `spec.runtime` on mesh create and update, including accepted, deprecated, skipped, and unsupported version behavior.
- Add successful-operation warnings for deprecated runtime targets without changing success exit codes.
- Extend `spec.migration.strategy` from only `"FullStop"` to `"FullStop"`, `"LiveMigration"`, and `"RollingPatch"`.
- Add strategy-specific version-change validation, including downgrade rejection, RollingPatch constraints, and LiveMigration topology restrictions.
- Start and persist active migrations when `spec.runtime` changes between catalog versions, including `Migration` conditions and `status.migration`.
- Add `mesh migrate <name>` to advance or complete active migrations.
- Reject runtime or strategy changes while a migration is active, while allowing unrelated spec updates.
- Update mesh stability so active migrations make meshes unstable.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `mesh-resource-management`: update mesh runtime validation, migration strategy validation, migration lifecycle/status behavior, warnings, `mesh migrate`, and stability rules.

## Impact

- Affects `meshctl.py` mesh create, update, describe, list/status projection, and a new `mesh migrate` subcommand.
- Affects persisted mesh resources by adding `status.migration` during active migrations and removing it on completion.
- Affects JSON success output by optionally adding sorted `warnings` on successful create/update operations.
- Affects tests for mesh validation, status, command routing, lifecycle transitions, warning output, and error ordering.
