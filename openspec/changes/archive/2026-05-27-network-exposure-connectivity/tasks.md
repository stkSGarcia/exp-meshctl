## 1. Exposure Validation

- [x] 1.1 Add `VALID_EXPOSURE_TYPES` constant and per-mode allowed-field sets (Gateway: `hostname`, `annotations`; DirectPort: `port`, `directPort`; Balancer: `port`)
- [x] 1.2 Add `validate_exposure(spec, errors)` function that checks: if `spec.exposure` is absent, skip; if `spec.exposure.type` is missing/null/empty, emit `required`; if type is unrecognized, emit `invalid`; then for each field present under `spec.exposure` (other than `type`), emit `forbidden` if not in the allowed set for the selected mode
- [x] 1.3 Call `validate_exposure` from `validate_and_build` (both create and update paths)

## 2. Connection Details Computation

- [x] 2.1 Add `DEFAULT_EXPOSURE_PORT = 443` constant
- [x] 2.2 Add `compute_connection_details(name, exposure)` helper that returns a `{"host": ..., "port": ..., "protocol": "https"}` dict based on exposure type: Gateway uses `hostname` or a default host; DirectPort uses `name` as host and `directPort` or default port; Balancer uses `"<name>-external"` as host and `port` or default port
- [x] 2.3 Extend `format_resource_for_output` (or the equivalent serialization path) to include `status.connectionDetails` when `spec.exposure` is present, by calling `compute_connection_details`

## 3. Management Endpoint

- [x] 3.1 Add `spec.management.enabled` default (`false`) in `validate_and_build` create path
- [x] 3.2 Add immutability check for `spec.management.enabled` in `check_immutable` (or equivalent update validation), emitting `{"field":"spec.management.enabled","type":"immutable","message":"field 'spec.management.enabled' is immutable after creation"}`
- [x] 3.3 Add `compute_management_connection_details(name)` helper returning `{"host": "<name>-admin", "port": 9990, "protocol": "https"}`
- [x] 3.4 Extend `format_resource_for_output` to include `status.managementConnectionDetails` when `spec.management.enabled` is `true`

## 4. mesh shell Command

- [x] 4.1 Add `cmd_shell(args)` function: load store, look up mesh by name; if not found emit standard `not_found` error; if `spec.exposure` is absent emit `{"field":"spec.exposure","type":"invalid","message":"mesh '<name>' has no exposure configured"}`; otherwise print only the `connectionDetails` object
- [x] 4.2 Register `shell` subcommand on the mesh subparsers (add `name` positional argument) and wire it to `cmd_shell`
