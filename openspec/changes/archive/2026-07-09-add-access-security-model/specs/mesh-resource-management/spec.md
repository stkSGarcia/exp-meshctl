## ADDED Requirements

### Requirement: Mesh access authentication
The system SHALL support authentication settings under `spec.access.authentication` and an optional `spec.access.credentialRef`.

#### Scenario: Authentication defaults to enabled with SHA-256
- **WHEN** a valid create input omits `spec.access.authentication.enabled` and `spec.access.authentication.digestAlgorithm`
- **THEN** the created resource SHALL include `spec.access.authentication.enabled` as `true` and `spec.access.authentication.digestAlgorithm` as `"SHA-256"`.

#### Scenario: Credential reference is preserved when authentication is enabled
- **WHEN** a valid create input includes `spec.access.credentialRef` while authentication is enabled
- **THEN** the created resource SHALL include `spec.access.credentialRef` with the provided value.

#### Scenario: Digest algorithm allows documented values
- **WHEN** `spec.access.authentication.digestAlgorithm` is present and is one of `"SHA-256"`, `"SHA-384"`, or `"SHA-512"`
- **THEN** the system SHALL accept the digest algorithm.

#### Scenario: Invalid digest algorithm is rejected
- **WHEN** `spec.access.authentication.digestAlgorithm` is present and is not one of `"SHA-256"`, `"SHA-384"`, or `"SHA-512"`
- **THEN** the system SHALL report field `spec.access.authentication.digestAlgorithm` with type `invalid`.

#### Scenario: Disabled authentication omits digest algorithm
- **WHEN** a mesh has `spec.access.authentication.enabled` equal to `false`
- **THEN** the returned resource SHALL include `spec.access.authentication` with only `enabled` equal to `false`.

#### Scenario: Digest algorithm is forbidden when authentication is disabled
- **WHEN** authentication is disabled and `spec.access.authentication.digestAlgorithm` is present
- **THEN** the system SHALL report field `spec.access.authentication.digestAlgorithm` with type `forbidden`.

#### Scenario: Credential reference is forbidden when authentication is disabled
- **WHEN** authentication is disabled and `spec.access.credentialRef` is present
- **THEN** the system SHALL report field `spec.access.credentialRef` with type `forbidden`.

### Requirement: Mesh access permissions
The system SHALL support optional permission role validation under `spec.access.permissions`.

#### Scenario: Permissions default to disabled
- **WHEN** a valid create input omits `spec.access.permissions.enabled`
- **THEN** the created resource SHALL include `spec.access.permissions.enabled` as `false`.

#### Scenario: Roles are required when permissions are enabled
- **WHEN** `spec.access.permissions.enabled` is `true` and `spec.access.permissions.roles` is missing or empty
- **THEN** the system SHALL report field `spec.access.permissions.roles` with type `required`.

#### Scenario: Role name is required
- **WHEN** `spec.access.permissions.roles` contains a role with missing or empty `name`
- **THEN** the system SHALL report field `spec.access.permissions.roles[<index>].name` with type `required`.

#### Scenario: Role permissions are required
- **WHEN** `spec.access.permissions.roles` contains a role with missing or empty `permissions`
- **THEN** the system SHALL report field `spec.access.permissions.roles[<index>].permissions` with type `required`.

#### Scenario: Duplicate role names are rejected
- **WHEN** `spec.access.permissions.roles` contains more than one role with the same `name`
- **THEN** the system SHALL report field `spec.access.permissions.roles` with type `duplicate`.

#### Scenario: Roles appear only when permissions are enabled
- **WHEN** a returned mesh has `spec.access.permissions.enabled` equal to `false`
- **THEN** the returned resource SHALL omit `spec.access.permissions.roles`.

### Requirement: Mesh access encryption
The system SHALL support encryption certificate source selection under `spec.access.encryption`.

#### Scenario: Encryption defaults to none
- **WHEN** a valid create input omits `spec.access.encryption`
- **THEN** the created resource SHALL include `spec.access.encryption.source` as `"None"` and `spec.access.encryption.clientMode` as `"None"`.

#### Scenario: Encryption source validates allowed values
- **WHEN** `spec.access.encryption.source` is present and is not `"None"`, `"Secret"`, or `"Service"`
- **THEN** the system SHALL report field `spec.access.encryption.source` with type `invalid`.

#### Scenario: Encryption client mode validates allowed values
- **WHEN** `spec.access.encryption.clientMode` is present and is not `"None"`, `"Authenticate"`, or `"Validate"`
- **THEN** the system SHALL report field `spec.access.encryption.clientMode` with type `invalid`.

