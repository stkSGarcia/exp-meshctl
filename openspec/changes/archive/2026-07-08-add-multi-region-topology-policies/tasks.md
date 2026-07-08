## 1. Test Coverage

- [x] 1.1 Add create/describe tests in `tests/test_meshctl_cli.py` for always-present `spec.placement` and `status.telemetryProbe`, starting from `test_defaults_and_absent_optional_fields`. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 Add metadata tag and telemetry label tests in `tests/test_meshctl_cli.py`, including enabled, disabled, ordered target/probe/instance label categories, and tag persistence.
- [x] 1.3 Add regional topology tests in `tests/test_meshctl_cli.py` for single-region omission, required `spec.regions.local`, local expose validation, positive `maxRelayNodes`, ordered remotes, and duplicate remote names. [extends mesh-connectivity/add-network-exposure-connectivity]
- [x] 1.4 Add regional encryption tests in `tests/test_meshctl_cli.py`, starting from `test_access_encryption_validation_and_output`, for protocol validation, Gateway `transportKeyStore`, key store sub-fields, omitted encryption output, and missing-trust-store warnings. [extends mesh-resource-management/add-access-security-model]
- [x] 1.5 Add status condition and migration restriction tests in `tests/test_meshctl_cli.py`, starting from `test_status_conditions_and_lifecycle_transitions` and migration guard tests, for region conditions, stable calculation, and create/update `LiveMigration` rejection.
- [x] 1.6 Add config bundle and extension tests in `tests/test_meshctl_cli.py` for create persistence, update preserve/change/clear behavior, transient `status.configRefresh`, ordered extensions, omitted `integrity`, and exactly-one source validation.

## 2. Mesh Data Normalization

- [x] 2.1 Update `meshctl.py` metadata handling in `normalize_mesh_for_create`, `update_patch`, and stored-resource upgrade paths to persist optional `metadata.tags` as string-to-string maps.
- [x] 2.2 Add placement helpers in `meshctl.py` to default `spec.placement.affinity.type` to `"preferred"` and `scope` to `"node"` during create, update, stored-resource upgrade, and public output. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.3 Add region normalization helpers in `meshctl.py` for `spec.regions.local`, local expose settings, optional `maxRelayNodes`, optional ordered `remotes`, relay discovery defaults, and omitted optional fields.
- [x] 2.4 Add extension normalization helpers in `meshctl.py` to preserve ordered `spec.extensions` entries and omit unset `integrity`.

## 3. Validation

- [x] 3.1 Extend `validate_merged_resource` in `meshctl.py` to call validation helpers for metadata tags, placement, regions, local discovery, remotes, config bundle reference, and extensions.
- [x] 3.2 Implement regional exposure validation in `meshctl.py` without expanding top-level `EXPOSURE_TYPES`, preserving separate field paths under `spec.regions.local.expose`. [extends mesh-connectivity/add-network-exposure-connectivity]
- [x] 3.3 Implement regional encryption validation in `meshctl.py` for section object type, protocol, key store object sub-fields, Gateway transport key store requirement, and missing trust-store warning. [extends mesh-resource-management/add-access-security-model]
- [x] 3.4 Enforce the `LiveMigration` with `spec.regions` restriction for both create and update in `meshctl.py`, not only runtime-version-change updates.
- [x] 3.5 Ensure all new validation errors use existing JSON error format, sorted output, and exact field/type/message values from the specs.

## 4. Status And Public Output

- [x] 4.1 Add telemetry probe reconciliation in `meshctl.py` so create and describe output always includes `status.telemetryProbe` derived from `metadata.tags`.
- [x] 4.2 Add region condition reconciliation in `meshctl.py` so regional meshes include `DiscoveryRelayReady` and `RegionViewFormed`, conditions remain sorted, and `status.stable` ignores those condition types.
- [x] 4.3 Preserve existing connectivity and management status behavior in `meshctl.py` while adding regional status output. [extends mesh-connectivity/add-network-exposure-connectivity]
- [x] 4.4 Add warning output for local region encryption without `trustStore` using the existing warning response shape.

## 5. Config Bundle Refresh

- [x] 5.1 Update `mesh_update` and update patch handling in `meshctl.py` to distinguish omitted `spec.configBundleRef` from explicit `null`.
- [x] 5.2 Emit `status.configRefresh` only in the update response that changes, adds, or clears `spec.configBundleRef`, with `currentRef`, `pending`, and `previousRef`.
- [x] 5.3 Ensure later `mesh describe` output omits `status.configRefresh` while preserving the stored `spec.configBundleRef` value.

## 6. Verification

- [x] 6.1 Run `uv run pytest tests/test_meshctl_cli.py` and fix regressions.
- [x] 6.2 Run `openspec status --change "add-multi-region-topology-policies"` and confirm all proposal artifacts remain complete.
