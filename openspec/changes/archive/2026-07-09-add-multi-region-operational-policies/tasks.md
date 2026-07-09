## 1. Mesh Data Shape

- [x] 1.1 Update `meshctl.py` metadata normalization/validation to persist `metadata.tags` as a string map and reject invalid tag shapes. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 Add `spec.placement.affinity` normalization in `meshctl.py` with default `type: preferred` and `scope: node`, including create/describe output defaults. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.3 Add `spec.extensions` normalization in `meshctl.py` that preserves declaration order, omits unset `integrity`, and accepts exactly one of `url` or `artifact`. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.4 Add `spec.configBundleRef` create/update handling in `meshctl.py`, including omit-to-preserve and explicit-null-to-clear behavior. [extends vault-resource-management/add-vault-resource-management]

## 2. Region Topology

- [x] 2.1 Add `spec.regions.local` normalization and validation in `meshctl.py` for required local name, required expose type, valid expose values, and optional positive `maxRelayNodes`. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.2 Add local region encryption handling in `meshctl.py` for `TLSv1.2`/`TLSv1.3`, key-store required fields, Gateway `transportKeyStore`, omitted-output behavior, and missing-`trustStore` warnings. [extends mesh-resource-management/add-access-security-model]
- [x] 2.3 Add regional discovery defaults and validation in `meshctl.py` for relay discovery, heartbeat interval/timeout defaults, object shape, relay-only type, and interval less than timeout. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.4 Add `spec.regions.remotes` handling in `meshctl.py` for ordered output, optional fields, empty arrays, and duplicate-name errors on the later entry index. [extends mesh-resource-management/add-meshctl-mesh-crud]

## 3. Status And Policy

- [x] 3.1 Update status reconciliation in `meshctl.py` to add sorted `DiscoveryRelayReady` and `RegionViewFormed` conditions only when `spec.regions` is present, without changing `recompute_status_stable()`. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 3.2 Update `public_resource()` or adjacent output helpers in `meshctl.py` to always derive `status.telemetryProbe` from `metadata.tags`, including enabled default, disabled output, and ordered label categories. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 3.3 Extend existing `validate_live_migration_topology()` in `meshctl.py` so create and update reject `LiveMigration` with the new `spec.regions` object shape and exact configured diagnostic. [extends mesh-migration-strategies/add-mesh-migration-strategies]
- [x] 3.4 Add transient `status.configRefresh` computation in `meshctl.py` for update responses that add, change, or clear `spec.configBundleRef`, and ensure later describe output omits it. [extends vault-resource-management/add-vault-resource-management]

## 4. CLI Tests

- [x] 4.1 Update `tests/test_meshctl_cli.py` minimal/default tests to assert always-present `spec.placement` and `status.telemetryProbe`.
- [x] 4.2 Add `tests/test_meshctl_cli.py` coverage for metadata tags, telemetry enabled/disabled behavior, and telemetry label parsing order.
- [x] 4.3 Add `tests/test_meshctl_cli.py` coverage for local region defaults, required fields, invalid expose type, invalid `maxRelayNodes`, discovery defaults, and heartbeat validation.
- [x] 4.4 Add `tests/test_meshctl_cli.py` coverage for regional encryption success, Gateway missing `transportKeyStore`, missing key-store sub-fields, invalid protocol, non-object encryption, and missing-`trustStore` warnings.
- [x] 4.5 Add `tests/test_meshctl_cli.py` coverage for remotes order, duplicate remote names, region readiness condition sorting, and stable status independence.
- [x] 4.6 Update the existing LiveMigration-with-regions assertion in `tests/test_meshctl_cli.py` to use the new `spec.regions.local` shape, and add update-path coverage.
- [x] 4.7 Add `tests/test_meshctl_cli.py` coverage for placement validation, config bundle create/update/clear/describe behavior, and extension order/invalid-shape diagnostics.

## 5. Verification

- [x] 5.1 Run `uv run pytest` and fix any failures.
- [x] 5.2 Run `openspec status --change "add-multi-region-operational-policies"` and confirm all planning artifacts are complete before applying.
