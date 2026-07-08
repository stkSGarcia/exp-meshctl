> Extends: mesh-resource-management/add-meshctl-mesh-crud
> Extends: vault-resource-management/add-vault-resource-management
> Extends: mesh-resource-management/add-access-security-model

## ADDED Requirements

### Requirement: Mesh metadata tags
The system SHALL support optional `metadata.tags` as a map of string keys to string values and SHALL persist every tag. (adapts vault-resource-management/add-vault-resource-management/vault-spec-fields-and-defaults)

#### Scenario: Persisting metadata tags
- **WHEN** a mesh is created with `metadata.tags`
- **THEN** the successful output includes all submitted tag key/value pairs under `metadata.tags`

### Requirement: Defaulted operational output
The system SHALL include `spec.placement` and `status.telemetryProbe` in successful mesh create and describe output, even when those fields are omitted from input. (adapts mesh-resource-management/add-access-security-model/mesh-access-output)

#### Scenario: Output includes defaults
- **WHEN** a mesh is created without `spec.placement` and without telemetry tags
- **THEN** the output includes `spec.placement.affinity.type` set to `"preferred"`
- **AND** the output includes `spec.placement.affinity.scope` set to `"node"`
- **AND** the output includes `status.telemetryProbe` set to `{"enabled": true}`

### Requirement: Region topology
The system SHALL support `spec.regions` for multi-region operation and SHALL treat meshes without `spec.regions` as single-region meshes.

#### Scenario: Single-region mesh has no region conditions
- **WHEN** a mesh is created without `spec.regions`
- **THEN** the output does not add `DiscoveryRelayReady` or `RegionViewFormed` conditions

#### Scenario: Missing local region is rejected
- **WHEN** a mesh is created with `spec.regions` and without `spec.regions.local`
- **THEN** validation fails with `field` set to `"spec.regions.local"` and `type` set to `"required"`

### Requirement: Local region configuration
The system SHALL require `spec.regions.local.name` and `spec.regions.local.expose.type` when `spec.regions` is present.

#### Scenario: Valid local region exposure
- **WHEN** `spec.regions.local.expose.type` is `"Internal"`, `"DirectPort"`, `"Balancer"`, or `"Gateway"`
- **THEN** the local region exposure is accepted

#### Scenario: Invalid local region exposure
- **WHEN** `spec.regions.local.expose.type` is not one of `"Internal"`, `"DirectPort"`, `"Balancer"`, or `"Gateway"`
- **THEN** validation fails with `field` set to `"spec.regions.local.expose.type"` and `type` set to `"invalid"`

#### Scenario: Invalid local relay node limit
- **WHEN** `spec.regions.local.maxRelayNodes` is present and is not an integer greater than `0`
- **THEN** validation fails with `field` set to `"spec.regions.local.maxRelayNodes"` and `type` set to `"invalid"`

### Requirement: Inter-region encryption
The system SHALL support inter-region encryption under `spec.regions.local.encryption` separately from `spec.access`.

#### Scenario: Gateway transport key store is required
- **WHEN** `spec.regions.local.expose.type` is `"Gateway"` and `spec.regions.local.encryption.transportKeyStore` is missing
- **THEN** validation fails with `field` set to `"spec.regions.local.encryption.transportKeyStore"` and `type` set to `"required"`

#### Scenario: Missing trust store warning
- **WHEN** `spec.regions.local.encryption` is present without `trustStore`
- **THEN** the response includes a non-fatal warning

#### Scenario: Invalid encryption protocol
- **WHEN** `spec.regions.local.encryption.protocol` is not `"TLSv1.2"` or `"TLSv1.3"`
- **THEN** validation fails with `field` set to `"spec.regions.local.encryption.protocol"` and `type` set to `"invalid"`

#### Scenario: Missing key store field
- **WHEN** an encryption key store object omits `secretRef`, `alias`, or `filename`
- **THEN** validation fails with `field` set to the missing `spec.regions.local.encryption.<store>.<field>` path and `type` set to `"required"`

### Requirement: Region discovery
The system SHALL default local region discovery to relay discovery with heartbeat enabled, interval `10000`, and timeout `30000` when `spec.regions` is present.

#### Scenario: Region discovery defaults
- **WHEN** a mesh is created with `spec.regions` and without `spec.regions.local.discovery`
- **THEN** the output includes `spec.regions.local.discovery.type` set to `"relay"`
- **AND** heartbeat is enabled with interval `10000` and timeout `30000`

