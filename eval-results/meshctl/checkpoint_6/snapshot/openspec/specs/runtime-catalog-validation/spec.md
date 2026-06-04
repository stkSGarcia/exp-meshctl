# runtime-catalog-validation Specification

## Purpose
TBD - created by archiving change mesh-migration-strategies. Update Purpose after archive.
## Requirements
### Requirement: Runtime catalog lookup
When `spec.runtime` is present, the system SHALL look it up in the runtime version catalog after the format check passes. The catalog maps version strings to one of: `supported`, `deprecated`, or `skipped`. Versions not present in the catalog SHALL be rejected as invalid.

#### Scenario: Supported version accepted
- **WHEN** `spec.runtime` is a catalog version with status `supported`
- **THEN** the operation proceeds without errors or warnings for that field

#### Scenario: Version not in catalog rejected
- **WHEN** `spec.runtime` is a valid `major.minor.patch` string not present in the catalog
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}`

#### Scenario: Absent runtime skips catalog check
- **WHEN** `spec.runtime` is absent from the input
- **THEN** no catalog lookup is performed and `spec.runtime` is omitted from output

### Requirement: Skipped version rejection
A catalog version with status `skipped` SHALL be rejected with a specific message.

#### Scenario: Skipped version produces specific error
- **WHEN** `spec.runtime` is a catalog version with status `skipped`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"runtime version '<version>' is skipped and cannot be targeted"}`

### Requirement: Deprecated version warning
A catalog version with status `deprecated` SHALL be accepted but SHALL cause a warning to be emitted on success.

#### Scenario: Deprecated version accepted with warning
- **WHEN** `spec.runtime` is a catalog version with status `deprecated` and the operation succeeds
- **THEN** the response includes `{"field":"spec.runtime","message":"runtime version '<version>' is deprecated"}` in the `warnings` array

#### Scenario: Deprecated version warning suppressed on error
- **WHEN** `spec.runtime` is a deprecated catalog version but another validation error exists
- **THEN** no warnings are emitted (only `{"errors":[...]}` is output)

### Requirement: Catalog validation on create and update
Catalog validation SHALL be applied on both `create` and `update` operations whenever `spec.runtime` is present.

#### Scenario: Catalog validation on create
- **WHEN** a new mesh is created with a skipped `spec.runtime`
- **THEN** the create is rejected with the skipped-version error

#### Scenario: Catalog validation on update
- **WHEN** an existing mesh is updated with a deprecated `spec.runtime`
- **THEN** the update succeeds and the deprecated warning is emitted

