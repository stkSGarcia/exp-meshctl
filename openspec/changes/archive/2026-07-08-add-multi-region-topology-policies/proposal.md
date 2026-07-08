## Why

Meshes need first-class topology and operational policy fields so create, update, and describe flows can represent regional deployment intent, telemetry tagging, placement defaults, refresh tracking, and extension sources consistently. Adding these fields now keeps the mesh resource contract explicit as multi-region operation and policy-driven automation become part of the supported surface.

## What Changes

- Add persisted `metadata.tags` support for arbitrary string key/value tags.
- Add always-present `spec.placement` defaults and always-present `status.telemetryProbe` output.
- Add `spec.regions` for single-region and multi-region topology, including local region exposure, optional remote regions, relay discovery defaults, inter-region encryption settings, and initial region conditions.
- Add validation and warning behavior for region topology, encryption, discovery heartbeat settings, duplicate remotes, placement affinity, config bundle references, and extension entries.
- Reject `spec.migration.strategy = "LiveMigration"` when region topology is configured.
- Add metadata-tag-driven telemetry probe output with ordered label categories.
- Add create/update behavior for `spec.configBundleRef`, including transient `status.configRefresh` reporting when the reference changes.
- Add ordered `spec.extensions` entries that accept exactly one source, either `url` or `artifact`.

## Related Work

### Related Changes

- No related intent nodes were returned by the shallow KG search.

### Related Specs

- `mesh-resource-management/add-meshctl-mesh-crud`: Defines the core `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` resource surface. This change extends that resource contract with additional persisted fields, defaulted status output, validation, and update behavior.
- `vault-resource-management/add-vault-resource-management`: Establishes the broader resource-management style for create/list/describe/update/delete flows and JSON error handling. This change follows the same resource validation and output preservation style for mesh topology policy fields.
- `mesh-resource-management/add-access-security-model`: Defines mesh security configuration under `spec.access`. This change complements it by adding separate inter-region encryption settings under `spec.regions.local.encryption` rather than overloading access authentication.

## Capabilities

### New Capabilities

- `mesh-topology-policies`: Covers mesh topology, metadata tags, telemetry probe output, placement defaults, config bundle refresh tracking, and extension source validation.

### Modified Capabilities

- None.

## Impact

- Affects mesh create, update, and describe behavior exposed through `meshctl.py`.
- Affects mesh resource persistence and JSON output shape for `metadata`, `spec`, and `status`.
- Adds validation errors and one non-fatal warning case using existing JSON error and warning formats.
- Does not introduce new external dependencies.
