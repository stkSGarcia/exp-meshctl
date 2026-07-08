## Why

Mesh definitions need to describe regional topology and operational policy in the same resource shape used by create, update, and describe workflows. The current mesh behavior lacks explicit defaults for placement and telemetry, does not track config bundle refreshes, and has no contract for multi-region validation, discovery, remote regions, or extension artifacts.

## What Changes

- Add optional `metadata.tags` persistence and derive `status.telemetryProbe` from telemetry-related tags.
- Add `spec.regions` for single-region and multi-region topology, including local region exposure, inter-region encryption, relay discovery, remote region declarations, and region-specific initial conditions.
- Reject `LiveMigration` when regional topology is configured on create and update.
- Add defaulted `spec.placement.affinity` output for every mesh.
- Add `spec.configBundleRef` create/update semantics and transient `status.configRefresh` reporting when the bundle reference changes.
- Add ordered `spec.extensions` declarations with exactly-one source validation.
- Preserve JSON error and warning formats for required, invalid, duplicate, and non-fatal warning cases.

## Capabilities

### New Capabilities
- `multi-region-topology-policies`: Defines regional topology, metadata-driven telemetry, placement defaults, config bundle refresh tracking, and mesh extension declarations.

### Modified Capabilities
- `mesh-resource-management/add-meshctl-mesh-crud`: Create, update, and describe responses now include defaulted placement and telemetry output and validate new mesh fields.
- `mesh-resource-management/add-access-security-model`: Inter-region encryption is explicitly separate from `spec.access` while reusing the same JSON validation style for credential-bearing security settings.
- `mesh-connectivity/add-network-exposure-connectivity`: Region-local exposure accepts the supported exposure modes and adds Gateway-specific encryption validation.

## Related Work

### Related Changes
- No related intent nodes were returned by the shallow KG search.

### Related Specs
- `mesh-resource-management/add-meshctl-mesh-crud`: Implements the mesh CLI command surface for create, list, describe, and delete. This change extends the mesh resource contract that create, update, and describe operate on.
- `mesh-resource-management/add-access-security-model`: Implements authentication and credential reference behavior under `spec.access`. This change complements it by keeping inter-region encryption separate while following its structured validation approach.
- `mesh-connectivity/add-network-exposure-connectivity`: Implements optional mesh exposure and connectivity behavior. This change adapts the exposure vocabulary for `spec.regions.local.expose.type` and adds Gateway-specific key store requirements.

## Impact

- Mesh create, update, and describe JSON output includes new defaulted fields and persisted optional sections.
- Mesh validation expands to cover regional topology, inter-region encryption, relay discovery, remotes, placement, config bundle references, and extensions.
- Status output gains `telemetryProbe`, conditional region readiness conditions, and transient `configRefresh` data on config bundle changes.
- Existing tests around mesh lifecycle, access, and exposure should be extended with create/update/describe coverage for the new fields and validation cases.
