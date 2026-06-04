## 1. Input Schema and Defaulting

- [x] 1.1 Accept `metadata.tags` (optional string→string map) in YAML input; persist and include in output
- [x] 1.2 Accept `spec.regions` as a recognized top-level spec key (pass-through for now)
- [x] 1.3 Accept `spec.placement`, `spec.configBundleRef`, and `spec.extensions` as recognized top-level spec keys
- [x] 1.4 Apply `spec.placement.affinity` defaults (`type: "preferred"`, `scope: "node"`) when `spec.placement` is absent or affinity fields are absent
- [x] 1.5 Apply discovery default for `spec.regions.local.discovery` when `spec.regions` is present and `discovery` is absent

## 2. Validation — Placement and Config Bundle

- [x] 2.1 Validate `spec.placement` is an object when present; return `invalid` error on `spec.placement`
- [x] 2.2 Validate `spec.placement.affinity` is an object when present; return `invalid` error on `spec.placement.affinity`
- [x] 2.3 Validate `spec.placement.affinity.type` is one of `"preferred"`, `"required"`; return `invalid` error
- [x] 2.4 Validate `spec.placement.affinity.scope` is one of `"node"`, `"zone"`; return `invalid` error
- [x] 2.5 Validate `spec.configBundleRef` on create: must be a string when present (reject `null`); return `invalid` error

## 3. Validation — Multi-Region Topology

- [x] 3.1 Validate that `spec.regions.local` is present when `spec.regions` exists; return `required` error
- [x] 3.2 Validate `spec.regions.local.name` is non-empty; return `required` error
- [x] 3.3 Validate `spec.regions.local.expose.type` is required and one of `"Internal"`, `"DirectPort"`, `"Balancer"`, `"Gateway"`; return `required` or `invalid` errors
- [x] 3.4 Validate `spec.regions.local.maxRelayNodes` when present: must be integer > 0 (reject `null` and 0); return `invalid` error
- [x] 3.5 Validate `spec.regions.local.encryption` is an object when present; return `invalid` error
- [x] 3.6 Validate `spec.regions.local.encryption.protocol` is one of `"TLSv1.2"`, `"TLSv1.3"` when present; return `invalid` error
- [x] 3.7 Validate `transportKeyStore` is required when expose type is `"Gateway"` and encryption is present; return `required` error
- [x] 3.8 Validate each key store sub-field (`secretRef`, `alias`, `filename`) is present and non-empty; return `required` errors with full dot-path field names
- [x] 3.9 Validate `spec.regions.local.discovery` is an object when present; return `invalid` error
- [x] 3.10 Validate `spec.regions.local.discovery.type` is `"relay"`; return `invalid` error
- [x] 3.11 Validate `heartbeat.interval` < `heartbeat.timeout`; return `invalid` error on `spec.regions.local.discovery.heartbeat`
- [x] 3.12 Validate remotes: `name` and `url` required per entry; duplicate `name` produces `duplicate` error on the later entry index
- [x] 3.13 Reject `spec.migration.strategy = "LiveMigration"` when `spec.regions` is present; return `invalid` with the specified message

## 4. Validation — Extensions

- [x] 4.1 Validate each extension entry: exactly one of `url` or `artifact` must be set; return `invalid` error with `field = "spec.extensions[<index>]"` and the required message

## 5. Warnings

- [x] 5.1 Emit a non-fatal warning when `spec.regions.local.encryption` is present but `trustStore` is absent; include warning in the success response

## 6. Output Construction

- [x] 6.1 Always include `spec.placement` (with defaults applied) in create and describe output
- [x] 6.2 Always include `status.telemetryProbe` in create and describe output; compute from `metadata.tags`
- [x] 6.3 Include region conditions (`DiscoveryRelayReady`, `RegionViewFormed`) in `status.conditions` when `spec.regions` is present; ensure full conditions array remains sorted alphabetically
- [x] 6.4 Omit `spec.regions.local.maxRelayNodes` from output when unset; omit `spec.regions.local.encryption` from output when absent; preserve remotes declaration order; omit optional remote fields when unset
- [x] 6.5 Omit `integrity` from extension entries when unset; preserve extensions declaration order

## 7. Config Bundle Refresh

- [x] 7.1 Implement update-time `configBundleRef` merge: omit = keep, `null` = clear, string = replace
- [x] 7.2 On update, detect when `configBundleRef` changed; attach `status.configRefresh` to the update response with `currentRef`, `previousRef`, `pending: true`
- [x] 7.3 Ensure `status.configRefresh` is never persisted to `store.json` and is absent from describe responses

## 8. Migration Strategy Validator Update

- [x] 8.1 Update migration strategy validator to accept `"LiveMigration"` as a valid value when `spec.regions` is absent (currently all non-`FullStop` values are rejected)

## 9. Tests

- [x] 9.1 Add test: single-region mesh — no region conditions, placement and telemetryProbe defaults present
- [x] 9.2 Add test: multi-region mesh create — valid input with local region, remotes, encryption; verify output and region conditions
- [x] 9.3 Add test: missing `spec.regions.local` produces required error
- [x] 9.4 Add test: invalid expose type produces invalid error
- [x] 9.5 Add test: Gateway expose type without transportKeyStore produces required error
- [x] 9.6 Add test: heartbeat interval >= timeout produces invalid error
- [x] 9.7 Add test: duplicate remote name produces duplicate error on later index
- [x] 9.8 Add test: LiveMigration rejected when regions present; accepted when regions absent
- [x] 9.9 Add test: `metadata.tags` persisted; `status.telemetryProbe` computed correctly for enabled/disabled/with-labels cases
- [x] 9.10 Add test: `spec.placement` defaults applied and always present in output; invalid type/scope rejected
- [x] 9.11 Add test: `spec.configBundleRef` create validation; update merge semantics; `status.configRefresh` on change; absent from describe
- [x] 9.12 Add test: `spec.extensions` url/artifact mutual exclusion; integrity optional; order preserved
- [x] 9.13 Add test: encryption without trustStore emits warning in success response
