## Why

Mesh resources can be created, updated, and described, but callers do not yet have a contract for how a mesh is reachable after creation. Defining exposure modes, computed connection details, management endpoint details, and a direct `mesh shell` lookup gives operators predictable connectivity output and validation behavior.

## What Changes

- Add optional `spec.exposure` support with `Gateway`, `DirectPort`, and `Balancer` exposure modes.
- Validate exposure type requirements, allowed fields per mode, default ports, and mode-specific forbidden fields.
- Include computed `status.connectionDetails` in successful create and describe output when exposure is configured.
- Add optional `spec.management.enabled` with a `false` default, immutable update behavior, and computed `status.managementConnectionDetails` when enabled.
- Add `mesh shell <name>` to return the exposed connection details for a mesh, with structured errors for missing meshes or meshes without exposure.
- Require exposure and shell validation errors to use the established JSON error format and sort by `field`, then `type`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mesh-resource-management`: Define mesh exposure, connection detail status, management endpoint status, and `mesh shell` behavior.

## Impact

- `meshctl.py` mesh create, describe, update, shell command routing, validation, defaulting, status rendering, and JSON error paths.
- Mesh resource tests covering exposure validation, computed connection details, management immutability, management status output, `mesh shell` success/error output, and error ordering.
- No new runtime dependencies are expected.
