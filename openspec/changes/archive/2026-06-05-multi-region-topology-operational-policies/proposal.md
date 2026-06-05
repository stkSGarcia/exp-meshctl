## Why

The meshctl tool currently manages single-region meshes with basic lifecycle and access controls, but operators running production workloads need multi-region federation, structured telemetry reporting, node/zone affinity policies, config bundle refresh tracking, and plugin extensions — none of which exist today. This change introduces those operational capabilities to close the gap between the current tool and real-world mesh deployments.

### Related Changes

**`mesh-lifecycle-and-topology`** — Adds mesh update with a lifecycle state machine and topology fields (`storage`, `replicationFactor`) missing from the initial model.

**`security-model`** — Adds the complete `spec.access` contract (authentication, permissions, certificate-based encryption) for secure mesh deployments.

**`network-exposure-connectivity`** — Adds structured external network access via Gateway, DirectPort, and Balancer modes plus a `mesh shell` command for connectivity details.

These prior changes established the mesh resource schema and lifecycle foundation. This change builds on them by adding the multi-region federation layer, operational observability (telemetry probe), placement policies, and extensibility (extensions array and config bundle refresh).

## What Changes

- **`spec.regions`** — New optional block for multi-region configuration. When present, `spec.regions.local` is required and configures the local region name, expose type, optional max relay nodes, inter-region encryption, and relay discovery settings. `spec.regions.remotes` is an optional array of remote region endpoints.
- **`spec.placement`** — New always-present section with affinity type (`"preferred"` / `"required"`) and scope (`"node"` / `"zone"`), defaulted when omitted.
- **`spec.configBundleRef`** — New optional string. Updates that change this value produce a transient `status.configRefresh` block in the response.
- **`spec.extensions`** — New optional array for plugin extensions, each requiring exactly one of `url` or `artifact`.
- **`metadata.tags`** — New optional string-to-string map. Tag keys `mesh.io/telemetry`, `mesh.io/targetLabels`, `mesh.io/probeTargetLabels`, and `mesh.io/instanceLabels` drive telemetry behavior.
- **`status.telemetryProbe`** — Always present on create/describe output; reflects the telemetry enabled state and label categories derived from tags.
- **Region conditions** — When `spec.regions` is present, `DiscoveryRelayReady` and `RegionViewFormed` conditions are added to `status.conditions` (sorted alphabetically, not affecting `status.stable`).
- **Migration restriction** — `spec.migration.strategy = "LiveMigration"` is rejected when `spec.regions` is present.

## Capabilities

### New Capabilities

- `multi-region`: Local region, inter-region encryption, relay discovery, remote region array, region conditions, and migration restriction for multi-region mesh topology.

### Modified Capabilities

- `mesh-management`: Adds `spec.placement` (always-present with defaults), `spec.configBundleRef` (with update-time refresh tracking), `spec.extensions`, `metadata.tags`, `status.telemetryProbe` (always-present), and the LiveMigration restriction when regions are configured.

## Impact

- `meshctl.py` — Create and update handlers require new field validation for regions, placement, extensions, configBundleRef, and tag-based telemetry.
- Output format — `status.telemetryProbe` and `spec.placement` are now always present in create/describe output; `status.configRefresh` is conditionally present on update.
- Existing tests — Any test asserting the exact shape of `create`/`describe` output must be updated to include the new always-present fields.
