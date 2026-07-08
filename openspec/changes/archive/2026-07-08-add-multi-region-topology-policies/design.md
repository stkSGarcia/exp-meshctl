## Context

Mesh resources are normalized, validated, persisted, and rendered from `meshctl.py`. The current flow already separates create normalization (`normalize_mesh_for_create`), update patching (`update_patch` and `deep_merge`), stored-resource upgrades (`upgrade_stored_resource`), validation (`validate_merged_resource`), status finalization (`initialize_status`, `reconcile_update_status`, `finalize_status`), and public output (`public_resource` and `print_resource`).

This change adds several mesh policy surfaces at once: metadata tags, region topology, telemetry status, placement defaults, config bundle refresh tracking, and extensions. The implementation should keep those concerns factored into helpers so the single-file CLI stays readable.

## Related Work

**`mesh-resource-management/add-meshctl-mesh-crud`**: Defines the core mesh create/list/describe/delete resource surface — informs the decision to implement this as mesh resource normalization, validation, update, and describe output behavior because the new fields extend the same mesh lifecycle contract.

**`vault-resource-management/add-vault-resource-management`**: Establishes resource field defaults, create/update validation, parent-aware status, and JSON error style — informs the decision to preserve declaration order, omit unset optional fields, and validate update input atomically because the new topology and extension fields follow that resource-management pattern.

**`mesh-resource-management/add-access-security-model`**: Defines defaulted mesh security output under `spec.access` — informs the decision to keep inter-region encryption under `spec.regions.local.encryption` and to render defaults through output canonicalization because topology encryption is separate from access authentication.

## Goals / Non-Goals

**Goals:**

- Persist `metadata.tags` and expose all required `spec` and `status` fields in create, update, and describe output.
- Normalize new mesh fields through create and legacy-upgrade paths so old stored resources remain describable.
- Validate all required and invalid cases with existing JSON error formatting and sorted output.
- Add region conditions without changing the definition of `status.stable`.
- Track `status.configRefresh` only in the update response that changes `spec.configBundleRef`.
- Cover the behavior in `tests/test_meshctl_cli.py` with create, update, describe, warning, and validation scenarios.

**Non-Goals:**

- Implement real cross-region networking, credential lookup, or config bundle fetching.
- Change the storage format outside the existing JSON store.
- Add new commands or external dependencies.

## Decisions

1. Add focused normalization helpers for new fields.

   `normalize_mesh_for_create` should delegate to helpers such as `normalize_metadata_tags`, `normalize_placement`, `normalize_regions`, `normalize_config_bundle_ref`, and `normalize_extensions`. This follows the existing access, migration, network, exposure, and management helper pattern and keeps create-time defaults explicit. _(see `vault-resource-management/add-vault-resource-management`)_

   Alternative considered: validate raw dictionaries only in `validate_merged_resource`. That would leave create output defaults and omitted optional fields inconsistent with existing resource behavior.

2. Upgrade stored meshes to the new public shape.

   `upgrade_stored_resource` should add default `spec.placement`, preserve existing `metadata.tags` only when it is a valid map, and initialize `status.telemetryProbe` through a helper rather than persisting stale derived status. Region defaults should be applied only when `spec.regions` exists so single-region meshes do not gain region conditions. _(see `mesh-resource-management/add-meshctl-mesh-crud`)_

   Alternative considered: only add defaults during create. That would make describe output for older stored meshes violate the always-present placement and telemetry probe requirements.

3. Treat telemetry and config refresh as derived output concerns.

   `status.telemetryProbe` should be recomputed from `metadata.tags` in `finalize_status` or `public_resource`, and `status.configRefresh` should be attached to the update response when the stored and candidate `spec.configBundleRef` values differ. The transient refresh field should be removed before persistence or stripped from later public describe output.

   Alternative considered: persist both fields permanently. That would make telemetry vulnerable to stale tag-derived state and would violate the requirement that config refresh appears only in the update response.

4. Keep region encryption separate from access encryption.

   Add `validate_regions_object` and related helpers for `spec.regions.local.encryption`, key stores, discovery, remotes, and duplicate remote names. Do not reuse `spec.access.encryption` validation because the valid fields, defaults, and warning behavior differ. _(see `mesh-resource-management/add-access-security-model`)_

   Alternative considered: route region encryption through access encryption helpers. That would couple unrelated schemas and make Gateway transport key store validation hard to express clearly.

5. Reuse existing status condition mechanics.

   Region conditions should be added through `set_condition`, sorted by `sort_conditions`, and excluded from `calculate_stable`. The existing `calculate_stable` function already limits stability to health, prechecks, graceful shutdown, scaling, and migration conditions.

   Alternative considered: calculate stability from all false conditions. That would regress meshes that are operationally stable while region discovery is still forming.

## Risks / Trade-offs

- [Risk] Many new validation branches in one file can make `meshctl.py` harder to navigate -> Mitigation: group constants and helpers by domain and keep tests aligned to domain sections.
- [Risk] Update merging can accidentally retain a cleared `configBundleRef` -> Mitigation: handle explicit `null` in a config bundle update helper before or immediately after `deep_merge`.
- [Risk] Derived `status.telemetryProbe` and transient `status.configRefresh` can be persisted incorrectly -> Mitigation: centralize public status shaping and assert persistence behavior in tests.
- [Risk] The simple YAML fallback parser has limited list support -> Mitigation: write tests through the normal PyYAML-backed environment and keep any fallback-sensitive structures represented as mappings where existing parser behavior allows.

## Migration Plan

1. Add helper functions and constants in `meshctl.py`.
2. Update create normalization and stored-resource upgrade paths.
3. Update validation and status finalization/public output.
4. Add tests for default output, region validation, telemetry tags, config bundle update behavior, and extensions.
5. Run the existing test suite.

Rollback is a code-only rollback: remove the new helpers/tests and revert the normalization, validation, and status shaping hooks.

## Open Questions

- None.
