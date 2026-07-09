## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud
> Extends: mesh-resource-management/add-access-security-model
> Extends: mesh-migration-strategies/add-mesh-migration-strategies
> Extends: vault-resource-management/add-vault-resource-management

### Requirement: Metadata tag persistence
The system SHALL support `metadata.tags` as an optional map of string keys to string values and SHALL persist every tag on mesh create, update, and describe output.

#### Scenario: Tags persisted
- **GIVEN** a mesh payload contains `metadata.tags`
- **WHEN** the mesh is created or updated
- **THEN** every tag is persisted and returned by `mesh describe`

### Requirement: Always-present operational output
The system SHALL include `spec.placement` and `status.telemetryProbe` in successful mesh create and describe output even when the input omits placement and telemetry tags. (adapts mesh-resource-management/add-meshctl-mesh-crud/mesh-defaulting)

#### Scenario: Placement and telemetry defaults appear
- **GIVEN** a mesh payload omits `spec.placement` and telemetry metadata tags
- **WHEN** the mesh is created
- **THEN** output includes defaulted `spec.placement`
- **AND** output includes `status.telemetryProbe`

### Requirement: Local region topology
The system SHALL support optional `spec.regions` for multi-region operation, SHALL treat omitted `spec.regions` as single-region operation, and SHALL require `spec.regions.local` with a non-empty `name` and an `expose.type` value of `Internal`, `DirectPort`, `Balancer`, or `Gateway` when `spec.regions` is present.

#### Scenario: Single-region mesh omits region conditions
- **GIVEN** a mesh payload omits `spec.regions`
- **WHEN** the mesh is created
- **THEN** the mesh is treated as single-region
- **AND** no region readiness conditions are added

#### Scenario: Missing local region rejected
- **GIVEN** a mesh payload contains `spec.regions` without `spec.regions.local`
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.local` and `type` set to `required`

#### Scenario: Invalid local expose type rejected
- **GIVEN** a mesh payload sets `spec.regions.local.expose.type` to an unsupported value
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.local.expose.type` and `type` set to `invalid`

### Requirement: Local relay sizing
The system SHALL omit `spec.regions.local.maxRelayNodes` when unset and SHALL reject present values that are not integers greater than `0`, including `null`.

#### Scenario: Max relay nodes unset
- **GIVEN** a regional mesh payload omits `spec.regions.local.maxRelayNodes`
- **WHEN** the mesh is created
- **THEN** output omits `spec.regions.local.maxRelayNodes`

#### Scenario: Invalid max relay nodes rejected
- **GIVEN** a regional mesh payload sets `spec.regions.local.maxRelayNodes` to `0`, a non-integer, or `null`
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.local.maxRelayNodes` and `type` set to `invalid`

### Requirement: Inter-region encryption
The system SHALL validate `spec.regions.local.encryption` separately from `spec.access`, SHALL default `protocol` to `TLSv1.3` when encryption is present, SHALL accept only `TLSv1.2` or `TLSv1.3`, SHALL require `transportKeyStore` when local expose type is `Gateway`, and SHALL omit the encryption section from output when absent. (adapts mesh-resource-management/add-access-security-model/mesh-access-output)

#### Scenario: Gateway transport key store required
- **GIVEN** a regional mesh payload sets `spec.regions.local.expose.type` to `Gateway`
- **AND** `spec.regions.local.encryption` omits `transportKeyStore`
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.local.encryption.transportKeyStore` and `type` set to `required`

#### Scenario: Invalid encryption protocol rejected
- **GIVEN** a regional mesh payload sets `spec.regions.local.encryption.protocol` to an unsupported value
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.local.encryption.protocol` and `type` set to `invalid`

#### Scenario: Missing trust store warns
- **GIVEN** a regional mesh payload includes `spec.regions.local.encryption`
- **AND** the encryption section omits `trustStore`
- **WHEN** the mesh is created or updated
- **THEN** the operation succeeds with a non-fatal warning

### Requirement: Encryption key store shape
The system SHALL require every `transportKeyStore`, `relayKeyStore`, and `trustStore` object under `spec.regions.local.encryption` to include `secretRef`, `alias`, and `filename`.

#### Scenario: Missing key store sub-field rejected
- **GIVEN** a regional mesh payload includes an encryption key store object
- **AND** that object omits `secretRef`, `alias`, or `filename`
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.local.encryption.<store>.<field>` and `type` set to `required`

