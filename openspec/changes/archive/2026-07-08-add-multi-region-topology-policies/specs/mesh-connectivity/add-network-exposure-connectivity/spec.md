## ADDED Requirements

> Extends: mesh-connectivity/add-network-exposure-connectivity

### Requirement: Region-local exposure modes
The system SHALL validate `spec.regions.local.expose.type` as one of `"Internal"`, `"DirectPort"`, `"Balancer"`, or `"Gateway"` and SHALL keep region-local exposure separate from top-level mesh exposure.

#### Scenario: Supported region-local exposure is accepted
- **WHEN** a local region uses a supported expose type
- **THEN** output preserves the selected `spec.regions.local.expose.type`

### Requirement: Gateway regional exposure security
The system SHALL require `spec.regions.local.encryption.transportKeyStore` when the local region expose type is `"Gateway"`.

#### Scenario: Gateway exposure without transport key store is rejected
- **WHEN** `spec.regions.local.expose.type` is `"Gateway"` and no transport key store is configured
- **THEN** validation returns a required error for `spec.regions.local.encryption.transportKeyStore`
