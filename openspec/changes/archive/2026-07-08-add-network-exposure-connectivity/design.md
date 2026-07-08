## Context

`meshctl.py` already owns mesh command dispatch, YAML normalization, persistence, status projection, and JSON error formatting in a single CLI module. Mesh create and update normalize `spec` into a canonical stored resource, while describe prints `public_resource()` output. The connectivity change adds a new mesh spec branch, derived status fields, an immutable management flag, and one additional mesh subcommand.

## Related Work

**`one-shot-operations/add-one-shot-operations`**: Defines one-shot command behavior that extends existing mesh, vault, policy, and credential command surfaces - informs the `mesh shell` output decision because this proposal adds a single-purpose command that returns a focused JSON payload rather than the full resource.

**`mesh-resource-management/add-mesh-lifecycle-topology`**: Adds update behavior and lifecycle/topology fields on mesh resources - informs the update validation decision because exposure and management fields must participate in the same partial-update merge and rejection flow.

**`mesh-resource-management/add-mesh-migration-strategies`**: Extends mesh resource management with runtime validation and update restrictions - informs the validation placement because connectivity checks should run alongside runtime, migration, and network validation and suppress warnings when errors exist.

**`mesh-resource-management/add-meshctl-mesh-crud`**: Establishes `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` through `meshctl.py` - informs parser and output integration because create and describe must expose derived connection details while preserving the existing resource envelope.

## Goals / Non-Goals

**Goals:**
- Normalize and validate `spec.exposure` for `Gateway`, `DirectPort`, and `Balancer`.
- Preserve accepted exposure fields and reject mode-incompatible sub-fields with full dot-path JSON errors.
- Derive `status.connectionDetails` consistently for create, describe, and `mesh shell`.
- Normalize `spec.management.enabled` to `false` when omitted, derive management connection details when enabled, and reject updates that change the flag.
- Add `meshctl mesh shell <name>` using the same not-found shape as other mesh commands.
- Cover the behavior in `tests/test_meshctl_cli.py`.

**Non-Goals:**
- Implement real networking, gateway provisioning, load balancer allocation, or port binding.
- Add new storage backends or external dependencies.
- Change existing mesh list summary output unless a future spec requires it.

## Decisions

1. Add connectivity normalization near existing mesh spec normalization.

   `normalize_mesh_for_create()` should call new helpers such as `normalize_exposure()` and `normalize_management()` after existing mesh spec branches. `upgrade_stored_resource()` should default `spec.management.enabled` for legacy stored meshes but should not invent `spec.exposure` when it is absent. This follows the mesh lifecycle pattern where stored resources are upgraded at read time _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_.

   Alternative considered: keep exposure only as raw user input and validate it late. That would make describe and shell less predictable because legacy and newly created resources could have different shapes.

2. Compute connection details from the public resource projection.

   Add a helper that updates status from `spec.exposure` and `spec.management.enabled`, then call it from status initialization/finalization or `public_resource()`. The helper should remove stale `status.connectionDetails` when exposure is absent and remove stale `status.managementConnectionDetails` when management is disabled. This keeps create and describe output aligned without asking callers to remember a second step _(see `mesh-resource-management/add-meshctl-mesh-crud`)_.

   Alternative considered: persist derived status only during create and update. That is simpler for write operations but risks stale output if stored resources are upgraded or status is recomputed during describe.

3. Validate exposure fields with an explicit allowed-field table.

   A small mapping from exposure type to allowed fields should drive forbidden-field errors. Type-specific validation should preserve `Gateway.annotations` as a mapping of string keys to string values, accept integer `port` fields for `DirectPort` and `Balancer`, and accept integer `directPort` for `DirectPort`. Error paths should use `spec.exposure.<field>` so sorting through `print_errors()` satisfies the ordering contract _(see `mesh-resource-management/add-mesh-migration-strategies`)_.

   Alternative considered: silently ignore fields that do not apply to the selected type. That would hide invalid configuration and violate the checkpoint contract.

4. Treat `spec.management.enabled` as a normalized immutable spec field.

   Normalize `spec.management` to `{"enabled": false}` when absent, validate it as a boolean, and compare stored versus candidate values in `validate_merged_resource()` on update. The immutable error should use the exact field, type, and message required by the spec _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_.

   Alternative considered: omit disabled management from stored spec. That would keep JSON smaller but complicate immutability checks because absent and false would need special-case equality.

5. Add `mesh shell` as a focused mesh subcommand.

   Extend `build_parser()` and `main()` with `mesh shell <name>`, then implement `mesh_shell()` beside `mesh_migrate()`. It should load and upgrade the mesh, fail with the standard not-found error when missing, fail with `spec.exposure` invalid when no connection details exist, and print the `connectionDetails` object only on success. This mirrors existing command dispatch while using the narrow output style from one-shot command work _(see `one-shot-operations/add-one-shot-operations`)_.

   Alternative considered: add a flag to `mesh describe` to print connection details. A dedicated command better matches the checkpoint and avoids changing describe semantics.

## Risks / Trade-offs

- Default port ambiguity -> Use one constant for the default exposure/direct port so tests and implementation agree.
- Derived status staleness -> Recompute connectivity status during public projection and after status transitions.
- Update merge edge cases -> Add tests where partial update attempts to change only `spec.management.enabled`.
- Error ordering regressions -> Reuse `print_errors()` and add multi-error tests for forbidden exposure fields.

## Migration Plan

No persistent migration step is required. Existing meshes are upgraded lazily when loaded: `spec.management.enabled` defaults to `false`, no exposure is added, and stale connectivity status fields are removed from public output when their driving spec fields are absent.

Rollback is code-only: removing the new helpers and parser command returns legacy meshes to their prior behavior because the new fields are optional.

## Open Questions

- What exact numeric default should be used for `spec.exposure.port` and `spec.exposure.directPort` when omitted? The checkpoint requires a default but does not name the value.
