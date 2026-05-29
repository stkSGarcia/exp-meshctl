## ADDED Requirements

### Requirement: Metadata tags
The system SHALL accept an optional `metadata.tags` field that is a map of string keys to string values, and SHALL persist every tag without modification.

#### Scenario: Tags preserved on create
- **WHEN** the create YAML includes `metadata.tags` with one or more string key-value pairs
- **THEN** the persisted resource includes the exact tags provided

#### Scenario: Tags absent when not provided
- **WHEN** the create YAML omits `metadata.tags`
- **THEN** the output resource does not include a `metadata.tags` field

---

### Requirement: Always-present placement output
The system SHALL include `spec.placement` in every create and describe output, applying defaults when the field is omitted from input.

#### Scenario: Placement defaulted when omitted
- **WHEN** the create YAML omits `spec.placement`
- **THEN** the output includes `"placement":{"affinity":{"type":"preferred","scope":"node"}}`

#### Scenario: Placement values preserved when provided
- **WHEN** the create YAML includes `spec.placement.affinity.type` and `spec.placement.affinity.scope`
- **THEN** the output reflects the provided values

#### Scenario: Non-object placement rejected
- **WHEN** `spec.placement` is present but not an object
- **THEN** output `{"errors":[{"field":"spec.placement","type":"invalid","message":"<msg>"}]}`

#### Scenario: Non-object placement affinity rejected
- **WHEN** `spec.placement.affinity` is present but not an object
- **THEN** output `{"errors":[{"field":"spec.placement.affinity","type":"invalid","message":"<msg>"}]}`

#### Scenario: Invalid placement affinity type rejected
- **WHEN** `spec.placement.affinity.type` is not one of `"preferred"` or `"required"`
- **THEN** output `{"errors":[{"field":"spec.placement.affinity.type","type":"invalid","message":"<msg>"}]}`

#### Scenario: Invalid placement affinity scope rejected
- **WHEN** `spec.placement.affinity.scope` is not one of `"node"` or `"zone"`
- **THEN** output `{"errors":[{"field":"spec.placement.affinity.scope","type":"invalid","message":"<msg>"}]}`

---

### Requirement: Always-present telemetry probe output
The system SHALL include `status.telemetryProbe` in every create and describe output, derived from `metadata.tags`.

#### Scenario: Telemetry enabled by default with no label tags
- **WHEN** no telemetry-related tags are set
- **THEN** `status.telemetryProbe` is `{"enabled":true}`

#### Scenario: Telemetry disabled via tag
- **WHEN** `metadata.tags["mesh.io/telemetry"]` is `"false"`
- **THEN** `status.telemetryProbe` is `{"enabled":false}`

#### Scenario: Telemetry with label tags
- **WHEN** `metadata.tags["mesh.io/targetLabels"]` is set to a comma-separated string
- **THEN** `status.telemetryProbe.labels.targetLabels` contains the items as an ordered list

#### Scenario: Only present label categories included
- **WHEN** only `mesh.io/probeTargetLabels` is set (not targetLabels or instanceLabels)
- **THEN** `status.telemetryProbe.labels` contains only `probeTargetLabels`

---

### Requirement: Config bundle reference
The system SHALL accept an optional `spec.configBundleRef` string on create, persist it, and apply update semantics that distinguish key-absent from key-present-null.

#### Scenario: configBundleRef set on create
- **WHEN** the create YAML includes `spec.configBundleRef` as a non-null string
- **THEN** the value is persisted and included in output

#### Scenario: Invalid non-string configBundleRef on create
- **WHEN** the create YAML sets `spec.configBundleRef` to a non-string value
- **THEN** output `{"errors":[{"field":"spec.configBundleRef","type":"invalid","message":"<msg>"}]}`

#### Scenario: Omitting configBundleRef on update keeps stored value
- **WHEN** the update YAML omits `spec.configBundleRef` and a value was previously stored
- **THEN** the stored value is unchanged and no `status.configRefresh` is emitted

#### Scenario: Setting configBundleRef on update emits configRefresh
- **WHEN** the update YAML sets `spec.configBundleRef` to a new string value
- **THEN** `status.configRefresh` is included in the update response with `pending: true`, `currentRef` set to the new value, and `previousRef` set to the old value (or null)

#### Scenario: Nulling configBundleRef on update removes stored value and emits configRefresh
- **WHEN** the update YAML sets `spec.configBundleRef` to `null` and a value was previously stored
- **THEN** the stored field is removed and `status.configRefresh` is included with `currentRef: null`

