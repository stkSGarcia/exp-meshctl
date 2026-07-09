## Context

`meshctl.py` currently owns the mesh command parser, YAML normalization, validation, JSON store persistence, public resource rendering, and lifecycle status transitions. Mesh updates already use a stored resource plus a merged candidate, then reconcile status before saving. This change adds runtime catalog semantics and migration state to that same create/update path, plus a migration command that mutates stored status and prints the public mesh resource.

## Related Work

**`mesh-resource-management/add-meshctl-mesh-crud`**: Defines the existing mesh command surface for create, list, describe, and delete through `meshctl.py` — informs keeping runtime validation, migration commands, and output shapes inside the current mesh command family because `add-mesh-lifecycle-topology` already extended the same CLI surface with update and lifecycle status behavior.

**`mesh-resource-management/add-vault-resource-management`**: Defines dependency checks that prevent deleting meshes referenced by vaults — informs preserving existing mesh storage and not changing delete semantics because migration state is orthogonal to vault dependency validation.

## Goals / Non-Goals

**Goals:**
- Validate `spec.runtime` against a catalog while preserving the existing semantic-version shape check.
- Allow the new migration strategies and enforce their version-change constraints during create/update.
- Persist active migration state in `status.conditions` and `status.migration`.
- Add a migration transition operation that advances or completes an active migration and prints the full mesh.
- Keep warning and error output deterministic and compatible with current JSON response patterns.
- Update `status.stable` so active migrations make a mesh unstable.

**Non-Goals:**
- No external runtime catalog service or dependency.
- No asynchronous migration execution outside the JSON store.
- No changes to vault dependency behavior or one-shot resource contracts.
- No automatic background progression of migration stages.

## Decisions

### Runtime Catalog

Add a module-level runtime catalog in `meshctl.py`, keyed by version with status values of `supported`, `deprecated`, and `skipped`. Validation should run after the existing semantic-version parser accepts a string, so malformed runtimes continue to produce the current `spec.runtime` invalid error without catalog lookups.

Alternative considered: load the catalog from a file. The checkpoint describes a fixed catalog table and the current project is a single-file CLI with no config loading pattern, so an in-code catalog is the smallest consistent choice.

### Warning Collection

Thread a warning list through mesh create/update validation alongside errors. Deprecated runtimes append a warning only after the operation has no errors; before printing success, sort warnings by `field` and `message` and include a top-level `warnings` array in the success payload when non-empty.

Alternative considered: print warnings to stderr. Current CLI behavior returns machine-readable JSON and keeps stderr empty in tests, so warnings should be serialized in stdout.

### Strategy and Version Rules

Replace the single-value strategy validator with an allowed-strategy set and keep `FullStop` as the default. Add helpers for parsing runtime versions into integer tuples, comparing downgrades, checking RollingPatch major/minor compatibility, and detecting LiveMigration with configured `spec.regions`.

The version-change helper should run only when both stored and candidate runtimes are catalog-valid versions and the value changes. First assignment of `spec.runtime` should persist normally without creating migration state. _(see `mesh-resource-management/add-meshctl-mesh-crud`)_

### Migration State

Represent an active migration with both a `Migration` condition and `status.migration` containing `sourceRuntime`, `targetRuntime`, and `stage`. Use existing condition helpers (`set_condition`, `clear_condition`, and `sort_conditions`) so ordering and deduplication remain consistent with lifecycle/topology status.

For `FullStop` and `RollingPatch`, the stage sequence is `["Migrate"]`. For `LiveMigration`, define a deterministic multi-stage sequence in code. The exact names are implementation details, but the first stage must be stable across create/update and tests.

### Migration Commands

Add a mesh operation that advances active migrations by name. `mesh migrate <name>` should load the store, use the same not-found shape as describe/delete, reject missing `status.migration`, advance to the next stage when possible, or complete by removing the `Migration` condition and `status.migration`. It should then save and print `public_resource(resource)`.

Rollback is modeled as a separate mesh operation backed by the same migration helper. It should be accepted only when the active migration strategy is `LiveMigration`; on success, clear the migration condition and `status.migration`. This keeps rollback state transitions explicit without overloading normal update semantics, which must reject runtime and strategy changes during active migration.

Alternative considered: advance migrations during `mesh describe`. Existing pending scale/resume transitions already complete on describe, but migrations are operator-controlled and the checkpoint introduces `mesh migrate`, so migration state should not progress by reading the resource.

### Active Migration Update Guard

During `mesh update`, detect active migration on the stored resource before status reconciliation. If the incoming patch changes `spec.runtime` or `spec.migration.strategy`, accumulate the specified invalid errors. Other spec changes continue through normal validation and reconciliation.

### Stability Computation

Centralize stable-state calculation so update reconciliation and public rendering both consider `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration`. Existing scale/shutdown code can still set transition conditions, but the final public status should treat active migration as unstable.

## Risks / Trade-offs

- Catalog status and semver validation can produce duplicate `spec.runtime` errors if ordering is careless -> Run catalog checks only after the runtime value is a syntactically valid version.
- Adding warning output changes successful response shape -> Include `warnings` only when non-empty so existing success payloads remain unchanged.
- Migration state can be lost if status reconciliation overwrites conditions -> Use condition helpers after existing lifecycle reconciliation, then recompute stability.
- RollingPatch can produce multiple same-field errors -> Append both errors and keep existing error sorting without deduplicating by field/type.
- Rollback command naming is not explicitly stated in the checkpoint -> Keep rollback implementation isolated so the CLI alias can be adjusted without touching migration state logic.

## Migration Plan

1. Add catalog, warning, strategy, and version helper tests.
2. Implement validation helpers and success warning serialization.
3. Add migration state helpers and active-update guards.
4. Add the migrate and rollback command paths.
5. Update stability calculation and dependent one-shot stability tests as needed.

Rollback of this code change is straightforward: remove the new commands and helpers, restore the previous single-strategy validator, and keep existing store data compatible by ignoring `status.migration` on older code.

## Open Questions

- The checkpoint names `mesh migrate` but does not name the rollback CLI surface. The implementation should default to an explicit `mesh rollback <name>` operation unless an applying change decides to expose rollback as a flag or hidden helper.
