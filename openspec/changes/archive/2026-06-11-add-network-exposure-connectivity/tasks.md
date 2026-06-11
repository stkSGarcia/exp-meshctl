## 1. Command Surface

- [x] 1.1 Add `mesh shell <name>` parser wiring and dispatch to the mesh command flow.
- [x] 1.2 Implement `mesh_shell(name)` with standard missing mesh handling, unexposed mesh rejection, and connection-details-only JSON output.

## 2. Exposure Normalization and Validation

- [x] 2.1 Add exposure constants/helpers for supported types, allowed fields, default host, default port, and mode-specific connection detail derivation.
- [x] 2.2 Normalize optional `spec.exposure` during create/update while preserving valid Gateway annotations and mode-specific fields.
- [x] 2.3 Validate missing, null, empty, or invalid `spec.exposure.type` with the documented `required` and `invalid` errors.
- [x] 2.4 Reject exposure sub-fields forbidden by the selected mode using full dot-path `forbidden` errors.

## 3. Management Endpoint

- [x] 3.1 Add `spec.management.enabled` create defaulting to `false` and boolean validation.
- [x] 3.2 Enforce update immutability for `spec.management.enabled` after create with the documented field, type, and message.
- [x] 3.3 Compute `status.managementConnectionDetails` for enabled management endpoints and omit it when disabled.

## 4. Computed Connectivity Output

- [x] 4.1 Compute `status.connectionDetails` in public mesh output for Gateway, DirectPort, and Balancer exposure modes.
- [x] 4.2 Ensure create and describe output omit `status.connectionDetails` when `spec.exposure` is absent.
- [x] 4.3 Keep derived connection details consistent across create, describe, and `mesh shell` output.

## 5. Tests

- [x] 5.1 Add CLI tests for each exposure mode, preserved fields, defaulted connection details, and omitted connection details without exposure.
- [x] 5.2 Add validation tests for missing/invalid exposure type and forbidden fields sorted by field then type.
- [x] 5.3 Add management tests for default disabled output, enabled management connection details, invalid boolean values, and immutable updates.
- [x] 5.4 Add `mesh shell` tests for success output, missing mesh `not_found`, and unexposed mesh `spec.exposure` invalid errors.
- [x] 5.5 Run the existing meshctl CLI test suite and OpenSpec validation for the change.
