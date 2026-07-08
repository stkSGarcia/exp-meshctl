## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud

### Requirement: Mesh operational policy output
The system SHALL include defaulted operational policy fields in successful `mesh create`, `mesh update`, and `mesh describe` JSON output.

#### Scenario: Create and describe include operational defaults
- **WHEN** a mesh is created or described
- **THEN** the response includes `spec.placement`
- **AND** the response includes `status.telemetryProbe`

### Requirement: Mesh policy validation on lifecycle operations
The system SHALL apply multi-region topology, placement, config bundle, telemetry tag, and extension validation during mesh create and update operations.

#### Scenario: Update rejects invalid regional migration
- **WHEN** a mesh update sets `spec.regions` with `spec.migration.strategy` equal to `"LiveMigration"`
- **THEN** validation returns the multi-region topology migration error
