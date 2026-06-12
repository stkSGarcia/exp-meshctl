## 1. CLI Surface

- [x] 1.1 Add `mesh shell <name>` parsing and dispatch in `meshctl.py`, starting from the existing mesh subparser and `mesh_describe()` lookup flow. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 Implement `mesh_shell(name)` in `meshctl.py` so missing meshes use the standard `not_found` shape and exposed meshes print only `status.connectionDetails`. [extends mesh-resource-management/add-meshctl-mesh-crud]

## 2. Exposure Model

- [x] 2.1 Add exposure constants and helper functions in `meshctl.py` for allowed modes, allowed fields, default ports, and computed connection details. [extends mesh-resource-management/add-access-security-model]
- [x] 2.2 Normalize `spec.exposure` during mesh create in `meshctl.py`, preserving Gateway annotations and accepted mode-specific fields. [extends mesh-resource-management/add-access-security-model]
- [x] 2.3 Validate `spec.exposure.type` and forbidden sub-fields in `meshctl.py` during create and update, using full dot-path errors sorted by existing `print_errors()`. [extends mesh-resource-management/add-access-security-model]
- [x] 2.4 Update public resource projection in `meshctl.py` so exposed meshes include `status.connectionDetails` and unexposed meshes omit it. [extends mesh-resource-management/add-mesh-lifecycle-topology]

## 3. Management Endpoint

- [x] 3.1 Normalize `spec.management.enabled` to `false` during mesh create and resource upgrade in `meshctl.py`. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.2 Add immutable update validation for `spec.management.enabled` in `validate_merged_resource()` in `meshctl.py`. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.3 Derive `status.managementConnectionDetails` in `meshctl.py` only when management is enabled. [extends mesh-resource-management/add-mesh-lifecycle-topology]

## 4. Tests

- [x] 4.1 Add create and describe tests in `tests/test_meshctl_cli.py` for omitted exposure, Gateway, DirectPort, Balancer, default ports, and preserved annotations.
- [x] 4.2 Add validation tests in `tests/test_meshctl_cli.py` for missing exposure type, invalid type, forbidden mode fields, and deterministic error sorting.
- [x] 4.3 Add management endpoint tests in `tests/test_meshctl_cli.py` for default disabled output, enabled status details, and immutable update rejection.
- [x] 4.4 Add `mesh shell` tests in `tests/test_meshctl_cli.py` for success output, missing mesh, and unexposed mesh rejection.

## 5. Verification

- [x] 5.1 Run the project test suite with `uv run pytest` or the repository's configured test command.
- [x] 5.2 Run `openspec status --change "add-network-exposure-connectivity"` and confirm all required artifacts are complete.
