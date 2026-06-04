# runtime-version-validation Specification

## Purpose
TBD - created by archiving change mesh-migration-strategies. Update Purpose after archive.
## Requirements
### Requirement: Runtime version validation
`spec.runtime`, when present, SHALL first parse as `major.minor.patch` where each part is a non-negative integer, then SHALL be validated against the runtime catalog. If absent, it SHALL be omitted from output. (adapts mesh-management/runtime-version-validation)

#### Scenario: Valid runtime in catalog accepted
- **WHEN** `spec.runtime` is a well-formed version string present in the catalog as `supported`
- **THEN** runtime validation passes and the value is preserved (see scenario: mesh-management/runtime-version-validation/valid-runtime)

#### Scenario: Invalid runtime format rejected before catalog check
- **WHEN** `spec.runtime` is `"1.2"` or `"v1.2.3"` or `"1.2.x"`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}` (format error, no catalog lookup performed)

#### Scenario: Absent runtime omitted
- **WHEN** `spec.runtime` is not in the input
- **THEN** `spec.runtime` is absent from the output JSON and no catalog check is done

#### Scenario: Version not in catalog rejected
- **WHEN** `spec.runtime` has valid format but is not in the catalog
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}`

