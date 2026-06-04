## Why

The mesh management tool currently handles single-region deployments only, leaving no way to configure multi-region topology, telemetry observability, workload placement affinity, config bundle refresh tracking, or runtime extensions. As mesh deployments scale across regions, operators need first-class support for these operational policies directly in the create/update/describe workflow.

### Related Specs

**`spec:mesh-management`** — Core meshctl CRUD operations and validation pipeline. _Why it exists: foundational meshctl operations for managing mesh resources._ This change extends that spec by adding new top-level `spec` sections (`regions`, `placement`, `configBundleRef`, `extensions`) and new `status` fields (`telemetryProbe`, `configRefresh`).

**`spec:mesh-exposure`** — Exposure type validation (`Gateway`, `DirectPort`, `Balancer`). _Why it exists: controls how the mesh is externally accessible._ This change builds on those exposure type definitions — the local region's `expose.type` shares the same valid values plus `Internal`, and `Gateway` type gains a new inter-region encryption constraint (`transportKeyStore` required).

**`spec:mesh-connection-details`** — Connection detail output when exposure is configured. _Why it exists: provides computed connectivity information in create/describe responses._ This change complements it by adding `status.telemetryProbe` as a new always-present status field alongside connection details.

The related specs collectively establish the pattern of spec-driven field validation, defaulting, and enriched status output that this change follows and extends into multi-region and observability domains.

## What Changes

- Add `spec.regions` for multi-region topology: `local` (required when `spec.regions` present) with `name`, `expose.type`, `maxRelayNodes`, `encryption`, and `discovery` sub-fields; `remotes` array for peer regions.
- Add `spec.placement` with `affinity.type` and `affinity.scope` — always present in output with defaults applied.
- Add `metadata.tags` as a free-form string→string map persisted as-is.
- Add `status.telemetryProbe` — always present in output, driven by `metadata.tags`.
- Add `spec.configBundleRef` with update-time refresh tracking via `status.configRefresh`.
- Add `spec.extensions` array for URL- or artifact-based runtime extensions.
- Add `DiscoveryRelayReady` and `RegionViewFormed` status conditions when `spec.regions` is present.
- **BREAKING**: Reject `spec.migration.strategy = "LiveMigration"` when `spec.regions` is present.

## Capabilities

### New Capabilities

- `multi-region-topology`: `spec.regions` configuration — local region definition (name, expose type, maxRelayNodes, encryption, discovery) and remotes array; region conditions in status.
- `telemetry-probe`: `metadata.tags`-driven `status.telemetryProbe` output with label categories.
- `mesh-placement`: `spec.placement.affinity` with type/scope defaults, always included in output.
- `config-bundle-ref`: `spec.configBundleRef` field with update-time `status.configRefresh` tracking.
- `mesh-extensions`: `spec.extensions` array with url/artifact mutual exclusion validation.

### Modified Capabilities

- `mesh-management`: Add `spec.regions`, `spec.placement`, `spec.configBundleRef`, `spec.extensions`, `metadata.tags` to the recognized input schema; add `status.telemetryProbe` as always-present output field; reject `LiveMigration` when regions are present.

## Impact

- `meshctl.py` — main processing pipeline (validation, defaulting, output construction) extended for all new fields.
- `store.json` — persists new fields; existing resources unaffected (new fields are optional).
- Status conditions array gains two new entries when regions are configured; sort order maintained.
- Error/warning output format unchanged; new error and warning cases added per spec.
