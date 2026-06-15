## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud

### Requirement: Optional exposure configuration
The system SHALL accept optional `spec.exposure` configuration for mesh resources and SHALL configure no external access when `spec.exposure` is omitted.

#### Scenario: Mesh created without exposure
- **GIVEN** a valid mesh manifest without `spec.exposure`
- **WHEN** the mesh is created
- **THEN** the output SHALL omit `status.connectionDetails`

#### Scenario: Mesh described without exposure
- **GIVEN** an existing mesh without `spec.exposure`
- **WHEN** the mesh is described
- **THEN** the output SHALL omit `status.connectionDetails`

### Requirement: Exposure mode validation
The system SHALL require `spec.exposure.type` when `spec.exposure` is present, SHALL allow only `Gateway`, `DirectPort`, and `Balancer`, and SHALL reject fields that are not valid for the selected exposure mode.

#### Scenario: Missing exposure type
- **GIVEN** a mesh manifest with `spec.exposure` present
- **WHEN** `spec.exposure.type` is missing, null, or empty
- **THEN** the system SHALL return an error with `field` set to `spec.exposure.type` and `type` set to `required`

#### Scenario: Invalid exposure type
- **GIVEN** a mesh manifest with `spec.exposure.type` set to an unsupported value
- **WHEN** the mesh is created or updated
- **THEN** the system SHALL return an error with `field` set to `spec.exposure.type` and `type` set to `invalid`

#### Scenario: Forbidden exposure field
- **GIVEN** a mesh manifest with an exposure field that is not allowed for the selected mode
- **WHEN** the mesh is created or updated
- **THEN** the system SHALL return a forbidden-field error using the full dot-path for the disallowed field

### Requirement: Exposure field rules
The system SHALL enforce mode-specific exposure fields: `Gateway` permits `hostname` and `annotations`; `DirectPort` permits `port` and `directPort`; and `Balancer` permits `port`.

#### Scenario: Gateway exposure fields
- **GIVEN** a mesh manifest with `spec.exposure.type` set to `Gateway`
- **WHEN** `hostname` and `annotations` are provided
- **THEN** the system SHALL preserve the `annotations` string mapping in create and describe output

#### Scenario: DirectPort exposure fields
- **GIVEN** a mesh manifest with `spec.exposure.type` set to `DirectPort`
- **WHEN** `port` or `directPort` are provided
- **THEN** the system SHALL include the accepted exposure fields in create and describe output

#### Scenario: Balancer exposure fields
- **GIVEN** a mesh manifest with `spec.exposure.type` set to `Balancer`
- **WHEN** `port` is provided
- **THEN** the system SHALL include the accepted exposure field in create and describe output

> Extends: mesh-resource-management/add-access-security-model

### Requirement: Connection details output
The system SHALL include `status.connectionDetails` in successful mesh create and describe output when exposure is configured, and SHALL omit it when exposure is absent. (adapts mesh-resource-management/add-access-security-model/mesh-access-output)

#### Scenario: Gateway connection details
- **GIVEN** a mesh with `spec.exposure.type` set to `Gateway`
- **WHEN** the mesh is created or described
- **THEN** `status.connectionDetails` SHALL contain `host` set to `spec.exposure.hostname` when provided or to a default otherwise, `port` set to `443`, and `protocol` set to `https`

#### Scenario: DirectPort connection details
- **GIVEN** a mesh with `spec.exposure.type` set to `DirectPort`
- **WHEN** the mesh is created or described
- **THEN** `status.connectionDetails` SHALL contain `host` set to the mesh name, `port` set to `spec.exposure.directPort` when provided or to a default otherwise, and `protocol` set to `https`

#### Scenario: Balancer connection details
- **GIVEN** a mesh with `spec.exposure.type` set to `Balancer`
- **WHEN** the mesh is created or described
- **THEN** `status.connectionDetails` SHALL contain `host` set to `<name>-external`, `port` set to `spec.exposure.port` when provided or to a default otherwise, and `protocol` set to `https`

> Extends: mesh-resource-management/add-mesh-lifecycle-topology

### Requirement: Management endpoint
The system SHALL default `spec.management.enabled` to `false`, SHALL treat `spec.management.enabled` as immutable after creation, and SHALL include `status.managementConnectionDetails` when management is enabled. (adapts mesh-resource-management/add-mesh-lifecycle-topology/successful-mesh-output)

#### Scenario: Management endpoint disabled by default
- **GIVEN** a valid mesh manifest without `spec.management.enabled`
- **WHEN** the mesh is created
- **THEN** the output SHALL include `spec.management.enabled` as `false`
- **AND** the output SHALL omit `status.managementConnectionDetails`

#### Scenario: Management endpoint enabled
- **GIVEN** a mesh manifest with `spec.management.enabled` set to `true`
- **WHEN** the mesh is created or described
- **THEN** `status.managementConnectionDetails` SHALL contain `host` set to `<name>-admin`, `port` set to `9990`, and `protocol` set to `https`

#### Scenario: Management endpoint update rejected
- **GIVEN** an existing mesh
- **WHEN** an update changes `spec.management.enabled`
- **THEN** the system SHALL return an error with `field` set to `spec.management.enabled`, `type` set to `immutable`, and `message` set to `field 'spec.management.enabled' is immutable after creation`

### Requirement: Mesh shell command
The system SHALL expose `mesh shell <name>` and SHALL print only the target mesh `status.connectionDetails` object when the mesh has exposure configured.

#### Scenario: Shell returns connection details
- **GIVEN** an existing mesh with exposure configured
- **WHEN** `meshctl.py mesh shell <name>` is run
- **THEN** stdout SHALL contain only the connection details object without a resource envelope
- **AND** stderr SHALL be empty

#### Scenario: Shell missing mesh
- **GIVEN** no mesh exists with the requested name
- **WHEN** `meshctl.py mesh shell <name>` is run
- **THEN** the system SHALL return the standard `not_found` error shape

#### Scenario: Shell rejects unexposed mesh
- **GIVEN** an existing mesh without exposure configured
- **WHEN** `meshctl.py mesh shell <name>` is run
- **THEN** the system SHALL return an error with `field` set to `spec.exposure`, `type` set to `invalid`, and `message` set to `mesh '<name>' has no exposure configured`

### Requirement: Exposure error output
The system SHALL use the JSON error format for exposure, management, and shell validation failures and SHALL sort errors by `field`, then by `type`.

#### Scenario: Multiple exposure validation errors
- **GIVEN** a mesh manifest with multiple invalid exposure fields
- **WHEN** the mesh is created or updated
- **THEN** the JSON error output SHALL list the errors sorted by `field`, then by `type`