#### Scenario: Non-object encryption rejected
- **GIVEN** a regional mesh payload sets `spec.regions.local.encryption` to a non-object value
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.local.encryption` and `type` set to `invalid`

### Requirement: Regional discovery policy
The system SHALL default `spec.regions.local.discovery` to relay discovery with enabled heartbeat interval `10000` and timeout `30000` when `spec.regions` is present, SHALL require a present discovery section to be an object, SHALL require discovery `type` to be `relay`, and SHALL require `heartbeat.interval` to be strictly less than `heartbeat.timeout`.

#### Scenario: Regional discovery defaults
- **GIVEN** a regional mesh payload omits `spec.regions.local.discovery`
- **WHEN** the mesh is created
- **THEN** output includes relay discovery with heartbeat enabled, interval `10000`, and timeout `30000`

#### Scenario: Invalid discovery type rejected
- **GIVEN** a regional mesh payload sets `spec.regions.local.discovery.type` to a value other than `relay`
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.local.discovery.type` and `type` set to `invalid`

#### Scenario: Heartbeat interval rejected
- **GIVEN** a regional mesh payload sets heartbeat interval greater than or equal to heartbeat timeout
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.local.discovery.heartbeat` and `type` set to `invalid`

### Requirement: Remote region references
The system SHALL support `spec.regions.remotes` as an optional ordered array, SHALL allow the array to be empty, SHALL preserve declaration order, SHALL omit optional remote fields when unset, and SHALL reject duplicate remote names on the later entry index.

#### Scenario: Remotes preserve order
- **GIVEN** a regional mesh payload includes multiple `spec.regions.remotes` entries
- **WHEN** the mesh is created or described
- **THEN** the remote entries are returned in declaration order
- **AND** unset optional fields are omitted

#### Scenario: Duplicate remote rejected
- **GIVEN** a regional mesh payload includes a later remote entry whose `name` matches an earlier remote entry
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.regions.remotes[<index>].name` and `type` set to `duplicate`

### Requirement: Region readiness conditions
The system SHALL add `DiscoveryRelayReady` and `RegionViewFormed` conditions with `status` set to `False` and empty `message` when `spec.regions` is present, SHALL sort the full conditions array alphabetically by `type`, and SHALL NOT include those conditions in `status.stable` calculation.

#### Scenario: Regional conditions added and sorted
- **GIVEN** a mesh payload contains `spec.regions`
- **WHEN** the mesh is created
- **THEN** status conditions include `DiscoveryRelayReady` and `RegionViewFormed` with `status` set to `False` and empty `message`
- **AND** the full conditions array is sorted alphabetically by `type`

#### Scenario: Regional conditions do not affect stable
- **GIVEN** a regional mesh has `DiscoveryRelayReady` and `RegionViewFormed` set to `False`
- **WHEN** `status.stable` is calculated
- **THEN** stability depends only on `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration`

### Requirement: Regional migration restriction
The system SHALL reject `spec.migration.strategy` value `LiveMigration` when `spec.regions` is present on create and update, with `field` set to `spec.migration.strategy`, `type` set to `invalid`, and `message` set to `LiveMigration strategy is not supported with multi-region topology`. (adapts mesh-migration-strategies/add-mesh-migration-strategies/migration-strategy-values)

