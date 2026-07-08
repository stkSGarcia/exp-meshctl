## ADDED Requirements

> Extends: one-shot-operations/add-one-shot-operations
> Extends: mesh-resource-management/add-mesh-lifecycle-topology

### Requirement: Mesh shell command surface (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-cli-command-surface)
The system SHALL expose `mesh shell <name>` through `meshctl.py` and SHALL return only the target mesh connection details object on success.

#### Scenario: Shell returns connection details
- **WHEN** `meshctl mesh shell <name>` targets a mesh with exposure configured
- **THEN** the command succeeds
- **AND** the output is exactly the `connectionDetails` object
- **AND** the output does not include a resource envelope

#### Scenario: Shell mesh not found
- **WHEN** `meshctl mesh shell <name>` targets a mesh that does not exist
- **THEN** the command fails using the standard `not_found` shape

#### Scenario: Shell mesh has no exposure
- **WHEN** `meshctl mesh shell <name>` targets a mesh with no exposure configured
- **THEN** the command fails with `field = "spec.exposure"`
- **AND** the command fails with `type = "invalid"`
- **AND** the command fails with `message = "mesh '<name>' has no exposure configured"`
