## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud

### Requirement: Always-present operational output
The system SHALL include defaulted `spec.placement` and `status.telemetryProbe` in every successful mesh create and describe output while preserving omitted fields that have no defaults as absent. (adapts mesh-resource-management/add-meshctl-mesh-crud/mesh-defaulting)

#### Scenario: Create output includes defaulted operational fields
- **GIVEN** a valid mesh create input omits `spec.placement` and telemetry metadata tags
- **WHEN** the mesh is created
- **THEN** the JSON output includes `spec.placement.affinity.type` set to `"preferred"` and `spec.placement.affinity.scope` set to `"node"`
- **AND** the JSON output includes `status.telemetryProbe` set to `{"enabled": true}`

#### Scenario: Describe output includes defaulted operational fields
- **GIVEN** a stored mesh was created without `spec.placement` and without telemetry metadata tags
- **WHEN** the mesh is described
- **THEN** the JSON output includes the defaulted placement affinity
- **AND** the JSON output includes `status.telemetryProbe` set to `{"enabled": true}`

### Requirement: Metadata tag persistence
The system SHALL accept optional `metadata.tags` as a map of string keys to string values and persist every tag on successful create and update.

#### Scenario: Tags are persisted
- **GIVEN** a valid mesh input includes `metadata.tags`
- **WHEN** the mesh is created or updated
- **THEN** later describe output includes every supplied tag key and value unchanged

### Requirement: Region topology configuration
The system SHALL support optional `spec.regions` for multi-region operation and require `spec.regions.local` when `spec.regions` is present.

#### Scenario: Omitted regions remain single-region
- **GIVEN** a valid mesh input omits `spec.regions`
- **WHEN** the mesh is created
- **THEN** the mesh is treated as single-region
- **AND** region-specific conditions are not added to `status.conditions`

#### Scenario: Regions require local region
- **GIVEN** a mesh input includes `spec.regions` without `spec.regions.local`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local` and type `required`

### Requirement: Local region validation
The system SHALL validate `spec.regions.local.name`, `spec.regions.local.expose.type`, and optional `spec.regions.local.maxRelayNodes` when `spec.regions` is present. (adapts mesh-resource-management/add-meshctl-mesh-crud/mesh-field-validation)

#### Scenario: Local region requires name and expose type
- **GIVEN** a mesh input includes `spec.regions.local` without a non-empty `name` or without `expose.type`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.name` and type `required` for the missing name
- **AND** validation fails with field `spec.regions.local.expose.type` and type `required` for the missing expose type

#### Scenario: Local region rejects invalid expose type
- **GIVEN** a mesh input includes `spec.regions.local.expose.type` outside `"Internal"`, `"DirectPort"`, `"Balancer"`, and `"Gateway"`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.expose.type` and type `invalid`

#### Scenario: Local region max relay nodes must be positive
- **GIVEN** a mesh input sets `spec.regions.local.maxRelayNodes` to `null`, a non-integer, zero, or a negative integer
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.maxRelayNodes` and type `invalid`

#### Scenario: Unset max relay nodes is omitted
- **GIVEN** a valid multi-region mesh input omits `spec.regions.local.maxRelayNodes`
- **WHEN** the mesh is created or described
- **THEN** `spec.regions.local.maxRelayNodes` is absent from the JSON output

### Requirement: Inter-region encryption validation
The system SHALL validate optional `spec.regions.local.encryption` separately from `spec.access`, default its `protocol` to `"TLSv1.3"` when present, and support `"TLSv1.2"` and `"TLSv1.3"` only.

#### Scenario: Encryption section is omitted when absent
- **GIVEN** a valid multi-region mesh input omits `spec.regions.local.encryption`
- **WHEN** the mesh is created or described
- **THEN** `spec.regions.local.encryption` is absent from the JSON output

#### Scenario: Encryption section must be an object
- **GIVEN** a mesh input sets `spec.regions.local.encryption` to a non-object value
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.encryption` and type `invalid`

#### Scenario: Encryption protocol is defaulted and validated
- **GIVEN** a valid mesh input includes `spec.regions.local.encryption` without `protocol`
- **WHEN** the mesh is created
- **THEN** output includes `spec.regions.local.encryption.protocol` set to `"TLSv1.3"`

#### Scenario: Invalid encryption protocol is rejected
- **GIVEN** a mesh input sets `spec.regions.local.encryption.protocol` outside `"TLSv1.2"` and `"TLSv1.3"`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.encryption.protocol` and type `invalid`

