## ADDED Requirements

### Requirement: Mesh metadata tags
The system SHALL support optional `metadata.tags` as a map of string keys to string values and SHALL persist every tag.

#### Scenario: Create persists metadata tags
- **WHEN** a valid mesh create input includes `metadata.tags`
- **THEN** create and describe output SHALL include every provided tag under `metadata.tags`.

#### Scenario: Update preserves omitted metadata tags
- **WHEN** a mesh has stored `metadata.tags` and an update omits `metadata.tags`
- **THEN** the system SHALL keep the stored tags.

#### Scenario: Update replaces provided metadata tags
- **WHEN** a mesh update provides `metadata.tags`
- **THEN** the system SHALL persist the provided tag map according to normal update merge semantics.

### Requirement: Mesh placement defaults and validation
The system SHALL include `spec.placement` in every returned mesh and SHALL support placement affinity defaults and validation.

#### Scenario: Omitted placement defaults on create
- **WHEN** a valid create input omits `spec.placement`
- **THEN** the returned and persisted mesh SHALL include `spec.placement.affinity.type` as `"preferred"` and `spec.placement.affinity.scope` as `"node"`.

#### Scenario: Describe includes defaulted placement
- **WHEN** an existing mesh is described and `spec.placement` was omitted from its create input
- **THEN** describe output SHALL include the defaulted `spec.placement`.

#### Scenario: Valid placement affinity override
- **WHEN** `spec.placement.affinity.type` is `"preferred"` or `"required"` and `spec.placement.affinity.scope` is `"node"` or `"zone"`
- **THEN** the system SHALL accept and persist the provided placement affinity.

#### Scenario: Non-object placement is rejected
- **WHEN** `spec.placement` is present and is not an object
- **THEN** the system SHALL report field `spec.placement` with type `invalid`.

#### Scenario: Non-object placement affinity is rejected
- **WHEN** `spec.placement.affinity` is present and is not an object
- **THEN** the system SHALL report field `spec.placement.affinity` with type `invalid`.

#### Scenario: Invalid placement affinity type is rejected
- **WHEN** `spec.placement.affinity.type` is present and is not `"preferred"` or `"required"`
- **THEN** the system SHALL report field `spec.placement.affinity.type` with type `invalid`.

#### Scenario: Invalid placement affinity scope is rejected
- **WHEN** `spec.placement.affinity.scope` is present and is not `"node"` or `"zone"`
- **THEN** the system SHALL report field `spec.placement.affinity.scope` with type `invalid`.

### Requirement: Mesh telemetry probe output
The system SHALL include `status.telemetryProbe` in every returned mesh and SHALL derive it from `metadata.tags`.

#### Scenario: Telemetry defaults to enabled
- **WHEN** a mesh has no `mesh.io/telemetry` metadata tag
- **THEN** the returned mesh SHALL include `status.telemetryProbe` equal to `{"enabled": true}` unless label tags are set.

#### Scenario: Telemetry enabled with target labels
- **WHEN** `metadata.tags.mesh.io/telemetry` is absent or `"true"` and `metadata.tags.mesh.io/targetLabels` is set to a comma-separated list
- **THEN** the returned mesh SHALL include `status.telemetryProbe.enabled` as `true` and `status.telemetryProbe.labels.targetLabels` as the list values in declaration order.

#### Scenario: Telemetry enabled with probe target labels
- **WHEN** telemetry is enabled and `metadata.tags.mesh.io/probeTargetLabels` is set to a comma-separated list
- **THEN** the returned mesh SHALL include `status.telemetryProbe.labels.probeTargetLabels` as the list values in declaration order.

#### Scenario: Telemetry enabled with instance labels
- **WHEN** telemetry is enabled and `metadata.tags.mesh.io/instanceLabels` is set to a comma-separated list
- **THEN** the returned mesh SHALL include `status.telemetryProbe.labels.instanceLabels` as the list values in declaration order.

