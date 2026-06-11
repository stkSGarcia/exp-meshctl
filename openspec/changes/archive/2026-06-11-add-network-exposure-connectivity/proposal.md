## Why

Meshes need a documented way to expose their service endpoints and report connection information back to operators. Adding exposure, management endpoint details, and a shell lookup command makes mesh resources usable for connectivity workflows while keeping the CLI output deterministic and structured.

## What Changes

- Add optional `spec.exposure` configuration with `Gateway`, `DirectPort`, and `Balancer` modes.
- Validate exposure mode requirements, allowed mode-specific fields, and forbidden fields with full dot-path JSON errors.
- Compute `status.connectionDetails` for exposed meshes in create and describe output, while omitting it for meshes without exposure.
- Add optional `spec.management.enabled`, defaulting to `false`, with create-time management connection details when enabled.
- Enforce immutability for `spec.management.enabled` after create.
- Add `mesh shell <name>` to return only the exposed mesh `connectionDetails` object or a structured error.

## Capabilities

### New Capabilities

### Modified Capabilities
- `mesh-resource-management`: Adds mesh exposure configuration, computed connectivity status, management endpoint status, and the `mesh shell` command contract.

## Impact

- Affects `meshctl.py` mesh create, describe, update, and command parsing paths.
- Extends mesh validation, defaulting, public output shaping, status computation, and JSON error handling.
- Requires tests for exposure modes, forbidden fields, connection details, management immutability, and `mesh shell` success/error behavior.
