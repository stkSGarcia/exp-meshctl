## ADDED Requirements

### Requirement: Multi-region spec block
The mesh spec SHALL support an optional `spec.regions` block. When absent, the mesh is single-region and no region conditions are added. When present, `spec.regions.local` SHALL be required.

#### Scenario: Single-region mesh — no regions block
- **WHEN** `spec.regions` is absent
- **THEN** the output contains no `DiscoveryRelayReady` or `RegionViewFormed` conditions and `spec.regions` is absent from output

#### Scenario: Regions present without local — rejected
- **WHEN** `spec.regions` is present but `spec.regions.local` is absent
- **THEN** output error `{"field":"spec.regions.local","type":"required","message":"<msg>"}`

---

### Requirement: Local region fields
`spec.regions.local.name` SHALL be required and non-empty. `spec.regions.local.expose.type` SHALL be required and SHALL be one of `"Internal"`, `"DirectPort"`, `"Balancer"`, `"Gateway"`. `spec.regions.local.maxRelayNodes`, when present, SHALL be a positive integer greater than `0`; `null` is invalid.

#### Scenario: Local name required
- **WHEN** `spec.regions.local.name` is absent or empty
- **THEN** output error `{"field":"spec.regions.local.name","type":"required","message":"<msg>"}`

#### Scenario: Local expose type required
- **WHEN** `spec.regions.local.expose.type` is absent
- **THEN** output error `{"field":"spec.regions.local.expose.type","type":"required","message":"<msg>"}`

#### Scenario: Invalid local expose type
- **WHEN** `spec.regions.local.expose.type` is not one of the valid values
- **THEN** output error `{"field":"spec.regions.local.expose.type","type":"invalid","message":"<msg>"}`

#### Scenario: Valid local configuration accepted
- **WHEN** `spec.regions.local.name` is non-empty and `expose.type` is `"Internal"`
- **THEN** the local region block is accepted

#### Scenario: maxRelayNodes null rejected
- **WHEN** `spec.regions.local.maxRelayNodes` is `null`
- **THEN** output error `{"field":"spec.regions.local.maxRelayNodes","type":"invalid","message":"<msg>"}`

#### Scenario: maxRelayNodes zero rejected
- **WHEN** `spec.regions.local.maxRelayNodes` is `0` or negative
- **THEN** output error `{"field":"spec.regions.local.maxRelayNodes","type":"invalid","message":"<msg>"}`

#### Scenario: maxRelayNodes valid
- **WHEN** `spec.regions.local.maxRelayNodes` is a positive integer
- **THEN** it is persisted and included in output

#### Scenario: maxRelayNodes absent omitted from output
- **WHEN** `spec.regions.local.maxRelayNodes` is not set
- **THEN** `maxRelayNodes` is absent from output

---

### Requirement: Inter-region encryption
`spec.regions.local.encryption` is optional. When absent, the encryption section is omitted from output. When present, it SHALL be an object. `protocol` defaults to `"TLSv1.3"` and SHALL be one of `"TLSv1.2"` or `"TLSv1.3"`. When expose type is `"Gateway"`, `transportKeyStore` SHALL be required. When the encryption section exists and `trustStore` is absent, a non-fatal warning SHALL be emitted. Each key store object SHALL have `secretRef`, `alias`, and `filename` (all required strings).

#### Scenario: Encryption absent — omitted from output
- **WHEN** `spec.regions.local.encryption` is not present
- **THEN** the encryption block is absent from output

#### Scenario: Encryption must be an object
- **WHEN** `spec.regions.local.encryption` is a scalar or list
- **THEN** output error `{"field":"spec.regions.local.encryption","type":"invalid","message":"<msg>"}`

#### Scenario: Protocol defaults to TLSv1.3
- **WHEN** `spec.regions.local.encryption` is present without `protocol`
- **THEN** `protocol` is `"TLSv1.3"` in output

#### Scenario: Invalid protocol rejected
- **WHEN** `spec.regions.local.encryption.protocol` is not `"TLSv1.2"` or `"TLSv1.3"`
- **THEN** output error `{"field":"spec.regions.local.encryption.protocol","type":"invalid","message":"<msg>"}`

#### Scenario: Gateway requires transportKeyStore
- **WHEN** expose type is `"Gateway"` and `spec.regions.local.encryption.transportKeyStore` is absent
- **THEN** output error `{"field":"spec.regions.local.encryption.transportKeyStore","type":"required","message":"<msg>"}`

#### Scenario: Missing trustStore emits warning
- **WHEN** `spec.regions.local.encryption` is present and `trustStore` is absent
- **THEN** the operation succeeds and a warning is emitted (non-fatal)

#### Scenario: Key store sub-fields required
- **WHEN** a key store object is present but `secretRef`, `alias`, or `filename` is absent
- **THEN** output error `{"field":"spec.regions.local.encryption.<store>.<field>","type":"required","message":"<msg>"}`

