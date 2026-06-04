# mesh-management-endpoint Specification

## Purpose
TBD - created by archiving change network-exposure-connectivity. Update Purpose after archive.
## Requirements
### Requirement: Management enabled field
`spec.management.enabled` SHALL be a boolean with default `false`. It controls whether a management endpoint is exposed.

#### Scenario: Management disabled by default
- **WHEN** a mesh is created without `spec.management`
- **THEN** `spec.management.enabled` defaults to `false` and `status.managementConnectionDetails` is absent

---

### Requirement: Management enabled is immutable after create
Once set, `spec.management.enabled` SHALL NOT be changed on update. Attempting to change it SHALL produce an error.

- `field = "spec.management.enabled"`
- `type = "immutable"`
- `message = "field 'spec.management.enabled' is immutable after creation"`

(adapts mesh-management/immutable-field-error-type)

#### Scenario: Attempt to change management enabled
- **WHEN** an update sets `spec.management.enabled` to a different value than stored
- **THEN** output an error with `field = "spec.management.enabled"`, `type = "immutable"`, and `message = "field 'spec.management.enabled' is immutable after creation"`

---

### Requirement: Management connection details when enabled
When `spec.management.enabled` is `true`, `create` and `describe` SHALL include `status.managementConnectionDetails`:

```json
{
  "host": "<name>-admin",
  "port": 9990,
  "protocol": "https"
}
```

Where `<name>` is the mesh name.

#### Scenario: Management connection details present when enabled
- **WHEN** a mesh has `spec.management.enabled: true`
- **THEN** the create and describe responses include `status.managementConnectionDetails` with `host = "<name>-admin"`, `port = 9990`, and `protocol = "https"`

#### Scenario: Management connection details absent when disabled
- **WHEN** a mesh has `spec.management.enabled: false` or absent
- **THEN** the response does not include `status.managementConnectionDetails`

