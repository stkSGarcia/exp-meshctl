## Why

The current mesh management system accepts any semver-formatted runtime version and only supports a single migration strategy (`FullStop`), leaving operators with no way to perform live or rolling upgrades and no guidance on which runtime versions are safe to target. Introducing a runtime catalog, expanded migration strategies, and a dedicated `mesh migrate` command gives operators structured, safe version lifecycle management.

## What Changes

- **BREAKING**: `spec.runtime` validation now checks against a catalog of known versions; unlisted versions are rejected regardless of format
- `spec.runtime` catalog entries carry a status (`supported`, `deprecated`, `skipped`); deprecated versions are accepted with a warning; skipped versions are rejected
- Responses may now include a top-level `warnings` array emitted on successful operations
- `spec.migration.strategy` now accepts `"LiveMigration"` and `"RollingPatch"` in addition to `"FullStop"`
- `RollingPatch` enforces same-major/minor constraint and requires target major ≥ 4
- `LiveMigration` is incompatible with multi-region topology (`spec.regions` present)
- All strategies forbid runtime version downgrades
- Changing `spec.runtime` from one catalog version to another starts a migration and populates `status.migration`
- Migrations advance through strategy-specific stage sequences via `mesh migrate <name>`
- Updates reject changes to `spec.runtime` or `spec.migration.strategy` while a migration is active
- `LiveMigration` supports rollback during an active migration
- `status.stable` now factors in the `Migration` condition

## Capabilities

### New Capabilities
- `runtime-catalog`: Runtime version catalog with supported/deprecated/skipped status; catalog validation on create and update; warning emission for deprecated versions
- `mesh-migration-lifecycle`: Migration start on runtime version change, stage sequencing per strategy, completion cleanup of `status.migration` and `Migration` condition
- `mesh-migrate-command`: `mesh migrate <name>` subcommand that advances (or completes) an active migration by one stage

### Modified Capabilities
- `mesh-management`: Expand accepted migration strategies, add migration-active update guards, update `status.stable` definition, add `spec.regions` field referenced by `LiveMigration` constraint

## Impact

- `meshctl.py` — new `mesh migrate` subcommand routing
- Mesh validation logic — runtime catalog lookup replaces format-only check; strategy enum expansion
- Mesh update logic — active-migration guard on `spec.runtime` and `spec.migration.strategy`
- Mesh status logic — `status.stable` formula updated; `status.migration` field added on migration start/cleared on completion
- Response serialization — top-level `warnings` array conditionally included in successful responses
