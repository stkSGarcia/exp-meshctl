## Context

`meshctl.py` is a single-file Python CLI. Mesh state lives in `store.json`. The mesh lifecycle is handled by three main functions: `validate_and_build` (create-time validation and resource construction), a parallel update path in `cmd_update`, and `format_resource_for_output`. Status conditions are managed by `set_condition` / `compute_stable`.

This change adds several independent feature areas to the mesh resource—regions, placement, telemetry, config bundles, and extensions—all routed through the existing create/update/describe pipeline.

## Goals / Non-Goals

**Goals:**
- Implement all new fields and validation rules from checkpoint 8 inside the existing `validate_and_build` and `cmd_update` logic.
- Emit always-present `status.telemetryProbe` and `spec.placement` (with defaults) on every create and describe.
- Emit `DiscoveryRelayReady` and `RegionViewFormed` conditions when `spec.regions` is present.
- Emit transient `status.configRefresh` on update when `configBundleRef` changes.

**Non-Goals:**
- Actual network connectivity between regions (runtime concern only).
- Persistent condition state transitions (conditions start at `"False"`).
- Changes to vault, task, snapshot, or recovery resource types.

## Decisions

### Single function extension vs. new helpers
Add targeted helper functions for logically distinct validation areas (regions, placement, telemetry, extensions) rather than growing `validate_and_build` into an unreadable monolith. Each helper receives `spec`, `errors`, and `warnings` and mutates them in place. This keeps the top-level function as an orchestrator.

### Always-present fields
`spec.placement` and `status.telemetryProbe` are injected after validation, not treated as optional output. This matches the checkpoint contract ("present even when omitted from input") and avoids conditional output logic at the describe layer.

### configRefresh as update-only transient
`status.configRefresh` is computed in `cmd_update` by comparing the stored `configBundleRef` with the incoming value, then attached to the response object before printing. It is not persisted to the store, so subsequent `describe` calls omit it naturally. This is the same pattern used for other transient status fields.

### Condition sort
After appending `DiscoveryRelayReady` and `RegionViewFormed`, re-sort the full `status.conditions` list alphabetically by `type`. This satisfies the sort contract without restructuring existing condition logic.

### LiveMigration guard
The check `spec.migration.strategy == "LiveMigration" and spec.regions is present` is added in both the create path (`validate_and_build`) and the update path (`cmd_update`), since both paths can set migration strategy.

## Risks / Trade-offs

- **Large single-file growth**: `meshctl.py` is already 2 271 lines. Adding ~200–300 lines increases that further. → Mitigation: keep new helpers focused and co-located with related logic.
- **Heartbeat defaults on update**: When `spec.regions` is omitted on update, the stored regions value is preserved; we must not re-inject discovery defaults. → Mitigation: only inject discovery defaults during create, or when the incoming doc explicitly provides `spec.regions` without a discovery block.
- **configBundleRef null semantics**: `null` means "clear the stored value"; omitting the key means "keep stored value". This is an unusual update semantic and must be handled explicitly in the merge logic, distinguishing between key-absent and key-present-with-null.
