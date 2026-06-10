## ADDED Requirements

### Requirement: Mesh metadata tags
The system SHALL support optional `metadata.tags` as a mapping of string keys to string values and SHALL persist every provided tag.

#### Scenario: Metadata tags are preserved
- **WHEN** a valid create or update input includes `metadata.tags` as a mapping of string keys to string values
- **THEN** create, update, and describe output SHALL include the same `metadata.tags` mapping.

#### Scenario: Metadata tags are optional
- **WHEN** a valid mesh input omits `metadata.tags`
- **THEN** the returned mesh SHALL omit `metadata.tags`.

### Requirement: Mesh telemetry probe output
The system SHALL include `status.telemetryProbe` in every returned mesh and SHALL derive it from telemetry tags in `metadata.tags`.

#### Scenario: Telemetry defaults to enabled
- **WHEN** a returned mesh omits `metadata.tags.mesh.io/telemetry`
- **THEN** `status.telemetryProbe` SHALL equal `{"enabled": true}` unless telemetry label tags are set.

#### Scenario: Telemetry enabled by tag
- **WHEN** a returned mesh has `metadata.tags.mesh.io/telemetry` equal to `"true"`
- **THEN** `status.telemetryProbe.enabled` SHALL be `true`.

#### Scenario: Telemetry disabled by tag
- **WHEN** a returned mesh has `metadata.tags.mesh.io/telemetry` equal to `"false"`
- **THEN** `status.telemetryProbe` SHALL equal `{"enabled": false}`.

#### Scenario: Target labels are derived from tag
- **WHEN** telemetry is enabled and `metadata.tags.mesh.io/targetLabels` contains a comma-separated label list
- **THEN** `status.telemetryProbe.labels.targetLabels` SHALL contain the parsed labels in declaration order.

#### Scenario: Probe target labels are derived from tag
- **WHEN** telemetry is enabled and `metadata.tags.mesh.io/probeTargetLabels` contains a comma-separated label list
- **THEN** `status.telemetryProbe.labels.probeTargetLabels` SHALL contain the parsed labels in declaration order.

#### Scenario: Instance labels are derived from tag
- **WHEN** telemetry is enabled and `metadata.tags.mesh.io/instanceLabels` contains a comma-separated label list
- **THEN** `status.telemetryProbe.labels.instanceLabels` SHALL contain the parsed labels in declaration order.

#### Scenario: Telemetry labels include only configured categories
- **WHEN** telemetry is enabled and only one or more telemetry label tags are present
- **THEN** `status.telemetryProbe.labels` SHALL include only the corresponding configured label categories.

#### Scenario: Disabled telemetry omits labels
- **WHEN** telemetry is disabled and telemetry label tags are present
- **THEN** `status.telemetryProbe` SHALL equal `{"enabled": false}`.

### Requirement: Mesh placement policy
The system SHALL include defaulted `spec.placement.affinity` in successful create, update, and describe output and SHALL validate provided placement policy fields.

#### Scenario: Placement defaults when omitted
- **WHEN** a valid create input omits `spec.placement`
- **THEN** the returned mesh SHALL include `spec.placement.affinity.type` as `"preferred"` and `spec.placement.affinity.scope` as `"node"`.

#### Scenario: Placement object is required when present
- **WHEN** `spec.placement` is present and is not an object
- **THEN** the system SHALL report field `spec.placement` with type `invalid`.

#### Scenario: Placement affinity object is required when present
- **WHEN** `spec.placement.affinity` is present and is not an object
- **THEN** the system SHALL report field `spec.placement.affinity` with type `invalid`.

#### Scenario: Placement affinity type validates allowed values
- **WHEN** `spec.placement.affinity.type` is present and is not `"preferred"` or `"required"`
- **THEN** the system SHALL report field `spec.placement.affinity.type` with type `invalid`.

#### Scenario: Placement affinity scope validates allowed values
- **WHEN** `spec.placement.affinity.scope` is present and is not `"node"` or `"zone"`
- **THEN** the system SHALL report field `spec.placement.affinity.scope` with type `invalid`.

#### Scenario: Placement preserves provided affinity
- **WHEN** a valid input provides `spec.placement.affinity.type` or `spec.placement.affinity.scope`
- **THEN** the returned mesh SHALL preserve the provided values and default any omitted affinity fields.

