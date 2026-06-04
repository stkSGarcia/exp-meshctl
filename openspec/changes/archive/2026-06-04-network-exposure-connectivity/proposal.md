## Why

The mesh tool currently has no way to expose a mesh externally or report how clients connect to it. Operators need structured exposure settings, computed connection endpoints, and a management port — plus a `mesh shell` shortcut to retrieve those connection details directly.

### Related Specs

**`spec:mesh-management`** — Core mesh CRUD and lifecycle management. _Why it exists: to provide a single CLI tool for creating, reading, updating, and deleting mesh resources with full validation._ This change extends that spec by adding `spec.exposure` and `spec.management` sub-fields to the mesh schema, and by including `status.connectionDetails` and `status.managementConnectionDetails` in create/describe output.

**`spec:mesh-migrate-command`** — The `meshctl mesh migrate` command for advancing active migrations. _Why it exists: to provide a discrete CLI command for mesh migration stage transitions._ This change complements it by introducing a new `mesh shell` command following the same not-found error pattern.

Together these specs establish the CLI command shape and error conventions this change must follow — making network exposure a natural next tier of mesh configuration on top of the existing management foundation.

## What Changes

- Add `spec.exposure` (optional) to the mesh schema with three modes: `Gateway`, `DirectPort`, and `Balancer`, each with their own allowed sub-fields.
- Validate exposure type presence, type validity, and forbidden sub-fields per mode.
- Compute `status.connectionDetails` (`host`, `port`, `protocol`) on create/describe when exposure is configured.
- Add `spec.management.enabled` (boolean, default `false`) as an immutable-after-create field.
- Compute `status.managementConnectionDetails` when management is enabled.
- Add `meshctl mesh shell <name>` command that returns the connection details object directly.

## Capabilities

### New Capabilities

- `mesh-exposure`: spec.exposure configuration — type validation, per-mode allowed fields, forbidden field enforcement
- `mesh-connection-details`: Computation of `status.connectionDetails` from exposure type and fields for create and describe output
- `mesh-management-endpoint`: `spec.management.enabled` field with immutability enforcement and `status.managementConnectionDetails` output
- `mesh-shell-command`: `meshctl mesh shell <name>` command returning connection details or an error

### Modified Capabilities

- `mesh-management`: Add `spec.exposure` and `spec.management` to the YAML input schema and success output for create and describe

## Impact

- `meshctl.py` — new `shell` subcommand under `mesh`; create/update/describe handlers must include connectionDetails and managementConnectionDetails when applicable
- YAML input schema — new optional top-level `spec` sub-keys: `exposure`, `management`
- Output JSON schema — new optional `status` sub-keys: `connectionDetails`, `managementConnectionDetails`
- Error output format — unchanged; uses existing `field`/`type`/`message` shape with new field paths
