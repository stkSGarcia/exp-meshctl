## 1. Contract Tests

- [x] 1.1 Add `tests/test_meshctl_cli.py` coverage for default `spec.placement`, default `status.telemetryProbe`, persisted `metadata.tags`, and describe output. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 Add `tests/test_meshctl_cli.py` coverage for valid `spec.regions.local`, ordered remotes, region conditions, and single-region meshes without region conditions. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.3 Add `tests/test_meshctl_cli.py` coverage for region validation errors, including missing local region, missing local name, missing expose type, invalid expose type, invalid relay node limits, invalid discovery, duplicate remotes, and LiveMigration rejection. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.4 Add `tests/test_meshctl_cli.py` coverage for inter-region encryption key stores, Gateway transport key store requirements, invalid protocols, missing key store fields, and the missing `trustStore` warning. [extends mesh-resource-management/add-access-security-model]
- [x] 1.5 Add `tests/test_meshctl_cli.py` coverage for telemetry label tag parsing, placement affinity validation, config bundle reference update refresh behavior, and extension source validation. [extends vault-resource-management/add-vault-resource-management]

## 2. Mesh Data Normalization

- [x] 2.1 Update `meshctl.py` `normalize_mesh_for_create` to preserve `metadata.tags` and normalize `spec.placement`, `spec.regions`, `spec.configBundleRef`, and `spec.extensions`.
- [x] 2.2 Add `meshctl.py` helper constants and functions for allowed local expose types, encryption protocols, placement values, telemetry tag keys, and extension source validation.
- [x] 2.3 Update `meshctl.py` `upgrade_stored_resource` to add default placement and derived telemetry probe output for existing stored meshes without adding region conditions to single-region meshes.
- [x] 2.4 Update `meshctl.py` update patch/config bundle handling so omitted `spec.configBundleRef` retains the stored value and explicit `null` clears it.

## 3. Validation And Warnings

- [x] 3.1 Update `meshctl.py` `validate_merged_resource` to validate `metadata.tags`, placement, regions, config bundle refs, and extensions with the required `field` and `type` values.
- [x] 3.2 Add region validation helpers in `meshctl.py` for local region shape, exposure type, relay node limits, encryption objects, key store sub-fields, discovery heartbeat timing, and remote duplicate names.
- [x] 3.3 Extend `meshctl.py` warning collection so existing local region encryption without `trustStore` emits a non-fatal warning in the same JSON warning format as runtime warnings.
- [x] 3.4 Ensure `meshctl.py` rejects `spec.migration.strategy = "LiveMigration"` with `spec.regions` on both create and update using the specified error message.

## 4. Status And Public Output

- [x] 4.1 Update `meshctl.py` status finalization or public rendering to derive `status.telemetryProbe` from `metadata.tags` on create, update, and describe.
- [x] 4.2 Update `meshctl.py` region status handling to add `DiscoveryRelayReady` and `RegionViewFormed` conditions only when `spec.regions` is present and keep `status.stable` based only on the existing stability condition set.
- [x] 4.3 Update `meshctl.py` update response handling so changed, added, or cleared `spec.configBundleRef` returns transient `status.configRefresh` and later describe output omits it.
- [x] 4.4 Verify optional fields are omitted from public output for unset remote fields, omitted encryption, unset extension integrity, and absent config refresh.

## 5. Verification

- [x] 5.1 Run `uv run pytest tests/test_meshctl_cli.py` and fix failures.
- [x] 5.2 Run `openspec status --change add-multi-region-topology-policies` and confirm all proposal artifacts remain complete.
