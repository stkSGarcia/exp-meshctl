## ADDED Requirements

> Extends: mesh-resource-management/add-access-security-model

### Requirement: Region encryption separation
The system SHALL keep inter-region encryption under `spec.regions.local.encryption` separate from `spec.access` while using the established JSON validation format for credential-bearing security settings. (adapts mesh-resource-management/add-access-security-model/mesh-access-encryption)

#### Scenario: Access and region encryption are independent
- **WHEN** a mesh defines both `spec.access.encryption` and `spec.regions.local.encryption`
- **THEN** each section is validated and emitted under its own path
- **AND** errors for regional encryption use `spec.regions.local.encryption` field paths

### Requirement: Region key store validation
The system SHALL require `secretRef`, `alias`, and `filename` on each configured local region key store object.

#### Scenario: Region key store sub-field is missing
- **WHEN** `transportKeyStore`, `relayKeyStore`, or `trustStore` is present without a required sub-field
- **THEN** validation returns a required error for `spec.regions.local.encryption.<store>.<field>`
