## MODIFIED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology
> Extends: one-shot-operations/add-one-shot-operations

### Requirement: Mesh CLI command surface (adapts mesh-resource-management/add-mesh-lifecycle-topology/mesh-cli-command-surface)
The system SHALL expose `mesh create`, `mesh list`, `mesh describe`, `mesh delete`, `mesh update`, and `mesh shell` operations through `meshctl.py`.

#### Scenario: Shell returns connection details
- **GIVEN** an existing mesh with exposure configured
- **WHEN** `meshctl mesh shell <name>` is run
- **THEN** the command outputs the mesh `connectionDetails` object only
- **AND** the output does not include a resource envelope

#### Scenario: Shell rejects missing mesh
- **GIVEN** no mesh exists for the requested name
- **WHEN** `meshctl mesh shell <name>` is run
- **THEN** the command returns the standard `not_found` JSON error shape

#### Scenario: Shell rejects unexposed mesh
- **GIVEN** an existing mesh without exposure configured
- **WHEN** `meshctl mesh shell <name>` is run
- **THEN** the command returns a JSON error with `field` equal to `spec.exposure`
- **AND** the error `type` is `invalid`
- **AND** the error `message` is `mesh '<name>' has no exposure configured`
