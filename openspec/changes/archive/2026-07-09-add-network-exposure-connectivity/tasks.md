## 1. Resource Model and Validation

- [x] 1.1 In `meshctl.py`, add exposure mode/default constants and a mode-to-allowed-fields table for `Gateway`, `DirectPort`, and `Balancer`. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 In `meshctl.py`, normalize `spec.exposure` during mesh create/update without defaulting the object when omitted; preserve Gateway `annotations`. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.3 In `meshctl.py`, validate required/invalid `spec.exposure.type`, mode-specific forbidden fields with full dot-paths, integer port fields, and string-to-string annotations. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 1.4 In `meshctl.py`, normalize `spec.management.enabled` to `false` on create and validate it as a boolean when present. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.5 In `meshctl.py`, compare stored and candidate `spec.management.enabled` during update and emit the exact immutable error when it changes. [extends mesh-resource-management/add-mesh-lifecycle-topology]

## 2. Derived Status Output

- [x] 2.1 In `meshctl.py`, add a helper that derives `status.connectionDetails` for Gateway, DirectPort, and Balancer using the specified host, port, and `https` protocol rules. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.2 In `meshctl.py`, add a helper that derives `status.managementConnectionDetails` as `<name>-admin`, port `9990`, protocol `https` when management is enabled. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.3 In `meshctl.py`, call the derived status helpers from `public_resource`, removing stale connectivity status when exposure or management is absent. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.4 In `meshctl.py`, ensure create and describe output include derived connectivity status while list summaries remain unchanged. [extends mesh-resource-management/add-meshctl-mesh-crud]

## 3. Shell Command

- [x] 3.1 In `meshctl.py`, add parser and dispatcher support for `meshctl.py mesh shell <name>`. [extends one-shot-operations/add-one-shot-operations]
- [x] 3.2 In `meshctl.py`, implement `mesh_shell` to load the stored mesh, use the standard `metadata.name` `not_found` error when absent, and compute public output before reading connection details. [extends one-shot-operations/add-one-shot-operations]
- [x] 3.3 In `meshctl.py`, make `mesh_shell` reject meshes without exposure using `field = "spec.exposure"`, `type = "invalid"`, and `message = "mesh '<name>' has no exposure configured"`. [extends one-shot-operations/add-one-shot-operations]
- [x] 3.4 In `meshctl.py`, make successful `mesh shell` output only the `connectionDetails` object, without the mesh resource envelope. [extends one-shot-operations/add-one-shot-operations]

## 4. Tests and Verification

- [x] 4.1 In `tests/test_meshctl_cli.py`, add create/describe coverage for omitted exposure, Gateway annotations, Gateway host/default host behavior, DirectPort directPort/default behavior, and Balancer port/default behavior.
- [x] 4.2 In `tests/test_meshctl_cli.py`, add validation coverage for missing/null/empty exposure type, invalid exposure type, and forbidden fields sorted by field then type.
- [x] 4.3 In `tests/test_meshctl_cli.py`, add management endpoint coverage for default disabled output, enabled output, omitted update preservation, and immutable update rejection.
- [x] 4.4 In `tests/test_meshctl_cli.py`, add `mesh shell` coverage for missing mesh, unexposed mesh, and successful connectionDetails-only output.
- [x] 4.5 Run `uv run pytest` and confirm all tests pass.
