## Context

`meshctl.py` currently keeps mesh behavior in one local resource model: YAML input is normalized into a persisted JSON store, updates are deep-merged, validation emits structured JSON errors, and public output is projected with derived status fields. Existing mesh requirements already cover lifecycle conditions, exposure, migration, warnings, and defaulted topology fields. This change extends that same model with multi-region topology and operational policy fields without adding a new command surface.

The new fields are cross-cutting because they affect input validation, persisted spec shape, update merge semantics, warning generation, migration restrictions, status projection, and output shape. The most important implementation constraint is preserving existing behavior for single-region meshes while making `spec.placement` and `status.telemetryProbe` present for every successful mesh output.

## Goals / Non-Goals

**Goals:**
- Normalize and validate `metadata.tags`, `spec.regions`, `spec.placement`, `spec.configBundleRef`, and `spec.extensions`.
- Preserve ordered list inputs where the contract requires order: remote regions, telemetry label lists, and extensions.
- Add multi-region conditions only when `spec.regions` is configured, and keep those conditions independent from `status.stable`.
- Enforce the `LiveMigration` and multi-region incompatibility on both create and update.
- Emit config refresh status only for the update response that changes, adds, or clears `spec.configBundleRef`.
- Keep JSON error and warning output consistent with existing sorting and shape rules.

**Non-Goals:**
- No new CLI commands or resource kinds.
- No real network, discovery, telemetry, encryption, or extension execution behavior.
- No changes to vault, task, snapshot, or recovery behavior except as indirectly affected by mesh output shape.
- No external dependencies or persistent storage format migration beyond handling missing fields on read.

## Decisions

1. Treat the new inputs as mesh resource fields handled by existing normalization and projection helpers.

   Rationale: The CLI already centralizes mesh create, update, validation, and public output in `meshctl.py`. Extending that path keeps create, update, describe, list, migrate, and shell behavior consistent.

   Alternative considered: Introduce dedicated multi-region helpers with a separate resource model. That would add indirection without a new command boundary and would make update merging harder to reason about.

2. Store canonical spec values and compute transient status values during public projection.

   Rationale: `spec.placement`, defaulted regional discovery, and telemetry probe status should be visible in output, while `status.configRefresh` is explicitly transient and must not leak into later describe responses. Keeping transient status out of persisted state avoids cleanup paths.

   Alternative considered: Persist every derived status field. That would simplify describe reads but risks stale telemetry or config refresh status.

3. Validate nested topology with explicit field paths.

   Rationale: Existing tests and requirements rely on exact `field` and `type` values. Region encryption, discovery heartbeat, duplicate remotes, and extensions need predictable paths such as `spec.regions.remotes[1].name` and `spec.extensions[0]`.

   Alternative considered: Reuse generic object validation errors. That would be faster to implement but would not meet the checkpoint's required error contract.

4. Keep multi-region status conditions separate from stability calculation.

   Rationale: `DiscoveryRelayReady` and `RegionViewFormed` start as `"False"` operational readiness indicators, but the checkpoint explicitly says they do not affect `status.stable`. Stability remains tied to the existing lifecycle conditions.

   Alternative considered: Treat every false condition as unstable. That would conflict with the required multi-region initial status.

## Risks / Trade-offs

- [Risk] The always-present `status.telemetryProbe` and `spec.placement` fields change output snapshots for many existing tests. -> Mitigation: Update shared output expectations first and add focused regression tests for omitted input.
- [Risk] Deep-merge update semantics can make clearing `configBundleRef` ambiguous. -> Mitigation: Special-case `spec.configBundleRef` so omission preserves, `null` clears, and changed values create one transient refresh object.
- [Risk] Region validation adds many nested paths and could miss aggregate ordering rules. -> Mitigation: Add table-driven tests for required, invalid, duplicate, warning, and output preservation cases.
- [Risk] Warning generation for missing `trustStore` could accidentally appear on failed operations. -> Mitigation: Reuse the existing warning pipeline that suppresses warnings when errors exist.

## Migration Plan

No persisted data migration is required. Existing mesh records without the new fields remain valid and are projected with default `spec.placement` and `status.telemetryProbe` on the next successful create, update, describe, or migrate output. Rollback consists of reverting the implementation and tests for these fields; persisted unknown fields may remain in the JSON store but will not be exercised by older code.

## Open Questions

None.
