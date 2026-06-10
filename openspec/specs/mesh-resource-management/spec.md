# mesh-resource-management

## Purpose

Define the mesh CLI resource model, operations, validation, defaulting, persistence behavior, and JSON output contract.

## Requirements

### Requirement: Mesh CLI command surface
The system SHALL expose `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` operations through `meshctl.py`.

#### Scenario: Create command accepts a YAML file
- **WHEN** the user runs `uv run --project /app meshctl.py mesh create -f <path>`
- **THEN** the system SHALL read `<path>` as the mesh YAML input and attempt to create the resource.

#### Scenario: List command returns existing mesh summaries
- **WHEN** the user runs `uv run --project /app meshctl.py mesh list`
- **THEN** the system SHALL print a JSON array of mesh summaries.

#### Scenario: Describe command returns a named mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh describe <name>`
- **THEN** the system SHALL print the full persisted mesh resource for `<name>`.

#### Scenario: Delete command removes a named mesh
- **WHEN** the user runs `uv run --project /app meshctl.py mesh delete <name>`
- **THEN** the system SHALL remove the mesh and print a JSON confirmation object.

### Requirement: Mesh create input format
The system SHALL accept exactly one YAML document whose root value is a mapping with supported top-level `metadata` and `spec` content.

#### Scenario: YAML read or parse failure
- **WHEN** the create input file cannot be read or parsed as YAML
- **THEN** the system SHALL print a JSON error object containing an error with field `""` and type `parse`.

#### Scenario: YAML document is not a mapping
- **WHEN** the create input parses but the YAML document root is not a mapping
- **THEN** the system SHALL print a JSON error object and SHALL NOT persist a mesh.

### Requirement: Mesh name validation
The system SHALL require `metadata.name` to be a non-empty string of at least two characters matching `^[a-z0-9][a-z0-9-]*[a-z0-9]$`.

#### Scenario: Missing null or empty name
- **WHEN** a create input omits `metadata.name` or provides it as null or an empty string
- **THEN** the system SHALL report field `metadata.name` with type `required`.

#### Scenario: Invalid name format
- **WHEN** a create input provides a `metadata.name` that does not match the required format
- **THEN** the system SHALL report field `metadata.name` with type `invalid`.

### Requirement: Mesh duplicate and not-found handling
The system SHALL reject duplicate create requests and missing named resources using structured JSON errors.

#### Scenario: Duplicate mesh name on create
- **WHEN** a create request uses a `metadata.name` that already exists
- **THEN** the system SHALL report field `metadata.name` with type `duplicate` and SHALL NOT overwrite the existing resource.

#### Scenario: Missing mesh on describe
- **WHEN** the user describes a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing mesh on delete
- **WHEN** the user deletes a mesh name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

### Requirement: Mesh defaulting
The system SHALL apply documented defaults to successful create output and persisted resources while leaving fields without defaults absent when omitted.

#### Scenario: Defaults applied to omitted fields
- **WHEN** a valid create input omits `spec.instances`, `spec.resources.memory`, `spec.access.authentication.enabled`, and `spec.migration.strategy`
- **THEN** the created resource SHALL include `spec.instances` as `1`, `spec.resources.memory` as `{"limit": "1Gi", "request": "1Gi"}`, `spec.access.authentication.enabled` as `true`, and `spec.migration.strategy` as `"FullStop"`.

#### Scenario: Fields without defaults remain absent
- **WHEN** a valid create input omits `spec.runtime`, `spec.resources.cpu`, or any other field without a documented default
- **THEN** the created resource SHALL omit those fields from the returned and persisted resource.

### Requirement: Mesh field validation
The system SHALL validate mesh scalar fields and map each failed condition to the documented field and error type.

#### Scenario: Invalid instance count
- **WHEN** `spec.instances` is present and is not a positive integer
- **THEN** the system SHALL report field `spec.instances` with type `invalid`.

#### Scenario: Invalid runtime version
- **WHEN** `spec.runtime` is present and does not parse as semantic version `major.minor.patch` with non-negative integer parts
- **THEN** the system SHALL report field `spec.runtime` with type `invalid`.