### Requirement: Mesh multi-region topology
The system SHALL support optional `spec.regions` for multi-region topology, with `spec.regions.local` required whenever `spec.regions` is present.

#### Scenario: Omitted regions creates single-region mesh
- **WHEN** a valid mesh input omits `spec.regions`
- **THEN** the returned mesh SHALL omit `spec.regions` and SHALL NOT include region-specific conditions.

#### Scenario: Regions requires local region
- **WHEN** `spec.regions` is present and `spec.regions.local` is missing
- **THEN** the system SHALL report field `spec.regions.local` with type `required`.

#### Scenario: Local region name is required
- **WHEN** `spec.regions.local.name` is missing, null, or an empty string
- **THEN** the system SHALL report field `spec.regions.local.name` with type `required`.

#### Scenario: Local expose type is required
- **WHEN** `spec.regions.local.expose.type` is missing, null, or an empty string
- **THEN** the system SHALL report field `spec.regions.local.expose.type` with type `required`.

#### Scenario: Local expose type validates allowed values
- **WHEN** `spec.regions.local.expose.type` is present and is not `"Internal"`, `"DirectPort"`, `"Balancer"`, or `"Gateway"`
- **THEN** the system SHALL report field `spec.regions.local.expose.type` with type `invalid`.

#### Scenario: Local max relay nodes is optional
- **WHEN** a valid multi-region input omits `spec.regions.local.maxRelayNodes`
- **THEN** the returned mesh SHALL omit `spec.regions.local.maxRelayNodes`.

#### Scenario: Local max relay nodes must be positive
- **WHEN** `spec.regions.local.maxRelayNodes` is present and is not an integer greater than `0`
- **THEN** the system SHALL report field `spec.regions.local.maxRelayNodes` with type `invalid`.

#### Scenario: Local max relay nodes rejects null
- **WHEN** `spec.regions.local.maxRelayNodes` is null
- **THEN** the system SHALL report field `spec.regions.local.maxRelayNodes` with type `invalid`.

### Requirement: Mesh region encryption
The system SHALL support optional `spec.regions.local.encryption` for inter-region encryption and SHALL validate encryption protocol and key store objects.

#### Scenario: Absent region encryption is omitted
- **WHEN** a valid multi-region input omits `spec.regions.local.encryption`
- **THEN** the returned mesh SHALL omit `spec.regions.local.encryption`.

#### Scenario: Region encryption must be an object
- **WHEN** `spec.regions.local.encryption` is present and is not an object
- **THEN** the system SHALL report field `spec.regions.local.encryption` with type `invalid`.

#### Scenario: Region encryption protocol defaults to TLSv1.3
- **WHEN** a valid region encryption object omits `protocol`
- **THEN** the returned mesh SHALL include `spec.regions.local.encryption.protocol` as `"TLSv1.3"`.

#### Scenario: Region encryption protocol validates allowed values
- **WHEN** `spec.regions.local.encryption.protocol` is present and is not `"TLSv1.2"` or `"TLSv1.3"`
- **THEN** the system SHALL report field `spec.regions.local.encryption.protocol` with type `invalid`.

#### Scenario: Gateway region encryption requires transport key store
- **WHEN** `spec.regions.local.expose.type` is `"Gateway"` and `spec.regions.local.encryption.transportKeyStore` is missing
- **THEN** the system SHALL report field `spec.regions.local.encryption.transportKeyStore` with type `required`.

#### Scenario: Region key store requires secret reference
- **WHEN** a region encryption key store object omits `secretRef`
- **THEN** the system SHALL report the corresponding `spec.regions.local.encryption.<store>.secretRef` field with type `required`.

#### Scenario: Region key store requires alias
- **WHEN** a region encryption key store object omits `alias`
- **THEN** the system SHALL report the corresponding `spec.regions.local.encryption.<store>.alias` field with type `required`.

#### Scenario: Region key store requires filename
- **WHEN** a region encryption key store object omits `filename`
- **THEN** the system SHALL report the corresponding `spec.regions.local.encryption.<store>.filename` field with type `required`.

#### Scenario: Region encryption preserves stores
- **WHEN** a valid region encryption object includes `transportKeyStore`, `relayKeyStore`, or `trustStore`
- **THEN** the returned mesh SHALL include the provided key store objects.

