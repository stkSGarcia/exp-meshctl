## Why

Mesh resources need a richer operations contract for multi-region deployments, placement defaults, telemetry labeling, config bundle refreshes, and extension sources. Defining these behaviors together keeps create, update, describe, validation, and warning output predictable for operators.

## What Changes

- Add optional `metadata.tags` persistence and derive `status.telemetryProbe` from documented telemetry tags on every returned mesh.
- Add always-present `spec.placement` output with defaulted affinity settings and validation for placement objects, affinity type, and affinity scope.
- Add optional `spec.regions` support for local region topology, remotes, relay discovery defaults, inter-region encryption, and multi-region status conditions.
- Reject `LiveMigration` whenever multi-region topology is configured on create or update.
- Add optional `spec.configBundleRef` persistence and transient `status.configRefresh` output when updates add, change, or clear the reference.
- Add optional ordered `spec.extensions` entries with exactly-one source validation for `url` versus `artifact`.
- Emit non-fatal warnings for region encryption that omits `trustStore`, using the established warning output contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mesh-resource-management`: Define multi-region topology, telemetry probe output, placement defaults, config bundle refresh tracking, extension validation, and associated errors/warnings.

## Impact

- `meshctl.py` mesh create, update, describe, validation, defaulting, persistence, status rendering, and warning paths.
- Mesh resource tests covering tags, telemetry labels, placement defaults/validation, regions, remotes, discovery, encryption stores, config refresh transitions, extensions, migration restrictions, and error/warning output.
- No new runtime dependencies are expected.
