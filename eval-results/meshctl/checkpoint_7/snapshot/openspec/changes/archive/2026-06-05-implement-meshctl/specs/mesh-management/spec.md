## ADDED Requirements

### Requirement: CLI entry point
The tool SHALL be invokable as `uv run --project /app meshctl.py mesh <operation> [arguments]` and SHALL route to the correct operation handler.

#### Scenario: Valid subcommand dispatched
- **WHEN** the user runs `meshctl.py mesh create -f <path>`
- **THEN** the create handler is invoked with the given file path

#### Scenario: Unknown subcommand
- **WHEN** the user runs `meshctl.py mesh <unknown>`
- **THEN** the tool exits with a non-success indicator (implementation detail)

---

### Requirement: Mesh create
The system SHALL read a YAML document from the file path given by `-f`, apply all defaults, validate all fields, and — if valid and the name is not already taken — persist the resource and print the full resource as JSON to stdout.

#### Scenario: Valid create
- **WHEN** a valid YAML file is provided with a unique mesh name
- **THEN** the resource is persisted with defaults applied and the full resource JSON is printed

#### Scenario: Duplicate name rejected
- **WHEN** `create` is called with a name that already exists
- **THEN** output `{"errors":[{"field":"metadata.name","type":"duplicate","message":"<msg>"}]}` and do not persist

#### Scenario: Invalid YAML file
- **WHEN** the file cannot be read or is not valid YAML
- **THEN** output `{"errors":[{"field":"","type":"parse","message":"<msg>"}]}`

---

### Requirement: Mesh list
The system SHALL print a JSON array of all stored mesh summaries, sorted by `name` ascending lexicographically (case-sensitive).

#### Scenario: Non-empty store
- **WHEN** one or more meshes exist
- **THEN** output a JSON array of `{"name":"<string>","status":{"state":"<string>"}}` objects sorted by name

#### Scenario: Empty store
- **WHEN** no meshes exist
- **THEN** output `[]`

---

### Requirement: Mesh describe
The system SHALL print the full resource JSON for the mesh identified by `<name>`.

#### Scenario: Existing mesh
- **WHEN** the named mesh exists
- **THEN** output the full resource JSON including all defaulted spec fields and `status`

#### Scenario: Unknown mesh
- **WHEN** the named mesh does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Mesh delete
The system SHALL remove the named mesh from the store and print a confirmation JSON object.

#### Scenario: Existing mesh deleted
- **WHEN** the named mesh exists
- **THEN** remove it from the store and output `{"message":"<non-empty>","metadata":{"name":"<string>"}}`

#### Scenario: Unknown mesh
- **WHEN** the named mesh does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: YAML input schema
The system SHALL accept a YAML document that is a mapping with top-level keys `metadata` and `spec`. Any other top-level structure SHALL produce a parse error.

#### Scenario: Valid mapping with metadata and spec
- **WHEN** the YAML document has `metadata.name` and a `spec` block
- **THEN** the document is accepted for further validation

#### Scenario: Non-mapping document
- **WHEN** the YAML document is a list or scalar
- **THEN** output `{"errors":[{"field":"","type":"parse","message":"<msg>"}]}`

---

