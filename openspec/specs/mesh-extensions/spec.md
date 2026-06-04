# mesh-extensions Specification

## Purpose
TBD - created by archiving change multi-region-mesh-topology. Update Purpose after archive.
## Requirements
### Requirement: extensions-array-optional

`spec.extensions` is an optional array of extension objects. When present, declaration order SHALL be preserved in output.

#### Scenario: extensions order preserved

- **GIVEN** a mesh created with two extension entries
- **WHEN** the create response is produced
- **THEN** the extensions SHALL appear in the same order as declared

---

### Requirement: extension-url-or-artifact-exclusive

Each extension entry SHALL set exactly one of `url` or `artifact`. Setting both or neither SHALL produce an `invalid` error with `field = "spec.extensions[<index>]"` and `message = "exactly one of 'url' or 'artifact' must be set"`.

#### Scenario: both url and artifact set produces invalid error

- **GIVEN** an extension entry with both `url` and `artifact` set
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with the correct field and message

#### Scenario: neither url nor artifact set produces invalid error

- **GIVEN** an extension entry with neither `url` nor `artifact`
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.extensions[<index>]"`

#### Scenario: url-only extension is valid

- **GIVEN** an extension entry with only `url` set
- **WHEN** create is called
- **THEN** the extension SHALL be persisted and included in the response

#### Scenario: artifact-only extension is valid

- **GIVEN** an extension entry with only `artifact` set
- **WHEN** create is called
- **THEN** the extension SHALL be persisted and included in the response

---

### Requirement: extension-integrity-optional

`integrity` is optional on each extension. When absent, it SHALL be omitted from output.

#### Scenario: integrity omitted when unset

- **GIVEN** an extension entry with `url` but no `integrity`
- **WHEN** the create response is produced
- **THEN** `integrity` SHALL be absent from that extension entry in the output

#### Scenario: integrity preserved when set

- **GIVEN** an extension entry with `url` and `integrity: "sha256-abc"`
- **WHEN** the create response is produced
- **THEN** `integrity` SHALL equal `"sha256-abc"` in the output

