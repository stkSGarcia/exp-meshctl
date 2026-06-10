## 1. Metadata, Placement, And Output Defaults

- [x] 1.1 Persist optional `metadata.tags` on create and update while preserving all provided string key/value entries.
- [x] 1.2 Add telemetry tag parsing for `mesh.io/telemetry`, `mesh.io/targetLabels`, `mesh.io/probeTargetLabels`, and `mesh.io/instanceLabels`.
- [x] 1.3 Include `status.telemetryProbe` in every returned mesh, with disabled telemetry suppressing all labels.
- [x] 1.4 Add `spec.placement.affinity` defaults for omitted placement input and ensure create, update, and describe output include the defaulted placement.
- [x] 1.5 Validate `spec.placement`, `spec.placement.affinity`, affinity `type`, and affinity `scope` with the required invalid errors.

## 2. Multi-Region Topology

- [x] 2.1 Add `spec.regions` normalization for local region fields, discovery defaults, optional remotes, and optional encryption.
- [x] 2.2 Validate required local region fields, allowed expose types, and positive non-null `maxRelayNodes`.
- [x] 2.3 Validate region encryption object shape, protocol values, Gateway transport key store requirements, and key store sub-fields.
- [x] 2.4 Generate a successful-operation warning when region encryption exists without `trustStore`, while suppressing warnings on errors.
- [x] 2.5 Validate region discovery object shape, relay-only type, heartbeat defaults, and interval-less-than-timeout rule.
- [x] 2.6 Preserve remote region declaration order, optional fields, empty arrays, and reject duplicate remote names on the later index.

## 3. Status, Migration, And Config Refresh

- [x] 3.1 Add `DiscoveryRelayReady` and `RegionViewFormed` conditions for multi-region meshes and omit them for single-region meshes.
- [x] 3.2 Keep the full conditions array sorted by `type` and ensure region conditions do not affect `status.stable`.
- [x] 3.3 Reject `LiveMigration` with `spec.regions` on create and update using the required `spec.migration.strategy` invalid message.
- [x] 3.4 Persist valid create-time `spec.configBundleRef` strings and reject invalid create-time values.
- [x] 3.5 Implement update handling that distinguishes omitted `spec.configBundleRef`, changed string values, first assignment, and explicit null clearing.
- [x] 3.6 Emit transient `status.configRefresh` only in the update response that adds, changes, or clears `spec.configBundleRef`.

## 4. Extensions And Projection

- [x] 4.1 Add ordered `spec.extensions` persistence for entries sourced by either `url` or `artifact`.
- [x] 4.2 Preserve optional extension `integrity` only when set and omit it when unset.
- [x] 4.3 Reject extension entries that set both `url` and `artifact`, or neither, with the required indexed invalid error.
- [x] 4.4 Ensure public projection preserves declaration order for telemetry label lists, remote regions, and extensions.
- [x] 4.5 Ensure create, update, migrate, and describe output consistently include placement and telemetry probe additions without leaking stale `status.configRefresh`.

## 5. Tests And Verification

- [x] 5.1 Add CLI tests for metadata tag persistence and telemetry probe enabled, disabled, label, and default output.
- [x] 5.2 Add CLI tests for placement default output and placement validation errors.
- [x] 5.3 Add CLI tests for local region required fields, expose validation, max relay validation, discovery defaults, and discovery validation.
- [x] 5.4 Add CLI tests for region encryption defaults, key store validation, Gateway transport store requirements, and missing trust store warnings.
- [x] 5.5 Add CLI tests for remotes, duplicate remote names, region conditions, stable status, and LiveMigration region rejection on create and update.
- [x] 5.6 Add CLI tests for config bundle reference create validation, update add/change/clear behavior, omitted-update preservation, and describe omission of prior refresh status.
- [x] 5.7 Add CLI tests for extension ordering, optional integrity, URL/artifact source preservation, and exactly-one source validation.
- [x] 5.8 Run the full test suite and `openspec validate add-multi-region-operational-policies`.
