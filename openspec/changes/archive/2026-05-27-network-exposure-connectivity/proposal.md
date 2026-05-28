## Why

The mesh tool currently has no way to expose meshes externally or provide connection information to consumers. This change adds network exposure modes, computed connection details, a management endpoint flag, and the `mesh shell` command to enable connectivity-oriented workflows.

## What Changes

- `spec.exposure` optional block added to mesh resources with three modes: `Gateway`, `DirectPort`, and `Balancer`
- `status.connectionDetails` computed and returned on `create` and `describe` when exposure is configured
- `spec.management.enabled` boolean flag (immutable after create) for enabling a management endpoint
- `status.managementConnectionDetails` returned when `spec.management.enabled` is `true`
- `mesh shell <name>` subcommand added, returning raw `connectionDetails` without a resource envelope
- Forbidden-field validation enforced per exposure type (mode-specific fields not allowed in other modes)
- Immutability enforced on `spec.management.enabled` after creation

## Capabilities

### New Capabilities
- `mesh-exposure`: Exposure type validation, allowed/forbidden field rules per mode, and `connectionDetails` computation for Gateway, DirectPort, and Balancer types
- `mesh-shell`: The `mesh shell` command — requires exposure, returns `connectionDetails` without envelope

### Modified Capabilities
- `mesh-management`: Adds `spec.management.enabled` field (immutable), `status.managementConnectionDetails`, and expands `create`/`describe` output contract to include both connection detail blocks

## Impact

- `meshctl.py`: New `shell` subcommand dispatcher and handler; create/describe output serialization must include `connectionDetails` and `managementConnectionDetails` conditionally
- `mesh-management` spec: Extended with management endpoint and output contract changes
- Store schema unchanged (fields added at spec and status level only)
