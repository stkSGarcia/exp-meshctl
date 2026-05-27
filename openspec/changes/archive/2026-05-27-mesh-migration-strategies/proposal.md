## Why

The current mesh migration system only supports `FullStop` as a strategy and has no mechanism for managing a runtime version catalog, tracking active migration lifecycle stages, or advancing migrations through a `mesh migrate` command. This change introduces a complete migration lifecycle — catalog-backed runtime validation, two additional strategies (`LiveMigration`, `RollingPatch`), version-change rules, a migration state machine, and the `mesh migrate` subcommand.

## What Changes

- `spec.migration.strategy` accepts `"LiveMigration"` and `"RollingPatch"` in addition to `"FullStop"`.
- A runtime version catalog is introduced; `spec.runtime`, when present, must match a catalog entry with status `supported` or `deprecated` (skipped versions are rejected).
- Deprecated runtime versions emit a warning on successful `create`/`update` rather than an error.
- A warnings output block `{"warnings":[{"field":"…","message":"…"}]}` is added to successful responses.
- Version-change rules for downgrades, `RollingPatch` constraints, and `LiveMigration` multi-region restrictions are enforced on `create`/`update`.
- Changing `spec.runtime` from one catalog version to another starts an active migration, persisting `status.migration` and a `Migration` condition.
- `mesh migrate <name>` is added to advance an active migration by one stage, completing it when the final stage is reached.
- `status.stable` is updated to account for the `Migration` condition.
- Updating `spec.runtime` or `spec.migration.strategy` while a migration is active is rejected.
- Only `LiveMigration` supports rollback during an active migration.

## Capabilities

### New Capabilities

- `runtime-catalog`: Runtime version catalog with `supported`/`deprecated`/`skipped` statuses, catalog validation on create/update, and deprecation warnings.
- `migration-lifecycle`: Migration state machine — version-change rules, downgrade rejection, strategy-specific constraints, active migration tracking (`status.migration`, `Migration` condition), stage sequences, completion, and update restrictions during active migration.
- `mesh-migrate`: The `mesh migrate <name>` CLI command that advances or completes an active migration.

### Modified Capabilities

- `mesh-management`: Strategy validation expanded to accept `LiveMigration` and `RollingPatch`; `status.stable` formula updated to include `Migration` condition; warnings output format added to success responses.

## Impact

- `meshctl.py`: New `mesh migrate` command handler; updated strategy validation; runtime version validation now checks catalog; migration lifecycle state management.
- `store.json` schema: `status.migration` object and `Migration` condition added.
- Output format: Successful responses may include a top-level `warnings` array alongside the resource JSON.
