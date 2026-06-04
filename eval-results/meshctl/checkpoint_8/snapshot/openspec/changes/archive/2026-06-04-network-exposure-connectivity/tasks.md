## 1. Exposure Schema and Validation

- [x] 1.1 Add `spec.exposure` as an optional field in the YAML input schema parser
- [x] 1.2 Validate `spec.exposure.type` is present and non-null when `spec.exposure` is present (required error)
- [x] 1.3 Validate `spec.exposure.type` is one of `Gateway`, `DirectPort`, `Balancer` (invalid error)
- [x] 1.4 Enforce per-mode field allowlist: reject forbidden sub-fields with full dot-path forbidden errors
- [x] 1.5 Store `spec.exposure` (with preserved `annotations` map) in the persisted resource

## 2. Connection Details Computation

- [x] 2.1 Implement `compute_connection_details(name, exposure)` helper that returns `{host, port, protocol}` per mode
- [x] 2.2 Gateway mode: host = hostname if set else `<name>-gateway`, port = 443
- [x] 2.3 DirectPort mode: host = `<name>`, port = directPort if set else default (e.g., 8080)
- [x] 2.4 Balancer mode: host = `<name>-external`, port = port if set else default (e.g., 8080)
- [x] 2.5 Include `status.connectionDetails` in create and describe responses when exposure is configured
- [x] 2.6 Omit `status.connectionDetails` when `spec.exposure` is absent

## 3. Management Endpoint

- [x] 3.1 Add `spec.management.enabled` as an optional boolean field (default `false`) in schema parsing
- [x] 3.2 Enforce immutability of `spec.management.enabled` on update: compare incoming vs stored value
- [x] 3.3 Return immutable error with correct message when `spec.management.enabled` is changed
- [x] 3.4 Include `status.managementConnectionDetails` (`host = <name>-admin`, `port = 9990`, `protocol = "https"`) in create and describe when enabled
- [x] 3.5 Omit `status.managementConnectionDetails` when management is disabled or absent

## 4. mesh shell Command

- [x] 4.1 Register `shell` as a recognized subcommand under `mesh` in the CLI dispatcher
- [x] 4.2 Implement shell handler: load mesh by name, return not-found error if absent
- [x] 4.3 Return invalid error (`spec.exposure`, `"mesh '<name>' has no exposure configured"`) if mesh has no exposure
- [x] 4.4 On success, output only the `connectionDetails` object (no resource envelope)

## 5. Error Sorting and Output

- [x] 5.1 Verify all new error field paths use correct dot-notation (e.g., `spec.exposure.type`, `spec.exposure.directPort`)
- [x] 5.2 Confirm error array is sorted by `field` then `type` in all affected handlers
