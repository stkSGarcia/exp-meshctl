## Context

`meshctl.py` currently keeps the mesh resource model in a single CLI module with helpers for create normalization, update merge behavior, validation, status reconciliation, warnings, and public output projection. The existing spec already covers lifecycle conditions, migration strategy validation, warning shape, and JSON output conventions; this change extends the same mesh resource contract rather than introducing a new subsystem.

The checkpoint adds several resource-model concerns that interact with one another: region topology affects status conditions and migration restrictions, telemetry output derives from metadata tags, placement is always defaulted, config bundle updates create transient status, and extension entries require ordered validation.

## Goals / Non-Goals

**Goals:**

- Normalize and persist the new mesh fields while preserving existing create, describe, update, and list command behavior.
- Keep defaulting and public projection deterministic for always-present `spec.placement` and `status.telemetryProbe`.
- Validate multi-region topology, region encryption/discovery, placement affinity, config bundle references, and extension entries using the existing JSON error/warning conventions.
- Preserve update atomicity and existing merge semantics, including special handling for clearing `spec.configBundleRef`.
- Add tests that cover successful output, validation failures, warnings, transient config refresh status, and describe-after-transient behavior.

**Non-Goals:**

- Add real networking, certificate, telemetry scraping, or remote-region connectivity behavior.
- Change storage format outside the local JSON store used by the CLI.
- Change the command surface or add new commands.
- Make `mesh list` include the new topology or telemetry fields.

## Decisions

1. Keep the fields in the existing mesh normalization, validation, and projection pipeline.

   Rationale: the resource is already canonicalized in `normalize_mesh_for_create`, `validate_merged_resource`, `reconcile_update_status`, `finalize_mesh_status`, and `public_resource`. Extending those helpers avoids a second model layer and keeps create/update/describe behavior consistent.

   Alternative considered: introduce a region-specific model class. That would be larger than the current single-file CLI style and would not match neighboring access, network, exposure, and migration helpers.

2. Treat `metadata.tags`, `spec.regions`, `spec.placement`, `spec.configBundleRef`, and `spec.extensions` as canonical stored fields.

   Rationale: callers expect describe output to reflect create/update input after validation. Defaults should be stored where they are stable, especially `spec.placement`, while transient output such as `status.configRefresh` should be removed after the update response.

   Alternative considered: compute all new fields only during public projection. That would make update comparisons and transient config refresh detection harder to reason about.

3. Model region conditions as normal condition entries but exclude them from the stability predicate.

   Rationale: existing condition sorting and uniqueness rules should apply to `DiscoveryRelayReady` and `RegionViewFormed`. Their initial `"False"` state reflects topology readiness without making an otherwise healthy mesh unstable.

   Alternative considered: store region readiness outside `status.conditions`. That would duplicate condition machinery and make output less uniform.

4. Derive telemetry probe output from `metadata.tags` during finalization/projection.

   Rationale: telemetry is a read-model status value with simple tag-derived behavior. Keeping it generated ensures `status.telemetryProbe` is always present and remains synchronized with tag updates.

   Alternative considered: persist user-supplied telemetry status. That would allow stale or contradictory status and is not requested by the contract.

5. Detect config bundle refresh in the update flow before storing the final resource.

   Rationale: `status.configRefresh` is only visible on the update response that changes, adds, or clears `spec.configBundleRef`; it must not remain in stored describe output.

   Alternative considered: persist the transient and clear it on describe. That would create unnecessary store churn and leak a one-response status into later reads if describe is never called.

## Risks / Trade-offs

- New validation paths may interact with existing update merge behavior -> Mitigate with create and update tests for both omitted and explicit fields.
- Config bundle clearing uses `null`, while omitted update fields preserve values -> Mitigate by handling `spec.configBundleRef` explicitly in `update_patch` and testing omit, change, add, and clear cases.
- Region topology has many nested validation errors -> Mitigate with focused helper functions and tests for field paths and error types.
- Telemetry labels parse comma-separated strings without extra schema metadata -> Mitigate by preserving order, trimming only where implementation needs predictable labels, and documenting output behavior through tests.
