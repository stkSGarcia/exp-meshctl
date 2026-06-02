# mesh-migrate-command Specification

## ADDED Requirements

### Requirement: mesh migrate subcommand routing
The CLI SHALL accept `mesh migrate <name>` and route to the migrate handler with the given mesh name.

#### Scenario: Valid migrate subcommand dispatched
- **WHEN** the user runs `meshctl.py mesh migrate <name>`
- **THEN** the migrate handler is invoked with the given name

---

### Requirement: mesh migrate advances migration by one stage
`mesh migrate <name>` SHALL advance the active migration by one stage. After advancing, the system SHALL print the full mesh resource JSON to stdout.

#### Scenario: Stage advances to next
- **WHEN** the mesh has an active migration with a next stage available
- **THEN** `status.migration.stage` is updated to the next stage in the sequence and the full resource is printed

---

### Requirement: mesh migrate completes migration at final stage
When the current stage is the final stage of the migration sequence, `mesh migrate` SHALL complete the migration instead of advancing to a non-existent next stage.

#### Scenario: Final stage triggers completion
- **WHEN** `mesh migrate` is called and the current stage is the last stage
- **THEN** the migration is completed: `Migration` condition and `status.migration` are removed, and the full resource is printed

---

### Requirement: mesh migrate not-found error
If the named mesh does not exist, `mesh migrate` SHALL output a not-found error.

#### Scenario: Missing mesh
- **WHEN** `mesh migrate <name>` is called and no mesh with that name exists
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: mesh migrate no-active-migration error
If the mesh exists but has no active migration, `mesh migrate` SHALL reject the operation.

#### Scenario: No active migration
- **WHEN** `mesh migrate <name>` is called and the mesh has no active migration
- **THEN** output `{"errors":[{"field":"status.migration","type":"invalid","message":"no active migration for mesh '<name>'"}]}`
