## Why

Mesh resources need to model multi-region deployments and the operational metadata that comes with them. Adding explicit topology, telemetry, placement, config refresh, and extension contracts makes create, describe, and update behavior predictable for automation.

## What Changes

- Add `metadata.tags` persistence for string tag maps.
- Add `spec.regions` for single-region defaults, required local region configuration, optional remotes, relay discovery defaults, and inter-region encryption validation.
- Add multi-region status conditions while keeping `status.stable` tied to existing lifecycle and migration conditions.
- Extend migration validation so `LiveMigration` is rejected whenever multi-region topology is configured on create or update.
- Add telemetry probe output derived from metadata tags and include it in every mesh output.
- Add placement affinity defaults and validation under `spec.placement`.
- Add `spec.configBundleRef` persistence and transient config refresh status on updates that change it.
- Add ordered extension declarations with exactly-one source validation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mesh-resource-management`: Extend the mesh resource contract with multi-region topology, tags, telemetry probe output, placement defaults, config bundle refresh tracking, extension declarations, and related validation/warning behavior.

## Impact

- Affected CLI behavior: `mesh create`, `mesh describe`, and `mesh update` JSON output and validation.
- Affected resource model: `metadata.tags`, `spec.regions`, `spec.placement`, `spec.configBundleRef`, `spec.extensions`, `status.telemetryProbe`, region conditions, and transient `status.configRefresh`.
- Affected tests: mesh create/update/describe coverage for defaulting, persistence, validation errors, warning output, condition ordering, and transient status projection.