#### Scenario: relayKeyStore optional
- **WHEN** `spec.regions.local.encryption.relayKeyStore` is absent
- **THEN** no error is produced for that field

---

### Requirement: Relay discovery
When `spec.regions` is present, discovery defaults to `{"type":"relay","heartbeat":{"enabled":true,"interval":10000,"timeout":30000}}`. When `spec.regions.local.discovery` is provided, it SHALL be an object, `discovery.type` SHALL be `"relay"`, and `heartbeat.interval` SHALL be strictly less than `heartbeat.timeout`.

#### Scenario: Discovery defaulted when regions present
- **WHEN** `spec.regions` is present and `spec.regions.local.discovery` is absent
- **THEN** output includes `spec.regions.local.discovery = {"type":"relay","heartbeat":{"enabled":true,"interval":10000,"timeout":30000}}`

#### Scenario: Discovery must be an object
- **WHEN** `spec.regions.local.discovery` is a scalar
- **THEN** output error `{"field":"spec.regions.local.discovery","type":"invalid","message":"<msg>"}`

#### Scenario: Discovery type must be relay
- **WHEN** `spec.regions.local.discovery.type` is not `"relay"`
- **THEN** output error `{"field":"spec.regions.local.discovery.type","type":"invalid","message":"<msg>"}`

#### Scenario: Heartbeat interval must be less than timeout
- **WHEN** `heartbeat.interval` >= `heartbeat.timeout`
- **THEN** output error `{"field":"spec.regions.local.discovery.heartbeat","type":"invalid","message":"<msg>"}`

---

### Requirement: Remote regions
`spec.regions.remotes` SHALL be an optional array. Each entry SHALL require `name` (string) and `url` (string). `credentialRef`, `namespace`, and `clusterRef` are optional and SHALL be omitted from output when unset. Remote entries SHALL be output in declaration order. Duplicate `name` values on later entries SHALL be invalid.

#### Scenario: Empty remotes array accepted
- **WHEN** `spec.regions.remotes` is an empty array
- **THEN** no error is produced

#### Scenario: Remote name required
- **WHEN** a remote entry is missing `name`
- **THEN** output error with `type: "required"` for the name field

#### Scenario: Remote url required
- **WHEN** a remote entry has `name` but missing `url`
- **THEN** output error with `type: "required"` for the url field

#### Scenario: Duplicate remote name rejected
- **WHEN** two remote entries share the same `name`
- **THEN** output error `{"field":"spec.regions.remotes[<index>].name","type":"duplicate","message":"<msg>"}` for the later entry

#### Scenario: Declaration order preserved
- **WHEN** remotes are provided in a specific order
- **THEN** output preserves that order

#### Scenario: Optional remote fields omitted when unset
- **WHEN** `credentialRef`, `namespace`, and `clusterRef` are absent from a remote entry
- **THEN** those fields are absent from output

---

### Requirement: Region conditions
When `spec.regions` is present, `DiscoveryRelayReady` and `RegionViewFormed` conditions SHALL be added to `status.conditions` with initial `status: "False"` and empty `message`. The full conditions array SHALL be sorted alphabetically by `type`. These conditions SHALL NOT affect `status.stable`.

#### Scenario: Region conditions added when regions present
- **WHEN** a mesh is created with `spec.regions`
- **THEN** `status.conditions` includes `{"type":"DiscoveryRelayReady","status":"False","message":""}` and `{"type":"RegionViewFormed","status":"False","message":""}`

#### Scenario: Region conditions sorted with other conditions
- **WHEN** a mesh has Healthy, PrechecksPassed, DiscoveryRelayReady, and RegionViewFormed conditions
- **THEN** `status.conditions` is sorted: `DiscoveryRelayReady`, `Healthy`, `PrechecksPassed`, `RegionViewFormed`

#### Scenario: status.stable not affected by region conditions
- **WHEN** only `DiscoveryRelayReady` and `RegionViewFormed` have `status: "False"` and no transient conditions are active
- **THEN** `status.stable = true`

#### Scenario: No region conditions for single-region mesh
- **WHEN** `spec.regions` is absent
- **THEN** `DiscoveryRelayReady` and `RegionViewFormed` are absent from `status.conditions`

---

### Requirement: LiveMigration restriction with regions
When `spec.regions` is present, `spec.migration.strategy = "LiveMigration"` SHALL be rejected on both create and update.

#### Scenario: LiveMigration rejected on create with regions
- **WHEN** `spec.regions` is present and `spec.migration.strategy` is `"LiveMigration"`
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}`

#### Scenario: LiveMigration rejected on update with regions
- **WHEN** a mesh with `spec.regions` is updated and `spec.migration.strategy` is set to `"LiveMigration"`
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}`