#### Scenario: Telemetry includes only configured label categories
- **WHEN** telemetry is enabled and one or more label tags are omitted
- **THEN** `status.telemetryProbe.labels` SHALL include only categories whose corresponding metadata tags are set.

#### Scenario: Telemetry disabled
- **WHEN** `metadata.tags.mesh.io/telemetry` is `"false"`
- **THEN** the returned mesh SHALL include `status.telemetryProbe` equal to `{"enabled": false}`.

### Requirement: Mesh region topology
The system SHALL support optional `spec.regions` for multi-region topology and SHALL treat omitted regions as single-region operation.

#### Scenario: Omitted regions is single-region
- **WHEN** a valid mesh create input omits `spec.regions`
- **THEN** the returned mesh SHALL NOT include region-specific conditions.

#### Scenario: Regions require local region
- **WHEN** `spec.regions` is present and omits `spec.regions.local`
- **THEN** the system SHALL report field `spec.regions.local` with type `required`.

#### Scenario: Local region requires name
- **WHEN** `spec.regions.local.name` is missing or empty
- **THEN** the system SHALL report field `spec.regions.local.name` with type `required`.

#### Scenario: Local region requires expose type
- **WHEN** `spec.regions.local.expose.type` is missing
- **THEN** the system SHALL report field `spec.regions.local.expose.type` with type `required`.

#### Scenario: Local region validates expose type
- **WHEN** `spec.regions.local.expose.type` is present and is not `"Internal"`, `"DirectPort"`, `"Balancer"`, or `"Gateway"`
- **THEN** the system SHALL report field `spec.regions.local.expose.type` with type `invalid`.

#### Scenario: Local region preserves valid max relay nodes
- **WHEN** `spec.regions.local.maxRelayNodes` is present as an integer greater than `0`
- **THEN** the returned mesh SHALL include the provided `maxRelayNodes`.

#### Scenario: Local region omits unset max relay nodes
- **WHEN** `spec.regions.local.maxRelayNodes` is omitted
- **THEN** the returned mesh SHALL omit `spec.regions.local.maxRelayNodes`.

#### Scenario: Local region rejects invalid max relay nodes
- **WHEN** `spec.regions.local.maxRelayNodes` is present and is null, non-integer, or less than `1`
- **THEN** the system SHALL report field `spec.regions.local.maxRelayNodes` with type `invalid`.

### Requirement: Mesh inter-region encryption
The system SHALL support optional inter-region encryption under `spec.regions.local.encryption` independent of `spec.access`.

#### Scenario: Omitted local encryption stays omitted
- **WHEN** `spec.regions.local.encryption` is absent
- **THEN** the returned mesh SHALL omit `spec.regions.local.encryption`.

#### Scenario: Local encryption defaults protocol
- **WHEN** `spec.regions.local.encryption` is present and omits `protocol`
- **THEN** the returned mesh SHALL include `spec.regions.local.encryption.protocol` as `"TLSv1.3"`.

#### Scenario: Local encryption accepts supported protocols
- **WHEN** `spec.regions.local.encryption.protocol` is `"TLSv1.2"` or `"TLSv1.3"`
- **THEN** the system SHALL accept the encryption protocol.

#### Scenario: Local encryption rejects invalid protocol
- **WHEN** `spec.regions.local.encryption.protocol` is present and is not `"TLSv1.2"` or `"TLSv1.3"`
- **THEN** the system SHALL report field `spec.regions.local.encryption.protocol` with type `invalid`.

#### Scenario: Local encryption must be object
- **WHEN** `spec.regions.local.encryption` is present and is not an object
- **THEN** the system SHALL report field `spec.regions.local.encryption` with type `invalid`.

#### Scenario: Gateway exposure requires transport key store
- **WHEN** `spec.regions.local.expose.type` is `"Gateway"` and `spec.regions.local.encryption.transportKeyStore` is missing
- **THEN** the system SHALL report field `spec.regions.local.encryption.transportKeyStore` with type `required`.