#### Scenario: LiveMigration rejected with regions
- **GIVEN** a mesh payload sets `spec.migration.strategy` to `LiveMigration`
- **AND** the payload contains `spec.regions`
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.migration.strategy`
- **AND** `type` is set to `invalid`
- **AND** `message` is set to `LiveMigration strategy is not supported with multi-region topology`

### Requirement: Telemetry probe derivation
The system SHALL always include `status.telemetryProbe`, SHALL treat absent `mesh.io/telemetry` metadata tag as enabled, SHALL use tag value `true` to enable telemetry and `false` to disable telemetry, and SHALL derive optional label arrays from comma-separated `mesh.io/targetLabels`, `mesh.io/probeTargetLabels`, and `mesh.io/instanceLabels` tags while preserving list order.

#### Scenario: Telemetry enabled without labels
- **GIVEN** a mesh has no telemetry metadata tags
- **WHEN** the mesh is created or described
- **THEN** `status.telemetryProbe` is `{"enabled": true}`

#### Scenario: Telemetry labels derived
- **GIVEN** a mesh has `metadata.tags.mesh.io/targetLabels` set to `region,env`
- **WHEN** the mesh is created or described
- **THEN** `status.telemetryProbe.labels.targetLabels` is `["region", "env"]`

#### Scenario: Telemetry disabled
- **GIVEN** a mesh has `metadata.tags.mesh.io/telemetry` set to `false`
- **WHEN** the mesh is created or described
- **THEN** `status.telemetryProbe` is `{"enabled": false}`

### Requirement: Placement affinity defaults and validation
The system SHALL support `spec.placement.affinity`, SHALL default affinity `type` to `preferred` and `scope` to `node`, SHALL include the defaulted placement in output, and SHALL reject non-object placement sections or unsupported affinity values. (adapts mesh-resource-management/add-access-security-model/mesh-defaulting)

#### Scenario: Placement defaulted
- **GIVEN** a mesh payload omits `spec.placement`
- **WHEN** the mesh is created or described
- **THEN** output includes `spec.placement.affinity.type` set to `preferred`
- **AND** `spec.placement.affinity.scope` set to `node`

#### Scenario: Invalid placement rejected
- **GIVEN** a mesh payload sets `spec.placement` or `spec.placement.affinity` to a non-object value
- **OR** sets affinity `type` or `scope` to an unsupported value
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with the matching `spec.placement` field and `type` set to `invalid`

### Requirement: Config bundle refresh tracking
The system SHALL support optional `spec.configBundleRef`, SHALL require a present create-time value to be a string, SHALL preserve the stored value when update omits the field, SHALL clear the stored value when update sets the field to `null`, and SHALL include transient `status.configRefresh` only in the update response that changes, adds, or clears the value. (adapts mesh-migration-strategies/add-mesh-migration-strategies/active-migration-updates-and-rollback)

#### Scenario: Invalid create-time config bundle rejected
- **GIVEN** a create payload sets `spec.configBundleRef` to a non-string value
- **WHEN** the mesh is created
- **THEN** the operation is rejected with `field` set to `spec.configBundleRef` and `type` set to `invalid`

#### Scenario: Omitted update keeps config bundle
- **GIVEN** a mesh has a stored `spec.configBundleRef`
- **WHEN** the mesh is updated without `spec.configBundleRef`
- **THEN** the stored value is preserved
- **AND** `status.configRefresh` is omitted

#### Scenario: Config bundle change emits transient refresh
- **GIVEN** a mesh has a stored `spec.configBundleRef`
- **WHEN** the mesh is updated to a different string value or to `null`
- **THEN** the update response includes `status.configRefresh` with `currentRef`, `pending` set to `true`, and `previousRef`
- **AND** later describe output omits `status.configRefresh`

### Requirement: Extension references
The system SHALL support `spec.extensions` as an optional ordered array of objects, SHALL preserve declaration order, SHALL require each entry to set exactly one of `url` or `artifact`, and SHALL omit `integrity` when unset.

#### Scenario: Extension order preserved
- **GIVEN** a mesh payload includes multiple `spec.extensions` entries
- **WHEN** the mesh is created or described
- **THEN** the extension entries are returned in declaration order
- **AND** entries without `integrity` omit that field

#### Scenario: Invalid extension rejected
- **GIVEN** a mesh payload includes an extension entry that sets both `url` and `artifact` or sets neither
- **WHEN** the mesh is created or updated
- **THEN** the operation is rejected with `field` set to `spec.extensions[<index>]`
- **AND** `type` is set to `invalid`
- **AND** `message` is set to `exactly one of 'url' or 'artifact' must be set`

### Requirement: JSON diagnostics
The system SHALL report all validation errors and non-fatal warnings for multi-region operational policy behavior using the existing JSON error and warning formats.

#### Scenario: Required and invalid diagnostics
- **GIVEN** a mesh payload violates a multi-region operational policy requirement
- **WHEN** the mesh is created or updated
- **THEN** the response uses the existing JSON diagnostic format
- **AND** the diagnostic includes the specified `field`, `type`, and `message` when a message is defined
