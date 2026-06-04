# migration-warnings Specification

## Purpose
TBD - created by archiving change mesh-migration-strategies. Update Purpose after archive.
## Requirements
### Requirement: Warning output shape
Each warning SHALL be an object with `field` (dot-path string) and `message` (human-readable string).

#### Scenario: Warning object has required fields
- **WHEN** a warning is emitted
- **THEN** it has the form `{"field":"<dot-path>","message":"<text>"}`

### Requirement: Warnings emitted only on success
Warnings SHALL only be included in the response when the operation succeeds (no errors). When any error exists, the output SHALL be `{"errors":[...]}` with no `warnings` key.

#### Scenario: Warnings absent when errors present
- **WHEN** a validation error exists alongside a condition that would generate a warning
- **THEN** the output is `{"errors":[...]}` with no `warnings` field

#### Scenario: Warnings present on success
- **WHEN** the operation succeeds and a warning condition applies
- **THEN** the output includes a `warnings` array alongside the resource fields

#### Scenario: Warnings key absent when no warnings
- **WHEN** the operation succeeds and no warning conditions apply
- **THEN** the output does not include a `warnings` key

### Requirement: Warning sort order
Warnings SHALL be sorted by `field` ascending; ties broken by `message` ascending.

#### Scenario: Multiple warnings sorted by field then message
- **WHEN** multiple warnings are emitted
- **THEN** the `warnings` array is sorted by `field` ascending, then by `message` ascending within the same `field`

### Requirement: Warnings do not affect exit code
The presence of warnings SHALL not change the success exit code.

#### Scenario: Warning does not change exit code
- **WHEN** a deprecated runtime warning is emitted
- **THEN** the process exits with a success code (same as a warning-free success)