#### Scenario: Missing trust store emits warning
- **WHEN** region encryption is present, `trustStore` is missing, and validation succeeds
- **THEN** the output SHALL include a warning for `spec.regions.local.encryption.trustStore`.

### Requirement: Mesh region discovery
The system SHALL default multi-region discovery to relay heartbeat settings and SHALL validate provided discovery configuration.

#### Scenario: Region discovery defaults
- **WHEN** `spec.regions` is present and `spec.regions.local.discovery` is omitted
- **THEN** the returned mesh SHALL include `spec.regions.local.discovery.type` as `"relay"`, `heartbeat.enabled` as `true`, `heartbeat.interval` as `10000`, and `heartbeat.timeout` as `30000`.

#### Scenario: Region discovery must be an object
- **WHEN** `spec.regions.local.discovery` is present and is not an object
- **THEN** the system SHALL report field `spec.regions.local.discovery` with type `invalid`.

#### Scenario: Region discovery type must be relay
- **WHEN** `spec.regions.local.discovery.type` is present and is not `"relay"`
- **THEN** the system SHALL report field `spec.regions.local.discovery.type` with type `invalid`.

#### Scenario: Region discovery heartbeat interval must be less than timeout
- **WHEN** `spec.regions.local.discovery.heartbeat.interval` is greater than or equal to `spec.regions.local.discovery.heartbeat.timeout`
- **THEN** the system SHALL report field `spec.regions.local.discovery.heartbeat` with type `invalid`.

#### Scenario: Region discovery preserves valid heartbeat values
- **WHEN** a valid multi-region input provides relay heartbeat settings with interval less than timeout
- **THEN** the returned mesh SHALL preserve the provided heartbeat settings and default any omitted discovery fields.

### Requirement: Mesh remote regions
The system SHALL support optional `spec.regions.remotes` as an ordered array of remote region references.

#### Scenario: Remote regions may be omitted
- **WHEN** a valid multi-region input omits `spec.regions.remotes`
- **THEN** the returned mesh SHALL omit `spec.regions.remotes`.

#### Scenario: Remote regions may be empty
- **WHEN** a valid multi-region input sets `spec.regions.remotes` to an empty array
- **THEN** the returned mesh SHALL include `spec.regions.remotes` as an empty array.

#### Scenario: Remote region required fields are preserved
- **WHEN** a valid remote region entry includes `name` and `url`
- **THEN** the returned mesh SHALL include those fields.

#### Scenario: Remote region optional fields are preserved
- **WHEN** a valid remote region entry includes `credentialRef`, `namespace`, or `clusterRef`
- **THEN** the returned mesh SHALL include the provided optional fields.

#### Scenario: Remote region optional fields are omitted when unset
- **WHEN** a valid remote region entry omits `credentialRef`, `namespace`, or `clusterRef`
- **THEN** the returned mesh SHALL omit the unset optional fields.

#### Scenario: Remote region order is preserved
- **WHEN** a valid multi-region input includes multiple remote region entries
- **THEN** the returned mesh SHALL preserve their declaration order.

#### Scenario: Duplicate remote names are rejected on later entry
- **WHEN** `spec.regions.remotes` contains a later entry whose `name` duplicates an earlier remote region name
- **THEN** the system SHALL report field `spec.regions.remotes[<index>].name` with type `duplicate` for the later entry index.

### Requirement: Mesh region conditions
The system SHALL add initial region conditions when `spec.regions` is present and SHALL keep condition output sorted by `type`.

#### Scenario: Multi-region mesh includes region conditions
- **WHEN** a mesh with `spec.regions` is returned
- **THEN** `status.conditions` SHALL include `DiscoveryRelayReady` and `RegionViewFormed` with status `"False"` and empty messages.

#### Scenario: Single-region mesh omits region conditions
- **WHEN** a mesh omits `spec.regions`
- **THEN** `status.conditions` SHALL omit `DiscoveryRelayReady` and `RegionViewFormed`.

#### Scenario: Region conditions are sorted with all conditions
- **WHEN** a returned mesh includes region conditions and other conditions
- **THEN** the full `status.conditions` array SHALL be sorted alphabetically by `type`.

