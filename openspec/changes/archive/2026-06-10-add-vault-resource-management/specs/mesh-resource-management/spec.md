## ADDED Requirements

### Requirement: Mesh deletion dependency conflicts
The system SHALL reject `mesh delete` when one or more vaults reference the mesh through `spec.meshRef`.

#### Scenario: Mesh delete blocked by dependent vault
- **WHEN** the user deletes a mesh that is referenced by at least one vault through `spec.meshRef`
- **THEN** the system SHALL NOT delete the mesh and SHALL report field `metadata.name` with type `conflict`.

#### Scenario: Conflict message names dependent vaults
- **WHEN** a mesh delete is blocked by dependent vaults
- **THEN** the error message SHALL name the dependent vaults.

#### Scenario: Conflict vault order is not contractual
- **WHEN** multiple vaults block a mesh delete
- **THEN** callers SHALL NOT rely on the order of vault names in the conflict message.