#### Scenario: Key store fields are required
- **WHEN** a provided `transportKeyStore`, `relayKeyStore`, or `trustStore` omits `secretRef`, `alias`, or `filename`
- **THEN** the system SHALL report field `spec.regions.local.encryption.<store>.<field>` with type `required`.

#### Scenario: Missing trust store emits warning
- **WHEN** mesh create or update succeeds with `spec.regions.local.encryption` present and `trustStore` missing
- **THEN** the system SHALL include a top-level warning for `spec.regions.local.encryption.trustStore`.

### Requirement: Mesh region discovery
The system SHALL default and validate local region discovery when `spec.regions` is present.

#### Scenario: Region discovery defaults to relay heartbeat
- **WHEN** `spec.regions` is present and `spec.regions.local.discovery` is omitted
- **THEN** the returned mesh SHALL include `spec.regions.local.discovery.type` as `"relay"`, `heartbeat.enabled` as `true`, `heartbeat.interval` as `10000`, and `heartbeat.timeout` as `30000`.

#### Scenario: Region discovery must be object
- **WHEN** `spec.regions.local.discovery` is present and is not an object
- **THEN** the system SHALL report field `spec.regions.local.discovery` with type `invalid`.

#### Scenario: Region discovery type must be relay
- **WHEN** `spec.regions.local.discovery.type` is present and is not `"relay"`
- **THEN** the system SHALL report field `spec.regions.local.discovery.type` with type `invalid`.

#### Scenario: Region discovery heartbeat interval must be less than timeout
- **WHEN** `spec.regions.local.discovery.heartbeat.interval` is greater than or equal to `spec.regions.local.discovery.heartbeat.timeout`
- **THEN** the system SHALL report field `spec.regions.local.discovery.heartbeat` with type `invalid`.

### Requirement: Mesh remote regions
The system SHALL support optional ordered remote region entries under `spec.regions.remotes`.

#### Scenario: Remote regions may be empty
- **WHEN** `spec.regions.remotes` is present as an empty array
- **THEN** the system SHALL accept and persist the empty array.

#### Scenario: Remote regions preserve declaration order
- **WHEN** `spec.regions.remotes` contains multiple valid entries
- **THEN** the returned mesh SHALL preserve their declaration order.

#### Scenario: Remote regions require name and url
- **WHEN** a remote region entry omits `name` or `url`
- **THEN** the system SHALL report the missing field path with type `required`.

#### Scenario: Remote regions omit unset optional fields
- **WHEN** a remote region entry omits `credentialRef`, `namespace`, or `clusterRef`
- **THEN** the returned mesh SHALL omit those optional fields from that entry.

#### Scenario: Duplicate remote region names are rejected on later entry
- **WHEN** two entries in `spec.regions.remotes` use the same `name`
- **THEN** the system SHALL report field `spec.regions.remotes[<index>].name` for the later entry with type `duplicate`.

### Requirement: Mesh region conditions
The system SHALL add region conditions only for meshes with `spec.regions` and SHALL keep the full `status.conditions` array sorted by `type`.

#### Scenario: Multi-region create initializes region conditions
- **WHEN** a mesh is created successfully with `spec.regions` present
- **THEN** `status.conditions` SHALL include `DiscoveryRelayReady` and `RegionViewFormed` conditions with status `"False"` and message `""`.

#### Scenario: Region conditions are sorted with other conditions
- **WHEN** a returned mesh includes region conditions and existing lifecycle conditions
- **THEN** the full `status.conditions` array SHALL be sorted alphabetically by `type`.

#### Scenario: Region conditions do not affect stable status
- **WHEN** a returned mesh satisfies the existing stable lifecycle predicate and has `DiscoveryRelayReady` and `RegionViewFormed` with status `"False"`
- **THEN** `status.stable` SHALL be `true`.

