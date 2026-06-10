## Context

`meshctl.py` currently models mesh resources through a single JSON store with shared create, update, describe, migrate, validation, defaulting, status reconciliation, warning, and public projection paths. Earlier changes already introduced lifecycle status, exposure, management connectivity, access settings, storage topology, runtime catalog validation, migration strategies, and warnings.

This change extends the same resource model with multi-region topology and operational policy fields. Several of the new fields affect public output even when omitted from input, so the implementation needs a clear split between stored intent, effective defaults, transient update-only status, and warnings.

## Goals / Non-Goals

**Goals:**

- Persist optional `metadata.tags` and use telemetry tags to derive an always-present `status.telemetryProbe`.
- Add defaulted `spec.placement.affinity` output and validate placement object shape and values.
- Support optional `spec.regions` with local region validation, remote region preservation, relay discovery defaults, inter-region encryption store validation, and region-specific initial conditions.
- Keep `status.stable` tied only to existing health, precheck, graceful shutdown, scaling, and migration signals.
- Track `spec.configBundleRef` updates with transient `status.configRefresh` output when a reference is added, changed, or cleared.
- Support ordered `spec.extensions` entries with exactly-one source validation.
- Preserve existing JSON success, warning, and error conventions.

**Non-Goals:**

- Contact remote regions, verify URLs, provision discovery relays, or validate external secret contents.
- Perform real telemetry scraping or config bundle refresh execution.
- Add new top-level CLI commands or persistent background reconciliation.
- Change vault, snapshot, recovery, or one-shot operation behavior.

## Decisions

1. Treat all checkpoint fields as part of `mesh-resource-management`.

   Rationale: The new fields live under mesh `metadata`, `spec`, or `status` and affect the same create, update, describe, validation, and output projection paths as existing mesh behavior.

   Alternative considered: Split telemetry, regions, and extensions into separate capabilities. That would make the proposal noisier without creating separate command surfaces or storage lifecycles.

2. Apply output defaults during normalization/projection while persisting the canonical mesh resource.

   Rationale: `spec.placement` and `status.telemetryProbe` must appear in returned meshes even when omitted from input, while absent region encryption and one-shot `status.configRefresh` have more precise output rules. A shared public projection step can consistently include required defaults and omit fields that should not persist into later describe output.

   Alternative considered: Store every output default directly at create time. That is simple for placement, but it is a poor fit for transient config refresh state and makes future projection-only additions harder to keep consistent for older stored resources.

3. Validate multi-region topology with focused helpers per nested concern.

   Rationale: Region local metadata, encryption stores, relay discovery, and remote entries have different rules and error fields. Separate validators keep required, invalid, duplicate, and warning cases deterministic and easier to test.

   Alternative considered: A single monolithic region validator. That would work initially but would be harder to audit against the many field-specific checkpoint errors.

4. Keep config refresh status transient to the update response.

   Rationale: The checkpoint says `status.configRefresh` appears only in the update response that changed `spec.configBundleRef` and is omitted from later describe output. Computing it from the stored previous and candidate values during update avoids adding durable job state.

   Alternative considered: Persist a pending refresh marker and clear it on describe. That would create hidden state transitions unrelated to any requested command.

5. Preserve declaration order for remotes, telemetry label lists, and extensions.

   Rationale: The checkpoint explicitly requires declaration/list order preservation for these outputs. Validation should detect duplicates without sorting or canonicalizing the user-provided arrays.

   Alternative considered: Sort arrays for deterministic output. That would violate the remotes and extensions ordering contract.

## Risks / Trade-offs

- Projection defaults can blur the line between omitted input and stored fields. Mitigation: tests should cover create, describe, and update outputs for omitted placement and telemetry tags.
- Deep-merge update behavior can leave incompatible nested region or extension fields after partial updates. Mitigation: validate the post-merge candidate atomically and report exact field paths.
- Config refresh depends on distinguishing omitted, null, and changed values. Mitigation: handle `spec.configBundleRef` before generic merge loses the difference between missing and explicit null.
- Region warnings must disappear when errors exist. Mitigation: reuse the existing warning gate so warnings are attached only after validation succeeds.
