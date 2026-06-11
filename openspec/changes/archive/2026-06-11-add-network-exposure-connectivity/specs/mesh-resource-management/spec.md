## ADDED Requirements

### Requirement: Mesh exposure configuration
The system SHALL support optional `spec.exposure` configuration for external mesh access.

#### Scenario: Omitted exposure configures no external access
- **WHEN** a valid mesh create input omits `spec.exposure`
- **THEN** the returned and persisted resource SHALL omit `spec.exposure` and SHALL omit `status.connectionDetails`.

#### Scenario: Exposure type is required
- **WHEN** `spec.exposure` is present and `spec.exposure.type` is missing, null, or an empty string
- **THEN** the system SHALL report field `spec.exposure.type` with type `required`.

#### Scenario: Exposure type validates allowed values
- **WHEN** `spec.exposure.type` is present and is not `"Gateway"`, `"DirectPort"`, or `"Balancer"`
- **THEN** the system SHALL report field `spec.exposure.type` with type `invalid`.

#### Scenario: Gateway exposure preserves hostname and annotations
- **WHEN** a valid mesh uses `spec.exposure.type` equal to `"Gateway"` with `hostname` and `annotations`
- **THEN** the returned and persisted resource SHALL preserve `spec.exposure.hostname` and the `spec.exposure.annotations` string mapping.

#### Scenario: Gateway exposure forbids port fields
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.port` or `spec.exposure.directPort` is present
- **THEN** the system SHALL report each provided forbidden field using its full dot path and type `forbidden`.

#### Scenario: DirectPort exposure accepts port fields
- **WHEN** a valid mesh uses `spec.exposure.type` equal to `"DirectPort"` with `port` or `directPort`
- **THEN** the returned and persisted resource SHALL preserve the provided integer port fields.

#### Scenario: DirectPort exposure forbids gateway fields
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.hostname` or `spec.exposure.annotations` is present
- **THEN** the system SHALL report each provided forbidden field using its full dot path and type `forbidden`.

#### Scenario: Balancer exposure accepts service port
- **WHEN** a valid mesh uses `spec.exposure.type` equal to `"Balancer"` with `port`
- **THEN** the returned and persisted resource SHALL preserve `spec.exposure.port`.

#### Scenario: Balancer exposure forbids gateway and direct port fields
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.hostname`, `spec.exposure.annotations`, or `spec.exposure.directPort` is present
- **THEN** the system SHALL report each provided forbidden field using its full dot path and type `forbidden`.

#### Scenario: Exposure scalar field validation
- **WHEN** `spec.exposure.hostname` is present and is not a string, `spec.exposure.port` is present and is not an integer, or `spec.exposure.directPort` is present and is not an integer
- **THEN** the system SHALL report each invalid field with type `invalid`.

#### Scenario: Exposure annotations validation
- **WHEN** `spec.exposure.annotations` is present and is not a map from string keys to string values
- **THEN** the system SHALL report field `spec.exposure.annotations` with type `invalid`.

### Requirement: Mesh connection details
The system SHALL compute `status.connectionDetails` for exposed meshes in successful create and describe output.

#### Scenario: Gateway connection details
- **WHEN** a mesh has `spec.exposure.type` equal to `"Gateway"`
- **THEN** `status.connectionDetails` SHALL contain `host` equal to `spec.exposure.hostname` when set or a default host when omitted, `port` equal to `443`, and `protocol` equal to `"https"`.

#### Scenario: DirectPort connection details
- **WHEN** a mesh named `<name>` has `spec.exposure.type` equal to `"DirectPort"`
- **THEN** `status.connectionDetails` SHALL contain `host` equal to `<name>`, `port` equal to `spec.exposure.directPort` when set or the default direct port when omitted, and `protocol` equal to `"https"`.

#### Scenario: Balancer connection details
- **WHEN** a mesh named `<name>` has `spec.exposure.type` equal to `"Balancer"`
- **THEN** `status.connectionDetails` SHALL contain `host` equal to `<name>-external`, `port` equal to `spec.exposure.port` when set or the default balancer port when omitted, and `protocol` equal to `"https"`.

#### Scenario: Connection details are absent without exposure
- **WHEN** a mesh omits `spec.exposure`
- **THEN** create and describe output SHALL omit `status.connectionDetails`.

### Requirement: Mesh management endpoint
The system SHALL support `spec.management.enabled` as a boolean management endpoint toggle with a default of `false`.

#### Scenario: Management defaults to disabled
- **WHEN** a valid create input omits `spec.management.enabled`
- **THEN** the returned and persisted resource SHALL include `spec.management.enabled` as `false` and SHALL omit `status.managementConnectionDetails`.

#### Scenario: Management enabled emits connection details
- **WHEN** a mesh named `<name>` has `spec.management.enabled` equal to `true`
- **THEN** create and describe output SHALL include `status.managementConnectionDetails` with `host` equal to `<name>-admin`, `port` equal to `9990`, and `protocol` equal to `"https"`.

#### Scenario: Management enabled validates as boolean
- **WHEN** `spec.management.enabled` is present and is not a boolean
- **THEN** the system SHALL report field `spec.management.enabled` with type `invalid`.

#### Scenario: Management enabled is immutable after create
- **WHEN** an update changes the stored `spec.management.enabled`
- **THEN** the system SHALL report field `spec.management.enabled` with type `immutable`, message `field 'spec.management.enabled' is immutable after creation`, and SHALL NOT persist the update.

### Requirement: Mesh shell command
The system SHALL expose `mesh shell <name>` to return connection details for an exposed mesh.

#### Scenario: Shell returns connection details object
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell <name>` for a mesh with exposure configured
- **THEN** the system SHALL print only the mesh `status.connectionDetails` object without a resource envelope.

