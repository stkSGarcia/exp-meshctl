## ADDED Requirements

### Requirement: Runtime version catalog
The system SHALL maintain a hardcoded catalog that maps specific runtime version strings to one of three statuses: `supported`, `deprecated`, or `skipped`. The minimum catalog SHALL include at least `3.0.0` (deprecated), `3.1.0` (skipped), `3.1.1` (supported), and `4.0.0` (supported).

#### Scenario: Catalog contains known versions
- **WHEN** the system starts
- **THEN** the catalog maps `3.0.0` → deprecated, `3.1.0` → skipped, `3.1.1` → supported, `4.0.0` → supported

---

### Requirement: Catalog membership check on create and update
When `spec.runtime` is present, the system SHALL reject any value that is not a key in the runtime catalog, in addition to the existing format check. Catalog validation SHALL be skipped when `spec.runtime` is absent.

#### Scenario: Runtime absent — no catalog check
- **WHEN** `spec.runtime` is not present in the input
- **THEN** catalog validation is skipped and no catalog-related error is emitted

#### Scenario: Runtime format-valid but not in catalog
- **WHEN** `spec.runtime` is `"2.0.0"` (valid format, absent from catalog)
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}`

#### Scenario: Runtime in catalog as supported — accepted
- **WHEN** `spec.runtime` is `"4.0.0"` (supported)
- **THEN** no error for catalog membership

---

### Requirement: Skipped version rejection
A runtime version with catalog status `skipped` SHALL be rejected on both `create` and `update`. The error message SHALL use the exact text `"runtime version '<version>' is skipped and cannot be targeted"`.

#### Scenario: Skipped version on create
- **WHEN** `spec.runtime` is `"3.1.0"` (skipped) on a `create` call
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"runtime version '3.1.0' is skipped and cannot be targeted"}`

#### Scenario: Skipped version on update
- **WHEN** `spec.runtime` is changed to `"3.1.0"` (skipped) on an `update` call
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"runtime version '3.1.0' is skipped and cannot be targeted"}`

---

### Requirement: Deprecated version warning
A runtime version with catalog status `deprecated` SHALL be accepted but SHALL cause a warning to be included in the response under a `warnings` array. The warning SHALL have `field = "spec.runtime"` and `message = "runtime version '<version>' is deprecated"`.

#### Scenario: Deprecated version on create
- **WHEN** `spec.runtime` is `"3.0.0"` (deprecated) on a `create` call with no other errors
- **THEN** the response includes the resource JSON and `"warnings":[{"field":"spec.runtime","message":"runtime version '3.0.0' is deprecated"}]`

#### Scenario: Deprecated version warning suppressed when errors exist
- **WHEN** `spec.runtime` is `"3.0.0"` (deprecated) AND another field is invalid on the same call
- **THEN** the response contains only the `errors` array; no `warnings` key is emitted

---

### Requirement: Warning output shape and ordering
Warnings SHALL be emitted only when the operation succeeds (no errors). Warnings SHALL be sorted by `field` ascending, then `message` ascending. Warnings SHALL NOT change the exit code.

The response shape when warnings are present is:
```json
{
  "warnings": [
    {"field": "<dot-path>", "message": "<text>"}
  ]
}
```
merged alongside the normal resource output.

#### Scenario: Multiple warnings sorted by field then message
- **WHEN** two warnings have different `field` values
- **THEN** the `warnings` array is sorted by `field` ascending

#### Scenario: No warnings on error response
- **WHEN** validation fails
- **THEN** the response is `{"errors":[...]}` with no `warnings` key

### Related Scenarios

**`implement-meshctl/mesh-management/runtime-version-validation/valid-runtime`** — When `spec.runtime` is `"1.2.3"`, runtime validation passes. _(matched on: runtime catalog version validation)_

**`implement-meshctl/mesh-management/runtime-version-validation/invalid-runtime-format`** — When `spec.runtime` is `"1.2"` or `"v1.2.3"` or `"1.2.x"`, output a format error. _(matched on: runtime catalog version validation)_
