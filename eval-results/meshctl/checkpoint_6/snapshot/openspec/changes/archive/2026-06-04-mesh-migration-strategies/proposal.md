## Why

The current meshctl implementation only supports a single migration strategy (`FullStop`) and performs no catalog-based validation of `spec.runtime` — it only checks the version format. As mesh infrastructure evolves, operators need lifecycle-aware migration paths (rolling patches, live migrations without downtime) and the system must enforce version compatibility via a curated catalog that distinguishes supported, deprecated, and skipped runtime versions.

### Related Specs

**`mesh-management`** — Covers mesh create/update/delete/describe operations, field validation, status conditions, and the migration strategy field (currently only `FullStop`). _Why it exists: managing mesh resources with validation and persistence._ This change extends that spec by expanding migration strategy values, adding catalog-based runtime validation, and introducing migration lifecycle state and the `mesh migrate` command.

This change builds directly on the foundation `mesh-management` established for strategy validation and runtime version format checking, replacing the simple format-only checks with catalog lookups and lifecycle management.

## What Changes

- **Runtime catalog validation**: `spec.runtime`, when present, must match a catalog entry; unlisted versions are rejected. Catalog statuses `supported`, `deprecated` (accept with warning), and `skipped` (reject) are enforced.
- **Warning output**: Successful operations may now emit a `warnings` array alongside the resource JSON for deprecated runtime versions.
- **Expanded migration strategies**: `spec.migration.strategy` now accepts `"LiveMigration"` and `"RollingPatch"` in addition to `"FullStop"`.
- **Version change rules**: Changing `spec.runtime` starts a migration; downgrades are forbidden for all strategies; `RollingPatch` and `LiveMigration` have additional constraints.
- **Migration lifecycle**: Changing `spec.runtime` to a new catalog version sets up `status.migration` and adds the `Migration` condition; completion removes both.
- **`mesh migrate` command**: `meshctl mesh migrate <name>` advances an active migration by one stage; on final stage, completes the migration.
- **Active migration guards**: While `Migration` is active, `spec.runtime` and `spec.migration.strategy` changes are rejected.
- **LiveMigration rollback**: Only `LiveMigration` supports rollback during an active migration.
- **Updated stability definition**: `status.stable` now accounts for the `Migration` condition.

## Capabilities

### New Capabilities

- `runtime-catalog-validation`: Validates `spec.runtime` against a version catalog (supported/deprecated/skipped), emitting warnings for deprecated versions and errors for skipped or unlisted ones on create and update.
- `migration-warnings`: Defines the `warnings` array output format, emission rules (only on success, suppressed when errors exist), and sorting rules.
- `migration-lifecycle`: Manages migration state — starting a migration (first runtime assignment vs. version change), stage sequences per strategy, `status.migration` persistence, `Migration` condition, and completion logic.
- `mesh-migrate-command`: Implements `meshctl mesh migrate <name>` to advance an active migration by one stage or complete it if on the final stage.
- `migration-active-guards`: Enforces restrictions on `spec.runtime` and `spec.migration.strategy` changes while a migration is in progress; defines LiveMigration rollback behavior.

### Modified Capabilities

- `migration-strategy-validation-and-default` (in `mesh-management`): Accept `"LiveMigration"` and `"RollingPatch"` as valid strategy values. Add version-change constraints: downgrade prohibition (all strategies), `RollingPatch` major/minor match + minimum major-4 rules, `LiveMigration` multi-region rejection.
- `runtime-version-validation` (in `mesh-management`): Replace format-only check with catalog lookup. Skipped versions are rejected; deprecated versions pass with a warning; unlisted versions are rejected.
- `enriched-status-model` (in `mesh-management`): `status.stable` must now also check that `Migration` is absent or `"False"`. Success output includes `status.migration` when an active migration exists.

## Impact

- `meshctl.py` — new `migrate` subcommand handler under `mesh`
- Runtime version validation logic — catalog lookup replaces regex-only check
- Migration strategy validation — expand allowed values, add cross-field version-change checks
- Output serialization — add `warnings` array to success responses when applicable
- Status model — `status.migration` block and `Migration` condition lifecycle management
- `status.stable` computation — additional condition check
