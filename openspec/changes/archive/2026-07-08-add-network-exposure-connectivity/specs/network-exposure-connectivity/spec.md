## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud
> Extends: mesh-resource-management/add-mesh-lifecycle-topology
> Extends: one-shot-operations/add-one-shot-operations

### Requirement: Optional mesh exposure
The mesh resource SHALL accept optional `spec.exposure` configuration for externally reachable meshes.

#### Scenario: Exposure omitted
- **WHEN** a mesh is created without `spec.exposure`
- **THEN** no external access is configured
- **AND** `status.connectionDetails` is absent from create and describe output

#### Scenario: Exposure configured
- **WHEN** a mesh is created with `spec.exposure`
- **THEN** the mesh resource persists the exposure configuration
- **AND** create and describe output include `status.connectionDetails`

### Requirement: Exposure type validation
The mesh resource SHALL require `spec.exposure.type` when `spec.exposure` is present and SHALL only accept `Gateway`, `DirectPort`, and `Balancer` exposure types.

#### Scenario: Missing exposure type
- **WHEN** `spec.exposure` is present and `spec.exposure.type` is missing, null, or empty
- **THEN** validation fails with a JSON error whose `field` is `spec.exposure.type` and whose `type` is `required`

#### Scenario: Invalid exposure type
- **WHEN** `spec.exposure.type` is not `Gateway`, `DirectPort`, or `Balancer`
- **THEN** validation fails with a JSON error whose `field` is `spec.exposure.type` and whose `type` is `invalid`

### Requirement: Exposure mode fields
The mesh resource SHALL enforce exposure mode-specific fields: `Gateway` permits `hostname` and `annotations`; `DirectPort` permits `port` and `directPort`; `Balancer` permits `port`.

#### Scenario: Forbidden field rejected
- **WHEN** an exposure sub-field is provided for a mode that does not allow it
- **THEN** validation fails with a JSON error that uses the full dot-path of the forbidden field

#### Scenario: Gateway annotations preserved
- **WHEN** a `Gateway` exposure includes `annotations`
- **THEN** create and describe output preserve the annotations mapping as string keys to string values

### Requirement: Exposure connection details
The mesh resource SHALL compute `status.connectionDetails` with `host`, `port`, and `protocol` when exposure is configured.

#### Scenario: Gateway connection details
- **WHEN** `spec.exposure.type` is `Gateway`
- **THEN** `status.connectionDetails.host` is `spec.exposure.hostname` when set, otherwise a default host
- **AND** `status.connectionDetails.port` is `443`
- **AND** `status.connectionDetails.protocol` is `https`

#### Scenario: DirectPort connection details
- **WHEN** `spec.exposure.type` is `DirectPort`
- **THEN** `status.connectionDetails.host` is the mesh name
- **AND** `status.connectionDetails.port` is `spec.exposure.directPort` when set, otherwise the default direct port
- **AND** `status.connectionDetails.protocol` is `https`

#### Scenario: Balancer connection details
- **WHEN** `spec.exposure.type` is `Balancer`
- **THEN** `status.connectionDetails.host` is `<name>-external`
- **AND** `status.connectionDetails.port` is `spec.exposure.port` when set, otherwise the default exposure port
- **AND** `status.connectionDetails.protocol` is `https`

### Requirement: Mesh management endpoint
The mesh resource SHALL support `spec.management.enabled` as an optional boolean that defaults to `false` and is immutable after creation.

#### Scenario: Management disabled by default
- **WHEN** a mesh is created without `spec.management.enabled`
- **THEN** `spec.management.enabled` behaves as `false`
- **AND** `status.managementConnectionDetails` is absent

#### Scenario: Management connection details
- **WHEN** a mesh is created with `spec.management.enabled` set to `true`
- **THEN** `status.managementConnectionDetails.host` is `<name>-admin`
- **AND** `status.managementConnectionDetails.port` is `9990`
- **AND** `status.managementConnectionDetails.protocol` is `https`

#### Scenario: Management update rejected
- **WHEN** an update changes `spec.management.enabled` after creation
- **THEN** validation fails with a JSON error whose `field` is `spec.management.enabled`
- **AND** the error `type` is `immutable`
- **AND** the error `message` is `field 'spec.management.enabled' is immutable after creation`

### Requirement: Mesh shell command (adapts mesh-resource-management/add-meshctl-mesh-crud/mesh-cli-command-surface)
The mesh CLI command surface SHALL expose `mesh shell <name>` through `meshctl.py` to return connection details for an exposed mesh.

#### Scenario: Missing mesh
- **WHEN** `mesh shell <name>` is run for a mesh that does not exist
- **THEN** the command fails using the standard `not_found` JSON error shape

#### Scenario: Mesh without exposure rejected
- **WHEN** `mesh shell <name>` is run for a mesh with no exposure configured
- **THEN** the command fails with a JSON error whose `field` is `spec.exposure`
- **AND** the error `type` is `invalid`
- **AND** the error `message` is `mesh '<name>' has no exposure configured`

#### Scenario: Mesh shell output
- **WHEN** `mesh shell <name>` is run for an exposed mesh
- **THEN** the command outputs the `connectionDetails` object only
- **AND** the output does not include a resource envelope

### Requirement: Connectivity validation error ordering
The mesh exposure, management, and shell validation errors SHALL use the JSON error format and SHALL be sorted by `field`, then `type`.

#### Scenario: Multiple connectivity errors
- **WHEN** validation reports more than one exposure or management error
- **THEN** the JSON errors are ordered by `field`
- **AND** errors with the same `field` are ordered by `type`
