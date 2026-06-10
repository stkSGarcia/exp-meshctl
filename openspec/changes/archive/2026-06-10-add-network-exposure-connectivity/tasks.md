## 1. Exposure Model

- [x] 1.1 Add exposure constants for allowed types, allowed fields per type, default Gateway host behavior, default exposed ports, and HTTPS protocol output.
- [x] 1.2 Normalize mesh create output so omitted `spec.exposure` remains absent and provided exposure fields are preserved canonically.
- [x] 1.3 Validate `spec.exposure.type` as required when exposure is present and limited to `Gateway`, `DirectPort`, or `Balancer`.
- [x] 1.4 Validate exposure mode-specific forbidden fields with full dot-path `forbidden` errors.
- [x] 1.5 Preserve valid Gateway `annotations` mappings in persisted resources and public output.

## 2. Connection Status

- [x] 2.1 Add shared connection-detail computation from mesh name and `spec.exposure`.
- [x] 2.2 Include `status.connectionDetails` in mesh create and describe output when exposure is configured.
- [x] 2.3 Omit `status.connectionDetails` from persisted and public output when exposure is omitted.
- [x] 2.4 Ensure Gateway, DirectPort, and Balancer outputs use the required host, port, and `"https"` protocol values.

## 3. Management Endpoint

- [x] 3.1 Normalize omitted `spec.management.enabled` to `false` during mesh create and stored-resource upgrade.
- [x] 3.2 Include `status.managementConnectionDetails` with `<name>-admin`, port `9990`, and protocol `"https"` when management is enabled.
- [x] 3.3 Omit `status.managementConnectionDetails` when management is disabled.
- [x] 3.4 Reject updates that change `spec.management.enabled` with the required `immutable` field, type, and message.

## 4. Mesh Shell Command

- [x] 4.1 Add `mesh shell <name>` to argparse routing and command dispatch.
- [x] 4.2 Implement shell lookup for existing exposed meshes that prints only the connection details object.
- [x] 4.3 Return the standard `metadata.name` `not_found` error for missing meshes.
- [x] 4.4 Reject meshes without exposure using `spec.exposure` `invalid` and message `mesh '<name>' has no exposure configured`.

## 5. Tests

- [x] 5.1 Add tests for omitted exposure, each exposure mode, default ports, default Gateway host behavior, and annotation preservation.
- [x] 5.2 Add tests for exposure required, invalid, and forbidden-field validation errors, including sorted error output.
- [x] 5.3 Add tests for `status.connectionDetails` on create and describe for Gateway, DirectPort, and Balancer.
- [x] 5.4 Add tests for management defaulting, enabled management status output, disabled omission, and immutable update rejection.
- [x] 5.5 Add tests for `mesh shell` success output, missing mesh errors, and no-exposure errors.
- [x] 5.6 Add tests proving exposure and management validation failures remain atomic on update.

## 6. Verification

- [x] 6.1 Run the meshctl test suite.
- [x] 6.2 Run OpenSpec validation for `add-network-exposure-connectivity`.
