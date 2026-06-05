## ADDED Requirements

### Requirement: Metadata tags
`metadata.tags` SHALL be an optional map of string keys to string values. All provided tags SHALL be persisted and included in output.

#### Scenario: Tags persisted and output
- **WHEN** `metadata.tags` contains key-value pairs
- **THEN** all tags are present in the output under `metadata.tags`

#### Scenario: Tags absent when not set
- **WHEN** `metadata.tags` is not provided
- **THEN** `metadata.tags` is absent from output

---

### Requirement: Placement defaults
`spec.placement` SHALL always be present in create and describe output. When absent from input, it SHALL default to `{"affinity":{"type":"preferred","scope":"node"}}`. When present, it SHALL be an object. When `spec.placement.affinity` is present, it SHALL be an object. `type` SHALL be one of `"preferred"` or `"required"`. `scope` SHALL be one of `"node"` or `"zone"`.

#### Scenario: Placement defaulted when absent
- **WHEN** `spec.placement` is absent from input
- **THEN** output includes `spec.placement.affinity.type = "preferred"` and `spec.placement.affinity.scope = "node"`

#### Scenario: Provided placement values accepted
- **WHEN** `spec.placement.affinity.type` is `"required"` and `scope` is `"zone"`
- **THEN** the values are persisted and output as given

#### Scenario: Non-object placement rejected
- **WHEN** `spec.placement` is a scalar or list
- **THEN** output error `{"field":"spec.placement","type":"invalid","message":"<msg>"}`

#### Scenario: Non-object affinity rejected
- **WHEN** `spec.placement.affinity` is a scalar or list
- **THEN** output error `{"field":"spec.placement.affinity","type":"invalid","message":"<msg>"}`

#### Scenario: Invalid placement affinity type
- **WHEN** `spec.placement.affinity.type` is not `"preferred"` or `"required"`
- **THEN** output error `{"field":"spec.placement.affinity.type","type":"invalid","message":"<msg>"}`

#### Scenario: Invalid placement affinity scope
- **WHEN** `spec.placement.affinity.scope` is not `"node"` or `"zone"`
- **THEN** output error `{"field":"spec.placement.affinity.scope","type":"invalid","message":"<msg>"}`

---

### Requirement: Config bundle reference
`spec.configBundleRef` SHALL be an optional string on create. On create, when present, it SHALL be a string. On update, omitting `spec.configBundleRef` SHALL keep the stored value. Setting it to `null` SHALL remove the stored value. Changing the value (adding, updating, or clearing) SHALL produce a transient `status.configRefresh` in the update response only; `configRefresh` SHALL be absent from subsequent describe output.

The `status.configRefresh` object SHALL have the shape:
```json
{"currentRef": "<string-or-null>", "pending": true, "previousRef": "<string-or-null>"}
```

#### Scenario: configBundleRef stored on create
- **WHEN** `spec.configBundleRef` is a non-empty string on create
- **THEN** the value is persisted and included in output

#### Scenario: Non-string configBundleRef rejected on create
- **WHEN** `spec.configBundleRef` is not a string on create
- **THEN** output error `{"field":"spec.configBundleRef","type":"invalid","message":"<msg>"}`

#### Scenario: Omitting configBundleRef on update keeps stored value
- **WHEN** update YAML omits `spec.configBundleRef`
- **THEN** the stored value is unchanged and no `status.configRefresh` is produced

#### Scenario: Changing configBundleRef produces configRefresh
- **WHEN** update YAML sets `spec.configBundleRef` to a new string value
- **THEN** the update response includes `status.configRefresh` with `pending: true`, `currentRef` equal to the new value, and `previousRef` equal to the old value

#### Scenario: Setting configBundleRef to null clears it
- **WHEN** update YAML sets `spec.configBundleRef` to `null`
- **THEN** the stored value is removed, and `status.configRefresh.currentRef` is `null`

#### Scenario: configRefresh absent from describe output
- **WHEN** a describe is performed after a configBundleRef update
- **THEN** `status.configRefresh` is absent from the describe response

---

### Requirement: Extensions
`spec.extensions` is an optional array of plugin extension objects. Each entry SHALL have exactly one of `url` (string) or `artifact` (string). `integrity` (string) is optional and omitted from output when unset. Declaration order SHALL be preserved. Setting both `url` and `artifact`, or neither, is invalid.

#### Scenario: Extension with url accepted
- **WHEN** an extension entry has only `url` set
- **THEN** the entry is accepted and output with `url` present

#### Scenario: Extension with artifact accepted
- **WHEN** an extension entry has only `artifact` set
- **THEN** the entry is accepted and output with `artifact` present

#### Scenario: Extension with both url and artifact rejected
- **WHEN** an extension entry sets both `url` and `artifact`
- **THEN** output error `{"field":"spec.extensions[<index>]","type":"invalid","message":"exactly one of 'url' or 'artifact' must be set"}`

