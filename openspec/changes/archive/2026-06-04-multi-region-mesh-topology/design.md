## Context

The mesh management tool (`meshctl.py`) handles CRUD for mesh resources stored in a flat JSON file. The current implementation supports a fixed set of `spec` fields covering resources, authentication, encryption, exposure, migration, and lifecycle. Operational deployments now require multi-region topology support, tag-driven telemetry observability, workload placement policies, config bundle refresh tracking, and plugin-style runtime extensions.

All changes live in `meshctl.py` and `store.json`. The tool is a single-file Python script with no external runtime dependencies beyond PyYAML.

## Related Work

**`spec:mesh-management`**: Core CRUD and validation pipeline — informs the extension points for new field validation because the existing pipeline already separates validation, defaulting, and output construction into distinct phases. _(see `spec:mesh-management`)_

**`spec:mesh-exposure`**: Exposure type validation (`Gateway`, `DirectPort`, `Balancer`) — informs the local-region expose type validation because the same allowlist pattern applies, with `Internal` added. _(see `spec:mesh-exposure`)_

**`spec:mesh-connection-details`**: Always-present status field pattern — informs the `status.telemetryProbe` design because it establishes that status fields can be computed from spec fields and included unconditionally in create/describe output.

## Goals / Non-Goals

**Goals:**
- Add `spec.regions` with full validation, defaulting (discovery), and status conditions
- Add `status.telemetryProbe` computed from `metadata.tags`, always present
- Add `spec.placement` with defaults, always present in output
- Add `spec.configBundleRef` with update-time `status.configRefresh` tracking
- Add `spec.extensions` with mutual-exclusion validation
- Emit warning when encryption exists but `trustStore` is absent
- Reject `LiveMigration` when `spec.regions` is present

**Non-Goals:**
- Actual multi-region coordination or relay infrastructure
- Dynamic telemetry scraping or probe lifecycle management
- Scheduling or executing config bundle refreshes
- Extension loading or execution

## Decisions

### D1: Field ordering in output

New spec-level fields (`placement`, `configBundleRef`, `extensions`, `regions`) are appended to the existing output construction block in a predictable order. `status.telemetryProbe` is appended to the status block. This avoids restructuring existing output while keeping the output deterministic.

**Alternative considered:** Dynamic field ordering based on input presence — rejected because it makes test assertions fragile.

### D2: placement always-present

`spec.placement` is always included in output (with defaults applied) even when omitted from input, following the same pattern as `spec.resources`. This matches the spec requirement and avoids conditional output logic for a commonly needed field.

### D3: telemetryProbe always-present

`status.telemetryProbe` is always included in output. When telemetry is disabled via `mesh.io/telemetry: "false"`, it outputs `{"enabled": false}`. This avoids callers having to handle the absent case and aligns with the checkpoint requirement.

### D4: configRefresh transient

`status.configRefresh` is attached to the update response in-memory and is never persisted to `store.json`. Describe reads from the store, so `configRefresh` is naturally absent from describe responses without special-casing.

### D5: Discovery defaulting location

Discovery defaulting for `spec.regions.local.discovery` happens in the same defaulting phase as other field defaults (before validation), so heartbeat interval/timeout validation runs against the fully defaulted object.

### D6: Error accumulation

All new validations follow the existing pattern: collect errors into a list and return the full list at the end of the validation phase. Errors from multi-region validation, encryption validation, placement validation, and extension validation are all accumulated together.

## Risks / Trade-offs

- [Risk: store.json schema drift] Existing stored meshes have no `placement`, `telemetryProbe`, or `regions` fields. When describe is called on older records, the defaulting/output logic must produce correct defaults for absent fields. → Mitigation: apply the same defaulting path on both create and describe output paths.

- [Risk: warning output format] The spec requires a warning for missing `trustStore`. The existing error format is `{"errors": [...]}`. Warnings need to be emitted as a separate key `{"warnings": [...]}` alongside the success output. → Mitigation: follow the existing pattern established for warning output (if any) or add a `warnings` key to the response object.

- [Risk: LiveMigration behavior change] The checkpoint says `"LiveMigration"` is now an accepted strategy value (not rejected outright), but only rejected when regions are present. The existing spec rejects all non-`FullStop` values. → Mitigation: update the migration strategy validator to allow `"LiveMigration"` as a recognized value and add the regions-conditional rejection.

## Migration Plan

1. Update the YAML input schema handler to accept new fields.
2. Add defaulting logic for `placement` and regional discovery.
3. Add validation for all new fields (regions, placement, configBundleRef on create, extensions).
4. Update output construction to always include `placement` and `telemetryProbe`.
5. Add `configRefresh` to update response when applicable.
6. Add region conditions to `status.conditions` when `spec.regions` is present.
7. Update migration strategy validator to allow `LiveMigration` but reject it with regions.
8. Run existing test suite; add test cases per spec scenarios.

No rollback concerns — `store.json` changes are additive only.

## Open Questions

- Should `status.telemetryProbe` appear in the `list` summary output or only in create/describe? (Checkpoint says "create and describe" — list is excluded for now.)
- Are there existing tests that hard-assert that `LiveMigration` is always rejected? Those need updating.