### Requirement: Mesh multi-region migration restrictions
The system SHALL reject `spec.migration.strategy` equal to `"LiveMigration"` whenever `spec.regions` is present.

#### Scenario: Create rejects LiveMigration with regions
- **WHEN** a create input sets `spec.migration.strategy` to `"LiveMigration"` and includes `spec.regions`
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`.

#### Scenario: Update rejects LiveMigration with regions
- **WHEN** an update results in `spec.migration.strategy` equal to `"LiveMigration"` and `spec.regions` present
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`.

### Requirement: Mesh config bundle refresh
The system SHALL support optional `spec.configBundleRef` and SHALL report transient refresh status on updates that change it.

#### Scenario: Create persists config bundle reference
- **WHEN** a create input includes `spec.configBundleRef` as a string
- **THEN** the returned and persisted mesh SHALL include the provided `spec.configBundleRef`.

#### Scenario: Create rejects non-string config bundle reference
- **WHEN** a create input includes `spec.configBundleRef` with a non-string value
- **THEN** the system SHALL report field `spec.configBundleRef` with type `invalid`.

#### Scenario: Update omits config bundle reference
- **WHEN** a mesh has stored `spec.configBundleRef` and an update omits `spec.configBundleRef`
- **THEN** the system SHALL keep the stored value and SHALL NOT include `status.configRefresh`.

#### Scenario: Update adds config bundle reference
- **WHEN** an update adds the first `spec.configBundleRef`
- **THEN** the update response SHALL include `status.configRefresh.currentRef` as the new value, `pending` as `true`, and `previousRef` as null.

#### Scenario: Update changes config bundle reference
- **WHEN** an update changes `spec.configBundleRef` from one string value to another
- **THEN** the update response SHALL include `status.configRefresh.currentRef` as the new value, `pending` as `true`, and `previousRef` as the old value.

#### Scenario: Update clears config bundle reference
- **WHEN** an update sets `spec.configBundleRef` to null
- **THEN** the system SHALL remove the stored value and the update response SHALL include `status.configRefresh.currentRef` as null, `pending` as `true`, and `previousRef` as the old value.

#### Scenario: Describe omits previous config refresh
- **WHEN** a mesh is described after an update response included `status.configRefresh`
- **THEN** describe output SHALL omit `status.configRefresh`.

### Requirement: Mesh extensions
The system SHALL support optional ordered extension declarations under `spec.extensions`.

#### Scenario: Valid extensions preserve declaration order
- **WHEN** `spec.extensions` contains valid entries
- **THEN** the returned mesh SHALL preserve extension declaration order.

#### Scenario: Extension optional integrity is omitted when unset
- **WHEN** an extension entry omits `integrity`
- **THEN** the returned extension entry SHALL omit `integrity`.

#### Scenario: Extension url source is accepted
- **WHEN** an extension entry sets `url` and omits `artifact`
- **THEN** the system SHALL accept and persist the extension.

#### Scenario: Extension artifact source is accepted
- **WHEN** an extension entry sets `artifact` and omits `url`
- **THEN** the system SHALL accept and persist the extension.

#### Scenario: Extension requires exactly one source
- **WHEN** an extension entry sets both `url` and `artifact` or sets neither
- **THEN** the system SHALL report field `spec.extensions[<index>]` with type `invalid` and message `exactly one of 'url' or 'artifact' must be set`.

### Requirement: Mesh output additions
The system SHALL include `spec.placement` and `status.telemetryProbe` in create and describe output for every mesh.

#### Scenario: Create output includes always-present additions
- **WHEN** a mesh is created successfully
- **THEN** the create output SHALL include `spec.placement` and `status.telemetryProbe`.

#### Scenario: Describe output includes always-present additions
- **WHEN** a mesh is described successfully
- **THEN** the describe output SHALL include `spec.placement` and `status.telemetryProbe`.
