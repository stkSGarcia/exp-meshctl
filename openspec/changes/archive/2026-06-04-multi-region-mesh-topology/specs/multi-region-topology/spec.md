## ADDED Requirements

### Requirement: regions-section-optional

`spec.regions` is optional. When absent, the mesh SHALL be treated as single-region and no region-related conditions SHALL be added.

#### Scenario: single-region mesh has no region conditions

- **GIVEN** a mesh created without `spec.regions`
- **WHEN** the create or describe response is produced
- **THEN** `status.conditions` SHALL NOT contain `DiscoveryRelayReady` or `RegionViewFormed`

---

### Requirement: local-region-required-when-regions-present

When `spec.regions` is present, `spec.regions.local` SHALL be required and non-null.

#### Scenario: missing local produces required error

- **GIVEN** a mesh input that includes `spec.regions` but omits `spec.regions.local`
- **WHEN** create or update is called
- **THEN** the system SHALL return a `required` error with `field = "spec.regions.local"`

---

### Requirement: local-name-required

`spec.regions.local.name` SHALL be required and non-empty when `spec.regions` is present.

#### Scenario: missing local name produces required error

- **GIVEN** a mesh input with `spec.regions.local` that omits `name`
- **WHEN** create or update is called
- **THEN** the system SHALL return a `required` error with `field = "spec.regions.local.name"`

---

### Requirement: local-expose-type-required-and-valid

`spec.regions.local.expose.type` SHALL be required when `spec.regions.local` is present. It SHALL be one of `"Internal"`, `"DirectPort"`, `"Balancer"`, or `"Gateway"`. Any other value is invalid.

#### Scenario: missing expose type produces required error

- **GIVEN** `spec.regions.local` is present but `spec.regions.local.expose.type` is absent
- **WHEN** create is called
- **THEN** the system SHALL return a `required` error with `field = "spec.regions.local.expose.type"`

#### Scenario: invalid expose type produces invalid error

- **GIVEN** `spec.regions.local.expose.type` is set to `"LoadBalancer"`
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.regions.local.expose.type"`

---

### Requirement: max-relay-nodes-validation

`spec.regions.local.maxRelayNodes` is optional. When present it SHALL be an integer strictly greater than `0`. `null` is invalid.

#### Scenario: zero maxRelayNodes is invalid

- **GIVEN** `spec.regions.local.maxRelayNodes` is set to `0`
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.regions.local.maxRelayNodes"`

#### Scenario: absent maxRelayNodes is omitted from output

- **GIVEN** `spec.regions.local.maxRelayNodes` is not set
- **WHEN** the response is produced
- **THEN** `maxRelayNodes` SHALL be absent from `spec.regions.local` in the output

---

### Requirement: inter-region-encryption-optional

`spec.regions.local.encryption` is optional. When absent it SHALL be omitted from output. When present it SHALL be an object.

#### Scenario: non-object encryption produces invalid error

- **GIVEN** `spec.regions.local.encryption` is set to a non-object value (e.g., a string)
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.regions.local.encryption"`

---

### Requirement: encryption-protocol-valid

When `spec.regions.local.encryption` is present, `protocol` SHALL default to `"TLSv1.3"`. When provided, it SHALL be one of `"TLSv1.2"` or `"TLSv1.3"`.

#### Scenario: invalid protocol produces invalid error

- **GIVEN** `spec.regions.local.encryption.protocol` is set to `"TLSv1.0"`
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.regions.local.encryption.protocol"`

---

### Requirement: gateway-requires-transport-key-store

When `spec.regions.local.expose.type` is `"Gateway"` and `spec.regions.local.encryption` is present, `transportKeyStore` SHALL be required.

#### Scenario: missing transportKeyStore for Gateway produces required error

- **GIVEN** `spec.regions.local.expose.type` is `"Gateway"` and `spec.regions.local.encryption` is present but `transportKeyStore` is absent
- **WHEN** create or update is called
- **THEN** the system SHALL return a `required` error with `field = "spec.regions.local.encryption.transportKeyStore"`

---

### Requirement: key-store-sub-fields-required

Each key store object (`transportKeyStore`, `relayKeyStore`, `trustStore`) SHALL have `secretRef`, `alias`, and `filename`, all required and non-empty.

#### Scenario: missing key store sub-field produces required error