#### Scenario: Invalid heartbeat timing
- **WHEN** `spec.regions.local.discovery.heartbeat.interval` is greater than or equal to `spec.regions.local.discovery.heartbeat.timeout`
- **THEN** validation fails with `field` set to `"spec.regions.local.discovery.heartbeat"` and `type` set to `"invalid"`

### Requirement: Remote regions
The system SHALL support optional ordered `spec.regions.remotes` entries and SHALL preserve declaration order in output.

#### Scenario: Duplicate remote name
- **WHEN** a later `spec.regions.remotes` entry repeats an earlier remote name
- **THEN** validation fails with `field` set to `"spec.regions.remotes[<index>].name"` for the later entry and `type` set to `"duplicate"`

#### Scenario: Remote optional fields are omitted when unset
- **WHEN** a remote region omits `credentialRef`, `namespace`, or `clusterRef`
- **THEN** the output omits the unset optional fields for that remote entry

### Requirement: Region conditions
The system SHALL add `DiscoveryRelayReady` and `RegionViewFormed` conditions when `spec.regions` is present, and SHALL sort the full `status.conditions` array alphabetically by `type`.

#### Scenario: Initial region conditions
- **WHEN** a mesh is created with `spec.regions`
- **THEN** the output includes `DiscoveryRelayReady` and `RegionViewFormed` conditions with `status` set to `"False"` and `message` set to `""`
- **AND** those conditions do not affect `status.stable`

### Requirement: Multi-region migration restriction
The system SHALL reject `spec.migration.strategy = "LiveMigration"` when `spec.regions` is present on create or update.

#### Scenario: Live migration rejected with regions
- **WHEN** a mesh create or update request sets `spec.migration.strategy` to `"LiveMigration"` and includes `spec.regions`
- **THEN** validation fails with `field` set to `"spec.migration.strategy"`, `type` set to `"invalid"`, and `message` set to `"LiveMigration strategy is not supported with multi-region topology"`

### Requirement: Telemetry probe from tags
The system SHALL derive `status.telemetryProbe` from `metadata.tags`.

#### Scenario: Telemetry disabled by tag
- **WHEN** `metadata.tags["mesh.io/telemetry"]` is `"false"`
- **THEN** the output includes `status.telemetryProbe` set to `{"enabled": false}`

#### Scenario: Telemetry label tags
- **WHEN** telemetry is enabled and label tags are set under `mesh.io/targetLabels`, `mesh.io/probeTargetLabels`, or `mesh.io/instanceLabels`
- **THEN** `status.telemetryProbe.labels` includes only the categories whose tags are set
- **AND** each comma-separated label list preserves declaration order

### Requirement: Placement affinity
The system SHALL support `spec.placement.affinity` with default `type` `"preferred"` and default `scope` `"node"`.

#### Scenario: Invalid placement section
- **WHEN** `spec.placement` is present and is not an object
- **THEN** validation fails with `field` set to `"spec.placement"` and `type` set to `"invalid"`

#### Scenario: Invalid placement affinity value
- **WHEN** `spec.placement.affinity.type` is not `"preferred"` or `"required"` or `spec.placement.affinity.scope` is not `"node"` or `"zone"`
- **THEN** validation fails with the invalid field path and `type` set to `"invalid"`

### Requirement: Config bundle reference refresh
The system SHALL support optional `spec.configBundleRef` and SHALL report transient `status.configRefresh` when the value changes during update.

#### Scenario: Create-time config bundle reference
- **WHEN** a mesh is created with `spec.configBundleRef`
- **THEN** the value must be a string
- **AND** a non-string value fails validation with `field` set to `"spec.configBundleRef"` and `type` set to `"invalid"`

#### Scenario: Config bundle reference changed
- **WHEN** an update changes, adds, or clears `spec.configBundleRef`
- **THEN** the update response includes `status.configRefresh.currentRef`, `pending` set to `true`, and `previousRef`
- **AND** later describe output omits `status.configRefresh`

#### Scenario: Config bundle reference omitted on update
- **WHEN** an update omits `spec.configBundleRef`
- **THEN** the stored value is retained

### Requirement: Extension sources
The system SHALL support optional ordered `spec.extensions` entries where each entry sets exactly one of `url` or `artifact`.

#### Scenario: Extension source order and optional integrity
- **WHEN** a mesh is created with multiple `spec.extensions` entries
- **THEN** output preserves declaration order
- **AND** omits `integrity` when unset

#### Scenario: Invalid extension source
- **WHEN** a `spec.extensions` entry sets both `url` and `artifact` or sets neither
- **THEN** validation fails with `field` set to `"spec.extensions[<index>]"`, `type` set to `"invalid"`, and `message` set to `"exactly one of 'url' or 'artifact' must be set"`
