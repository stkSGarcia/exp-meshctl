## ADDED Requirements

### Requirement: Mesh metadata tags
The system SHALL support optional string metadata tags on mesh resources.

#### Scenario: Metadata tags are persisted
- **WHEN** a valid mesh create input includes `metadata.tags` as a mapping of string keys to string values
- **THEN** the created resource SHALL include every provided metadata tag.

#### Scenario: Metadata tags are optional
- **WHEN** a valid mesh create input omits `metadata.tags`
- **THEN** the created resource SHALL omit `metadata.tags`.

### Requirement: Mesh placement policy
The system SHALL support `spec.placement.affinity` and SHALL include default placement in every successful mesh output.

#### Scenario: Placement defaults when omitted
- **WHEN** a valid mesh create input omits `spec.placement`
- **THEN** the created resource SHALL include `spec.placement.affinity.type` equal to `"preferred"` and `spec.placement.affinity.scope` equal to `"node"`.

#### Scenario: Placement accepts required zone affinity
- **WHEN** a valid mesh create input sets `spec.placement.affinity.type` to `"required"` and `spec.placement.affinity.scope` to `"zone"`
- **THEN** the created resource SHALL preserve those placement values.

#### Scenario: Placement section must be an object
- **WHEN** `spec.placement` is present and is not an object
- **THEN** the system SHALL report field `spec.placement` with type `invalid`.

#### Scenario: Placement affinity section must be an object
- **WHEN** `spec.placement.affinity` is present and is not an object
- **THEN** the system SHALL report field `spec.placement.affinity` with type `invalid`.

#### Scenario: Placement affinity type validates allowed values
- **WHEN** `spec.placement.affinity.type` is present and is not `"preferred"` or `"required"`
- **THEN** the system SHALL report field `spec.placement.affinity.type` with type `invalid`.

#### Scenario: Placement affinity scope validates allowed values
- **WHEN** `spec.placement.affinity.scope` is present and is not `"node"` or `"zone"`
- **THEN** the system SHALL report field `spec.placement.affinity.scope` with type `invalid`.

### Requirement: Mesh multi-region topology
The system SHALL support optional `spec.regions` for multi-region mesh operation.

#### Scenario: Regions may be omitted
- **WHEN** a valid mesh create input omits `spec.regions`
- **THEN** the created resource SHALL represent a single-region mesh and SHALL NOT include region-specific conditions.

#### Scenario: Regions require local topology
- **WHEN** `spec.regions` is present and omits `spec.regions.local`
- **THEN** the system SHALL report field `spec.regions.local` with type `required`.

#### Scenario: Local region name is required
- **WHEN** `spec.regions.local.name` is missing, null, or empty
- **THEN** the system SHALL report field `spec.regions.local.name` with type `required`.

#### Scenario: Local expose type is required
- **WHEN** `spec.regions.local.expose.type` is missing, null, or empty
- **THEN** the system SHALL report field `spec.regions.local.expose.type` with type `required`.

#### Scenario: Local expose type validates allowed values
- **WHEN** `spec.regions.local.expose.type` is present and is not `"Internal"`, `"DirectPort"`, `"Balancer"`, or `"Gateway"`
- **THEN** the system SHALL report field `spec.regions.local.expose.type` with type `invalid`.

#### Scenario: Local max relay nodes is optional
- **WHEN** a valid multi-region mesh omits `spec.regions.local.maxRelayNodes`
- **THEN** the created resource SHALL omit `spec.regions.local.maxRelayNodes`.

#### Scenario: Local max relay nodes must be positive
- **WHEN** `spec.regions.local.maxRelayNodes` is present and is not an integer greater than `0`
- **THEN** the system SHALL report field `spec.regions.local.maxRelayNodes` with type `invalid`.

### Requirement: Mesh inter-region encryption
The system SHALL validate optional inter-region encryption under `spec.regions.local.encryption`.

#### Scenario: Encryption may be omitted
- **WHEN** a valid multi-region mesh omits `spec.regions.local.encryption`
- **THEN** the created resource SHALL omit `spec.regions.local.encryption`.

#### Scenario: Encryption section must be an object
- **WHEN** `spec.regions.local.encryption` is present and is not an object
- **THEN** the system SHALL report field `spec.regions.local.encryption` with type `invalid`.

#### Scenario: Encryption protocol defaults
- **WHEN** `spec.regions.local.encryption` is present and omits `protocol`
- **THEN** the created resource SHALL include `spec.regions.local.encryption.protocol` equal to `"TLSv1.3"`.

#### Scenario: Encryption protocol validates allowed values
- **WHEN** `spec.regions.local.encryption.protocol` is present and is not `"TLSv1.2"` or `"TLSv1.3"`
- **THEN** the system SHALL report field `spec.regions.local.encryption.protocol` with type `invalid`.

#### Scenario: Gateway exposure requires transport key store
- **WHEN** `spec.regions.local.expose.type` is `"Gateway"` and `spec.regions.local.encryption.transportKeyStore` is missing
- **THEN** the system SHALL report field `spec.regions.local.encryption.transportKeyStore` with type `required`.

