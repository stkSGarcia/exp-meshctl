## 1. Metadata Tags and Placement

- [x] 1.1 Accept `metadata.tags` as an optional string-to-string map and persist all tags on create
- [x] 1.2 Inject `spec.placement` defaults (`affinity.type: "preferred"`, `affinity.scope: "node"`) when omitted, include in all create/describe output
- [x] 1.3 Validate `spec.placement` and `spec.placement.affinity` are objects when present; validate `type` and `scope` enum values

## 2. Telemetry Probe

- [x] 2.1 Add `build_telemetry_probe(tags)` helper that derives `status.telemetryProbe` from `metadata.tags`
- [x] 2.2 Inject `status.telemetryProbe` into every create and describe output (always present)
- [x] 2.3 Handle `mesh.io/telemetry: "false"` disabling case; default to enabled when tag absent
- [x] 2.4 Parse comma-separated label tags (`targetLabels`, `probeTargetLabels`, `instanceLabels`) and include only present categories

## 3. Config Bundle Reference

- [x] 3.1 Accept `spec.configBundleRef` as an optional string on create; validate it is a string when present
- [x] 3.2 In `cmd_update`: distinguish key-absent (keep stored) vs key-present-null (clear stored) vs key-present-string (update stored)
- [x] 3.3 Emit `status.configRefresh` in the update response when `configBundleRef` changes (any of: set, changed, cleared); omit from store

## 4. Extensions

- [x] 4.1 Accept `spec.extensions` as an optional ordered array on create and update
- [x] 4.2 Validate each entry: exactly one of `url` or `artifact` must be set; emit `spec.extensions[<index>]` / `invalid` error otherwise
- [x] 4.3 Omit `integrity` from output when not present; preserve declaration order

## 5. Multi-Region Topology — Core

- [x] 5.1 Accept `spec.regions` as optional; when present, require `spec.regions.local`
- [x] 5.2 Validate `spec.regions.local.name` (required, non-empty) and `spec.regions.local.expose.type` (required, enum)
- [x] 5.3 Validate `spec.regions.local.maxRelayNodes`: must be positive integer when present; omit from output when absent
- [x] 5.4 Inject default discovery block (`type: "relay"`, heartbeat) when `spec.regions` is present and no discovery provided

## 6. Multi-Region Topology — Encryption

- [x] 6.1 Accept `spec.regions.local.encryption` as optional object; reject non-object
- [x] 6.2 Default `protocol` to `"TLSv1.3"`; validate enum values
- [x] 6.3 Require `transportKeyStore` when expose type is `"Gateway"`
- [x] 6.4 Validate required sub-fields (`secretRef`, `alias`, `filename`) for each key store present
- [x] 6.5 Emit warning when `trustStore` is absent and encryption section exists

## 7. Multi-Region Topology — Discovery and Remotes

- [x] 7.1 Validate `spec.regions.local.discovery` is an object when present; reject non-`"relay"` type
- [x] 7.2 Validate heartbeat: `interval` must be strictly less than `timeout`
- [x] 7.3 Accept `spec.regions.remotes` array; validate required fields (`name`, `url`); omit optional fields when absent
- [x] 7.4 Detect duplicate remote names and emit `spec.regions.remotes[<index>].name` / `duplicate` error on the later entry

## 8. Region Conditions and Migration Guard

- [x] 8.1 Add `DiscoveryRelayReady` and `RegionViewFormed` conditions (both `"False"`, empty message) when `spec.regions` is present; re-sort full conditions array alphabetically
- [x] 8.2 Reject `spec.migration.strategy = "LiveMigration"` when `spec.regions` is present on both create and update paths
