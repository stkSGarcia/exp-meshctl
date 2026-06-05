## Why

The `meshctl` tool validates `spec.runtime` format but has no concept of which runtime versions are actually available or deprecated, leaving users free to target invalid or end-of-life versions. The migration system only supports a single `FullStop` strategy with no lifecycle tracking, making it impossible to model real-world zero-downtime or patch-level upgrade workflows.

### Related Changes

**`mesh-lifecycle-and-topology`** — Added `mesh update` with lifecycle state machine, topology fields (`storage`, `replicationFactor`), and operational status (conditions, stable/stopped state). This change builds on that foundation by extending the update path with catalog-gated runtime transitions and full migration lifecycle management.

**`implement-meshctl`** — Introduced `spec.runtime` format validation (must parse as `major.minor.patch`) and a `spec.migration.strategy` field defaulting to `"FullStop"`. This change extends both: runtime validation now cross-references a version catalog, and migration strategy accepts two new values (`LiveMigration`, `RollingPatch`) with per-strategy version-change rules.

### Related Specs

**`implement-meshctl/mesh-management/runtime-version-validation`** — Ensures `spec.runtime` parses as `major.minor.patch`. _Why it exists: basic input hygiene before any catalog lookup._ This change extends it by adding catalog membership and status checks on top of the format check.

**`implement-meshctl/mesh-management/migration-strategy-validation-and-default`** — Accepts only `"FullStop"` as a valid migration strategy. _Why it exists: placeholder until additional strategies were specified._ This change replaces that constraint with the full three-strategy set and per-strategy version-change rules.

**`mesh-lifecycle-and-topology/mesh-management`** — Provides the update merge path, condition management helpers, and `status.stable` computation. _Why it exists: models real cluster lifecycle._ This change extends `status.stable` to include the `Migration` condition and adds the `status.migration` sub-object to the resource shape.

This combination of gaps makes it impossible to safely orchestrate runtime upgrades, validate version targets, or provide operators with meaningful migration progress signals—motivating these changes now, ahead of runtime upgrade tooling.

## What Changes

- Add a hardcoded runtime version catalog mapping each version string to `supported`, `deprecated`, or `skipped` status.
- `spec.runtime` validation on `create` and `update` now checks catalog membership; out-of-catalog versions are rejected, skipped versions are rejected with a specific message, deprecated versions are accepted with a `warnings` array in the response.
- `spec.migration.strategy` now accepts `"FullStop"` (default), `"LiveMigration"`, and `"RollingPatch"`, each with their own version-change constraints.
- Downgrades are forbidden for all strategies.
- `RollingPatch` requires same major+minor and target major ≥ 4; both rules are checked independently and both errors are reported when both fail.
- `LiveMigration` is rejected when `spec.regions` is configured.
- Changing `spec.runtime` from one catalog version to another starts a migration: sets `status.migration` (`sourceRuntime`, `targetRuntime`, `stage`) and adds a `Migration` condition.
- New `mesh migrate <name>` subcommand advances an active migration by one stage; completing the final stage removes `status.migration` and the `Migration` condition.
- Updates during active migration reject changes to `spec.runtime` and `spec.migration.strategy`.
- `LiveMigration` supports rollback (removes `Migration` condition and `status.migration`); other strategies do not.
- `status.stable` now requires `Migration` condition to be absent or `"False"`.
- Warnings are emitted only on success, sorted by `field` then `message`, and do not affect the exit code.

## Capabilities

### New Capabilities

- `runtime-catalog-validation`: Catalog-based `spec.runtime` validation with supported/deprecated/skipped status and deprecation warnings.
- `migration-lifecycle`: Migration state machine triggered by `spec.runtime` version changes, multi-stage progression via `mesh migrate`, and update guards during active migration.

### Modified Capabilities

- `mesh-management`: `status.stable` extended to gate on `Migration` condition; `spec.migration.strategy` validation expanded to three values; warning output shape added to all `create`/`update` responses.

## Impact

- `meshctl.py`: `validate_and_build`, `cmd_create`, `cmd_update` gain catalog checks and warning emission; `cmd_update` gains active-migration guards; new `cmd_migrate` handler added; `build_initial_status` and stability logic updated.
- `store.json`: mesh resources may now carry `status.migration` and a `Migration` condition entry.
- No external API or vault/task/snapshot resource shapes change.