#### Scenario: Key store fields are required
- **WHEN** any provided key store object under `spec.regions.local.encryption` omits `secretRef`, `alias`, or `filename`
- **THEN** the system SHALL report the missing sub-field path with type `required`.

#### Scenario: Missing trust store emits warning
- **WHEN** a mesh create or update succeeds with `spec.regions.local.encryption` present and `spec.regions.local.encryption.trustStore` missing
- **THEN** the successful JSON output SHALL include a warning for field `spec.regions.local.encryption.trustStore`.

### Requirement: Mesh regional discovery
The system SHALL default and validate local region discovery when `spec.regions` is present.

#### Scenario: Regional discovery defaults
- **WHEN** a valid multi-region mesh omits `spec.regions.local.discovery`
- **THEN** the created resource SHALL include `spec.regions.local.discovery.type` equal to `"relay"`, heartbeat enabled equal to `true`, heartbeat interval equal to `10000`, and heartbeat timeout equal to `30000`.

#### Scenario: Regional discovery section must be an object
- **WHEN** `spec.regions.local.discovery` is present and is not an object
- **THEN** the system SHALL report field `spec.regions.local.discovery` with type `invalid`.

#### Scenario: Regional discovery type must be relay
- **WHEN** `spec.regions.local.discovery.type` is present and is not `"relay"`
- **THEN** the system SHALL report field `spec.regions.local.discovery.type` with type `invalid`.

#### Scenario: Heartbeat interval must be less than timeout
- **WHEN** `spec.regions.local.discovery.heartbeat.interval` is greater than or equal to `spec.regions.local.discovery.heartbeat.timeout`
- **THEN** the system SHALL report field `spec.regions.local.discovery.heartbeat` with type `invalid`.

### Requirement: Mesh remote regions
The system SHALL support ordered remote region declarations under `spec.regions.remotes`.

#### Scenario: Remote regions may be omitted
- **WHEN** a valid multi-region mesh omits `spec.regions.remotes`
- **THEN** the created resource SHALL omit `spec.regions.remotes`.

#### Scenario: Remote regions may be empty
- **WHEN** a valid multi-region mesh sets `spec.regions.remotes` to an empty array
- **THEN** the created resource SHALL include an empty `spec.regions.remotes` array.

#### Scenario: Remote region preserves declaration order and optional fields
- **WHEN** a valid multi-region mesh includes remote region entries with `name`, `url`, `credentialRef`, `namespace`, or `clusterRef`
- **THEN** the created resource SHALL preserve remote entries in declaration order and SHALL omit optional fields that are unset.

#### Scenario: Duplicate remote names are rejected on later entry
- **WHEN** `spec.regions.remotes` contains more than one entry with the same `name`
- **THEN** the system SHALL report field `spec.regions.remotes[<index>].name` for the later duplicate entry with type `duplicate`.

### Requirement: Mesh region conditions
The system SHALL add initial region readiness conditions only for multi-region meshes.

#### Scenario: Multi-region meshes include region conditions
- **WHEN** a mesh with `spec.regions` is created successfully
- **THEN** `status.conditions` SHALL include `DiscoveryRelayReady` and `RegionViewFormed` conditions with status `"False"` and empty messages.

#### Scenario: Region conditions are sorted with all conditions
- **WHEN** a multi-region mesh is returned
- **THEN** the full `status.conditions` array SHALL be sorted alphabetically by condition `type`.

#### Scenario: Region conditions do not affect stable status
- **WHEN** a returned mesh otherwise satisfies stable status rules and has only `DiscoveryRelayReady` or `RegionViewFormed` region conditions with status `"False"`
- **THEN** `status.stable` SHALL remain `true`.

### Requirement: Mesh telemetry probe status
The system SHALL derive `status.telemetryProbe` from `metadata.tags` and SHALL include it in every successful mesh output.

#### Scenario: Telemetry defaults to enabled
- **WHEN** a mesh has no `metadata.tags["mesh.io/telemetry"]`
- **THEN** `status.telemetryProbe` SHALL equal an object with `enabled` equal to `true`.

#### Scenario: Telemetry can be disabled
- **WHEN** a mesh has `metadata.tags["mesh.io/telemetry"]` equal to `"false"`
- **THEN** `status.telemetryProbe` SHALL equal an object with `enabled` equal to `false`.

#### Scenario: Telemetry can be explicitly enabled
- **WHEN** a mesh has `metadata.tags["mesh.io/telemetry"]` equal to `"true"`
- **THEN** `status.telemetryProbe.enabled` SHALL be `true`.

#### Scenario: Telemetry target labels preserve order
- **WHEN** telemetry is enabled and `metadata.tags["mesh.io/targetLabels"]` contains a comma-separated list
- **THEN** `status.telemetryProbe.labels.targetLabels` SHALL contain the parsed labels in the same order.

#### Scenario: Telemetry probe target labels preserve order
- **WHEN** telemetry is enabled and `metadata.tags["mesh.io/probeTargetLabels"]` contains a comma-separated list
- **THEN** `status.telemetryProbe.labels.probeTargetLabels` SHALL contain the parsed labels in the same order.

