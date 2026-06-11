## 1. Contract Coverage

- [x] 1.1 Add mesh create/describe tests for always-present `spec.placement` and `status.telemetryProbe`.
- [x] 1.2 Add metadata tag persistence and telemetry label parsing tests, including disabled telemetry.
- [x] 1.3 Add multi-region create tests for local region defaults, remote ordering, region conditions, and stable status.
- [x] 1.4 Add validation tests for region local fields, encryption stores, discovery heartbeat, duplicate remotes, placement affinity, and extensions.
- [x] 1.5 Add config bundle update tests for omitted, added, changed, cleared, and describe-after-refresh behavior.
- [x] 1.6 Add migration restriction tests for `LiveMigration` with `spec.regions` on create and update.

## 2. Resource Normalization

- [x] 2.1 Extend mesh create normalization to persist `metadata.tags`, default `spec.placement`, and accept `spec.configBundleRef`, `spec.extensions`, and `spec.regions`.
- [x] 2.2 Normalize `spec.regions.local` with required expose fields, optional `maxRelayNodes`, encryption protocol defaults, discovery defaults, and ordered remotes.
- [x] 2.3 Extend update patch handling so omitted `spec.configBundleRef` preserves the stored value and explicit null clears it.
- [x] 2.4 Ensure stored resource upgrades backfill `spec.placement` and status projection for older meshes.

## 3. Validation and Warnings

- [x] 3.1 Implement placement validation for object shape, affinity type, and affinity scope.
- [x] 3.2 Implement region topology validation for required local region fields, expose type, max relay nodes, and remote uniqueness.
- [x] 3.3 Implement inter-region encryption validation for object shape, supported protocols, required Gateway transport key store, required key store sub-fields, and missing trust store warnings.
- [x] 3.4 Implement region discovery validation for object shape, relay-only type, and heartbeat interval less than timeout.
- [x] 3.5 Implement extension validation for exactly one of `url` or `artifact` per entry.
- [x] 3.6 Enforce `LiveMigration` rejection whenever the merged or created mesh has `spec.regions`.

## 4. Status and Output Projection

- [x] 4.1 Add `DiscoveryRelayReady` and `RegionViewFormed` conditions for multi-region meshes and keep condition sorting/uniqueness intact.
- [x] 4.2 Update the stability predicate so region conditions do not affect `status.stable`.
- [x] 4.3 Derive `status.telemetryProbe` from `metadata.tags` for create, update, describe, and list-dependent public resource reads.
- [x] 4.4 Add transient `status.configRefresh` to update responses when `spec.configBundleRef` changes and omit it from later describe output.
- [x] 4.5 Preserve output omission rules for unset optional fields in encryption, remotes, extensions, and config bundle references.

## 5. Verification

- [x] 5.1 Run the focused mesh CLI test suite and fix regressions.
- [x] 5.2 Run the full test suite.
- [x] 5.3 Run OpenSpec validation for `add-multi-region-topology-policies`.
