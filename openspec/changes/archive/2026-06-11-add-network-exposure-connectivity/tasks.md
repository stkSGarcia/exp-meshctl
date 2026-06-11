## 1. Tests

- [x] 1.1 Add create/describe tests for omitted exposure, Gateway exposure, DirectPort exposure, Balancer exposure, preserved Gateway annotations, and computed `status.connectionDetails`.
- [x] 1.2 Add validation tests for missing, empty, invalid, and null `spec.exposure.type`; invalid exposure field types; invalid annotations; and mode-specific forbidden fields using full dot-path errors.
- [x] 1.3 Add management endpoint tests for default `spec.management.enabled: false`, enabled management connection details, invalid non-boolean values, and immutable update errors.
- [x] 1.4 Add `mesh shell <name>` tests for successful connection details output, missing mesh not-found errors, and unexposed mesh invalid errors.
- [x] 1.5 Add update tests that verify exposure changes recompute connection details and validation failures are atomic.

## 2. Parser and Command Flow

- [x] 2.1 Add the `mesh shell <name>` argparse subcommand and dispatch branch.
- [x] 2.2 Implement `mesh_shell(name)` using the existing store load, upgrade, error printing, and JSON output helpers.

## 3. Spec Normalization and Validation

- [x] 3.1 Add exposure constants and helpers for default Gateway host, default service port, and default direct port.
- [x] 3.2 Implement create-time normalization for optional `spec.exposure`, preserving only allowed canonical fields for the selected mode.
- [x] 3.3 Implement merged-resource exposure validation for type requiredness, allowed values, field types, annotations string mapping, and forbidden fields.
- [x] 3.4 Implement `spec.management.enabled` normalization with default `false` and validation as a boolean.
- [x] 3.5 Add update immutability validation for changes to `spec.management.enabled`.
- [x] 3.6 Update stored-resource upgrade behavior so existing meshes receive `spec.management.enabled: false` while omitted `spec.exposure` stays absent.

## 4. Derived Status and Public Output

- [x] 4.1 Add helper functions that compute `status.connectionDetails` from `metadata.name` and `spec.exposure`.
- [x] 4.2 Add helper functions that compute `status.managementConnectionDetails` from `metadata.name` when management is enabled.
- [x] 4.3 Update mesh public projection and successful create/describe/update/migrate paths so derived connection details are present or absent according to spec.
- [x] 4.4 Ensure `mesh list` summary output remains unchanged.

## 5. Verification

- [x] 5.1 Run the focused new CLI tests for exposure, management, and shell behavior.
- [x] 5.2 Run the full test suite.
- [x] 5.3 Run `openspec status --change "add-network-exposure-connectivity"` and confirm the change is apply-ready.
