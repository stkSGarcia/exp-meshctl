## Why

Mesh resources need a contract for exposing network access and reporting the computed connection details that operators can use after creation. The CLI also needs a focused `mesh shell` command and immutable management endpoint semantics so connection-oriented workflows behave predictably.

## What Changes

- Add optional `spec.exposure` configuration with `Gateway`, `DirectPort`, and `Balancer` modes.
- Validate exposure type, allowed sub-fields, required exposure type, and forbidden fields using the JSON error format.
- Preserve Gateway annotations in resource output.
- Compute `status.connectionDetails` for exposed meshes in `create` and `describe` output, and omit it when no exposure is configured.
- Add `spec.management.enabled` with a default of `false`, immutable after creation.
- Compute `status.managementConnectionDetails` when management access is enabled.
- Add `meshctl mesh shell <name>` to return only the connection details object for exposed meshes.

## Related Work

### Related Changes

- None found by the shallow KG search.

### Related Specs

- `one-shot-operations/add-one-shot-operations`: Defines command-oriented behavior that extends mesh resource management; this change complements it by adding a one-shot `mesh shell` command whose success output is a single connection details object rather than a full resource envelope.
- `mesh-resource-management/add-mesh-lifecycle-topology`: Defines mesh update behavior and lifecycle/topology resource semantics; this change builds on it by extending mesh resource validation, create/describe output, and update immutability rules for connectivity fields.

## Capabilities

### New Capabilities

- `mesh-connectivity`: Exposure configuration, computed connection details, management endpoint status, and shell connection lookup behavior for meshes.

### Modified Capabilities

- `mesh-resource-management`: Mesh resource validation and lifecycle output now account for exposure and management endpoint fields.
- `one-shot-operations`: One-shot mesh commands now include `mesh shell` connection lookup output.

## Impact

- Mesh resource schema and validation for `spec.exposure` and `spec.management.enabled`.
- Mesh create, update, and describe command output.
- JSON error responses and deterministic error sorting by `field`, then `type`.
- CLI command surface for `meshctl mesh shell <name>`.