#### Scenario: Secret source requires certificate reference
- **WHEN** `spec.access.encryption.source` is `"Secret"` and `spec.access.encryption.certRef` is missing
- **THEN** the system SHALL report field `spec.access.encryption.certRef` with type `required`.

#### Scenario: Secret source forbids certificate service reference
- **WHEN** `spec.access.encryption.source` is `"Secret"` and `spec.access.encryption.certServiceRef` is present
- **THEN** the system SHALL report field `spec.access.encryption.certServiceRef` with type `forbidden`.

#### Scenario: Service source requires certificate service reference
- **WHEN** `spec.access.encryption.source` is `"Service"` and `spec.access.encryption.certServiceRef` is missing
- **THEN** the system SHALL report field `spec.access.encryption.certServiceRef` with type `required`.

#### Scenario: Service source forbids certificate reference
- **WHEN** `spec.access.encryption.source` is `"Service"` and `spec.access.encryption.certRef` is present
- **THEN** the system SHALL report field `spec.access.encryption.certRef` with type `forbidden`.

#### Scenario: None source forbids certificate references
- **WHEN** `spec.access.encryption.source` is `"None"` and `spec.access.encryption.certRef` or `spec.access.encryption.certServiceRef` is present
- **THEN** the system SHALL report each provided certificate reference field with type `forbidden`.

#### Scenario: None source allows only none client mode
- **WHEN** `spec.access.encryption.source` is `"None"` and `spec.access.encryption.clientMode` is `"Authenticate"` or `"Validate"`
- **THEN** the system SHALL report field `spec.access.encryption.clientMode` with type `invalid`.

### Requirement: Mesh access output
The system SHALL include `spec.access` with all applicable defaults in successful mesh create and describe output.

#### Scenario: Omitted access outputs full default section
- **WHEN** a valid create input omits `spec.access`
- **THEN** create and describe output SHALL include defaulted authentication, permissions, and encryption fields under `spec.access`.

#### Scenario: Optional access fields appear only when set and applicable
- **WHEN** optional access fields without defaults are omitted or are not applicable to the selected access mode
- **THEN** create and describe output SHALL omit those optional fields.

#### Scenario: Object key order is not contractual
- **WHEN** a mesh output contains `spec.access`
- **THEN** callers SHALL NOT rely on object key order.

## MODIFIED Requirements

### Requirement: Mesh defaulting
The system SHALL apply documented defaults to successful create output and persisted resources while leaving fields without defaults absent when omitted.

#### Scenario: Defaults applied to omitted fields
- **WHEN** a valid create input omits `spec.instances`, `spec.resources.memory`, `spec.access`, `spec.migration.strategy`, `spec.network.storage.size`, `spec.network.storage.ephemeral`, and `spec.network.replicationFactor`
- **THEN** the created resource SHALL include `spec.instances` as `1`, `spec.resources.memory` as `{"limit": "1Gi", "request": "1Gi"}`, `spec.access.authentication.enabled` as `true`, `spec.access.authentication.digestAlgorithm` as `"SHA-256"`, `spec.access.encryption.source` as `"None"`, `spec.access.encryption.clientMode` as `"None"`, `spec.access.permissions.enabled` as `false`, `spec.migration.strategy` as `"FullStop"`, `spec.network.storage.size` as `"1Gi"`, `spec.network.storage.ephemeral` as `false`, and a computed `spec.network.replicationFactor`.

#### Scenario: Fields without defaults remain absent
- **WHEN** a valid create input omits `spec.runtime`, `spec.resources.cpu`, `spec.network.storage.className`, or any other field without a documented default
- **THEN** the created resource SHALL omit those fields from the returned and persisted resource.

### Requirement: Error output
The system SHALL print errors as JSON to stdout with an `errors` array and SHALL print nothing to stderr.

#### Scenario: Error object shape
- **WHEN** any validation, parse, duplicate, not-found, immutable, forbidden, required, or post-merge constraint error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.

#### Scenario: Errors are sorted
- **WHEN** multiple errors are returned
- **THEN** the system SHALL sort errors by `field` ascending, then by `type` ascending.

#### Scenario: Immutable error message
- **WHEN** an immutable field is changed
- **THEN** the system SHALL report the changed field path with type `immutable` and message `field '<field>' is immutable after creation`.

#### Scenario: Post-merge invalid error message
- **WHEN** replication or another post-merge constraint fails
- **THEN** the system SHALL report the failing field path with type `invalid` and a message that names the actual value and the limit.
