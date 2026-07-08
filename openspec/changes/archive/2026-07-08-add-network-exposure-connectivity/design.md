## Context

`meshctl.py` is a single-file CLI with mesh create, update, describe, delete, migrate, and one-shot operations backed by a JSON store. Mesh create currently normalizes spec defaults, validates through `validate_merged_resource`, stores the resource, and prints `public_resource`; update deep-merges the incoming patch into the stored resource, validates the merged result, then prints the same public shape. Tests in `tests/test_meshctl_cli.py` exercise the CLI through subprocesses and assert JSON output.

## Related Work

**`one-shot-operations/add-one-shot-operations`**: Defines command-oriented operations layered on mesh resource management. It informs the decision to implement `mesh shell` as a narrow command handler that prints one purpose-built JSON object because this related work already treats command outputs as stable API contracts. _(see `one-shot-operations/add-one-shot-operations`)_

**`mesh-resource-management/add-mesh-lifecycle-topology`**: Defines mesh create/list/describe/delete/update behavior and update validation. It informs the decision to integrate exposure and management fields into the existing mesh normalization, validation, update, and public output flow because connectivity is part of mesh resource lifecycle state. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

## Goals / Non-Goals

**Goals:**

- Add `spec.exposure` support for Gateway, DirectPort, and Balancer modes.
- Compute `status.connectionDetails` for exposed meshes and omit it for unexposed meshes.
- Add `spec.management.enabled`, default it to `false`, compute management connection details when enabled, and reject post-create changes.
- Add `meshctl mesh shell <name>` with success output limited to the connection details object.
- Preserve the existing JSON error shape and sorted error ordering.

**Non-Goals:**

- No real network provisioning, socket connection, or shell session is introduced.
- No new persistent store format outside the existing mesh resource JSON is required.
- No new external dependency is required.

## Decisions

### Normalize Connectivity With Mesh Spec Defaults

Create helper functions in `meshctl.py` for exposure and management normalization, called from `normalize_mesh_for_create` and `upgrade_stored_resource`. Exposure remains absent when omitted, while management defaults to `{"enabled": false}` or an equivalent public `spec.management.enabled` shape.

Alternative considered: compute connectivity fields only in `public_resource`. That would make describe output work, but it would leave stored resources without canonical defaults and make update immutability checks harder to reason about.

### Validate Exposure by Mode in `validate_merged_resource`

Add `validate_exposure_object` and `validate_management_object` beside the existing access, migration, and network validators. These helpers should reject missing or invalid `spec.exposure.type`, reject forbidden sub-fields by full dot-path, validate string/map/integer/boolean types, and rely on the existing `print_errors` sorting.

Alternative considered: validate during normalization only. Update already validates merged resources after `deep_merge`, so keeping validation in `validate_merged_resource` gives create and update the same behavior.

### Recompute Connectivity Status From Spec

Add a status reconciliation helper that derives `status.connectionDetails` and `status.managementConnectionDetails` from the canonical spec during create, describe upgrade, and successful update. Gateway host uses `spec.exposure.hostname` or a default, DirectPort host uses mesh name, Balancer host uses `"<name>-external"`, and all protocols are `"https"`.

Alternative considered: store only the derived fields at create/update time. Recomputing in `upgrade_stored_resource` protects older store entries and keeps describe output consistent if defaults evolve inside the code.

### Add `mesh shell` as a Mesh Subcommand

Extend parser dispatch in `build_parser` and `main` with `mesh shell <name>`. The handler loads the mesh, returns the standard not-found error if missing, rejects meshes without `status.connectionDetails`, and prints only that object when present.

Alternative considered: add shell behavior to the existing one-shot command family. The checkpoint names `meshctl mesh shell <name>`, and the result is a lookup against mesh status rather than a separate resource lifecycle.

## Risks / Trade-offs

- Default port constants may be under-specified by the checkpoint -> define named constants in `meshctl.py` and cover default behavior in tests.
- Partial updates can leave stale status if recomputation is missed -> call the connectivity status helper from create, update, and `upgrade_stored_resource`.
- Deep-merge updates cannot remove exposure by omission -> this matches existing update semantics where omitted fields are preserved; explicit removal is out of scope.
- Error messages for type validation are not fully prescribed -> tests should assert required prescribed `field` and `type` values, and assert exact messages only where the checkpoint specifies them.

## Migration Plan

Existing mesh records are upgraded lazily through `upgrade_stored_resource`. Meshes without exposure will gain the management default and will not gain `status.connectionDetails`; meshes with future exposure-shaped data will have status recomputed on describe or update. Rollback is limited to removing the new fields from stored resources if needed.

## Open Questions

- The checkpoint says exposure ports have defaults but does not name the numeric defaults for DirectPort and Balancer. Implementation should choose stable constants and document them in tests.
- The default Gateway hostname is unspecified. Implementation should choose a deterministic value based on the mesh name or a fixed local convention and test it.
