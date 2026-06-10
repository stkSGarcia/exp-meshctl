## Why

Mesh runtime changes need an explicit compatibility and migration contract before the CLI can safely accept updates between runtime versions. This change adds catalog-backed runtime validation, user-visible warnings, migration strategy rules, and lifecycle state so version transitions are predictable and testable.

## What Changes

- Validate `spec.runtime` against a runtime catalog on `mesh create` and `mesh update` when the field is present.
- Accept supported catalog versions, accept deprecated versions with warnings on otherwise successful operations, and reject skipped or unknown versions.
- Add structured warning output sorted by `field` and `message`, without changing successful exit codes or appearing alongside errors.
- Expand `spec.migration.strategy` to accept `FullStop`, `LiveMigration`, and `RollingPatch`, defaulting to `FullStop`.
- Define version-change rules for downgrades, rolling patch compatibility, and live migration with multi-region topology.
- Start and persist migration status when `spec.runtime` changes between catalog versions, including source runtime, target runtime, stage, and a `Migration` condition.
- Add `mesh migrate <name>` to advance active migrations, print the full resource after transitions, and complete final-stage migrations.
- Reject runtime and migration strategy changes while a migration is active, while allowing unrelated spec updates.
- Support active `LiveMigration` rollback by removing migration status and condition state.
- Update `status.stable` so an active `Migration` condition makes the mesh unstable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mesh-resource-management`: Extend mesh runtime validation, warnings, migration strategy validation, migration lifecycle transitions, `mesh migrate`, active-migration update restrictions, rollback behavior, and stability requirements.

## Impact

- Affected code: `meshctl.py` validation/defaulting helpers, migration/status transition logic, persistence, CLI command dispatch, and JSON/YAML output shaping.
- Affected interface: `mesh create`, `mesh update`, `mesh describe`, and new `mesh migrate <name>` behavior.
- Affected tests: runtime catalog acceptance/rejection, warning emission/suppression/ordering, strategy validation, version-change constraints, migration start/advance/completion, active-migration update restrictions, rollback, and stable-status calculation.
- Dependencies: no new external dependency is expected.
