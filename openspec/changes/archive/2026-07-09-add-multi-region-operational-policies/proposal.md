## Why

Mesh resources need to model multi-region operation and related operational policy in the same contract used by create, update, and describe flows. The current mesh shape handles core lifecycle behavior, but checkpoint 8 expands the resource into regional topology, telemetry-derived status, placement defaults, config bundle refresh tracking, and extension references.

## What Changes

- Add optional `metadata.tags` persistence for arbitrary string tags and telemetry control tags.
- Add `spec.regions` for single-region default behavior and explicit multi-region topology, including required local region fields, local exposure policy, optional relay sizing, encryption, discovery defaults, remote region references, and region readiness conditions.
- Reject `LiveMigration` whenever regional topology is configured on create or update.
- Always include defaulted `spec.placement` output and validate placement affinity type and scope.
- Always include `status.telemetryProbe`, deriving enabled state and label categories from metadata tags.
- Add optional `spec.configBundleRef` with update-time refresh tracking when the reference changes, is first set, or is cleared.
- Add ordered `spec.extensions` entries that reference exactly one URL or artifact with optional integrity metadata.
- Preserve existing JSON error and warning formats, including non-fatal warnings for regional encryption without a trust store.

## Capabilities

### New Capabilities

- `multi-region-operational-policies`: Mesh topology, telemetry, placement, config refresh, and extension policy behavior for mesh create, update, and describe operations.

### Modified Capabilities

- None.

## Related Work

### Related Changes

- `add-mesh-lifecycle-topology`: Expanded the mesh resource from basic CRUD into topology validation and lifecycle-aware status. This change extends that direction by adding region topology, operational defaults, and status details that are derived from metadata and topology inputs.

### Related Specs

- `mesh-resource-management/add-meshctl-mesh-crud`: Defines the mesh command surface and JSON resource lifecycle. This change builds on it by adding fields that create, update, and describe must validate, persist, and render.
- `vault-resource-management/add-vault-resource-management`: Defines analogous create/list/describe/update/delete resource management patterns. This change reuses its update-oriented validation style for config bundle refresh behavior.
- `mesh-resource-management/add-access-security-model`: Defines mesh access security fields. This change keeps inter-region encryption separate from `spec.access` while using similar structured validation for referenced secret material.
- `mesh-migration-strategies/add-mesh-migration-strategies`: Defines migration strategy validation. This change complements it by adding the explicit `LiveMigration` restriction when regional topology is present.
- `mesh-resource-management/add-vault-resource-management`: Defines mesh deletion dependency conflicts for vault references. This change does not alter that behavior, but it must preserve existing mesh resource semantics while expanding the mesh schema.

## Impact

- Mesh create, update, and describe JSON contracts gain new persisted fields, defaulted output fields, transient update status, warnings, and validation failures.
- Existing mesh stability calculation remains limited to the current stability-related conditions; new region conditions are informational and start as not ready.
- Tests need to cover create-time defaults, update-time persistence and clearing, validation errors, warnings, ordered collections, and stable status independence.
