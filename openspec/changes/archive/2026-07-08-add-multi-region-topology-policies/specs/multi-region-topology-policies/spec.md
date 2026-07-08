## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud
> Extends: mesh-resource-management/add-access-security-model
> Extends: mesh-connectivity/add-network-exposure-connectivity

### Requirement: Always-present operational output
The system SHALL include `spec.placement` and `status.telemetryProbe` in successful mesh create and describe output for every mesh. (adapts mesh-resource-management/add-access-security-model/mesh-access-output)

#### Scenario: Minimal mesh output includes defaults
- **WHEN** a mesh is created or described without `spec.placement` and without telemetry tags
- **THEN** the output includes defaulted `spec.placement.affinity`
- **AND** the output includes `status.telemetryProbe` with telemetry enabled

### Requirement: Metadata tag persistence
The system SHALL accept optional `metadata.tags` as a map of string keys to string values and SHALL persist every tag.

#### Scenario: Metadata tags are preserved
- **WHEN** a mesh is created with `metadata.tags`
- **THEN** later describe output includes the same tag keys and values

### Requirement: Telemetry probe derivation
The system SHALL derive `status.telemetryProbe` from `metadata.tags` using `mesh.io/telemetry`, `mesh.io/targetLabels`, `mesh.io/probeTargetLabels`, and `mesh.io/instanceLabels`.

#### Scenario: Telemetry defaults to enabled
- **WHEN** no telemetry tags are set
- **THEN** `status.telemetryProbe` is `{"enabled": true}`

#### Scenario: Telemetry labels are derived in order
- **WHEN** telemetry is enabled and label tags contain comma-separated values
- **THEN** `status.telemetryProbe.labels` includes only the configured label categories
- **AND** each label list preserves declaration order

#### Scenario: Telemetry is disabled
- **WHEN** `metadata.tags["mesh.io/telemetry"]` is `"false"`
- **THEN** `status.telemetryProbe` is `{"enabled": false}`

### Requirement: Region topology
The system SHALL treat meshes without `spec.regions` as single-region meshes and SHALL require `spec.regions.local` when `spec.regions` is present.

#### Scenario: Single-region mesh has no region conditions
- **WHEN** `spec.regions` is omitted
- **THEN** the mesh is treated as single-region
- **AND** no region readiness conditions are added

#### Scenario: Missing local region is required
- **WHEN** `spec.regions` is present without `spec.regions.local`
- **THEN** validation returns an error with `field` set to `spec.regions.local` and `type` set to `required`

### Requirement: Local region settings
The system SHALL require non-empty `spec.regions.local.name`, SHALL require `spec.regions.local.expose.type` to be one of `"Internal"`, `"DirectPort"`, `"Balancer"`, or `"Gateway"`, and SHALL accept optional positive-integer `spec.regions.local.maxRelayNodes`.

#### Scenario: Missing local region name is required
- **WHEN** `spec.regions.local.name` is missing or empty
- **THEN** validation returns an error with `field` set to `spec.regions.local.name` and `type` set to `required`

#### Scenario: Invalid local exposure type is rejected
- **WHEN** `spec.regions.local.expose.type` is missing or not one of the supported values
- **THEN** validation returns a required or invalid error for `spec.regions.local.expose.type`

#### Scenario: Invalid relay node count is rejected
- **WHEN** `spec.regions.local.maxRelayNodes` is present as `null`, a non-integer, or an integer less than or equal to `0`
- **THEN** validation returns an error with `field` set to `spec.regions.local.maxRelayNodes` and `type` set to `invalid`

### Requirement: Inter-region encryption
The system SHALL validate `spec.regions.local.encryption` separately from `spec.access` and SHALL support protocol, transport key store, relay key store, and trust store settings. (adapts mesh-resource-management/add-access-security-model/mesh-access-encryption)

#### Scenario: Encryption section is omitted when absent
- **WHEN** no local region encryption section is configured
- **THEN** output omits `spec.regions.local.encryption`

#### Scenario: Gateway requires transport key store
- **WHEN** `spec.regions.local.expose.type` is `"Gateway"` and `spec.regions.local.encryption.transportKeyStore` is missing
- **THEN** validation returns an error with `field` set to `spec.regions.local.encryption.transportKeyStore` and `type` set to `required`

#### Scenario: Missing trust store emits warning
- **WHEN** local region encryption is present without `trustStore`
- **THEN** the response includes a non-fatal warning