#### Scenario: Telemetry instance labels preserve order
- **WHEN** telemetry is enabled and `metadata.tags["mesh.io/instanceLabels"]` contains a comma-separated list
- **THEN** `status.telemetryProbe.labels.instanceLabels` SHALL contain the parsed labels in the same order.

#### Scenario: Telemetry labels omitted when disabled
- **WHEN** telemetry is disabled
- **THEN** `status.telemetryProbe` SHALL contain only `enabled` equal to `false`.

### Requirement: Mesh config bundle reference
The system SHALL support optional `spec.configBundleRef` and transient config refresh status on updates that change it.

#### Scenario: Config bundle reference validates on create
- **WHEN** `spec.configBundleRef` is present on create and is not a string
- **THEN** the system SHALL report field `spec.configBundleRef` with type `invalid`.

#### Scenario: Config bundle reference is preserved on create
- **WHEN** a valid mesh create input includes `spec.configBundleRef`
- **THEN** the created resource SHALL include the provided `spec.configBundleRef`.

#### Scenario: Omitted config bundle update keeps stored value
- **WHEN** a mesh update omits `spec.configBundleRef`
- **THEN** the system SHALL keep the stored `spec.configBundleRef` value.

#### Scenario: Null config bundle update clears stored value
- **WHEN** a mesh update sets `spec.configBundleRef` to null
- **THEN** the system SHALL remove stored `spec.configBundleRef`.

#### Scenario: Config bundle update reports refresh
- **WHEN** an update changes, adds, or clears `spec.configBundleRef`
- **THEN** the update response SHALL include `status.configRefresh` with `currentRef`, `pending` equal to `true`, and `previousRef`.

#### Scenario: Config refresh is omitted after changing response
- **WHEN** a mesh is described after an earlier update changed `spec.configBundleRef`
- **THEN** the describe output SHALL omit `status.configRefresh`.

### Requirement: Mesh extensions
The system SHALL support ordered extension entries under `spec.extensions`.

#### Scenario: Extensions may be omitted
- **WHEN** a valid mesh create input omits `spec.extensions`
- **THEN** the created resource SHALL omit `spec.extensions`.

#### Scenario: Extension entries preserve declaration order
- **WHEN** a valid mesh create input includes extension entries with `url` or `artifact`
- **THEN** the created resource SHALL preserve `spec.extensions` entries in declaration order.

#### Scenario: Extension integrity is optional
- **WHEN** a valid extension entry omits `integrity`
- **THEN** the created resource SHALL omit `integrity` for that entry.

#### Scenario: Extension requires exactly one source
- **WHEN** a `spec.extensions` entry sets both `url` and `artifact` or sets neither field
- **THEN** the system SHALL report field `spec.extensions[<index>]` with type `invalid` and message `exactly one of 'url' or 'artifact' must be set`.

## MODIFIED Requirements

### Requirement: Mesh runtime version change rules
The system SHALL apply migration strategy validation when `spec.runtime` changes from one catalog version to another and SHALL reject `LiveMigration` whenever multi-region topology is configured.

#### Scenario: First runtime assignment does not start migration
- **WHEN** a mesh without stored `spec.runtime` is updated to set `spec.runtime` for the first time
- **THEN** the system SHALL persist the runtime version and SHALL NOT add a `Migration` condition or `status.migration`.

#### Scenario: Runtime downgrade is rejected
- **WHEN** an update changes `spec.runtime` from a higher catalog version to a lower catalog version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid` and message `version downgrade from '<current>' to '<target>' is not allowed`.

#### Scenario: FullStop permits non-downgrade version changes
- **WHEN** an update changes `spec.runtime` to a non-downgrade catalog version and `spec.migration.strategy` is `"FullStop"`
- **THEN** the system SHALL accept the version change and start a migration.

#### Scenario: RollingPatch requires same major and minor
- **WHEN** an update changes `spec.runtime` and `spec.migration.strategy` is `"RollingPatch"` but the source and target do not share the same major and minor version
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: RollingPatch requires target major at least four
- **WHEN** an update changes `spec.runtime` and `spec.migration.strategy` is `"RollingPatch"` but the target major version is less than `4`
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: RollingPatch reports independent failures
- **WHEN** an update changes `spec.runtime` with `"RollingPatch"` and both RollingPatch constraints fail
- **THEN** the system SHALL report both `spec.runtime` errors.

#### Scenario: LiveMigration rejects multi-region topology on create
- **WHEN** a create input sets `spec.migration.strategy` to `"LiveMigration"` and configures `spec.regions`
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`.

#### Scenario: LiveMigration rejects multi-region topology on update
- **WHEN** an update results in `spec.migration.strategy` equal to `"LiveMigration"` and `spec.regions` configured
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid` and message `LiveMigration strategy is not supported with multi-region topology`.

#### Scenario: LiveMigration permits non-downgrade version changes without regions
- **WHEN** an update changes `spec.runtime` to a non-downgrade catalog version, `spec.migration.strategy` is `"LiveMigration"`, and `spec.regions` is not configured
- **THEN** the system SHALL accept the version change and start a migration.