#### Scenario: Extension with neither url nor artifact rejected
- **WHEN** an extension entry sets neither `url` nor `artifact`
- **THEN** output error `{"field":"spec.extensions[<index>]","type":"invalid","message":"exactly one of 'url' or 'artifact' must be set"}`

#### Scenario: integrity omitted when absent
- **WHEN** an extension entry has no `integrity` field
- **THEN** `integrity` is absent from output

#### Scenario: Declaration order preserved
- **WHEN** multiple extensions are provided
- **THEN** output preserves their declaration order

---

### Requirement: Telemetry via metadata tags
Telemetry behavior SHALL be driven by `metadata.tags`. The tag `mesh.io/telemetry` SHALL control the enabled state: `"true"` enables it, `"false"` disables it; when absent, telemetry SHALL default to enabled. The tags `mesh.io/targetLabels`, `mesh.io/probeTargetLabels`, and `mesh.io/instanceLabels` SHALL be comma-separated label lists that map to their respective `labels` categories in `status.telemetryProbe`.

#### Scenario: Telemetry enabled by default
- **WHEN** `mesh.io/telemetry` tag is absent
- **THEN** telemetry is treated as enabled

#### Scenario: Telemetry explicitly disabled
- **WHEN** `mesh.io/telemetry` tag is `"false"`
- **THEN** telemetry is disabled

#### Scenario: Label tags parsed as comma-separated lists
- **WHEN** `mesh.io/targetLabels` is `"region,env"`
- **THEN** `status.telemetryProbe.labels.targetLabels = ["region", "env"]` with order preserved

#### Scenario: Only set label categories included
- **WHEN** only `mesh.io/targetLabels` is set among the label tags
- **THEN** `status.telemetryProbe.labels` contains only `targetLabels`

---

### Requirement: status.telemetryProbe always present
`status.telemetryProbe` SHALL be present on all create and describe outputs. When telemetry is enabled and no label tags are set, output `{"enabled": true}`. When telemetry is enabled and one or more label tags are set, include a `labels` object with only the populated categories. When telemetry is disabled, output `{"enabled": false}` only.

#### Scenario: telemetryProbe with no labels
- **WHEN** telemetry is enabled and no label tags are set
- **THEN** `status.telemetryProbe = {"enabled": true}`

#### Scenario: telemetryProbe with labels
- **WHEN** telemetry is enabled and `mesh.io/targetLabels` is `"region,env"` and `mesh.io/instanceLabels` is `"pod"`
- **THEN** `status.telemetryProbe = {"enabled": true, "labels": {"targetLabels": ["region", "env"], "instanceLabels": ["pod"]}}`

#### Scenario: telemetryProbe when disabled
- **WHEN** `mesh.io/telemetry` is `"false"`
- **THEN** `status.telemetryProbe = {"enabled": false}`

---

## MODIFIED Requirements

### Requirement: Success output — create and describe
The system SHALL print the full resource JSON with `metadata` (including `tags` when set), `spec` (all defaulted fields including `placement`, `configBundleRef` when present, and `extensions` when present), and a `status` block. The status block SHALL include `state`, `stable`, `instances`, `conditions`, `telemetryProbe`, and (when stopped) `desiredInstancesOnResume`. On update responses that changed `configBundleRef`, `status.configRefresh` SHALL also be included.

#### Scenario: Create output includes telemetryProbe and placement
- **WHEN** create succeeds
- **THEN** output includes `status.telemetryProbe` and `spec.placement` with defaults applied

#### Scenario: Update response with configRefresh
- **WHEN** `spec.configBundleRef` changes on update
- **THEN** output includes `status.configRefresh` in addition to the standard fields

#### Scenario: Describe output excludes configRefresh
- **WHEN** describe is called after a configBundleRef update
- **THEN** `status.configRefresh` is absent from the describe output

### Requirement: Migration strategy validation and default
`spec.migration.strategy` SHALL default to `"FullStop"` and SHALL accept `"FullStop"` or `"LiveMigration"`. `"LiveMigration"` is valid only when `spec.regions` is absent. When `spec.regions` is present, `"LiveMigration"` SHALL produce an `invalid` error. (adapts mesh-lifecycle-and-topology/mesh-management)

#### Scenario: FullStop accepted without regions
- **WHEN** `spec.migration.strategy` is `"FullStop"` and `spec.regions` is absent
- **THEN** the value is accepted

#### Scenario: LiveMigration accepted without regions
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and `spec.regions` is absent
- **THEN** the value is accepted

#### Scenario: LiveMigration rejected with regions
- **WHEN** `spec.migration.strategy` is `"LiveMigration"` and `spec.regions` is present
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}`

#### Scenario: Invalid strategy still rejected
- **WHEN** `spec.migration.strategy` is any value other than `"FullStop"` or `"LiveMigration"`
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"<msg>"}`
