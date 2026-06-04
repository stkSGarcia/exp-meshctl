## MODIFIED Requirements

> Extends: spec:mesh-management

### Requirement: YAML input schema
**Updated:** The system SHALL accept `spec.exposure` (optional) and `spec.management` (optional) as recognized top-level keys under `spec`. All existing fields remain unchanged.

#### Scenario: Exposure and management fields accepted
- **WHEN** the input YAML includes `spec.exposure` and `spec.management`
- **THEN** they are parsed and validated without a parse error

---

### Requirement: Success output — create and describe
**Updated:** The full resource JSON for create and describe SHALL include `status.connectionDetails` when `spec.exposure` is configured, and `status.managementConnectionDetails` when `spec.management.enabled` is `true`. Both fields are absent when not applicable.

(adapts mesh-management/success-output-create-and-describe)

#### Scenario: Create with exposure includes connectionDetails
- **WHEN** a mesh is created with a valid `spec.exposure` block
- **THEN** the response JSON includes `status.connectionDetails`

#### Scenario: Create without exposure omits connectionDetails
- **WHEN** a mesh is created without `spec.exposure`
- **THEN** `status.connectionDetails` is absent from the response
