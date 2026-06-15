## Context

`meshctl.py` stores mesh resources as JSON-compatible dictionaries and handles create, update, describe, validation, defaulting, status reconciliation, public projection, and warning output in one module. The new capability extends the mesh resource contract with more schema surface and status output, but it can reuse the existing CLI command flow and persisted store model.

## Related Work

> **`mesh-resource-management/add-access-security-model`**: Access security defaults and output are applied during normalization and public projection — informs the placement and telemetry defaulting approach because the new fields must be present in successful create and describe output even when omitted from input. _(see `mesh-resource-management/add-access-security-model`)_

> **`vault-resource-management/add-vault-resource-management`**: Dependent resources validate against existing meshes — informs keeping the mesh resource stable and fully normalized because later resources should not need to compensate for missing topology or policy fields. _(see `vault-resource-management/add-vault-resource-management`)_

> **`mesh-resource-management/add-meshctl-mesh-crud`**: Mesh CRUD establishes validation errors, persisted resource shape, and documented defaults — informs adding these fields through the existing normalization and validation pipeline instead of a separate parser. _(see `mesh-resource-management/add-meshctl-mesh-crud`)_

## Goals / Non-Goals

**Goals:**
- Normalize and persist `metadata.tags`, `spec.regions`, `spec.placement`, `spec.configBundleRef`, and `spec.extensions` consistently for create and update.
- Keep public create and describe output complete for always-present fields: `spec.placement` and `status.telemetryProbe`.
- Validate all checkpoint-defined required, invalid, duplicate, and warning cases using the existing JSON error and warning format.
- Add transient `status.configRefresh` only to the update response where `spec.configBundleRef` changed.
- Keep `status.stable` semantics unchanged except for sorted condition output.

**Non-Goals:**
- No actual network discovery, relay provisioning, telemetry collection, or extension download execution.
- No new persistence backend or external dependency.
- No changes to vault, task, snapshot, or recovery command semantics beyond relying on the updated mesh shape.

## Decisions

1. Extend mesh normalization helpers in `meshctl.py`.

   Add small focused helpers for tags, placement, regions, telemetry probe, config bundle reference, and extensions, called from `normalize_mesh_for_create`, `update_patch`, `validate_merged_resource`, and `public_resource`. This follows the current resource-dictionary approach and avoids introducing a parallel data model.

   Alternative considered: introduce dataclasses for the new mesh fields. Rejected for this change because the rest of the CLI works with dictionaries, and converting only these fields would add translation code without improving the checkpoint behavior.

2. Treat region defaults as stored canonical state, and telemetry probe as public status projection.

   Store defaulted `spec.regions.local.discovery` when `spec.regions` is present so update and describe behavior is deterministic. Compute `status.telemetryProbe` from `metadata.tags` in public output so tag changes automatically reflect in create, update, and describe responses.

   Alternative considered: store telemetryProbe under status. Rejected because it is wholly derived from tags and could become stale after metadata updates.

3. Keep `configRefresh` response-only.

   During `mesh_update`, compare the stored and candidate `spec.configBundleRef` values before saving. The persisted resource keeps only the new `spec.configBundleRef`; the printed update response receives a copied resource with transient `status.configRefresh`. Describe output never includes that field unless it exists from older data and is stripped during public projection.

   Alternative considered: persist pending refresh status until another operation clears it. Rejected because the checkpoint requires the field only in the update response that changed the reference.

4. Add multi-region conditions through existing status reconciliation.

   When `spec.regions` is present, ensure `DiscoveryRelayReady` and `RegionViewFormed` exist with status `"False"` and empty messages. Sort all conditions by `type` in the public resource and keep `status.stable` based only on the existing five condition types.

   Alternative considered: include region conditions in stable computation. Rejected because the checkpoint explicitly excludes them from `status.stable`.

5. Use existing warning output for missing trust stores.

   Extend `runtime_warnings` to append a non-fatal warning when `spec.regions.local.encryption` exists without `trustStore`. This keeps create and update output behavior aligned with existing warning handling.

   Alternative considered: make missing `trustStore` a validation error for Gateway exposure. Rejected because the checkpoint makes it a warning for every encryption section and only requires `transportKeyStore` for Gateway.

## Risks / Trade-offs

- Broad schema surface in one file -> mitigate with focused helper functions and table-driven tests for each validation field/type.
- Update merge semantics can accidentally preserve fields that should clear -> mitigate by explicitly handling `spec.configBundleRef: null` and by covering omit/change/clear cases in tests.
- Derived telemetry output may diverge from stored status if later code reads internal status directly -> mitigate by keeping telemetryProbe generation inside `public_resource`, the existing output boundary.
- Condition sorting may change output order expected by existing tests -> mitigate by updating tests to assert sorted order and stable status behavior rather than previous insertion order.

## Migration Plan

Existing stored meshes are upgraded lazily through `upgrade_stored_resource`. Add defaults for `spec.placement` at public-output time and ensure older resources without tags, regions, config bundle references, or extensions remain valid. Rollback is limited to reverting the code and tests because no irreversible store migration is introduced.

## Open Questions

None.
