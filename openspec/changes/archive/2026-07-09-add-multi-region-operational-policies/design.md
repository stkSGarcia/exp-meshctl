## Context

`meshctl.py` currently owns mesh resource parsing, normalization, validation, status reconciliation, and public output in one module. Mesh create and update already share validation helpers, update merges nested fields through `update_patch()`, status conditions are sorted centrally, warnings use the existing `warnings` array on successful responses, and `tests/test_meshctl_cli.py` covers CLI behavior through subprocess calls.

This change adds several resource-shape concerns at once: optional metadata tags, regional topology, inter-region encryption, discovery defaults, remotes, placement, telemetry status, config bundle refresh tracking, and extension references. The design keeps those concerns in the existing mesh flow instead of adding a new persistence or command layer.

## Related Work

**`mesh-resource-management/add-meshctl-mesh-crud`**: Defines mesh create, list, describe, and delete behavior — informs keeping create/describe output canonical and defaulted because the new fields are part of the mesh resource contract.

**`vault-resource-management/add-vault-resource-management`**: Defines resource update behavior for a related resource type — informs config bundle update semantics because omitted fields must preserve stored state while explicit `null` has meaning.

**`mesh-resource-management/add-access-security-model`**: Defines structured access security validation and canonical output — informs the separate inter-region encryption design because region encryption uses key-store objects but must not be folded into `spec.access`.

**`mesh-migration-strategies/add-mesh-migration-strategies`**: Defines migration strategy validation and active migration behavior — informs the regional `LiveMigration` restriction because regional topology narrows an otherwise valid strategy.

## Goals / Non-Goals

**Goals:**

- Add the checkpoint 8 mesh schema without changing command names or storage format.
- Preserve create/update atomicity: invalid regional, placement, config, telemetry, or extension input must not mutate stored meshes.
- Keep all user-facing diagnostics in the existing JSON error and warning formats.
- Ensure create and describe output always contain `spec.placement` and `status.telemetryProbe`.
- Keep regional readiness conditions sorted with existing conditions while leaving `status.stable` based only on existing stability condition types.

**Non-Goals:**

- Do not add real cross-region networking, relay orchestration, telemetry scraping, or config-bundle execution.
- Do not change vault dependency behavior or one-shot resource behavior.
- Do not introduce new third-party dependencies or a new persistence backend.

## Decisions

### Normalize new mesh fields beside existing mesh normalizers

Add focused helpers near the existing `normalize_access()`, `normalize_migration()`, and `normalize_network()` helpers:

- `normalize_metadata_tags()` to preserve `metadata.tags` only when it is a string map.
- `normalize_placement()` to always write default `spec.placement.affinity`.
- `normalize_regions()` to copy valid regional topology, apply local discovery and encryption defaults, omit unset optional fields, and preserve remote order.
- `normalize_config_bundle_ref()` to copy create-time string values.
- `normalize_extensions()` to preserve extension order and omit unset `integrity`.

Rationale: the existing implementation already separates normalization from validation and public canonicalization; following that shape minimizes special cases. Alternative considered: defer all new field shaping to `public_resource()`. That would make stored state differ from create output and make update behavior harder to reason about.

### Validate complete candidate resources after update merge

Keep using `candidate = deep_merge(stored, update_patch(document))`, then run validation on the merged candidate. For `spec.configBundleRef`, update semantics need one exception: if the update document explicitly sets the field to `null`, preserve that `null` through the patch long enough to clear the stored value and compute refresh state.

Rationale: most new rules depend on the complete effective spec, especially `LiveMigration` plus `spec.regions`, Gateway exposure plus encryption, duplicate remote names, and placement shape. Alternative considered: validate only the user patch. That would miss invalid combinations formed by stored values plus updated values.

### Keep region encryption separate from access encryption

Implement region encryption under `spec.regions.local.encryption` with its own allowed protocols, key-store object validation, default protocol, Gateway `transportKeyStore` requirement, and missing `trustStore` warning. Do not reuse `canonical_access()` or access encryption source/client-mode rules.

Rationale: the checkpoint explicitly separates inter-region encryption from `spec.access`, and the field model is different. The access security spec still informs the structured validation and canonical output approach. _(see `mesh-resource-management/add-access-security-model`)_

### Derive operational status at output and lifecycle boundaries

Set region readiness conditions during create/update status reconciliation when `spec.regions` is present, and remove them when an update clears regional topology if clearing is supported by the merge semantics. Compute `status.telemetryProbe` from `metadata.tags` in `public_resource()` so describe output reflects tag changes and stale stored status cannot linger.

Rationale: conditions are persisted status, while telemetry probe is a derived projection from metadata tags. Alternative considered: persist `status.telemetryProbe`; that would require extra cleanup every time tags change and provides no durable state.

### Record config refresh as transient update response status

Compare stored and candidate `spec.configBundleRef` during update after validation. When the effective value changes, add `status.configRefresh` with `currentRef`, `pending: true`, and `previousRef` to the printed update response, but remove it before saving or before later describe output.

Rationale: the requirement says the field appears only in the update response that changed the reference. This mirrors a transient acknowledgement, not durable operational state. Alternative considered: save `status.configRefresh` and hide it in `public_resource()` after first read. That would make persistence order and describe behavior more fragile.

### Extend the existing LiveMigration topology guard

Update `validate_live_migration_topology()` to treat the new `spec.regions` object shape as multi-region when present, while keeping the exact error field, type, and message.

Rationale: the guard already exists in `meshctl.py`; reusing it keeps migration validation centralized. _(see `mesh-migration-strategies/add-mesh-migration-strategies`)_

## Risks / Trade-offs

[Risk] `deep_merge()` may not currently distinguish omitted fields from explicit `null` for `spec.configBundleRef`. → Mitigation: add narrow patch handling for this field and tests for omit, change, first set, and clear.

[Risk] Adding many validators in one module can make `meshctl.py` harder to scan. → Mitigation: group helpers by field family and keep each helper small, following the existing access/network patterns.

[Risk] Region conditions could accidentally make every regional mesh unstable. → Mitigation: leave `recompute_status_stable()` unchanged except for tests proving it ignores `DiscoveryRelayReady` and `RegionViewFormed`.

[Risk] Telemetry tag parsing could silently emit empty labels from comma-separated input. → Mitigation: preserve order but trim whitespace and drop empty segments only if implementation tests codify that choice; otherwise preserve raw non-empty segments.

## Migration Plan

No external data migration is required. Existing stored meshes should be upgraded lazily by `upgrade_stored_resource()` or public normalization so they gain defaulted placement and telemetry output without editing the store manually.

Implementation should land behind the existing CLI behavior with regression tests for old minimal meshes, existing access defaults, migration strategy validation, and update atomicity.

## Open Questions

- Should `metadata.tags` reject non-string maps explicitly, or should non-map/non-string values pass through untouched? The checkpoint says optional map of string keys to string values, so implementation should reject invalid shapes unless existing metadata behavior requires permissiveness.
- Should comma-separated telemetry labels trim surrounding whitespace? The checkpoint only requires preserving list order, so tests should document the chosen behavior.