### Requirement: Name validation
`metadata.name` SHALL be required, non-null, non-empty, and SHALL match `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (minimum length 2).

#### Scenario: Valid name
- **WHEN** `metadata.name` is `"my-mesh"`
- **THEN** name validation passes

#### Scenario: Missing name
- **WHEN** `metadata.name` is absent or null
- **THEN** output error `{"field":"metadata.name","type":"required","message":"<msg>"}`

#### Scenario: Invalid name format
- **WHEN** `metadata.name` is `"My_Mesh"` or `"a"` (too short) or `"-bad"` (starts with hyphen)
- **THEN** output error `{"field":"metadata.name","type":"invalid","message":"<msg>"}`

---

### Requirement: Instance count validation and default
`spec.instances` SHALL be a positive integer. If absent, it SHALL default to `1`.

#### Scenario: Absent instances defaults to 1
- **WHEN** `spec.instances` is not specified
- **THEN** the persisted resource has `spec.instances = 1`

#### Scenario: Invalid instances
- **WHEN** `spec.instances` is `0`, negative, or non-integer
- **THEN** output error `{"field":"spec.instances","type":"invalid","message":"<msg>"}`

---

### Requirement: Runtime version validation
`spec.runtime`, when present, SHALL parse as `major.minor.patch` where each part is a non-negative integer. If absent, it SHALL be omitted from output.

#### Scenario: Valid runtime
- **WHEN** `spec.runtime` is `"1.2.3"`
- **THEN** runtime validation passes and value is preserved

#### Scenario: Invalid runtime format
- **WHEN** `spec.runtime` is `"1.2"` or `"v1.2.3"` or `"1.2.x"`
- **THEN** output error `{"field":"spec.runtime","type":"invalid","message":"<msg>"}`

#### Scenario: Absent runtime omitted
- **WHEN** `spec.runtime` is not in the input
- **THEN** `spec.runtime` is absent from the output JSON

---

### Requirement: Memory resource validation and defaults
When `spec.resources.memory` is absent, the system SHALL default it to `{"limit":"1Gi","request":"1Gi"}`. When present, `limit` SHALL be required and `request` SHALL default to `limit`. Memory quantities SHALL be a non-negative integer optionally suffixed with `Ki`, `Mi`, `Gi`, or `Ti`. `request` SHALL NOT exceed `limit`.

#### Scenario: Absent memory defaults applied
- **WHEN** `spec.resources.memory` is not specified
- **THEN** output has `spec.resources.memory = {"limit":"1Gi","request":"1Gi"}`

#### Scenario: Memory limit required when memory object present
- **WHEN** `spec.resources.memory` is present but `limit` is absent
- **THEN** output error `{"field":"spec.resources.memory.limit","type":"required","message":"<msg>"}`

#### Scenario: Memory request defaults to limit
- **WHEN** `spec.resources.memory.limit` is `"2Gi"` and `request` is absent
- **THEN** output has `spec.resources.memory.request = "2Gi"`

#### Scenario: Memory request exceeds limit rejected
- **WHEN** `spec.resources.memory.request` parses to a value greater than `limit`
- **THEN** output error `{"field":"spec.resources.memory.request","type":"invalid","message":"<msg>"}`

#### Scenario: Invalid memory quantity
- **WHEN** `spec.resources.memory.limit` is `"abc"` or `"-1Gi"`
- **THEN** output error `{"field":"spec.resources.memory.limit","type":"invalid","message":"<msg>"}`

---

### Requirement: CPU resource validation and defaults
When `spec.resources.cpu` is absent, it SHALL be omitted from output. When present, `limit` SHALL be required and `request` SHALL default to `limit`. CPU quantities SHALL be a non-negative integer optionally suffixed with `m`. `request` SHALL NOT exceed `limit`.

#### Scenario: Absent CPU omitted from output
- **WHEN** `spec.resources.cpu` is not specified
- **THEN** `spec.resources.cpu` is absent from the output JSON

#### Scenario: CPU limit required when cpu object present
- **WHEN** `spec.resources.cpu` is present but `limit` is absent
- **THEN** output error `{"field":"spec.resources.cpu.limit","type":"required","message":"<msg>"}`

#### Scenario: CPU request defaults to limit
- **WHEN** `spec.resources.cpu.limit` is `"500m"` and `request` is absent
- **THEN** output has `spec.resources.cpu.request = "500m"`

#### Scenario: CPU request exceeds limit rejected
- **WHEN** `spec.resources.cpu.request` parses to a value greater than `limit`
- **THEN** output error `{"field":"spec.resources.cpu.request","type":"invalid","message":"<msg>"}`

#### Scenario: Invalid CPU quantity
- **WHEN** `spec.resources.cpu.limit` is `"1.5"` or `"abc"`
- **THEN** output error `{"field":"spec.resources.cpu.limit","type":"invalid","message":"<msg>"}`

---

### Requirement: Authentication default
`spec.access.authentication.enabled` SHALL default to `true` when absent.

#### Scenario: Authentication defaults to true
- **WHEN** `spec.access.authentication.enabled` is not specified
- **THEN** output has `spec.access.authentication.enabled = true`

#### Scenario: Explicit false accepted
- **WHEN** `spec.access.authentication.enabled` is `false`
- **THEN** output has `spec.access.authentication.enabled = false`

---

### Requirement: Migration strategy validation and default
`spec.migration.strategy` SHALL default to `"FullStop"`. It SHALL only accept the value `"FullStop"`; any other value SHALL produce an invalid error.

#### Scenario: Migration strategy defaults to FullStop
- **WHEN** `spec.migration.strategy` is not specified
- **THEN** output has `spec.migration.strategy = "FullStop"`

#### Scenario: Invalid migration strategy rejected
- **WHEN** `spec.migration.strategy` is `"RollingUpdate"`
- **THEN** output error `{"field":"spec.migration.strategy","type":"invalid","message":"<msg>"}`

---

### Requirement: Forbidden autoScaling field
Any field named `autoScaling` anywhere under `spec` SHALL be rejected.

#### Scenario: autoScaling at spec root
- **WHEN** the input has `spec.autoScaling: ...`
- **THEN** output error `{"field":"spec.autoScaling","type":"forbidden","message":"<msg>"}`

#### Scenario: autoScaling nested under spec
- **WHEN** the input has `spec.resources.autoScaling: ...`
- **THEN** output error `{"field":"spec.resources.autoScaling","type":"forbidden","message":"<msg>"}`

---

### Requirement: Error output format
All validation and operational errors SHALL be printed as `{"errors":[...]}` to stdout with nothing to stderr. Each error object SHALL have `field` (dot-path string), `message` (human-readable string), and `type` (one of: `required`, `invalid`, `forbidden`, `duplicate`, `not_found`, `parse`).

#### Scenario: Single error
- **WHEN** one validation rule fails
- **THEN** output `{"errors":[{"field":"<path>","type":"<type>","message":"<msg>"}]}`

#### Scenario: Multiple errors
- **WHEN** multiple validation rules fail simultaneously
- **THEN** output `{"errors":[...]}` containing all violations; order is not significant

---

### Requirement: Success output — create and describe
Successful `create` and `describe` SHALL print the full resource JSON with `metadata`, `spec` (all defaulted fields), and `status.state = "Running"`.

#### Scenario: Create success output
- **WHEN** create succeeds
- **THEN** output `{"metadata":{"name":"<n>"},"spec":{...all fields...},"status":{"state":"Running"}}`

#### Scenario: New mesh starts as Running
- **WHEN** a mesh is first created
- **THEN** `status.state` is `"Running"`

---

### Requirement: Success output — delete
Successful `delete` SHALL print `{"message":"<non-empty>","metadata":{"name":"<string>"}}`. The exact message wording is not part of the contract.

#### Scenario: Delete confirmation printed
- **WHEN** delete succeeds
- **THEN** output contains a non-empty `message` and `metadata.name` matching the deleted resource
