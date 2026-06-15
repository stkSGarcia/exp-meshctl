## Why

Meshes can be created and managed, but their external connectivity contract is not specified. This change defines how exposure settings produce connection details, how management endpoints are represented, and how operators retrieve shell connection information.

## Related Work

### Related Changes

- `add-mesh-lifecycle-topology`: Added update behavior, topology validation, and lifecycle-aware status. This change extends that work by adding immutable management endpoint validation and status-derived connection details.
- `add-access-security-model`: Defined access authentication, permissions, encryption, and optional-field output behavior. This change complements that security model by preserving exposure annotations and omitting connection details when exposure is absent.
- `add-meshctl-mesh-crud`: Established the baseline mesh create, list, describe, and delete contract. This change builds on that CLI surface by adding `mesh shell` and expanding create/describe output for exposed meshes.

### Related Specs

- `mesh-resource-management/add-meshctl-mesh-crud`: Implements mesh CRUD commands, persistence, defaulting, validation, and JSON output. This change reuses that command and output model for exposure validation and `mesh shell`.
- `mesh-resource-management/add-access-security-model`: Implements access configuration output rules, including omission of optional fields when unset or inapplicable. This change adapts that projection pattern for optional exposure and preserved Gateway annotations.
- `mesh-resource-management/add-mesh-lifecycle-topology`: Implements update semantics and successful command output requirements. This change extends that update contract with immutable management endpoint behavior and computed status fields.

## What Changes

- Add optional `spec.exposure` support with `Gateway`, `DirectPort`, and `Balancer` modes.
- Validate required exposure type values and reject fields that are not allowed for the selected exposure mode.
- Preserve Gateway annotations and apply default ports where required.
- Include `status.connectionDetails` in create and describe output only when exposure is configured.
- Add optional `spec.management.enabled`, defaulting to `false`, and reject attempts to change it after creation.
- Include `status.managementConnectionDetails` when management is enabled.
- Add `meshctl.py mesh shell <name>` to return connection details for exposed meshes and structured errors for missing or unexposed meshes.

## Capabilities

### New Capabilities

- `network-exposure-connectivity`: Mesh exposure configuration, computed connection details, management endpoint status, and `mesh shell` behavior.

### Modified Capabilities

- None.

## Impact

- Affected code: `meshctl.py`, `tests/test_meshctl_cli.py`.
- Affected CLI: `mesh create`, `mesh describe`, `mesh update`, and new `mesh shell`.
- Affected API shape: `spec.exposure`, `spec.management.enabled`, `status.connectionDetails`, and `status.managementConnectionDetails`.
