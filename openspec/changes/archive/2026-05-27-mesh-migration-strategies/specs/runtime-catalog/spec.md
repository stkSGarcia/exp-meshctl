## ADDED Requirements

### Requirement: Runtime version catalog
The system SHALL maintain an internal catalog of known runtime versions, each with a status of `supported`, `deprecated`, or `skipped`. Only catalog-listed versions are accepted when `spec.runtime` is present.

#### Scenario: Supported version accepted
- **WHEN** `spec.runtime` is a catalog-listed version with status `supported`
- **THEN** the version is accepted with no warning

#### Scenario: Deprecated version accepted with warning
- **WHEN** `spec.runtime` is a catalog-listed version with status `deprecated`
- **THEN** the operation succeeds and a warning is emitted: `field = "spec.runtime"`, `message = "runtime version '<version>' is deprecated"`

#### Scenario: Skipped version rejected
- **WHEN** `spec.runtime` is a catalog-listed version with status `skipped`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"runtime version '<version>' is skipped and cannot be targeted"}`

#### Scenario: Version not in catalog rejected
- **WHEN** `spec.runtime` is a syntactically valid version string but is not present in the catalog
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}`

#### Scenario: Absent runtime skips catalog validation
- **WHEN** `spec.runtime` is absent from the input
- **THEN** no catalog validation is performed

---

### Requirement: Catalog validation on create and update
The system SHALL apply catalog validation whenever `spec.runtime` is present, on both `mesh create` and `mesh update`.

#### Scenario: Catalog validation on create
- **WHEN** `mesh create` is called with a `spec.runtime` that is catalog-listed
- **THEN** catalog status rules are enforced

#### Scenario: Catalog validation on update
- **WHEN** `mesh update` is called with a `spec.runtime` that is catalog-listed
- **THEN** catalog status rules are enforced

---

### Requirement: Warnings output format
The system SHALL include a `warnings` array in the top-level response JSON on successful operations when one or more warnings are applicable. When no warnings exist, the `warnings` key SHALL be omitted from the response.

#### Scenario: Warnings included on success with deprecated runtime
- **WHEN** an operation succeeds and `spec.runtime` is deprecated
- **THEN** the response includes `"warnings":[{"field":"spec.runtime","message":"runtime version '<version>' is deprecated"}]`

#### Scenario: Warnings omitted when none present
- **WHEN** an operation succeeds with no applicable warnings
- **THEN** the response does not include a `warnings` key

#### Scenario: Warnings not emitted when errors exist
- **WHEN** an operation fails with one or more errors
- **THEN** the response is `{"errors":[...]}` with no `warnings` key

---

### Requirement: Warning sort order
When multiple warnings are present, the system SHALL sort them by `field` ascending, with ties broken by `message` ascending.

#### Scenario: Warnings sorted by field then message
- **WHEN** multiple warnings are emitted for the same or different fields
- **THEN** the `warnings` array is sorted by `field` ascending, then `message` ascending
