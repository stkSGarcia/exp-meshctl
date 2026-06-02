# runtime-catalog Specification

## Purpose
TBD - created by archiving change mesh-migration-strategies. Update Purpose after archive.
## Requirements
### Requirement: Runtime catalog definition
The system SHALL maintain a catalog of known runtime versions. Each catalog entry SHALL have a version string and a status of `supported`, `deprecated`, or `skipped`. Only versions present in the catalog are valid targets for `spec.runtime`.

#### Scenario: Catalog lists at least the known versions
- **WHEN** the system initializes
- **THEN** the catalog includes at least `3.0.0` (deprecated), `3.1.0` (skipped), `3.1.1` (supported), and `4.0.0` (supported)

---

### Requirement: Catalog validation on create and update
When `spec.runtime` is present in a create or update request, the system SHALL look up the value in the runtime catalog. If the version is not in the catalog, the system SHALL reject the request.

#### Scenario: Unknown version rejected
- **WHEN** `spec.runtime` is a valid semver string that does not appear in the catalog
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}`

#### Scenario: Catalog validation skipped when runtime absent
- **WHEN** `spec.runtime` is not present in the input
- **THEN** no catalog validation error is produced for `spec.runtime`

---

### Requirement: Supported catalog status accepted
A runtime version with catalog status `supported` SHALL be accepted without warnings.

#### Scenario: Supported version accepted silently
- **WHEN** `spec.runtime` is a version with catalog status `supported`
- **THEN** the operation succeeds and no runtime warning is emitted

---

### Requirement: Deprecated catalog status accepted with warning
A runtime version with catalog status `deprecated` SHALL be accepted but SHALL produce a warning on successful operations.

#### Scenario: Deprecated version accepted with warning
- **WHEN** `spec.runtime` is a version with catalog status `deprecated` and the operation succeeds without errors
- **THEN** the response includes `{"warnings":[{"field":"spec.runtime","message":"runtime version '<version>' is deprecated"}]}`

#### Scenario: Deprecated version warning suppressed on error
- **WHEN** `spec.runtime` is deprecated but another validation error is present
- **THEN** no `warnings` key appears in the response

---

### Requirement: Skipped catalog status rejected
A runtime version with catalog status `skipped` SHALL be rejected with an invalid error.

#### Scenario: Skipped version rejected
- **WHEN** `spec.runtime` is a version with catalog status `skipped`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"runtime version '<version>' is skipped and cannot be targeted"}`

---

### Requirement: Warning response shape
The system SHALL include a top-level `warnings` array in the response JSON when one or more warnings exist and the operation has no errors.

#### Scenario: Warning shape
- **WHEN** a warning is emitted
- **THEN** the response contains `"warnings":[{"field":"<dot-path>","message":"<text>"}]`

#### Scenario: Warnings sorted by field then message
- **WHEN** multiple warnings are emitted
- **THEN** the `warnings` array is sorted by `field` ascending, then `message` ascending

#### Scenario: No warnings key when no warnings
- **WHEN** no warnings are triggered
- **THEN** the `warnings` key is absent from the response