#### Scenario: Region conditions do not affect stable status
- **WHEN** a returned mesh has only `DiscoveryRelayReady` or `RegionViewFormed` conditions with status `"False"` in addition to steady-state conditions
- **THEN** `status.stable` SHALL still depend only on `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration`.

### Requirement: Mesh migration restriction with regions
The system SHALL reject `spec.migration.strategy` equal to `"LiveMigration"` whenever `spec.regions` is present on create or update.

#### Scenario: Create rejects LiveMigration with regions
- **WHEN** a create input sets `spec.migration.strategy` to `"LiveMigration"` and includes `spec.regions`
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`.

#### Scenario: Update rejects LiveMigration with regions
- **WHEN** an update candidate has `spec.migration.strategy` equal to `"LiveMigration"` and `spec.regions` present after merge
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`.

### Requirement: Mesh config bundle reference
The system SHALL support optional `spec.configBundleRef` and SHALL emit transient `status.configRefresh` only in update responses that add, change, or clear the stored reference.

#### Scenario: Create preserves config bundle reference
- **WHEN** a valid create input includes `spec.configBundleRef` as a string
- **THEN** the returned and persisted mesh SHALL include the provided `spec.configBundleRef`.

#### Scenario: Create rejects invalid config bundle reference
- **WHEN** a create input includes `spec.configBundleRef` and it is not a string
- **THEN** the system SHALL report field `spec.configBundleRef` with type `invalid`.

#### Scenario: Update omits config bundle reference
- **WHEN** an update input omits `spec.configBundleRef`
- **THEN** the system SHALL keep the stored `spec.configBundleRef` value and SHALL omit `status.configRefresh`.

#### Scenario: Update adds config bundle reference
- **WHEN** an update changes `spec.configBundleRef` from absent to a string value
- **THEN** the update response SHALL include `status.configRefresh` with `currentRef` set to the new value, `previousRef` set to null, and `pending` set to `true`.

#### Scenario: Update changes config bundle reference
- **WHEN** an update changes `spec.configBundleRef` from one string value to a different string value
- **THEN** the update response SHALL include `status.configRefresh` with `currentRef` set to the new value, `previousRef` set to the old value, and `pending` set to `true`.

#### Scenario: Update clears config bundle reference
- **WHEN** an update sets `spec.configBundleRef` to null
- **THEN** the update response SHALL remove stored `spec.configBundleRef` and include `status.configRefresh` with `currentRef` set to null, `previousRef` set to the old value, and `pending` set to `true`.

#### Scenario: Describe omits prior config refresh
- **WHEN** a mesh is described after an update response emitted `status.configRefresh`
- **THEN** describe output SHALL omit `status.configRefresh`.

### Requirement: Mesh extensions
The system SHALL support optional ordered `spec.extensions` entries, each with exactly one source field selected from `url` or `artifact`.

#### Scenario: Extensions may be omitted
- **WHEN** a valid mesh input omits `spec.extensions`
- **THEN** the returned mesh SHALL omit `spec.extensions`.

#### Scenario: Extension URL source is preserved
- **WHEN** a valid extension entry sets `url` and omits `artifact`
- **THEN** the returned mesh SHALL include the extension `url`.

#### Scenario: Extension artifact source is preserved
- **WHEN** a valid extension entry sets `artifact` and omits `url`
- **THEN** the returned mesh SHALL include the extension `artifact`.

#### Scenario: Extension integrity is optional
- **WHEN** a valid extension entry omits `integrity`
- **THEN** the returned mesh SHALL omit `integrity` for that entry.

#### Scenario: Extension integrity is preserved
- **WHEN** a valid extension entry includes `integrity`
- **THEN** the returned mesh SHALL include the provided `integrity`.

#### Scenario: Extension order is preserved
- **WHEN** a valid mesh input includes multiple extension entries
- **THEN** the returned mesh SHALL preserve their declaration order.

#### Scenario: Extension rejects both sources
- **WHEN** a `spec.extensions` entry sets both `url` and `artifact`
- **THEN** the system SHALL report field `spec.extensions[<index>]` with type `invalid` and message `exactly one of 'url' or 'artifact' must be set`.

#### Scenario: Extension rejects missing source
- **WHEN** a `spec.extensions` entry sets neither `url` nor `artifact`
- **THEN** the system SHALL report field `spec.extensions[<index>]` with type `invalid` and message `exactly one of 'url' or 'artifact' must be set`.
