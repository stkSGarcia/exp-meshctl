## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud
> Extends: mesh-resource-management/add-mesh-lifecycle-topology

### Requirement: Mesh exposure configuration
The system SHALL support optional `spec.exposure` configuration for meshes, where omission configures no external access and suppresses `status.connectionDetails`.

#### Scenario: Exposure omitted
- **GIVEN** a mesh manifest without `spec.exposure`
- **WHEN** the mesh is created or described
- **THEN** no external access is configured
- **AND** `status.connectionDetails` is absent

#### Scenario: Exposure type required
- **GIVEN** a mesh manifest with `spec.exposure`
- **WHEN** `spec.exposure.type` is missing, null, or empty
- **THEN** validation returns an error with `field` equal to `spec.exposure.type`
- **AND** the error `type` is `required`

#### Scenario: Exposure type invalid
- **GIVEN** a mesh manifest with `spec.exposure.type`
- **WHEN** the type is not `Gateway`, `DirectPort`, or `Balancer`
- **THEN** validation returns an error with `field` equal to `spec.exposure.type`
- **AND** the error `type` is `invalid`

### Requirement: Exposure mode field validation
The system SHALL allow only the fields valid for the selected exposure mode and SHALL report forbidden sub-fields using the full dot-path.

#### Scenario: Gateway fields accepted
- **GIVEN** a mesh manifest with `spec.exposure.type` set to `Gateway`
- **WHEN** `spec.exposure.hostname` and `spec.exposure.annotations` are present
- **THEN** validation accepts those fields
- **AND** output preserves the `annotations` mapping

#### Scenario: DirectPort fields accepted
- **GIVEN** a mesh manifest with `spec.exposure.type` set to `DirectPort`
- **WHEN** `spec.exposure.port` or `spec.exposure.directPort` are present
- **THEN** validation accepts those fields

#### Scenario: Balancer fields accepted
- **GIVEN** a mesh manifest with `spec.exposure.type` set to `Balancer`
- **WHEN** `spec.exposure.port` is present
- **THEN** validation accepts that field

#### Scenario: Forbidden exposure field rejected
- **GIVEN** a mesh manifest with a sub-field not allowed for the selected exposure type
- **WHEN** validation runs
- **THEN** validation returns an error whose `field` is the full dot-path of the forbidden sub-field
- **AND** the error `type` is `forbidden`

### Requirement: Exposure connection details
The system SHALL include `status.connectionDetails` in `mesh create` and `mesh describe` output when exposure is configured, with `protocol` set to `https`.

#### Scenario: Gateway connection details
- **GIVEN** a mesh with `spec.exposure.type` set to `Gateway`
- **WHEN** the mesh is created or described
- **THEN** `status.connectionDetails.host` is `spec.exposure.hostname` when provided, otherwise the default host
- **AND** `status.connectionDetails.port` is `443`
- **AND** `status.connectionDetails.protocol` is `https`

#### Scenario: DirectPort connection details
- **GIVEN** a mesh with `spec.exposure.type` set to `DirectPort`
- **WHEN** the mesh is created or described
- **THEN** `status.connectionDetails.host` is the mesh name
- **AND** `status.connectionDetails.port` is `spec.exposure.directPort` when provided, otherwise the default port
- **AND** `status.connectionDetails.protocol` is `https`

#### Scenario: Balancer connection details
- **GIVEN** a mesh with `spec.exposure.type` set to `Balancer`
- **WHEN** the mesh is created or described
- **THEN** `status.connectionDetails.host` is `<name>-external`
- **AND** `status.connectionDetails.port` is `spec.exposure.port` when provided, otherwise the default port
- **AND** `status.connectionDetails.protocol` is `https`

### Requirement: Management endpoint details
The system SHALL support `spec.management.enabled` for meshes, default it to `false`, treat it as immutable after creation, and include `status.managementConnectionDetails` when enabled.

#### Scenario: Management disabled by default
- **GIVEN** a mesh manifest without `spec.management.enabled`
- **WHEN** the mesh is created
- **THEN** `spec.management.enabled` defaults to `false`
- **AND** `status.managementConnectionDetails` is absent

#### Scenario: Management details emitted
- **GIVEN** a mesh manifest with `spec.management.enabled` set to `true`
- **WHEN** the mesh is created or described
- **THEN** `status.managementConnectionDetails.host` is `<name>-admin`
- **AND** `status.managementConnectionDetails.port` is `9990`
- **AND** `status.managementConnectionDetails.protocol` is `https`

#### Scenario: Management enabled immutable
- **GIVEN** an existing mesh
- **WHEN** `mesh update -f <path>` changes `spec.management.enabled`
- **THEN** validation returns an error with `field` equal to `spec.management.enabled`
- **AND** the error `type` is `immutable`
- **AND** the error `message` is `field 'spec.management.enabled' is immutable after creation`
