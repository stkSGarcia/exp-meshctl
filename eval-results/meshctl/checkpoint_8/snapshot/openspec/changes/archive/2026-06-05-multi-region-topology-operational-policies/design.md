## Context

The meshctl tool currently supports single-region mesh lifecycle (CRUD, update, scale, stop/resume), access control (`spec.access`), network exposure modes, and a management endpoint. This change adds the multi-region federation layer, telemetry observability, placement policies, config bundle refresh tracking, and plugin extensions.

The implementation is a single Python file (`meshctl.py`) backed by a JSON store. All new fields are processed during create and update handling. Validation errors are accumulated and returned sorted.

## Related Work

**`mesh-lifecycle-and-topology`**: Established the mesh update lifecycle and topology fields — informs the field-level merge approach used for `spec.configBundleRef` update semantics (omit = keep, null = clear).

**`security-model`**: Established structured sub-section defaults in `spec.access` — informs the pattern used for `spec.placement` (always defaulted and present in output) and `spec.regions.local.encryption` (object validation before sub-field processing).

**`network-exposure-connectivity`**: Established expose type enumeration for `spec.exposure.type` — the local region expose type (`Internal`, `DirectPort`, `Balancer`, `Gateway`) reuses the same enumeration pattern _(see `network-exposure-connectivity`)_.

## Goals / Non-Goals

**Goals:**
- Add `spec.regions` with local region, encryption, discovery, and remotes — fully validated
- Add `spec.placement` always-present with defaults
- Add `spec.configBundleRef` with update-time refresh tracking
- Add `spec.extensions` array with url/artifact mutual exclusion
- Add `metadata.tags` passthrough and tag-driven `status.telemetryProbe`
- Add `DiscoveryRelayReady` and `RegionViewFormed` conditions when regions present
- Reject LiveMigration strategy when regions are present

**Non-Goals:**
- Actual relay/discovery network communication
- Dynamic condition status updates based on runtime state
- Tag key validation beyond what is needed for telemetry keys

## Decisions

### Decision: placement always present in output
`spec.placement` is always included in create/describe output (even if omitted from input) to give operators a stable contract. This follows the same pattern used for `spec.resources.memory` defaults.

### Decision: configRefresh only on the mutating response
`status.configRefresh` appears only in the update response that changes `configBundleRef`. Subsequent describe calls omit it. This avoids storing transient state permanently — the store holds only the current ref value.

_Alternative considered_: Store configRefresh in the resource and clear it on the next describe. Rejected because it introduces mutable transient state that complicates the store and makes describe non-idempotent.

### Decision: telemetryProbe always present
`status.telemetryProbe` is always present (like `spec.placement`) to give consumers a stable output shape. When telemetry is disabled, it carries only `{"enabled": false}` — callers always have a probe status to read.

### Decision: Encryption validation gated on encryption presence
The encryption sub-section is fully optional. When absent, no sub-field errors fire. When present, it must be an object and all sub-field rules apply. This avoids spurious errors for operators who don't configure inter-region encryption.

### Decision: trustStore warning is non-fatal
Missing `trustStore` inside an existing encryption section produces a warning (not an error) because the mesh is still operable without it, but operators should be informed of the security implication.

### Decision: Region conditions not factored into status.stable
`DiscoveryRelayReady` and `RegionViewFormed` reflect async cluster convergence, not synchronous validation outcomes. `status.stable` remains tied only to `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration` — consistent with prior lifecycle behavior.

## Risks / Trade-offs

[Single Python file growth] → Mitigation: Group new field validators into clearly named helper functions; the schema stays flat enough to keep it readable.

[Backwards compatibility for status output shape] → Mitigation: `status.telemetryProbe` and `spec.placement` are additive fields. Existing tests that assert exact output shapes must be updated, but no existing fields are removed or renamed.

[LiveMigration now valid without regions] → Mitigation: The mesh-management spec delta explicitly allows LiveMigration when regions are absent, fixing the prior blanket rejection. This is a spec-level correction reflected in both the spec delta and the implementation.

## Migration Plan

1. Update `meshctl.py` create handler: apply placement defaults, compute `telemetryProbe` from tags, validate and persist regions, extensions, configBundleRef.
2. Update `meshctl.py` update handler: implement configBundleRef merge semantics (omit=keep, null=clear), produce transient `configRefresh` when value changes.
3. Update describe handler: include `spec.placement` and `status.telemetryProbe` in all responses; omit `status.configRefresh`.
4. Update migration strategy validation: allow LiveMigration when regions absent; reject when regions present.
5. Update existing tests to include `spec.placement` and `status.telemetryProbe` in expected output shapes.