- **GIVEN** `spec.regions.local.encryption.transportKeyStore` is present but `alias` is missing
- **WHEN** create is called
- **THEN** the system SHALL return a `required` error with `field = "spec.regions.local.encryption.transportKeyStore.alias"`

---

### Requirement: missing-trust-store-warning

When `spec.regions.local.encryption` is present and `trustStore` is absent, the system SHALL emit a non-fatal warning.

#### Scenario: encryption without trustStore emits warning

- **GIVEN** `spec.regions.local.encryption` is present with `transportKeyStore` but no `trustStore`
- **WHEN** create succeeds
- **THEN** the response SHALL include a warning referencing the missing `trustStore`

---

### Requirement: discovery-defaulted-when-regions-present

When `spec.regions` is present and `spec.regions.local.discovery` is absent, the system SHALL default discovery to:

```json
{
  "type": "relay",
  "heartbeat": {
    "enabled": true,
    "interval": 10000,
    "timeout": 30000
  }
}
```

#### Scenario: discovery defaulted for multi-region mesh

- **GIVEN** a multi-region mesh with no `spec.regions.local.discovery`
- **WHEN** create is called
- **THEN** `spec.regions.local.discovery` in the output SHALL equal the default relay discovery object

---

### Requirement: discovery-validation

When `spec.regions.local.discovery` is present, it SHALL be an object and `type` SHALL be `"relay"`. `heartbeat.interval` SHALL be strictly less than `heartbeat.timeout`.

#### Scenario: non-relay discovery type is invalid

- **GIVEN** `spec.regions.local.discovery.type` is set to `"gossip"`
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.regions.local.discovery.type"`

#### Scenario: interval >= timeout is invalid

- **GIVEN** `spec.regions.local.discovery.heartbeat.interval` equals `heartbeat.timeout`
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.regions.local.discovery.heartbeat"`

---

### Requirement: remotes-array-optional

`spec.regions.remotes` is optional. When present it may be empty. Declaration order SHALL be preserved in output. Optional fields (`credentialRef`, `namespace`, `clusterRef`) SHALL be omitted when unset.

#### Scenario: remotes order preserved

- **GIVEN** `spec.regions.remotes` contains entries in a specific order
- **WHEN** the response is produced
- **THEN** remotes SHALL appear in the same order as declared

#### Scenario: duplicate remote name is invalid

- **GIVEN** `spec.regions.remotes` contains two entries with the same `name`
- **WHEN** create is called
- **THEN** the system SHALL return a `duplicate` error with `field = "spec.regions.remotes[<index>].name"` pointing to the later duplicate

---

### Requirement: remote-required-fields

Each remote entry SHALL have `name` (string, required) and `url` (string, required).

#### Scenario: missing remote url produces required error

- **GIVEN** a remote entry with `name` but no `url`
- **WHEN** create is called
- **THEN** the system SHALL return a `required` error for that entry's `url`

---

### Requirement: region-conditions-added

When `spec.regions` is present, the system SHALL add both `DiscoveryRelayReady` and `RegionViewFormed` conditions to `status.conditions`. Each SHALL have initial `status: "False"` and empty `message`. The full conditions array SHALL be sorted alphabetically by `type`. These conditions SHALL NOT affect `status.stable`.

#### Scenario: region conditions present for multi-region mesh

- **GIVEN** a mesh created with `spec.regions`
- **WHEN** the create response is produced
- **THEN** `status.conditions` SHALL contain both `DiscoveryRelayReady` and `RegionViewFormed` with `status: "False"` and `message: ""`

#### Scenario: region conditions sorted with others

- **GIVEN** existing conditions like `Healthy` and `PrechecksPassed` plus the two region conditions
- **WHEN** the response is produced
- **THEN** all conditions SHALL appear in alphabetical order by `type`

---

### Requirement: live-migration-rejected-with-regions

When `spec.regions` is present, `spec.migration.strategy = "LiveMigration"` SHALL be rejected on both create and update. Use `field = "spec.migration.strategy"`, `type = "invalid"`, `message = "LiveMigration strategy is not supported with multi-region topology"`.

#### Scenario: LiveMigration rejected when regions configured

- **GIVEN** a mesh input with both `spec.regions` and `spec.migration.strategy = "LiveMigration"`
- **WHEN** create or update is called
- **THEN** the system SHALL return an `invalid` error with the specified message

