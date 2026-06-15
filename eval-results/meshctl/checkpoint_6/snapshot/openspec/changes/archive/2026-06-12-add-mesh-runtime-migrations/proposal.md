## Why

Mesh runtime upgrades need an explicit contract so validation, warnings, migration state, and operator-driven advancement behave consistently across create, update, and migrate flows. Without this, `spec.runtime` changes can be accepted without catalog awareness or lifecycle guarantees.

## Related Work

### Related Changes

- `add-mesh-lifecycle-topology`: introduced mesh update semantics, topology validation, and lifecycle-aware status. This change builds on that update path by adding runtime catalog validation, migration guards, and `status.stable` behavior for migration state.
- `add-vault-resource-management`: introduced a second persisted resource type and dependency validation patterns. This change complements that validation approach by applying catalog-backed validation and warnings to mesh runtime targets.
- `add-meshctl-mesh-crud`: established the CRUD, defaulting, persistence, validation, and JSON output contract for mesh resources. This change extends the mesh resource contract with runtime migration-specific validation and command behavior.

### Related Specs

- `one-shot-operations/add-one-shot-operations`: defines one-shot resource command surfaces that extend mesh and vault resource management. This change reuses the command-output expectation that successful operations print the full resource, applying it to `meshctl mesh migrate`.
- `mesh-resource-management/add-mesh-lifecycle-topology`: defines mesh update behavior, topology validation, and lifecycle-aware status. This change builds on that capability with runtime version-change semantics, active migration update restrictions, and migration effects on stability.
- `mesh-resource-management/add-access-security-model`: defines additional mesh spec validation under the mesh resource management capability. This change follows the same field-scoped validation style for `spec.runtime` and `spec.migration.strategy`.

## What Changes

- Add runtime catalog validation for optional `spec.runtime` on mesh create and update.
- Emit sorted warnings for successful operations that target deprecated runtime versions.
- Reject skipped or unknown runtime versions with field-scoped validation errors.
- Add `spec.migration.strategy` values: `FullStop`, `LiveMigration`, and `RollingPatch`, with `FullStop` as the default.
- Enforce version-change rules for downgrades, strategy-specific constraints, and multi-region LiveMigration restrictions.
- Persist migration lifecycle state in `status.conditions` and `status.migration` when runtime version changes start a migration.
- Add `meshctl mesh migrate <name>` to advance or complete active migrations and print the full mesh resource.
- Reject runtime and migration strategy changes while a migration is active, while allowing unrelated spec updates.
- Update `status.stable` so active migration state prevents stability.

## Capabilities

### New Capabilities

- `mesh-runtime-migrations`: runtime catalog validation, migration strategy validation, migration lifecycle state, migration advancement, rollback behavior, and stability calculation.

### Modified Capabilities

- None.

## Impact

- Affected CLI behavior: `mesh create`, `mesh update`, and new `mesh migrate`.
- Affected mesh API fields: `spec.runtime`, `spec.migration.strategy`, `status.conditions`, `status.migration`, and `status.stable`.
- Affected validation and output shapes: field-scoped errors, successful-operation warnings, and full mesh resource output after migration advancement.