#### Scenario: configRefresh absent from describe output
- **WHEN** a mesh is described after a configBundleRef change
- **THEN** `status.configRefresh` is not present in the output

---

### Requirement: Extensions list
The system SHALL accept an optional `spec.extensions` array and preserve declaration order in output.

#### Scenario: Extension with url persisted
- **WHEN** an extension entry has `url` set and `artifact` absent
- **THEN** the extension is included in output with `url` (and `integrity` if provided)

#### Scenario: Extension with artifact persisted
- **WHEN** an extension entry has `artifact` set and `url` absent
- **THEN** the extension is included in output with `artifact` (and `integrity` if provided)

#### Scenario: Extension with both url and artifact rejected
- **WHEN** an extension entry has both `url` and `artifact` set
- **THEN** output `{"errors":[{"field":"spec.extensions[<index>]","type":"invalid","message":"exactly one of 'url' or 'artifact' must be set"}]}`

#### Scenario: Extension with neither url nor artifact rejected
- **WHEN** an extension entry has neither `url` nor `artifact`
- **THEN** output `{"errors":[{"field":"spec.extensions[<index>]","type":"invalid","message":"exactly one of 'url' or 'artifact' must be set"}]}`

#### Scenario: Integrity omitted when unset
- **WHEN** an extension entry has no `integrity` field
- **THEN** the output entry does not include an `integrity` key

#### Scenario: Declaration order preserved
- **WHEN** two or more extensions are provided
- **THEN** they appear in the output in the same order as declared

---

### Requirement: Multi-region topology
The system SHALL accept an optional `spec.regions` block. When present, `spec.regions.local` is required. Single-region meshes (no `spec.regions`) receive no region conditions.

#### Scenario: Single-region mesh has no region conditions
- **WHEN** `spec.regions` is omitted
- **THEN** `status.conditions` does not contain `DiscoveryRelayReady` or `RegionViewFormed`

#### Scenario: Multi-region mesh requires local
- **WHEN** `spec.regions` is present but `spec.regions.local` is absent
- **THEN** output `{"errors":[{"field":"spec.regions.local","type":"required","message":"<msg>"}]}`

#### Scenario: Local region name required
- **WHEN** `spec.regions.local` is present but `spec.regions.local.name` is absent or empty
- **THEN** output `{"errors":[{"field":"spec.regions.local.name","type":"required","message":"<msg>"}]}`

#### Scenario: Local expose type required
- **WHEN** `spec.regions.local` is present but `spec.regions.local.expose.type` is absent
- **THEN** output `{"errors":[{"field":"spec.regions.local.expose.type","type":"required","message":"<msg>"}]}`

#### Scenario: Invalid local expose type rejected
- **WHEN** `spec.regions.local.expose.type` is not one of `"Internal"`, `"DirectPort"`, `"Balancer"`, `"Gateway"`
- **THEN** output `{"errors":[{"field":"spec.regions.local.expose.type","type":"invalid","message":"<msg>"}]}`

#### Scenario: maxRelayNodes must be positive integer when present
- **WHEN** `spec.regions.local.maxRelayNodes` is present and is not a positive integer
- **THEN** output `{"errors":[{"field":"spec.regions.local.maxRelayNodes","type":"invalid","message":"<msg>"}]}`

#### Scenario: maxRelayNodes omitted when unset
- **WHEN** `spec.regions.local.maxRelayNodes` is not provided
- **THEN** the field does not appear in output

#### Scenario: Region conditions added for multi-region mesh
- **WHEN** `spec.regions` is present and valid
- **THEN** `status.conditions` contains `DiscoveryRelayReady` with `status: "False"` and `RegionViewFormed` with `status: "False"`

#### Scenario: Full conditions array sorted alphabetically
- **WHEN** region conditions are added alongside existing conditions
- **THEN** `status.conditions` is sorted by `type` ascending

#### Scenario: Region conditions do not affect stable
- **WHEN** `DiscoveryRelayReady` or `RegionViewFormed` is `"False"`
- **THEN** `status.stable` is still computed only from `Healthy`, `PrechecksPassed`, `GracefulShutdown`, `Scaling`, and `Migration`

---

### Requirement: Inter-region encryption
The system SHALL accept an optional `spec.regions.local.encryption` block with protocol, key stores, and trust store. When expose type is `"Gateway"`, `transportKeyStore` is required.