#### Scenario: Shell missing mesh
- **WHEN** the user runs `mesh shell <name>` for a mesh that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found` using the standard not-found shape.

#### Scenario: Shell rejects mesh without exposure
- **WHEN** the user runs `mesh shell <name>` for a mesh with no `spec.exposure`
- **THEN** the system SHALL report field `spec.exposure` with type `invalid` and message `mesh '<name>' has no exposure configured`.

## MODIFIED Requirements

### Requirement: Mesh CLI command surface
The system SHALL expose `mesh create`, `mesh list`, `mesh describe`, `mesh delete`, `mesh update`, `mesh migrate`, and `mesh shell` operations through `meshctl.py`.

#### Scenario: Create command accepts a YAML file
- **WHEN** the user runs `uv run --project /app meshctl.py mesh create -f <path>`
- **THEN** the system SHALL read `<path>` as the mesh YAML input and attempt to create the resource.

#### Scenario: List command returns existing mesh summaries
- **WHEN** the user runs `uv run --project /app meshctl.py mesh list`
- **THEN** the system SHALL print a JSON array of mesh summaries.

#### Scenario: Describe command returns a named mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh describe <name>`
- **THEN** the system SHALL print the full persisted mesh resource for `<name>`.

#### Scenario: Delete command removes a named mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh delete <name>`
- **THEN** the system SHALL remove the mesh and print a JSON confirmation object.

#### Scenario: Update command applies a partial mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh update -f <path>`
- **THEN** the system SHALL read `<path>` as a partial mesh YAML input and attempt to update the named resource.

#### Scenario: Migrate command advances a mesh migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>`
- **THEN** the system SHALL attempt to advance or complete the named mesh migration.

#### Scenario: Shell command returns mesh connection details
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell <name>`
- **THEN** the system SHALL attempt to return the named mesh connection details.

### Requirement: Mesh duplicate and not-found handling
The system SHALL reject duplicate create requests and missing named resources using structured JSON errors.

#### Scenario: Duplicate mesh name on create
- **WHEN** a create request uses a `metadata.name` that already exists
- **THEN** the system SHALL report field `metadata.name` with type `duplicate` and SHALL NOT overwrite the existing resource.

#### Scenario: Missing mesh on describe
- **WHEN** the user describes a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing mesh on delete
- **WHEN** the user deletes a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing mesh on update
- **WHEN** the user updates a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing mesh on migrate
- **WHEN** the user migrates a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing mesh on shell
- **WHEN** the user shells into a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

### Requirement: Mesh defaulting
The system SHALL apply documented defaults to successful create output and persisted resources while leaving fields without defaults absent when omitted.

#### Scenario: Defaults applied to omitted fields
- **WHEN** a valid create input omits `spec.instances`, `spec.resources.memory`, `spec.access`, `spec.migration.strategy`, `spec.network.storage.size`, `spec.network.storage.ephemeral`, `spec.network.replicationFactor`, and `spec.management.enabled`
- **THEN** the created resource SHALL include `spec.instances` as `1`, `spec.resources.memory` as `{"limit": "1Gi", "request": "1Gi"}`, `spec.access.authentication.enabled` as `true`, `spec.access.authentication.digestAlgorithm` as `"SHA-256"`, `spec.access.encryption.source` as `"None"`, `spec.access.encryption.clientMode` as `"None"`, `spec.access.permissions.enabled` as `false`, `spec.migration.strategy` as `"FullStop"`, `spec.network.storage.size` as `"1Gi"`, `spec.network.storage.ephemeral` as `false`, a computed `spec.network.replicationFactor`, and `spec.management.enabled` as `false`.

#### Scenario: Fields without defaults remain absent
- **WHEN** a valid create input omits `spec.runtime`, `spec.resources.cpu`, `spec.network.storage.className`, `spec.exposure`, or any other field without a documented default
- **THEN** the created resource SHALL omit those fields from the returned and persisted resource.
