## MODIFIED Requirements

### Requirement: Mesh delete
The system SHALL remove the named mesh from the store and print a confirmation JSON object. Before deleting, the system SHALL check whether any vaults reference the mesh through `spec.meshRef`. If one or more dependent vaults exist, the system SHALL reject the deletion with a `conflict` error and SHALL NOT remove the mesh.

#### Scenario: Existing mesh deleted when no dependent vaults exist
- **WHEN** the named mesh exists and no vault has `spec.meshRef` equal to that mesh name
- **THEN** remove it from the store and output `{"message":"<non-empty>","metadata":{"name":"<string>"}}`

#### Scenario: Unknown mesh
- **WHEN** the named mesh does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

#### Scenario: Delete blocked when dependent vaults exist
- **WHEN** the named mesh exists and one or more vaults have `spec.meshRef` equal to that mesh name
- **THEN** output `{"errors":[{"field":"metadata.name","type":"conflict","message":"<msg>"}]}` naming the dependent vaults, and do not delete the mesh
