## Context

Mesh lifecycle behavior is implemented in `meshctl.py`, with create/update normalization, merged-resource validation, public output shaping, and status reconciliation already centralized there. Existing tests in `tests/test_meshctl_cli.py` cover defaults, access security, migration guards, status conditions, update merge semantics, and exposure behavior.

## Related Work

**`mesh-resource-management/add-meshctl-mesh-crud`**: Implements the mesh create, list, describe, delete, and update resource workflow — informs the decision to add regional policy handling inside the existing mesh normalization, validation, update, and public output paths because this change extends the resource contract surfaced by those commands.

**`mesh-resource-management/add-access-security-model`**: Implements authentication, credential references, encryption source validation, and defaulted access output — informs the decision to validate `spec.regions.local.encryption` with separate field paths but the same error/warning shape because the new encryption settings are operational security data, not `spec.access` data.

**`mesh-connectivity/add-network-exposure-connectivity`**: Implements optional exposure modes and connection-details status output — informs the decision to reuse exposure vocabulary for `spec.regions.local.expose.type` while keeping region-local exposure independent from top-level `spec.exposure`.

## Goals / Non-Goals

**Goals:**
- Persist `metadata.tags` and all new `spec` sections exactly enough for stable create/update/describe round trips.
- Include always-present `spec.placement` and `status.telemetryProbe` in public mesh output.
- Add regional topology validation, defaults, warnings, and status conditions without changing the existing stability model.
- Support config bundle reference update semantics, including a transient `status.configRefresh` only on changing update responses.
- Keep error ordering and JSON error/warning shapes consistent with the existing CLI.

**Non-Goals:**
- Implement real network connectivity, certificate loading, relay heartbeats, or remote cluster communication.
- Add new CLI commands or external dependencies.
- Change existing `spec.access`, top-level `spec.exposure`, migration stage progression, or runtime catalog behavior except where regional topology must reject live migration.

## Decisions

1. Add focused normalizers for each new mesh section.

   `normalize_mesh_for_create`, `upgrade_stored_resource`, and `public_resource` should call helpers for metadata tags, placement, telemetry, regions, config bundle references, and extensions. This follows the existing `normalize_access`, `normalize_exposure`, and `defaulted_*` pattern, keeping defaults deterministic and ensuring older stored resources are upgraded on describe. _(see `mesh-resource-management/add-meshctl-mesh-crud`)_

   Alternative considered: perform all defaulting only in `public_resource`. That would make persisted resources less canonical and would complicate update semantics for `configBundleRef`, so create/update should store canonical fields where persistence matters.

2. Keep regional encryption separate from access encryption.

   Add local region encryption helpers that validate `protocol`, key store objects, Gateway transport key store requirements, and trust-store warnings under `spec.regions.local.encryption`. These helpers should not call or mutate `spec.access.encryption`, but they should reuse the same `error(field, message, type)` and warning object conventions. _(see `mesh-resource-management/add-access-security-model`)_

   Alternative considered: reuse `defaulted_access` encryption internals. That would mix unrelated field paths and defaults, and it would make the checkpoint's "separate from `spec.access`" rule harder to preserve.

3. Treat region-local exposure as its own small validation model.

   `spec.regions.local.expose.type` should accept `"Internal"`, `"DirectPort"`, `"Balancer"`, and `"Gateway"` independently from top-level `spec.exposure`. Gateway is the only regional exposure mode with an encryption-dependent required field. _(see `mesh-connectivity/add-network-exposure-connectivity`)_

   Alternative considered: extend top-level `EXPOSURE_TYPES` directly. That would accidentally allow `"Internal"` in `spec.exposure` and would blur the distinction between connectivity output and regional topology declaration.

4. Reconcile status from canonical spec state.

   Add a region-status reconciler that inserts `DiscoveryRelayReady` and `RegionViewFormed` only when `spec.regions` is present, sorts all conditions, and leaves `update_status_stability` dependent only on the existing five condition types. Add telemetry-probe reconciliation to the public output path so describe output remains stable for old resources.

   Alternative considered: store region and telemetry status only during create/update. That risks stale output after older stored resources are described and duplicates logic across create/update paths.

5. Model `configRefresh` as update-response-only state.

   Detect `spec.configBundleRef` presence in the incoming update document before deep merge. Store the canonical `spec.configBundleRef` value, but add a private transition marker or response-only status field for the current update response, then ensure `public_resource` or describe completion removes it for later output.

   Alternative considered: persist `status.configRefresh` and clear it during the next describe. That would make describe mutate state for a status field whose contract is explicitly transient.

## Risks / Trade-offs

- [Risk] The many validation cases can produce inconsistent messages or field paths. -> Mitigation: centralize field-path construction in helpers and add table-driven tests for every required/invalid case from the checkpoint.
- [Risk] Adding defaulted output changes existing minimal mesh snapshots. -> Mitigation: update baseline tests intentionally and add explicit assertions for the new always-present fields.
- [Risk] Region conditions could accidentally mark a mesh unstable. -> Mitigation: keep `update_status_stability` condition membership unchanged and test regional meshes with initial `"False"` region conditions.
- [Risk] `configBundleRef: null` can be lost by ordinary deep merge semantics. -> Mitigation: detect the key in the incoming update patch before merge and handle null as an explicit clear operation.

## Migration Plan

No external data migration is required. `upgrade_stored_resource` should add new defaults for older resources when they are read, and public output should reconcile telemetry, placement, and region conditions consistently.

Rollback is code-only: remove the new helpers and tests. Stored resources may contain the new optional fields after rollback, but the existing loader already tolerates unknown fields in persisted JSON.

## Open Questions

- Should telemetry label parsing trim whitespace around comma-separated values, or preserve values exactly after splitting? The checkpoint requires order preservation but does not specify whitespace handling.
- What warning message should be used when regional encryption is present without `trustStore`? The checkpoint requires a non-fatal warning but does not define exact text.
