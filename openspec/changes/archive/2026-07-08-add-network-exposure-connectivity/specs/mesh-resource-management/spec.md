## ADDED Requirements

> Extends: mesh-resource-management/add-mesh-lifecycle-topology

### Requirement: Mesh connectivity resource fields
The system SHALL include exposure and management endpoint fields in mesh resource create, update, and describe behavior.

#### Scenario: Create returns connectivity state
- **WHEN** `mesh create -f <path>` creates a mesh with exposure or management endpoint configuration
- **THEN** the returned mesh resource includes the accepted `spec.exposure` and `spec.management.enabled` values
- **AND** the returned mesh resource includes the corresponding computed status fields

#### Scenario: Describe returns connectivity state
- **WHEN** `mesh describe <name>` describes a mesh with exposure or management endpoint configuration
- **THEN** the returned mesh resource includes the accepted `spec.exposure` and `spec.management.enabled` values
- **AND** the returned mesh resource includes the corresponding computed status fields

#### Scenario: Update validates connectivity fields
- **WHEN** `mesh update -f <path>` applies a partial update containing exposure or management endpoint fields
- **THEN** the update applies the same validation, defaulting, forbidden-field checks, and immutability checks as mesh creation
