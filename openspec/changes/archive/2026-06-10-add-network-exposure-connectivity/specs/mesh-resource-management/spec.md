## ADDED Requirements

### Requirement: Mesh exposure
The system SHALL support optional `spec.exposure` configuration with mode-specific fields for external mesh access.

#### Scenario: Omitted exposure configures no external access
- **WHEN** a valid mesh create input omits `spec.exposure`
- **THEN** the returned and persisted mesh SHALL omit `spec.exposure` and SHALL omit `status.connectionDetails`.

#### Scenario: Exposure type is required when exposure is present
- **WHEN** `spec.exposure` is present and `spec.exposure.type` is missing, null, or an empty string
- **THEN** the system SHALL report field `spec.exposure.type` with type `required`.

#### Scenario: Exposure type validates allowed values
- **WHEN** `spec.exposure.type` is present and is not `"Gateway"`, `"DirectPort"`, or `"Balancer"`
- **THEN** the system SHALL report field `spec.exposure.type` with type `invalid`.

#### Scenario: Gateway exposure allows gateway fields
- **WHEN** a valid mesh input sets `spec.exposure.type` to `"Gateway"` and includes `spec.exposure.hostname` or `spec.exposure.annotations`
- **THEN** the returned and persisted mesh SHALL preserve those provided exposure fields.

#### Scenario: Gateway exposure forbids non-gateway fields
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.port` or `spec.exposure.directPort` is present
- **THEN** the system SHALL report each provided forbidden field with type `forbidden` using the full dot-path.

#### Scenario: DirectPort exposure allows port fields
- **WHEN** a valid mesh input sets `spec.exposure.type` to `"DirectPort"` and includes `spec.exposure.port` or `spec.exposure.directPort`
- **THEN** the returned and persisted mesh SHALL preserve those provided exposure fields.

#### Scenario: DirectPort exposure forbids gateway fields
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.hostname` or `spec.exposure.annotations` is present
- **THEN** the system SHALL report each provided forbidden field with type `forbidden` using the full dot-path.

#### Scenario: Balancer exposure allows port field
- **WHEN** a valid mesh input sets `spec.exposure.type` to `"Balancer"` and includes `spec.exposure.port`
- **THEN** the returned and persisted mesh SHALL preserve the provided exposure field.

#### Scenario: Balancer exposure forbids gateway and direct-port fields
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.hostname`, `spec.exposure.annotations`, or `spec.exposure.directPort` is present
- **THEN** the system SHALL report each provided forbidden field with type `forbidden` using the full dot-path.

#### Scenario: Exposure annotations mapping is preserved
- **WHEN** a valid Gateway mesh input includes `spec.exposure.annotations` as a mapping of string keys to string values
- **THEN** the returned and persisted mesh SHALL include the same annotations mapping.

### Requirement: Mesh connection details
The system SHALL include computed `status.connectionDetails` in create and describe output whenever `spec.exposure` is configured.

#### Scenario: Gateway connection details use configured hostname
- **WHEN** a mesh with `metadata.name` `alpha` has `spec.exposure.type` equal to `"Gateway"` and `spec.exposure.hostname` equal to `"alpha.example.test"`
- **THEN** create and describe output SHALL include `status.connectionDetails` as `{"host": "alpha.example.test", "port": 443, "protocol": "https"}`.

#### Scenario: Gateway connection details use default hostname
- **WHEN** a mesh with `metadata.name` `alpha` has `spec.exposure.type` equal to `"Gateway"` and omits `spec.exposure.hostname`
- **THEN** create and describe output SHALL include `status.connectionDetails` with host set to a default value, port `443`, and protocol `"https"`.

#### Scenario: DirectPort connection details use direct port
- **WHEN** a mesh with `metadata.name` `alpha` has `spec.exposure.type` equal to `"DirectPort"` and `spec.exposure.directPort` equal to `30443`
- **THEN** create and describe output SHALL include `status.connectionDetails` as `{"host": "alpha", "port": 30443, "protocol": "https"}`.

#### Scenario: DirectPort connection details use default direct port
- **WHEN** a mesh with `metadata.name` `alpha` has `spec.exposure.type` equal to `"DirectPort"` and omits `spec.exposure.directPort`
- **THEN** create and describe output SHALL include `status.connectionDetails` with host `"alpha"`, a default port, and protocol `"https"`.

#### Scenario: Balancer connection details use port
- **WHEN** a mesh with `metadata.name` `alpha` has `spec.exposure.type` equal to `"Balancer"` and `spec.exposure.port` equal to `8443`
- **THEN** create and describe output SHALL include `status.connectionDetails` as `{"host": "alpha-external", "port": 8443, "protocol": "https"}`.

#### Scenario: Balancer connection details use default port
- **WHEN** a mesh with `metadata.name` `alpha` has `spec.exposure.type` equal to `"Balancer"` and omits `spec.exposure.port`
- **THEN** create and describe output SHALL include `status.connectionDetails` with host `"alpha-external"`, a default port, and protocol `"https"`.

### Requirement: Mesh management endpoint
The system SHALL support `spec.management.enabled` with a default of `false`, immutable update behavior, and computed management connection details when enabled.

#### Scenario: Management defaults to disabled
- **WHEN** a valid mesh create input omits `spec.management.enabled`
- **THEN** the returned and persisted mesh SHALL include `spec.management.enabled` as `false` and SHALL omit `status.managementConnectionDetails`.

#### Scenario: Enabled management outputs connection details
- **WHEN** a valid mesh with `metadata.name` `alpha` has `spec.management.enabled` equal to `true`
- **THEN** create and describe output SHALL include `status.managementConnectionDetails` as `{"host": "alpha-admin", "port": 9990, "protocol": "https"}`.

#### Scenario: Disabled management omits connection details
- **WHEN** a returned mesh has `spec.management.enabled` equal to `false`
- **THEN** the output SHALL omit `status.managementConnectionDetails`.

#### Scenario: Management enabled is immutable
- **WHEN** an update changes the stored `spec.management.enabled` value
- **THEN** the system SHALL report field `spec.management.enabled` with type `immutable` and message `field 'spec.management.enabled' is immutable after creation`.

### Requirement: Mesh shell operation
The system SHALL expose `mesh shell <name>` to return only the exposed mesh connection details.

#### Scenario: Shell returns connection details object
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell alpha` for a mesh with exposure configured
- **THEN** the system SHALL print the `status.connectionDetails` object as JSON without a resource envelope.

#### Scenario: Shell missing mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell alpha` and no mesh named `alpha` exists
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Shell rejects mesh without exposure
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell alpha` for a mesh without `spec.exposure`
- **THEN** the system SHALL report field `spec.exposure` with type `invalid` and message `mesh 'alpha' has no exposure configured`.

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

#### Scenario: Migrate command advances migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>`
- **THEN** the system SHALL attempt to advance the active migration for the named mesh.

#### Scenario: Shell command returns connection details
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell <name>`
- **THEN** the system SHALL attempt to return the connection details for the named mesh.