#### Scenario: Key store sub-fields are required
- **WHEN** a configured key store object is missing `secretRef`, `alias`, or `filename`
- **THEN** validation returns a required error for `spec.regions.local.encryption.<store>.<field>`

### Requirement: Relay discovery defaults
The system SHALL default `spec.regions.local.discovery` to relay heartbeat settings when `spec.regions` is present and SHALL validate custom discovery settings.

#### Scenario: Multi-region discovery defaults to relay
- **WHEN** `spec.regions` is present and local discovery is omitted
- **THEN** output defaults discovery to type `"relay"` with heartbeat enabled, interval `10000`, and timeout `30000`

#### Scenario: Heartbeat interval must be less than timeout
- **WHEN** `heartbeat.interval` is greater than or equal to `heartbeat.timeout`
- **THEN** validation returns an error with `field` set to `spec.regions.local.discovery.heartbeat` and `type` set to `invalid`

### Requirement: Remote region declarations
The system SHALL accept optional ordered `spec.regions.remotes` entries with required `name` and `url` and optional `credentialRef`, `namespace`, and `clusterRef`.

#### Scenario: Remote declaration order is preserved
- **WHEN** multiple remote regions are configured
- **THEN** output preserves their declaration order
- **AND** unset optional fields are omitted

#### Scenario: Duplicate remote name is rejected on later entry
- **WHEN** a later remote repeats an earlier remote name
- **THEN** validation returns an error with `field` set to `spec.regions.remotes[<index>].name` and `type` set to `duplicate`

### Requirement: Region readiness conditions
The system SHALL add `DiscoveryRelayReady` and `RegionViewFormed` conditions when `spec.regions` is present and SHALL sort the full conditions array alphabetically by `type`.

#### Scenario: Region conditions do not affect stability
- **WHEN** a mesh has `spec.regions`
- **THEN** `DiscoveryRelayReady` and `RegionViewFormed` are initialized with status `"False"` and message `""`
- **AND** `status.stable` still depends only on `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration`

### Requirement: Regional migration restriction
The system SHALL reject `spec.migration.strategy = "LiveMigration"` when `spec.regions` is present on create and update.

#### Scenario: Live migration is invalid with regions
- **WHEN** a create or update request sets `spec.regions` and `spec.migration.strategy` to `"LiveMigration"`
- **THEN** validation returns an error with `field` set to `spec.migration.strategy`, `type` set to `invalid`, and `message` set to `"LiveMigration strategy is not supported with multi-region topology"`

### Requirement: Placement affinity defaults
The system SHALL default `spec.placement.affinity.type` to `"preferred"` and `spec.placement.affinity.scope` to `"node"` and SHALL validate placement objects.

#### Scenario: Placement defaults are included
- **WHEN** `spec.placement` is omitted
- **THEN** output includes the defaulted placement affinity

#### Scenario: Invalid placement sections are rejected
- **WHEN** `spec.placement` or `spec.placement.affinity` is present as a non-object
- **THEN** validation returns an invalid error for the corresponding field

### Requirement: Config bundle refresh tracking
The system SHALL support optional `spec.configBundleRef` on create and SHALL preserve, clear, or change it on update with transient `status.configRefresh` output when the value changes.

#### Scenario: Config bundle value changes
- **WHEN** an update changes, adds, or clears `spec.configBundleRef`
- **THEN** that update response includes `status.configRefresh` with `currentRef`, `pending: true`, and `previousRef`
- **AND** later describe output omits `status.configRefresh`

#### Scenario: Omitted config bundle keeps stored value
- **WHEN** an update omits `spec.configBundleRef`
- **THEN** the stored config bundle reference is unchanged
- **AND** no `status.configRefresh` is emitted

### Requirement: Extension declarations
The system SHALL accept optional ordered `spec.extensions` entries that set exactly one of `url` or `artifact` and may set `integrity`.

#### Scenario: Extension source is valid
- **WHEN** an extension entry sets exactly one source field
- **THEN** output preserves the entry order
- **AND** output omits `integrity` when unset

#### Scenario: Extension source is invalid
- **WHEN** an extension entry sets both `url` and `artifact` or neither source
- **THEN** validation returns an error with `field` set to `spec.extensions[<index>]`, `type` set to `invalid`, and `message` set to `"exactly one of 'url' or 'artifact' must be set"`
