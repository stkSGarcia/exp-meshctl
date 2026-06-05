## 1. Exposure Validation

- [x] 1.1 Add `spec.exposure` optional field handling: when absent, skip all exposure validation and omit `status.connectionDetails` from output
- [x] 1.2 Add `spec.exposure.type` required-field check: emit `{"field":"spec.exposure.type","type":"required"}` when exposure is present but type is missing or null
- [x] 1.3 Add `spec.exposure.type` enum validation: emit `{"field":"spec.exposure.type","type":"invalid"}` for unrecognized values
- [x] 1.4 Build exposure type dispatch table mapping `"Gateway"` → `{hostname, annotations}`, `"DirectPort"` → `{port, directPort}`, `"Balancer"` → `{port}`
- [x] 1.5 Enforce forbidden sub-fields for each exposure type using full dot-paths (`spec.exposure.<field>`) with `type: "forbidden"`
- [x] 1.6 Preserve `spec.exposure.annotations` map exactly as provided in output

## 2. Connection Details Computation

- [x] 2.1 Implement `compute_connection_details(name, exposure)` function that returns `{host, port, protocol: "https"}` based on exposure type
- [x] 2.2 Gateway mode: use `spec.exposure.hostname` if set, else fall back to mesh `name`; always set `port: 443`
- [x] 2.3 DirectPort mode: set `host` to mesh `name`; use `spec.exposure.directPort` if set, else use default port
- [x] 2.4 Balancer mode: set `host` to `"<name>-external"`; use `spec.exposure.port` if set, else use default port
- [x] 2.5 Inject `status.connectionDetails` into `create` and `describe` output when exposure is configured; omit otherwise

## 3. Management Endpoint

- [x] 3.1 Add `spec.management.enabled` field with default `false`
- [x] 3.2 Add immutability guard on update: compare new `spec.management.enabled` against stored value; emit `{"field":"spec.management.enabled","type":"immutable","message":"field 'spec.management.enabled' is immutable after creation"}` if changed
- [x] 3.3 Compute `status.managementConnectionDetails` as `{"host":"<name>-admin","port":9990,"protocol":"https"}` when `spec.management.enabled` is `true`
- [x] 3.4 Inject `status.managementConnectionDetails` into `create` and `describe` output when management is enabled; omit otherwise

## 4. mesh shell Command

- [x] 4.1 Add `shell` branch to the mesh sub-command router in `meshctl.py`
- [x] 4.2 Implement shell handler: look up mesh by name; emit `not_found` error if absent
- [x] 4.3 Reject meshes with no `spec.exposure`: emit `{"field":"spec.exposure","type":"invalid","message":"mesh '<name>' has no exposure configured"}`
- [x] 4.4 On success, output only the `connectionDetails` object (no resource envelope)

## 5. Error Sorting

- [x] 5.1 Ensure error array is sorted by `field` ascending, then `type` ascending for all error output paths (including new `immutable` type)
