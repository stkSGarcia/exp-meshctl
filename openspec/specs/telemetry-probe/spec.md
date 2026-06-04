# telemetry-probe Specification

## Purpose
TBD - created by archiving change multi-region-mesh-topology. Update Purpose after archive.
## Requirements
### Requirement: metadata-tags-persisted

`metadata.tags` is an optional map of string keys to string values. When present, every tag SHALL be persisted and included in output as-is.

#### Scenario: tags round-trip

- **GIVEN** a mesh created with `metadata.tags: {"env": "prod", "team": "platform"}`
- **WHEN** describe is called
- **THEN** `metadata.tags` in the output SHALL equal `{"env": "prod", "team": "platform"}`

---

### Requirement: telemetry-probe-always-present

`status.telemetryProbe` SHALL be present in create and describe output for every mesh.

#### Scenario: telemetry probe present when no tags set

- **GIVEN** a mesh with no `metadata.tags`
- **WHEN** the create response is produced
- **THEN** `status.telemetryProbe` SHALL equal `{"enabled": true}`

---

### Requirement: telemetry-tag-controls-enabled

The tag `mesh.io/telemetry` SHALL control whether telemetry is enabled. `"true"` SHALL enable it; `"false"` SHALL disable it. When absent, telemetry SHALL default to enabled.

#### Scenario: telemetry disabled via tag

- **GIVEN** `metadata.tags` contains `{"mesh.io/telemetry": "false"}`
- **WHEN** the create response is produced
- **THEN** `status.telemetryProbe` SHALL equal `{"enabled": false}`

#### Scenario: telemetry enabled when tag absent

- **GIVEN** `metadata.tags` is absent
- **WHEN** the create response is produced
- **THEN** `status.telemetryProbe.enabled` SHALL be `true`

---

### Requirement: telemetry-label-tags

When telemetry is enabled, the following tags SHALL populate label categories in `status.telemetryProbe.labels`:

| Tag Key | Category |
|---|---|
| `mesh.io/targetLabels` | `targetLabels` |
| `mesh.io/probeTargetLabels` | `probeTargetLabels` |
| `mesh.io/instanceLabels` | `instanceLabels` |

Each tag value is a comma-separated list. The list order SHALL be preserved. Only categories whose tags are set SHALL appear in `labels`. When no label tags are set, `labels` SHALL be absent.

#### Scenario: label tags populate probe labels

- **GIVEN** `metadata.tags` contains `{"mesh.io/targetLabels": "region,env"}`
- **WHEN** the create response is produced
- **THEN** `status.telemetryProbe` SHALL equal `{"enabled": true, "labels": {"targetLabels": ["region", "env"]}}`

#### Scenario: multiple label categories included

- **GIVEN** `metadata.tags` contains both `mesh.io/targetLabels` and `mesh.io/instanceLabels`
- **WHEN** the create response is produced
- **THEN** both categories SHALL appear in `status.telemetryProbe.labels`

#### Scenario: label order preserved

- **GIVEN** `metadata.tags` contains `{"mesh.io/targetLabels": "zone,region,env"}`
- **WHEN** the create response is produced
- **THEN** `targetLabels` SHALL equal `["zone", "region", "env"]` in that order

#### Scenario: telemetry disabled ignores label tags

- **GIVEN** `metadata.tags` contains `{"mesh.io/telemetry": "false", "mesh.io/targetLabels": "region"}`
- **WHEN** the create response is produced
- **THEN** `status.telemetryProbe` SHALL equal `{"enabled": false}` with no `labels`

