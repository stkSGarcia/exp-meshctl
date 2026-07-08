## ADDED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology

### Requirement: Optional mesh exposure
The system SHALL treat `spec.exposure` as optional and SHALL configure no external access when the field is omitted.

#### Scenario: Exposure omitted
- **WHEN** a mesh is created without `spec.exposure`
- **THEN** no external access is configured
- **AND** `status.connectionDetails` is absent from create and describe output

### Requirement: Exposure type validation
The system SHALL require `spec.exposure.type` when `spec.exposure` is present and SHALL reject missing, null, empty, or invalid exposure types using the JSON error format.

#### Scenario: Exposure type missing
- **WHEN** a mesh includes `spec.exposure` without a non-empty `spec.exposure.type`
- **THEN** validation fails with `field = "spec.exposure.type"`
- **AND** validation fails with `type = "required"`

#### Scenario: Exposure type invalid
- **WHEN** a mesh includes `spec.exposure.type` with a value other than `"Gateway"`, `"DirectPort"`, or `"Balancer"`
- **THEN** validation fails with `field = "spec.exposure.type"`
- **AND** validation fails with `type = "invalid"`

### Requirement: Exposure mode field constraints
The system SHALL allow only the exposure sub-fields permitted for the selected exposure type and SHALL report forbidden sub-fields by full dot-path.

#### Scenario: Gateway fields
- **WHEN** `spec.exposure.type` is `"Gateway"`
- **THEN** `spec.exposure.hostname` and `spec.exposure.annotations` are allowed
- **AND** any other `spec.exposure` sub-field is rejected as forbidden using its full dot-path

#### Scenario: DirectPort fields
- **WHEN** `spec.exposure.type` is `"DirectPort"`
- **THEN** `spec.exposure.port` and `spec.exposure.directPort` are allowed
- **AND** any other `spec.exposure` sub-field is rejected as forbidden using its full dot-path

#### Scenario: Balancer fields
- **WHEN** `spec.exposure.type` is `"Balancer"`
- **THEN** `spec.exposure.port` is allowed
- **AND** any other `spec.exposure` sub-field is rejected as forbidden using its full dot-path

### Requirement: Exposure field typing and defaults
The system SHALL validate exposure field types, preserve Gateway annotations, and apply defaults for optional exposure ports when omitted.

#### Scenario: Gateway annotations preserved
- **WHEN** a Gateway exposure includes `spec.exposure.annotations`
- **THEN** the annotations mapping is preserved in resource output

#### Scenario: DirectPort defaults
- **WHEN** a DirectPort exposure omits `spec.exposure.port` or `spec.exposure.directPort`
- **THEN** the omitted port value uses the configured default for that field

#### Scenario: Balancer port default
- **WHEN** a Balancer exposure omits `spec.exposure.port`
- **THEN** `spec.exposure.port` uses the configured default

### Requirement: Connection details status
The system SHALL include `status.connectionDetails` in `mesh create` and `mesh describe` output when exposure is configured.

#### Scenario: Gateway connection details
- **WHEN** a mesh uses Gateway exposure
- **THEN** `status.connectionDetails.host` is `spec.exposure.hostname` when provided, otherwise the default Gateway host
- **AND** `status.connectionDetails.port` is `443`
- **AND** `status.connectionDetails.protocol` is `"https"`

#### Scenario: DirectPort connection details
- **WHEN** a mesh uses DirectPort exposure
- **THEN** `status.connectionDetails.host` is the mesh name
- **AND** `status.connectionDetails.port` is `spec.exposure.directPort` when provided, otherwise the default DirectPort value
- **AND** `status.connectionDetails.protocol` is `"https"`

#### Scenario: Balancer connection details
- **WHEN** a mesh uses Balancer exposure
- **THEN** `status.connectionDetails.host` is `"<name>-external"`
- **AND** `status.connectionDetails.port` is `spec.exposure.port` when provided, otherwise the default Balancer port
- **AND** `status.connectionDetails.protocol` is `"https"`

### Requirement: Management endpoint status
The system SHALL default `spec.management.enabled` to `false` and SHALL include `status.managementConnectionDetails` when management access is enabled.

#### Scenario: Management disabled by default
- **WHEN** a mesh is created without `spec.management.enabled`
- **THEN** `spec.management.enabled` defaults to `false`
- **AND** `status.managementConnectionDetails` is absent

#### Scenario: Management enabled
- **WHEN** a mesh is created with `spec.management.enabled` set to `true`
- **THEN** `status.managementConnectionDetails.host` is `"<name>-admin"`
- **AND** `status.managementConnectionDetails.port` is `9990`
- **AND** `status.managementConnectionDetails.protocol` is `"https"`

### Requirement: Management endpoint immutability
The system SHALL reject updates that change `spec.management.enabled` after mesh creation.

#### Scenario: Management flag changed after create
- **WHEN** `mesh update -f <path>` changes `spec.management.enabled` after creation
- **THEN** validation fails with `field = "spec.management.enabled"`
- **AND** validation fails with `type = "immutable"`
- **AND** validation fails with `message = "field 'spec.management.enabled' is immutable after creation"`

### Requirement: Connectivity error ordering
The system SHALL sort connectivity validation errors by `field`, then `type`.

#### Scenario: Multiple connectivity errors
- **WHEN** validation produces multiple exposure or management errors
- **THEN** the JSON error list is sorted first by `field` and then by `type`