#### Scenario: Gateway expose requires transport key store
- **GIVEN** a mesh input sets `spec.regions.local.expose.type` to `"Gateway"` and includes encryption without `transportKeyStore`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.encryption.transportKeyStore` and type `required`

#### Scenario: Key store objects require all sub-fields
- **GIVEN** a mesh input includes `transportKeyStore`, `relayKeyStore`, or `trustStore` without `secretRef`, `alias`, or `filename`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.encryption.<store>.<field>` and type `required`

#### Scenario: Missing trust store emits warning
- **GIVEN** a valid mesh input includes `spec.regions.local.encryption` without `trustStore`
- **WHEN** the mesh is created or updated
- **THEN** the command succeeds
- **AND** the JSON response includes a non-fatal warning for the missing `trustStore`

### Requirement: Region discovery defaults and validation
The system SHALL default `spec.regions.local.discovery` to relay heartbeat settings when `spec.regions` is present and SHALL validate user-supplied discovery configuration.

#### Scenario: Multi-region discovery defaults to relay heartbeat
- **GIVEN** a valid mesh input includes `spec.regions` and omits `spec.regions.local.discovery`
- **WHEN** the mesh is created
- **THEN** output includes discovery type `"relay"`
- **AND** output includes heartbeat `enabled: true`, `interval: 10000`, and `timeout: 30000`

#### Scenario: Discovery must be an object
- **GIVEN** a mesh input sets `spec.regions.local.discovery` to a non-object value
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.discovery` and type `invalid`

#### Scenario: Discovery type must be relay
- **GIVEN** a mesh input sets `spec.regions.local.discovery.type` to a value other than `"relay"`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.discovery.type` and type `invalid`

#### Scenario: Heartbeat interval must be less than timeout
- **GIVEN** a mesh input sets `spec.regions.local.discovery.heartbeat.interval` greater than or equal to `spec.regions.local.discovery.heartbeat.timeout`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.local.discovery.heartbeat` and type `invalid`

### Requirement: Remote region preservation and validation
The system SHALL accept optional `spec.regions.remotes` as an array, preserve declaration order, omit unset optional fields, and reject duplicate remote names.

#### Scenario: Remote region order is preserved
- **GIVEN** a valid mesh input includes multiple `spec.regions.remotes` entries
- **WHEN** the mesh is created or described
- **THEN** the JSON output preserves the declaration order of the remote entries
- **AND** optional fields `credentialRef`, `namespace`, and `clusterRef` are omitted when unset

#### Scenario: Empty remote region array is valid
- **GIVEN** a valid mesh input sets `spec.regions.remotes` to an empty array
- **WHEN** the mesh is created
- **THEN** the JSON output includes the empty remote array

#### Scenario: Duplicate remote names are rejected
- **GIVEN** a mesh input includes a later remote entry with a name already used by an earlier remote entry
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.regions.remotes[<index>].name` and type `duplicate` for the later entry index

### Requirement: Region status conditions
The system SHALL add `DiscoveryRelayReady` and `RegionViewFormed` conditions when `spec.regions` is present, sort all status conditions alphabetically by `type`, and keep `status.stable` based only on `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration`.

#### Scenario: Multi-region conditions are initialized and sorted
- **GIVEN** a valid mesh input includes `spec.regions`
- **WHEN** the mesh is created
- **THEN** `status.conditions` includes `DiscoveryRelayReady` with status `"False"` and empty message
- **AND** `status.conditions` includes `RegionViewFormed` with status `"False"` and empty message
- **AND** the full conditions array is sorted alphabetically by `type`

#### Scenario: Region conditions do not affect stable status
- **GIVEN** a multi-region mesh has `DiscoveryRelayReady` and `RegionViewFormed` set to `"False"`
- **WHEN** `status.stable` is computed
- **THEN** only `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration` affect the result

### Requirement: Multi-region migration restriction
The system SHALL reject `spec.migration.strategy` set to `"LiveMigration"` on create and update when `spec.regions` is present.

