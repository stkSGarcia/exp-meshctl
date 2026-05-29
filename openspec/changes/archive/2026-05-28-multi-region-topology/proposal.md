## Why

The mesh resource needs to support multi-region deployments, operational policies (placement, telemetry, config bundles, extensions), and metadata tagging so that operators can configure cross-region connectivity and observe mesh behavior from a single control plane.

## What Changes

- Add `spec.regions` for multi-region topology: local region identity, expose type, encryption, discovery, and remote peer configuration.
- Add `metadata.tags` as a string-to-string map for labeling and driving telemetry behavior.
- Add `status.telemetryProbe` (always present) driven by telemetry-related metadata tags.
- Add `spec.placement` (always present with defaults) controlling pod affinity type and scope.
- Add `spec.configBundleRef` for referencing a config bundle, with update semantics that emit a transient `status.configRefresh` on change.
- Add `spec.extensions` as an ordered list of extension entries (url or artifact, optional integrity).
- Reject `LiveMigration` strategy when `spec.regions` is present.
- Add `DiscoveryRelayReady` and `RegionViewFormed` status conditions when regions are configured.

## Capabilities

### New Capabilities

*(none — all changes extend the existing mesh management capability)*

### Modified Capabilities

- `mesh-management`: New fields on mesh create/update/describe: `spec.regions`, `metadata.tags`, `spec.placement`, `spec.configBundleRef`, `spec.extensions`, `status.telemetryProbe`, `status.configRefresh`, and new region-related status conditions with validation rules for all new fields.

## Impact

- `meshctl.py` mesh create, update, and describe operations all gain new fields and validation paths.
- `mesh-management` spec requires a delta spec covering the new field contracts.
- No new CLI subcommands; no changes to other resource types (vaults, tasks, snapshots, etc.).
