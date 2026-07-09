## Why

Meshes can be created and described, but they cannot yet model how workloads are exposed to callers or how operators discover the resulting connection endpoint. This leaves external access, management access, and shell-style connection workflows underspecified at the point users need to validate and use a mesh.

## What Changes

- Add optional `spec.exposure` configuration with `Gateway`, `DirectPort`, and `Balancer` modes.
- Validate exposure mode-specific fields, including required type errors, invalid type errors, and forbidden sub-fields reported with full dot-paths.
- Preserve Gateway annotations and emit computed `status.connectionDetails` from `create` and `describe` whenever exposure is configured.
- Add `spec.management.enabled` with a default of `false`, immutable update validation, and computed `status.managementConnectionDetails` when enabled.
- Add `meshctl mesh shell <name>` to return the connection details for exposed meshes and reject missing or unexposed meshes using the established JSON error format.

## Capabilities

### New Capabilities
- `mesh-network-connectivity`: Covers mesh exposure configuration, computed connection details, management endpoint status, and shell connection lookup.

### Modified Capabilities
- `mesh-resource-management`: Extends mesh create, describe, and update behavior with exposure validation, status output, management immutability, and the `mesh shell` command.

## Related Work

### Related Changes
- `add-access-security-model`: Motivated richer mesh access configuration beyond minimal defaults; this change complements it by defining network reachability and management endpoint metadata without altering access roles or certificates.
- `add-mesh-lifecycle-topology`: Expanded mesh resources with update semantics, topology validation, and lifecycle-aware status; this change extends that lifecycle contract with exposure-derived status and immutable management configuration.
- `add-one-shot-operations`: Added operational command flows against existing meshes; this change complements that by adding a read-oriented shell endpoint lookup for an existing mesh.

### Related Specs
- `one-shot-operations/add-one-shot-operations`: Defines CLI command and error patterns for operations against existing meshes; this change reuses those conventions for `mesh shell`.
- `mesh-resource-management/add-meshctl-mesh-crud`: Defines the base `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` command surface; this change extends create and describe output with connection details.
- `mesh-resource-management/add-mesh-lifecycle-topology`: Defines mesh update and validation behavior; this change builds on it for management endpoint immutability.
- `vault-resource-management/add-vault-resource-management`: Provides adjacent resource-management conventions for create/list/describe/update/delete flows and JSON error handling; this change follows those conventions for mesh connectivity errors.

## Impact

- Affects mesh resource parsing, validation, persistence, and status rendering.
- Affects `meshctl.py` command routing for `mesh create`, `mesh describe`, `mesh update`, and the new `mesh shell` subcommand.
- Adds acceptance coverage for exposure validation, connection detail computation, management endpoint immutability, and shell command errors.
