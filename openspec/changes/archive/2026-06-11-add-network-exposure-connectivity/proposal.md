## Why

Meshes need a documented way to expose their service endpoints and surface the computed connection information clients should use. Operators also need a management endpoint toggle and a direct `mesh shell` command that returns the active connection target without wrapping it in the full resource envelope.

## What Changes

- Add optional `spec.exposure` support with `Gateway`, `DirectPort`, and `Balancer` exposure modes.
- Validate exposure mode requiredness, mode-specific allowed fields, field types, and forbidden sub-fields with sorted JSON errors.
- Include computed `status.connectionDetails` on successful mesh create and describe output whenever exposure is configured.
- Preserve Gateway exposure annotations in persisted and returned mesh resources.
- Add `spec.management.enabled`, defaulting to `false`, with immutability after create.
- Include computed `status.managementConnectionDetails` when management is enabled.
- Add `mesh shell <name>` to return only the mesh `status.connectionDetails` object and reject meshes without exposure.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mesh-resource-management`: Extend mesh resource schema, validation, status projection, update immutability rules, and CLI operations for network exposure, connection details, management endpoint details, and `mesh shell`.

## Impact

- Affects `meshctl.py` mesh create, describe, update, and command dispatch behavior.
- Affects persisted mesh spec/status shape and public JSON output.
- Requires focused CLI tests for exposure validation/defaulting, computed connection details, management immutability, and `mesh shell` success/error cases.
