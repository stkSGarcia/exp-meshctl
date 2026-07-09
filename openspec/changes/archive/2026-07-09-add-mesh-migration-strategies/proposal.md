## Why

Mesh runtime changes currently need explicit validation and lifecycle semantics so operators can distinguish unsupported targets, deprecated-but-allowed runtimes, skipped versions, and active migration progress. Adding catalog-backed runtime rules and strategy-aware migration state gives `meshctl` predictable update behavior before runtime upgrades become more complex.

## What Changes

- Add runtime catalog validation for `spec.runtime` on `mesh create` and `mesh update` when the field is present.
- Emit sorted warnings for deprecated catalog versions only on otherwise successful operations.
- Accept `spec.migration.strategy` values of `FullStop`, `LiveMigration`, and `RollingPatch`, with `FullStop` as the default.
- Apply strategy-specific version change rules, including downgrade rejection, `RollingPatch` major/minor constraints, and `LiveMigration` multi-region restrictions.
- Start and persist active migration state when `spec.runtime` changes from one catalog version to another.
- Add `meshctl mesh migrate <name>` to advance or complete active migrations and print the full mesh resource.
- Reject runtime and strategy changes while a migration is active, while allowing unrelated spec updates.
- Support rollback for active `LiveMigration` migrations and reject rollback for other strategies.
- Include migration activity in `status.stable` computation.

## Capabilities

### New Capabilities

- `mesh-migration-strategies`: Runtime catalog validation, migration strategy validation, migration lifecycle state, `mesh migrate`, rollback, and stability behavior for mesh resources.

### Modified Capabilities

- None.

## Related Work

### Related Changes

- `add-mesh-lifecycle-topology`: Expanded the mesh resource contract beyond basic CRUD into update semantics, topology validation, and lifecycle-aware status. This change complements it by adding runtime-version lifecycle transitions and migration-specific status behavior.

### Related Specs

- `mesh-resource-management/add-meshctl-mesh-crud`: Defines the existing `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` command surface through `meshctl.py`. This change reuses that command surface and extends it with update-time runtime validation and the new `mesh migrate` action.
- `mesh-resource-management/add-vault-resource-management`: Defines mesh deletion dependency conflicts when vaults reference a mesh. This change stays compatible with mesh resource dependency behavior while adding migration constraints that apply before deletion concerns.

## Impact

- `meshctl.py` mesh create/update validation, output shaping, and command routing.
- Mesh resource persistence shape for `status.conditions`, `status.migration`, and `status.stable`.
- Error and warning response serialization for validation failures and successful operations with warnings.
- Test coverage for runtime catalog statuses, migration strategy values, version change constraints, active migration updates, rollback, migration command errors, and stability calculations.
