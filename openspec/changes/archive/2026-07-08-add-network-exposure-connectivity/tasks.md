## 1. Mesh Connectivity Model

- [x] 1.1 Add exposure and management constants plus normalization helpers in `meshctl.py` near existing mesh spec helpers. [extends `mesh-resource-management/add-mesh-lifecycle-topology`]
- [x] 1.2 Call the new normalization helpers from `normalize_mesh_for_create` and `upgrade_stored_resource` in `meshctl.py`, preserving omitted `spec.exposure` and defaulting `spec.management.enabled` to `false`. [extends `mesh-resource-management/add-mesh-lifecycle-topology`]
- [x] 1.3 Add a connectivity status reconciliation helper in `meshctl.py` that computes `status.connectionDetails` and `status.managementConnectionDetails` from the mesh name and canonical spec. [extends `mesh-resource-management/add-mesh-lifecycle-topology`]
- [x] 1.4 Ensure create, update, and describe paths in `meshctl.py` call the reconciliation helper before public output or persistence. [extends `mesh-resource-management/add-mesh-lifecycle-topology`]

## 2. Validation

- [x] 2.1 Add `validate_exposure_object` in `meshctl.py` and call it from `validate_merged_resource` to enforce required type, valid modes, field typing, forbidden sub-fields, and full dot-path errors.
- [x] 2.2 Add `validate_management_object` in `meshctl.py` and call it from `validate_merged_resource` to enforce boolean `spec.management.enabled`.
- [x] 2.3 Extend update immutability checks in `validate_merged_resource` to reject post-create changes to `spec.management.enabled` with the prescribed field, type, and message. [extends `mesh-resource-management/add-mesh-lifecycle-topology`]
- [x] 2.4 Preserve existing `print_errors` sorting by adding tests that produce multiple connectivity errors and assert ordering by `field`, then `type`.

## 3. Mesh Shell Command

- [x] 3.1 Extend `build_parser` and `main` in `meshctl.py` with `mesh shell <name>`. [extends `mesh-resource-management/add-mesh-lifecycle-topology`]
- [x] 3.2 Implement `mesh_shell(name)` in `meshctl.py` to load the mesh, return the standard not-found shape when absent, reject meshes without exposure, and print only the `connectionDetails` object on success. [extends `one-shot-operations/add-one-shot-operations`]

## 4. Tests

- [x] 4.1 Add `tests/test_meshctl_cli.py` coverage for omitted exposure, all three exposure modes, defaulted ports/hosts, Gateway annotations preservation, and create/describe connection details. [extends `mesh-resource-management/add-mesh-lifecycle-topology`]
- [x] 4.2 Add `tests/test_meshctl_cli.py` coverage for management defaulting, enabled management status, and immutable update rejection.
- [x] 4.3 Add `tests/test_meshctl_cli.py` coverage for invalid exposure type, missing exposure type, forbidden mode-specific fields, invalid field types, and sorted errors.
- [x] 4.4 Add `tests/test_meshctl_cli.py` coverage for `mesh shell` success output, no-exposure rejection, and missing-mesh not-found behavior. [extends `one-shot-operations/add-one-shot-operations`]
- [x] 4.5 Run `uv run pytest` and fix any regressions in existing mesh, vault, migration, and one-shot tests.
