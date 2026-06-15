## Context

`meshctl.py` currently implements mesh create, update, describe, delete, migrate, persistence, validation, and public JSON projection in a single module. Mesh status is initialized and reconciled in shared helpers, while `public_resource()` controls the successful output shape and `print_errors()` already sorts JSON errors by `field` and `type`.

The new capability adds optional connectivity data under `spec.exposure`, derived connection details under `status`, an immutable management endpoint flag, and a new `mesh shell` subcommand.

## Related Work

> **`mesh-resource-management/add-meshctl-mesh-crud`**: Mesh CRUD commands, persistence, validation, and JSON output — informs adding `mesh shell` through the existing argparse and store lookup flow because the prior intent established mesh command behavior as the primary operator interface. _(see `mesh-resource-management/add-meshctl-mesh-crud`)_

> **`mesh-resource-management/add-access-security-model`**: Access configuration output and optional-field projection — informs preserving only applicable exposure fields and omitting `status.connectionDetails` when exposure is absent because the prior intent keeps public resource output explicit and mode-aware. _(see `mesh-resource-management/add-access-security-model`)_

> **`mesh-resource-management/add-mesh-lifecycle-topology`**: Mesh update semantics and status-aware successful output — informs validating `spec.management.enabled` immutability during update and deriving connection status in the public resource path because the prior intent made lifecycle status part of the mesh contract. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

## Goals / Non-Goals

**Goals:**

- Normalize and validate `spec.exposure` for `Gateway`, `DirectPort`, and `Balancer`.
- Compute `status.connectionDetails` and `status.managementConnectionDetails` from persisted resource state.
- Keep absent exposure equivalent to no external access and no connection details.
- Add `mesh shell <name>` with resource lookup, unexposed-mesh validation, and connection-details-only output.
- Cover create, describe, update, shell, and validation behavior with CLI tests.

**Non-Goals:**

- Provision real gateways, ports, load balancers, shells, or network connections.
- Add authentication negotiation to `mesh shell`.
- Change the existing JSON error envelope or process exit behavior.

## Decisions

1. Store normalized exposure and management configuration under `spec`, then derive connection status during status initialization, update reconciliation, and public projection.
   - Rationale: connection details are deterministic from the mesh name and spec values, so a helper can recalculate them whenever resource state is exposed.
   - Alternative considered: persist only status details. That risks stale status when exposure fields are updated.

2. Add dedicated helpers for `normalize_exposure()`, `validate_exposure_object()`, `connection_details_for()`, `normalize_management()`, and `management_connection_details_for()`.
   - Rationale: exposure has mode-specific field rules and status derivation that are distinct from access, resources, migration, and network storage validation.
   - Alternative considered: fold all rules into `validate_merged_resource()`. That would make update immutability and create-time normalization harder to read and test.

3. Enforce `spec.management.enabled` immutability inside `validate_merged_resource()` when a stored resource is available.
   - Rationale: existing immutable storage-size validation already lives there, so management immutability belongs in the same update validation stage.
   - Alternative considered: reject it inside `mesh_update()` before merging. That would duplicate path handling and miss future callers of merged validation.

4. Implement `mesh shell <name>` as a read-only command that loads the stored mesh, projects the public resource, and prints `status.connectionDetails` only.
   - Rationale: this reuses not-found behavior and computed status projection while satisfying the no-envelope output requirement.
   - Alternative considered: reconstruct details directly from raw store data in the command. That would create a second derivation path.

## Risks / Trade-offs

- Default host and port values are synthetic, not provider-backed -> Keep them deterministic and covered by tests so the local CLI contract stays stable.
- Public projection recalculates derived fields -> Ensure create, describe, shell, and update all call the same helper path to avoid drift.
- Mode-specific forbidden-field validation can produce multiple errors -> Use full dot-paths and rely on existing sorted error output for deterministic tests.

## Migration Plan

No data migration is required. Existing meshes without `spec.exposure` will continue to load and will omit `status.connectionDetails`; existing meshes without `spec.management` should be upgraded or projected with `spec.management.enabled` defaulting to `false`.

Rollback is limited to removing the new fields and `mesh shell` command before any callers depend on them.

## Open Questions

- None.
