## ADDED Requirements

### Requirement: Mesh exposure configuration
The system SHALL support optional mesh exposure configuration under `spec.exposure`.

#### Scenario: Exposure may be omitted
- **WHEN** a valid mesh create input omits `spec.exposure`
- **THEN** the created resource SHALL omit `spec.exposure` and SHALL omit `status.connectionDetails`.

#### Scenario: Exposure type is required when exposure is present
- **WHEN** `spec.exposure` is present and `spec.exposure.type` is missing, null, or an empty string
- **THEN** the system SHALL report field `spec.exposure.type` with type `required`.

#### Scenario: Exposure type validates allowed values
- **WHEN** `spec.exposure.type` is present and is not `"Gateway"`, `"DirectPort"`, or `"Balancer"`
- **THEN** the system SHALL report field `spec.exposure.type` with type `invalid`.

#### Scenario: Gateway exposure preserves allowed fields
- **WHEN** a valid mesh create input uses `spec.exposure.type` equal to `"Gateway"` with `hostname` and `annotations`
- **THEN** the created resource SHALL preserve `spec.exposure.hostname` and the full `spec.exposure.annotations` mapping.

#### Scenario: DirectPort exposure preserves allowed fields
- **WHEN** a valid mesh create input uses `spec.exposure.type` equal to `"DirectPort"` with `port` and `directPort`
- **THEN** the created resource SHALL preserve `spec.exposure.port` and `spec.exposure.directPort`.

#### Scenario: Balancer exposure preserves allowed fields
- **WHEN** a valid mesh create input uses `spec.exposure.type` equal to `"Balancer"` with `port`
- **THEN** the created resource SHALL preserve `spec.exposure.port`.

#### Scenario: Gateway exposure forbids non-gateway fields
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.port` or `spec.exposure.directPort` is present
- **THEN** the system SHALL report each provided forbidden field using its full dot-path with type `forbidden`.

#### Scenario: DirectPort exposure forbids non-direct fields
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.hostname` or `spec.exposure.annotations` is present
- **THEN** the system SHALL report each provided forbidden field using its full dot-path with type `forbidden`.

#### Scenario: Balancer exposure forbids non-balancer fields
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.hostname`, `spec.exposure.annotations`, or `spec.exposure.directPort` is present
- **THEN** the system SHALL report each provided forbidden field using its full dot-path with type `forbidden`.

### Requirement: Mesh exposure connection details
The system SHALL include computed `status.connectionDetails` in create and describe output when `spec.exposure` is configured.

#### Scenario: Gateway connection details use hostname or default
- **WHEN** a mesh has `spec.exposure.type` equal to `"Gateway"`
- **THEN** `status.connectionDetails` SHALL contain `host` equal to `spec.exposure.hostname` when set or a default host when omitted, `port` equal to `443`, and `protocol` equal to `"https"`.

#### Scenario: DirectPort connection details use mesh name and direct port
- **WHEN** a mesh named `<name>` has `spec.exposure.type` equal to `"DirectPort"`
- **THEN** `status.connectionDetails` SHALL contain `host` equal to `<name>`, `port` equal to `spec.exposure.directPort` when set or a default port when omitted, and `protocol` equal to `"https"`.

#### Scenario: Balancer connection details use external host and port
- **WHEN** a mesh named `<name>` has `spec.exposure.type` equal to `"Balancer"`
- **THEN** `status.connectionDetails` SHALL contain `host` equal to `<name>-external`, `port` equal to `spec.exposure.port` when set or a default port when omitted, and `protocol` equal to `"https"`.

#### Scenario: Connection details omitted without exposure
- **WHEN** a mesh has no `spec.exposure`
- **THEN** create and describe output SHALL omit `status.connectionDetails`.

### Requirement: Mesh management endpoint
The system SHALL support `spec.management.enabled` as a boolean create-time setting that controls management connection details.

#### Scenario: Management defaults to disabled
- **WHEN** a valid mesh create input omits `spec.management.enabled`
- **THEN** the created resource SHALL include `spec.management.enabled` as `false` and SHALL omit `status.managementConnectionDetails`.

#### Scenario: Enabled management outputs management connection details
- **WHEN** a mesh named `<name>` has `spec.management.enabled` equal to `true`
- **THEN** create and describe output SHALL include `status.managementConnectionDetails` with `host` equal to `<name>-admin`, `port` equal to `9990`, and `protocol` equal to `"https"`.

#### Scenario: Management enabled validates boolean values
- **WHEN** `spec.management.enabled` is present and is not a boolean
- **THEN** the system SHALL report field `spec.management.enabled` with type `invalid`.

#### Scenario: Management enabled is immutable
- **WHEN** an update changes `spec.management.enabled` from its stored value
- **THEN** the system SHALL report field `spec.management.enabled` with type `immutable` and message `field 'spec.management.enabled' is immutable after creation`.

### Requirement: Mesh shell connection lookup
The system SHALL expose `mesh shell <name>` to return connection details for exposed meshes.

#### Scenario: Shell returns connection details only
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell <name>` for a mesh with exposure configured
- **THEN** the system SHALL print the mesh `status.connectionDetails` object without a resource envelope.

#### Scenario: Shell missing mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell <name>` and the mesh does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Shell rejects unexposed mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell <name>` for a mesh with no exposure configured
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

#### Scenario: Migrate command advances a named mesh migration
- **WHEN** the user runs `uv run --project /app meshctl.py mesh migrate <name>`
- **THEN** the system SHALL attempt to advance or complete the active migration for `<name>`.

#### Scenario: Shell command returns connection details
- **WHEN** the user runs `uv run --project /app meshctl.py mesh shell <name>`
- **THEN** the system SHALL attempt to return the exposed mesh connection details.

### Requirement: Mesh defaulting
The system SHALL apply documented defaults to successful create output and persisted resources while leaving fields without defaults absent when omitted.

#### Scenario: Defaults applied to omitted fields
- **WHEN** a valid create input omits `spec.instances`, `spec.resources.memory`, `spec.access`, `spec.migration.strategy`, `spec.management.enabled`, `spec.network.storage.size`, `spec.network.storage.ephemeral`, and `spec.network.replicationFactor`
- **THEN** the created resource SHALL include `spec.instances` as `1`, `spec.resources.memory` as `{"limit": "1Gi", "request": "1Gi"}`, `spec.access.authentication.enabled` as `true`, `spec.access.authentication.digestAlgorithm` as `"SHA-256"`, `spec.access.encryption.source` as `"None"`, `spec.access.encryption.clientMode` as `"None"`, `spec.access.permissions.enabled` as `false`, `spec.migration.strategy` as `"FullStop"`, `spec.management.enabled` as `false`, `spec.network.storage.size` as `"1Gi"`, `spec.network.storage.ephemeral` as `false`, and a computed `spec.network.replicationFactor`.

#### Scenario: Fields without defaults remain absent
- **WHEN** a valid create input omits `spec.runtime`, `spec.resources.cpu`, `spec.exposure`, `spec.network.storage.className`, or any other field without a documented default
- **THEN** the created resource SHALL omit those fields from the returned and persisted resource.
