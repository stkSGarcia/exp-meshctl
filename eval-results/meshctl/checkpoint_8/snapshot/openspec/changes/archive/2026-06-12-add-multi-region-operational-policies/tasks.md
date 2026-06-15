## 1. Mesh Normalization and Output Defaults

- [x] 1.1 In `meshctl.py`, extend `normalize_mesh_for_create`, `update_patch`, and `upgrade_stored_resource` to preserve `metadata.tags`, `spec.regions`, `spec.placement`, `spec.configBundleRef`, and `spec.extensions`. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 In `meshctl.py`, add placement normalization helpers so successful create and describe output always include `spec.placement.affinity.type` and `spec.placement.affinity.scope` defaults. [extends mesh-resource-management/add-access-security-model]
- [x] 1.3 In `meshctl.py`, add telemetry projection in `public_resource` so `status.telemetryProbe` is always derived from `metadata.tags` and never needs separate persisted state. [extends mesh-resource-management/add-access-security-model]
- [x] 1.4 In `tests/test_meshctl_cli.py`, update default-output tests to assert always-present placement and telemetry probe fields.

## 2. Region Topology and Validation

- [x] 2.1 In `meshctl.py`, add constants and helpers for region expose types, encryption protocols, key store fields, discovery defaults, and heartbeat validation. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.2 In `meshctl.py`, extend `validate_merged_resource` to enforce `spec.regions.local`, local name, expose type, `maxRelayNodes`, encryption object/protocol/key store, discovery object/type/heartbeat, remote duplicate-name, and `LiveMigration` restriction errors. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.3 In `meshctl.py`, add region defaulting so `spec.regions.local.discovery` defaults to relay heartbeat values when regions are present and omitted.
- [x] 2.4 In `meshctl.py`, update status reconciliation and `public_resource` so multi-region meshes include sorted `DiscoveryRelayReady` and `RegionViewFormed` conditions without changing `status.stable` inputs. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.5 In `meshctl.py`, extend `runtime_warnings` to emit a non-fatal JSON warning when region encryption exists without `trustStore`.
- [x] 2.6 In `tests/test_meshctl_cli.py`, add create and update tests for region defaults, remote preservation, sorted conditions, `status.stable`, migration restriction, validation field/type mappings, and missing-trust-store warning.

## 3. Telemetry, Config Bundle, and Extensions

- [x] 3.1 In `meshctl.py`, implement telemetry tag parsing for `mesh.io/telemetry`, `mesh.io/targetLabels`, `mesh.io/probeTargetLabels`, and `mesh.io/instanceLabels`, preserving comma-separated list order.
- [x] 3.2 In `meshctl.py`, validate create-time `spec.configBundleRef`, preserve the stored value when update omits the field, clear it on explicit `null`, and add transient `status.configRefresh` only to the update response that changes it.
- [x] 3.3 In `meshctl.py`, validate ordered `spec.extensions` entries so each entry sets exactly one of `url` or `artifact`, preserve declaration order, and omit unset `integrity`.
- [x] 3.4 In `tests/test_meshctl_cli.py`, add tests for telemetry enabled/disabled/labels, config bundle add/change/clear/describe behavior, and extension source validation.

## 4. Verification

- [x] 4.1 Run `python -m unittest tests/test_meshctl_cli.py` and fix any regressions.
- [x] 4.2 Run `openspec status --change "add-multi-region-operational-policies"` and confirm all required proposal artifacts are complete.