#### Scenario: Encryption omitted when absent
- **WHEN** `spec.regions.local.encryption` is not provided
- **THEN** the encryption block does not appear in output

#### Scenario: Non-object encryption section rejected
- **WHEN** `spec.regions.local.encryption` is present but not an object
- **THEN** output `{"errors":[{"field":"spec.regions.local.encryption","type":"invalid","message":"<msg>"}]}`

#### Scenario: Default protocol applied when absent
- **WHEN** `spec.regions.local.encryption` is present and `protocol` is not provided
- **THEN** `protocol` defaults to `"TLSv1.3"`

#### Scenario: Invalid protocol rejected
- **WHEN** `spec.regions.local.encryption.protocol` is not `"TLSv1.2"` or `"TLSv1.3"`
- **THEN** output `{"errors":[{"field":"spec.regions.local.encryption.protocol","type":"invalid","message":"<msg>"}]}`

#### Scenario: Gateway expose type requires transportKeyStore
- **WHEN** expose type is `"Gateway"` and `spec.regions.local.encryption.transportKeyStore` is absent
- **THEN** output `{"errors":[{"field":"spec.regions.local.encryption.transportKeyStore","type":"required","message":"<msg>"}]}`

#### Scenario: Key store missing required sub-field rejected
- **WHEN** a key store object is present but any of `secretRef`, `alias`, or `filename` is absent
- **THEN** output `{"errors":[{"field":"spec.regions.local.encryption.<store>.<field>","type":"required","message":"<msg>"}]}`

#### Scenario: Missing trustStore emits warning
- **WHEN** `spec.regions.local.encryption` is present and `trustStore` is absent
- **THEN** a non-fatal warning is emitted

---

### Requirement: Region discovery
When `spec.regions` is present, the system SHALL default discovery to relay mode with standard heartbeat settings. Custom discovery values override the defaults.

#### Scenario: Default discovery injected when regions present
- **WHEN** `spec.regions` is provided without a `discovery` block
- **THEN** the output includes `spec.regions.local.discovery` with type `"relay"` and heartbeat `{enabled: true, interval: 10000, timeout: 30000}`

#### Scenario: Non-object discovery section rejected
- **WHEN** `spec.regions.local.discovery` is present but not an object
- **THEN** output `{"errors":[{"field":"spec.regions.local.discovery","type":"invalid","message":"<msg>"}]}`

#### Scenario: Non-relay discovery type rejected
- **WHEN** `spec.regions.local.discovery.type` is present and not `"relay"`
- **THEN** output `{"errors":[{"field":"spec.regions.local.discovery.type","type":"invalid","message":"<msg>"}]}`

#### Scenario: Heartbeat interval must be less than timeout
- **WHEN** `heartbeat.interval` is greater than or equal to `heartbeat.timeout`
- **THEN** output `{"errors":[{"field":"spec.regions.local.discovery.heartbeat","type":"invalid","message":"<msg>"}]}`

---

### Requirement: Remote peers
The system SHALL accept an optional `spec.regions.remotes` array. Remote names must be unique within the array. Preserve declaration order.

#### Scenario: Empty remotes array accepted
- **WHEN** `spec.regions.remotes` is an empty array
- **THEN** the resource is accepted and the empty array appears in output

#### Scenario: Remote fields preserved
- **WHEN** a remote entry has all optional fields set
- **THEN** all provided fields appear in output in the same order

#### Scenario: Remote optional fields omitted when unset
- **WHEN** a remote entry omits `credentialRef`, `namespace`, or `clusterRef`
- **THEN** those keys do not appear in the output entry

#### Scenario: Duplicate remote name rejected on later entry
- **WHEN** two remote entries share the same `name`
- **THEN** output `{"errors":[{"field":"spec.regions.remotes[<index>].name","type":"duplicate","message":"<msg>"}]}` for the later index

---

### Requirement: LiveMigration restricted with regions
The system SHALL reject `spec.migration.strategy = "LiveMigration"` on both create and update when `spec.regions` is present.

#### Scenario: LiveMigration rejected on create with regions
- **WHEN** `spec.regions` is present and `spec.migration.strategy` is `"LiveMigration"`
- **THEN** output `{"errors":[{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}]}`

#### Scenario: LiveMigration rejected on update with regions
- **WHEN** the stored mesh has `spec.regions` and the update sets `spec.migration.strategy` to `"LiveMigration"`
- **THEN** output `{"errors":[{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}]}`
