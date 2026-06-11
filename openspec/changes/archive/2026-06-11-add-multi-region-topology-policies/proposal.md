## Why

Mesh resources currently model a single-region deployment shape and do not expose the operational metadata needed to coordinate relay discovery, telemetry probes, placement defaults, config bundle refreshes, or extension bundles. Multi-region mesh operation needs an explicit contract so create, update, describe, and migration behavior remain predictable as topology grows beyond one local deployment.

## What Changes

- Add optional `metadata.tags` and persist all tag key/value pairs.
- Always include `spec.placement` with affinity defaults and always include `status.telemetryProbe` in successful mesh output.
- Add `spec.regions` for local and remote region topology, including local exposure, relay limits, inter-region encryption, discovery defaults, remote declarations, and multi-region status conditions.
- Reject `LiveMigration` whenever multi-region topology is configured, on both create and update.
- Derive telemetry probe output from metadata tags, including label categories and explicit enable/disable behavior.
- Add optional `spec.configBundleRef` with create validation and update-time refresh status tracking.
- Add optional ordered `spec.extensions` entries with exactly-one source validation.
- Extend mesh validation, warning, status, and public output contracts for the new fields.

## Capabilities

### New Capabilities

### Modified Capabilities
- `mesh-resource-management`: Extend mesh metadata, spec, validation, status, and output requirements for multi-region topology and operational policy fields.

## Impact

- Affected code: `meshctl.py` mesh normalization, validation, update merge behavior, lifecycle/status projection, warning output, and public resource projection.
- Affected tests: `tests/test_meshctl_cli.py` coverage for create, update, describe, validation, warning, and output-shape scenarios.
- Affected API contract: JSON output for every mesh now includes defaulted placement and telemetry probe status; multi-region meshes include region conditions; config bundle changes can produce transient refresh status.