#### Scenario: Live migration is rejected for multi-region meshes
- **GIVEN** a mesh input includes `spec.regions` and sets `spec.migration.strategy` to `"LiveMigration"`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.migration.strategy`, type `invalid`, and message `"LiveMigration strategy is not supported with multi-region topology"`

### Requirement: Telemetry tags and probe output
The system SHALL derive `status.telemetryProbe` from `metadata.tags` using `mesh.io/telemetry`, `mesh.io/targetLabels`, `mesh.io/probeTargetLabels`, and `mesh.io/instanceLabels`.

#### Scenario: Telemetry defaults to enabled
- **GIVEN** a valid mesh has no `mesh.io/telemetry` tag
- **WHEN** the mesh is created or described
- **THEN** `status.telemetryProbe` is `{"enabled": true}` unless label tags are present

#### Scenario: Telemetry can be disabled
- **GIVEN** a valid mesh has metadata tag `mesh.io/telemetry` set to `"false"`
- **WHEN** the mesh is created or described
- **THEN** `status.telemetryProbe` is `{"enabled": false}`

#### Scenario: Telemetry labels preserve list order
- **GIVEN** a valid mesh has telemetry label tags containing comma-separated values
- **WHEN** the mesh is created or described
- **THEN** `status.telemetryProbe.labels` includes only categories whose tags are set
- **AND** each label list preserves the comma-separated order from the tag value

### Requirement: Placement affinity defaults and validation
The system SHALL support `spec.placement.affinity` with default `type` `"preferred"` and default `scope` `"node"` and validate placement sections when present. (adapts mesh-resource-management/add-access-security-model/mesh-defaulting)

#### Scenario: Placement defaults are included
- **GIVEN** a valid mesh input omits `spec.placement`
- **WHEN** the mesh is created or described
- **THEN** output includes `spec.placement.affinity.type` set to `"preferred"`
- **AND** output includes `spec.placement.affinity.scope` set to `"node"`

#### Scenario: Placement section must be an object
- **GIVEN** a mesh input sets `spec.placement` to a non-object value
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.placement` and type `invalid`

#### Scenario: Placement affinity must be an object
- **GIVEN** a mesh input sets `spec.placement.affinity` to a non-object value
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.placement.affinity` and type `invalid`

#### Scenario: Placement affinity values are constrained
- **GIVEN** a mesh input sets `spec.placement.affinity.type` outside `"preferred"` and `"required"` or sets `spec.placement.affinity.scope` outside `"node"` and `"zone"`
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.placement.affinity.type` or `spec.placement.affinity.scope` and type `invalid`

### Requirement: Config bundle reference refresh tracking
The system SHALL validate optional `spec.configBundleRef` on create and SHALL emit transient `status.configRefresh` only in the update response that changes, adds, or clears the stored config bundle reference.

#### Scenario: Create validates config bundle reference
- **GIVEN** a mesh create input includes `spec.configBundleRef` with a non-string value
- **WHEN** the mesh is created
- **THEN** validation fails with field `spec.configBundleRef` and type `invalid`

#### Scenario: Update omission keeps stored config bundle reference
- **GIVEN** a stored mesh has `spec.configBundleRef`
- **WHEN** an update omits `spec.configBundleRef`
- **THEN** the stored value remains unchanged
- **AND** `status.configRefresh` is absent from the update response

#### Scenario: Update change emits transient config refresh
- **GIVEN** a stored mesh has `spec.configBundleRef` set to a string or absent
- **WHEN** an update changes the value, adds the first value, or sets `spec.configBundleRef` to `null`
- **THEN** the update response includes `status.configRefresh.currentRef`, `status.configRefresh.pending` set to `true`, and `status.configRefresh.previousRef`
- **AND** later describe output omits `status.configRefresh`

### Requirement: Extension source validation
The system SHALL accept optional ordered `spec.extensions` entries and require each entry to set exactly one of `url` or `artifact`, with optional `integrity` omitted when unset. (adapts mesh-resource-management/add-meshctl-mesh-crud/mesh-field-validation)

#### Scenario: Extension order and optional fields are preserved
- **GIVEN** a valid mesh input includes multiple extension entries
- **WHEN** the mesh is created or described
- **THEN** `spec.extensions` preserves declaration order
- **AND** `integrity` is omitted for entries where it is unset

#### Scenario: Extension source is exclusive and required
- **GIVEN** a mesh input includes an extension entry that sets both `url` and `artifact` or sets neither
- **WHEN** the mesh is created or updated
- **THEN** validation fails with field `spec.extensions[<index>]`, type `invalid`, and message `"exactly one of 'url' or 'artifact' must be set"`

### Requirement: JSON errors and warnings
The system SHALL report validation failures using JSON error objects and non-fatal policy notices using JSON warning objects.

#### Scenario: Validation failures use documented JSON error fields
- **GIVEN** a mesh input violates a documented multi-region operational policy
- **WHEN** the mesh is created or updated
- **THEN** the command returns JSON errors containing the documented `field`, `type`, and any required `message`

#### Scenario: Warnings do not prevent success
- **GIVEN** a mesh input triggers only a documented warning
- **WHEN** the mesh is created or updated
- **THEN** the command succeeds
- **AND** the JSON response includes the warning object