#### Scenario: Invalid migration strategy
- **WHEN** `spec.migration.strategy` is present and is not `"FullStop"`
- **THEN** the system SHALL report field `spec.migration.strategy` with type `invalid`.

### Requirement: Mesh resource quantity validation
The system SHALL validate memory and CPU resource quantities and ensure requests do not exceed limits.

#### Scenario: Memory limit required when memory object is present
- **WHEN** `spec.resources.memory` is present but `spec.resources.memory.limit` is missing or null
- **THEN** the system SHALL report field `spec.resources.memory.limit` with type `required`.

#### Scenario: CPU limit required when CPU object is present
- **WHEN** `spec.resources.cpu` is present but `spec.resources.cpu.limit` is missing or null
- **THEN** the system SHALL report field `spec.resources.cpu.limit` with type `required`.

#### Scenario: Invalid memory quantity
- **WHEN** a memory `limit` or `request` is not a non-negative integer with optional `Ki`, `Mi`, `Gi`, or `Ti` suffix
- **THEN** the system SHALL report the corresponding `spec.resources.memory.<field>` with type `invalid`.

#### Scenario: Invalid CPU quantity
- **WHEN** a CPU `limit` or `request` is not a non-negative integer core count or non-negative integer with `m` suffix
- **THEN** the system SHALL report the corresponding `spec.resources.cpu.<field>` with type `invalid`.

#### Scenario: Memory request exceeds limit
- **WHEN** `spec.resources.memory.request` represents a quantity greater than `spec.resources.memory.limit`
- **THEN** the system SHALL report field `spec.resources.memory.request` with type `invalid`.

#### Scenario: CPU request exceeds limit
- **WHEN** `spec.resources.cpu.request` represents a quantity greater than `spec.resources.cpu.limit`
- **THEN** the system SHALL report field `spec.resources.cpu.request` with type `invalid`.

#### Scenario: Resource request defaults to limit
- **WHEN** `spec.resources.memory.request` or `spec.resources.cpu.request` is omitted from a present resource object with a valid limit
- **THEN** the system SHALL default the omitted request to the corresponding limit.

### Requirement: Autoscaling fields are forbidden
The system SHALL reject any field named `autoScaling` that appears under `spec`.

#### Scenario: Top-level autoscaling under spec
- **WHEN** create input contains `spec.autoScaling`
- **THEN** the system SHALL report field `spec.autoScaling` with type `forbidden`.

#### Scenario: Nested autoscaling under spec
- **WHEN** create input contains a nested field named `autoScaling` anywhere under `spec`
- **THEN** the system SHALL report the full dot path to that field with type `forbidden`.

### Requirement: Successful mesh output
The system SHALL print successful command results as JSON to stdout, print nothing to stderr, and include all defaulted fields.

#### Scenario: Create returns full running resource
- **WHEN** a mesh is created successfully
- **THEN** the system SHALL print the full resource with `metadata.name`, the defaulted `spec`, and `status.state` equal to `"Running"`.

#### Scenario: Describe returns full resource
- **WHEN** an existing mesh is described
- **THEN** the system SHALL print the full persisted resource.

#### Scenario: Delete returns confirmation object
- **WHEN** an existing mesh is deleted
- **THEN** the system SHALL print a JSON object containing a non-empty `message` and `metadata.name`.

### Requirement: Mesh list output
The system SHALL list mesh summaries sorted by `name` ascending using lexicographic, case-sensitive ordering.

#### Scenario: List returns sorted summaries
- **WHEN** meshes named `beta`, `alpha`, and `gamma` exist
- **THEN** `mesh list` SHALL print summaries in the order `alpha`, `beta`, `gamma`.

#### Scenario: List summary shape
- **WHEN** `mesh list` returns a mesh
- **THEN** each array item SHALL contain only the mesh `name` and `status.state` summary fields.

### Requirement: Error output
The system SHALL print errors as JSON to stdout with an `errors` array and SHALL print nothing to stderr.

#### Scenario: Error object shape
- **WHEN** any validation, parse, duplicate, or not-found error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.

#### Scenario: Error order is not contractual
- **WHEN** multiple errors are returned
- **THEN** callers SHALL NOT rely on the order of errors in the `errors` array.
