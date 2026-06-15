## Why

Mesh create, describe, and update output needs to capture multi-region topology and operational policy state without requiring callers to infer defaults or transient status from omitted fields. This change extends the mesh contract so region topology, telemetry tags, placement defaults, config bundle refresh tracking, and extensions are validated and represented consistently.

## Related Work

### Related Changes

- `add-vault-resource-management`: introduced a second persisted resource type and parent-resource validation. This change complements that work by keeping mesh validation precise enough for dependent resources to rely on stable mesh topology and operational fields.
- `add-meshctl-mesh-crud`: established mesh create, list, describe, delete behavior, validation, defaulting, persistence, and JSON output. This change extends that contract with additional mesh schema fields and output defaults.
- `add-mesh-lifecycle-topology`: expanded mesh behavior into update semantics, topology validation, and lifecycle-aware status. This change builds on that topology and status model with multi-region conditions, migration restrictions, and config refresh tracking.

### Related Specs

- `mesh-resource-management/add-access-security-model`: covers access security defaults and successful create/describe output. This change reuses the same defaulting style for `spec.placement`, `status.telemetryProbe`, and optional region encryption fields while keeping inter-region encryption separate from `spec.access`.
- `vault-resource-management/add-vault-resource-management`: covers validation against existing mesh resources. This change strengthens the mesh resource shape that vault and future dependent resources can reference.
- `mesh-resource-management/add-meshctl-mesh-crud`: covers mesh command surface, field validation, and documented defaults. This change adapts those validation and defaulting patterns for regions, remotes, telemetry, placement, config bundle references, and extensions.

## What Changes

- Add optional `metadata.tags` persistence for string key/value tags.
- Add `spec.regions` for single-region default behavior, required local region configuration when present, optional remotes, discovery defaults, inter-region encryption validation, and region status conditions.
- Reject `LiveMigration` on create and update whenever `spec.regions` is present.
- Always include defaulted `spec.placement` and `status.telemetryProbe` in successful mesh create and describe output.
- Derive telemetry enablement and label lists from `metadata.tags`.
- Add `spec.configBundleRef` create validation and update-time transient `status.configRefresh` when the reference changes.
- Add ordered `spec.extensions` entries with exactly one source per entry.
- Emit documented JSON errors and non-fatal warnings, including missing `trustStore` warnings for region encryption.

## Capabilities

### New Capabilities

- `multi-region-operational-policies`: Mesh schema, validation, defaulting, output, warnings, and update behavior for region topology, telemetry tags, placement defaults, config bundle refresh tracking, and extensions.

### Modified Capabilities

- None.

## Impact

- Affects `meshctl.py` mesh create, describe, and update handling.
- Adds and updates tests under `tests/` for validation failures, warnings, defaulted output, persisted fields, update semantics, and condition ordering.
- No new runtime dependencies are expected.
