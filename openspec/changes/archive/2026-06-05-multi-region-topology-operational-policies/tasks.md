## 1. Metadata and Always-Present Fields

- [x] 1.1 Add `metadata.tags` passthrough: persist and include in output when set; omit when absent
- [x] 1.2 Add `spec.placement` defaulting: apply `{"affinity":{"type":"preferred","scope":"node"}}` when absent on create; include in all create/describe outputs
- [x] 1.3 Validate `spec.placement` and `spec.placement.affinity` are objects when present; validate `type` and `scope` enum values
- [x] 1.4 Add `status.telemetryProbe` computation from `metadata.tags`; always include in create/describe output
- [x] 1.5 Parse `mesh.io/telemetry`, `mesh.io/targetLabels`, `mesh.io/probeTargetLabels`, `mesh.io/instanceLabels` tags and map to `telemetryProbe` shape

## 2. Config Bundle Reference

- [x] 2.1 Add `spec.configBundleRef` on create: validate it is a string when present; persist value
- [x] 2.2 Implement update-time configBundleRef merge semantics: omit=keep, null=clear, new string=update
- [x] 2.3 Produce `status.configRefresh` in update response when configBundleRef changes (add, update, or clear); omit from describe

## 3. Extensions Array

- [x] 3.1 Add `spec.extensions` parsing: accept optional array; validate each entry has exactly one of `url` or `artifact`
- [x] 3.2 Emit `{"field":"spec.extensions[<index>]","type":"invalid","message":"exactly one of 'url' or 'artifact' must be set"}` for invalid entries
- [x] 3.3 Preserve declaration order and omit `integrity` when absent

## 4. Multi-Region Spec Block

- [x] 4.1 Add `spec.regions` detection: when absent, skip all region validation; when present, require `spec.regions.local`
- [x] 4.2 Validate `spec.regions.local.name` (required, non-empty) and `spec.regions.local.expose.type` (required, one of `Internal`, `DirectPort`, `Balancer`, `Gateway`)
- [x] 4.3 Validate `spec.regions.local.maxRelayNodes`: reject null and non-positive integers; omit from output when unset
- [x] 4.4 Validate and apply `spec.regions.local.encryption`: must be object when present; default `protocol` to `"TLSv1.3"`; validate protocol enum; require `transportKeyStore` when expose type is `"Gateway"`; emit warning when `trustStore` absent
- [x] 4.5 Validate key store sub-objects (`transportKeyStore`, `relayKeyStore`, `trustStore`): require `secretRef`, `alias`, `filename` when present
- [x] 4.6 Apply discovery default when `spec.regions` present and `spec.regions.local.discovery` absent; validate discovery is object, type is `"relay"`, and `heartbeat.interval < heartbeat.timeout`

## 5. Remote Regions

- [x] 5.1 Parse `spec.regions.remotes` optional array; validate `name` and `url` required per entry
- [x] 5.2 Detect duplicate remote `name` values and emit `duplicate` error for later entry
- [x] 5.3 Preserve declaration order; omit optional fields (`credentialRef`, `namespace`, `clusterRef`) when unset

## 6. Region Conditions and Migration Restriction

- [x] 6.1 When `spec.regions` is present, add `DiscoveryRelayReady` and `RegionViewFormed` conditions with `status: "False"` and empty `message` to `status.conditions`
- [x] 6.2 Ensure full conditions array is sorted alphabetically by `type` including new region conditions
- [x] 6.3 Confirm `status.stable` computation ignores `DiscoveryRelayReady` and `RegionViewFormed` conditions
- [x] 6.4 Update migration strategy validation: allow `"LiveMigration"` when `spec.regions` is absent; reject with `invalid` error when `spec.regions` is present on both create and update

## 7. Test Coverage

- [x] 7.1 Update all existing create/describe test assertions to include `spec.placement` and `status.telemetryProbe` in expected output
- [x] 7.2 Add tests for telemetry tag combinations (no tags, tag-disabled, partial label tags, all label tags)
- [x] 7.3 Add tests for placement validation errors (non-object, invalid type/scope)
- [x] 7.4 Add tests for `spec.configBundleRef` create, update (keep/change/clear), and describe (no configRefresh)
- [x] 7.5 Add tests for `spec.extensions` valid entries, both-set error, neither-set error, integrity omission
- [x] 7.6 Add tests for multi-region: missing local, local field validation, encryption validation, discovery validation, remotes, duplicate names
- [x] 7.7 Add tests for region conditions presence/absence and sort order
- [x] 7.8 Add tests for LiveMigration restriction with and without regions
