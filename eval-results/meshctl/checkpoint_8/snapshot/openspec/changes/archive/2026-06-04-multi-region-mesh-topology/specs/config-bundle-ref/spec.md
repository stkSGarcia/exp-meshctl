## ADDED Requirements

### Requirement: config-bundle-ref-optional-on-create

`spec.configBundleRef` is optional on create. When present, it SHALL be a string (non-null). A non-string value SHALL produce an `invalid` error.

#### Scenario: valid configBundleRef on create is persisted

- **GIVEN** a mesh created with `spec.configBundleRef: "bundle-v1"`
- **WHEN** the create response is produced
- **THEN** `spec.configBundleRef` in the output SHALL equal `"bundle-v1"`

#### Scenario: null configBundleRef on create produces invalid error

- **GIVEN** a mesh create input with `spec.configBundleRef: null`
- **WHEN** create is called
- **THEN** the system SHALL return an `invalid` error with `field = "spec.configBundleRef"`

---

### Requirement: config-bundle-ref-update-semantics

On update, `spec.configBundleRef` SHALL follow these merge semantics:

- Omitting the field SHALL keep the stored value unchanged.
- Setting the field to `null` SHALL remove the stored value.
- Setting the field to a new string SHALL replace the stored value.

#### Scenario: omitting configBundleRef on update preserves stored value

- **GIVEN** a mesh with `spec.configBundleRef: "bundle-v1"` and an update that omits the field
- **WHEN** update is called
- **THEN** `spec.configBundleRef` in the response SHALL still equal `"bundle-v1"`

#### Scenario: setting configBundleRef to null removes it

- **GIVEN** a mesh with `spec.configBundleRef: "bundle-v1"` and an update that sets `configBundleRef: null`
- **WHEN** update is called
- **THEN** `spec.configBundleRef` SHALL be absent from the update response

---

### Requirement: config-refresh-on-change

When the `configBundleRef` value changes (added, removed, or replaced) during an update, the system SHALL include `status.configRefresh` in the update response:

```json
{
  "currentRef": "<new-value-or-null>",
  "pending": true,
  "previousRef": "<old-value-or-null>"
}
```

`status.configRefresh` SHALL be omitted from subsequent describe responses.

#### Scenario: changing configBundleRef produces configRefresh

- **GIVEN** a mesh with `spec.configBundleRef: "bundle-v1"` and an update setting it to `"bundle-v2"`
- **WHEN** update is called
- **THEN** the update response SHALL include `status.configRefresh` with `currentRef: "bundle-v2"`, `previousRef: "bundle-v1"`, `pending: true`

#### Scenario: first-time configBundleRef set produces configRefresh

- **GIVEN** a mesh with no `configBundleRef` and an update setting it to `"bundle-v1"`
- **WHEN** update is called
- **THEN** `status.configRefresh` SHALL appear with `currentRef: "bundle-v1"`, `previousRef: null`

#### Scenario: clearing configBundleRef produces configRefresh

- **GIVEN** a mesh with `spec.configBundleRef: "bundle-v1"` and an update setting it to `null`
- **WHEN** update is called
- **THEN** `status.configRefresh` SHALL appear with `currentRef: null`, `previousRef: "bundle-v1"`

#### Scenario: configRefresh absent from describe

- **GIVEN** an update that changed `configBundleRef`
- **WHEN** describe is called afterwards
- **THEN** `status.configRefresh` SHALL be absent from the describe response

