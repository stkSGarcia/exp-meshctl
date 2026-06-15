## Why

Runtime version changes currently lack a formal contract for catalog validation, migration strategy behavior, warning emission, and migration progress. This change defines how `meshctl` accepts, rejects, tracks, and completes runtime migrations so updates are predictable and dependent workflows can rely on mesh stability.

## Related Work

### Related Changes

- `add-mesh-lifecycle-topology`: added mesh update semantics, topology validation, and lifecycle-aware status. This change extends that work by making runtime changes a first-class lifecycle transition with explicit validation and status state.
- `add-vault-resource-management`: added dependency validation across persisted resources. This change complements that validation model by adding catalog-backed runtime validation and deterministic error shapes.
- `add-meshctl-mesh-crud`: established the core mesh CRUD contract, validation, defaulting, persistence, and JSON output shape. This change builds on that command surface by adding a migration command and warning output for successful operations.

### Related Specs

- `mesh-resource-management/add-mesh-lifecycle-topology`: specifies `mesh update -f <path>` and lifecycle status derivation. This change reuses update selection, partial-update behavior, and condition-driven status semantics for runtime version transitions.
- `one-shot-operations/add-one-shot-operations`: consumes `status.stable` when running task, snapshot, and recovery operations. This change updates the definition of stability so active migrations correctly make meshes unstable for those operations.
- `mesh-resource-management/add-vault-resource-management`: specifies validation-driven rejection for unsafe operations. This change follows that style for runtime catalog, strategy, and migration-state validation failures.

## What Changes

- Add runtime catalog validation for `spec.runtime` during mesh create and update when the field is present.
- Emit sorted warnings for deprecated runtime versions only when an operation otherwise succeeds.
- Add `spec.migration.strategy` values `FullStop`, `LiveMigration`, and `RollingPatch`, with `FullStop` as the default.
- Define downgrade rejection and strategy-specific runtime version-change constraints.
- Start and persist migration state when `spec.runtime` changes from one catalog version to another.
- Add `meshctl mesh migrate <name>` to advance or complete an active migration.
- Reject runtime and migration strategy changes while a migration is active, while allowing unrelated spec updates.
- Update `status.stable` so active migration state makes the mesh unstable.

## Capabilities

### New Capabilities

- `runtime-migration-strategies`: runtime catalog validation, migration strategy rules, migration lifecycle status, migration advancement, warning output, and stability behavior.

### Modified Capabilities

- None.

## Impact

- Affects mesh create, update, describe/output serialization, status derivation, validation error accumulation, and CLI command routing.
- Adds persisted migration status fields and a `Migration` condition to mesh resources.
- Adds warning output to successful create/update responses without changing success exit codes.
- Adds tests for runtime catalog states, strategy validation, migration lifecycle, migrate command errors, active-migration update restrictions, and stability calculation.
