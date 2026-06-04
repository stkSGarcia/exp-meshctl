# mesh-placement Specification

## Purpose
TBD - created by archiving change multi-region-mesh-topology. Update Purpose after archive.
## Requirements
### Requirement: placement-always-in-output

`spec.placement` SHALL be included in create and describe output for every mesh, with defaults applied even when omitted from input.

#### Scenario: placement defaulted when absent

- **GIVEN** a mesh created without `spec.placement`
- **WHEN** the create response is produced
- **THEN** `spec.placement.affinity` SHALL equal `{"type": "preferred", "scope": "node"}`

---

### Requirement: placement-affinity-defaults

`spec.placement.affinity.type` SHALL default to `"preferred"`. `spec.placement.affinity.scope` SHALL default to `"node"`.

#### Scenario: affinity type defaults to preferred

- **GIVEN** `spec.placement` is present but `affinity.type` is absent
- **WHEN** the create response is produced
- **THEN** `spec.placement.affinity.type` SHALL equal `"preferred"`

#### Scenario: affinity scope defaults to node

- **GIVEN** `spec.placement` is present but `affinity.scope` is absent
- **WHEN** the create response is produced
- **THEN** `spec.placement.affinity.scope` SHALL equal `"node"`

---

### Requirement: placement-affinity-type-valid

`spec.placement.affinity.type` SHALL be one of `"preferred"` or `"required"`. Any other value is invalid.

#### Scenario: invalid affinity type produces invalid error

- **GIVEN** `spec.placement.affinity.type` is set to `"strict"`
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.placement.affinity.type"`

---

### Requirement: placement-affinity-scope-valid

`spec.placement.affinity.scope` SHALL be one of `"node"` or `"zone"`. Any other value is invalid.

#### Scenario: invalid affinity scope produces invalid error

- **GIVEN** `spec.placement.affinity.scope` is set to `"rack"`
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.placement.affinity.scope"`

---

### Requirement: placement-must-be-object

When `spec.placement` is present, it SHALL be an object. When `spec.placement.affinity` is present, it SHALL be an object.

#### Scenario: non-object placement produces invalid error

- **GIVEN** `spec.placement` is set to a string value
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.placement"`

#### Scenario: non-object affinity produces invalid error

- **GIVEN** `spec.placement.affinity` is set to a boolean
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.placement.affinity"`

