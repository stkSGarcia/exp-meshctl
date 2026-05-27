# Mesh Migrate

## Purpose

Defines the requirements for the `meshctl mesh migrate` command, which advances an active migration by one stage or completes it when the final stage is reached.

## Requirements

### Requirement: mesh migrate command
The system SHALL support the command `meshctl mesh migrate <name>` to advance an active migration by one stage. After advancing, the full mesh resource SHALL be printed to stdout.

#### Scenario: Migration advanced by one stage
- **WHEN** `mesh migrate <name>` is called and the current stage is not the final stage
- **THEN** `status.migration.stage` advances to the next stage and the full mesh resource is printed

#### Scenario: Full resource printed after stage advance
- **WHEN** `mesh migrate` successfully advances a stage
- **THEN** the response is the full mesh resource JSON (same shape as `mesh describe`)

---

### Requirement: mesh migrate — final stage completes migration
When `mesh migrate` is called on the final stage, the system SHALL complete the migration instead of advancing.

#### Scenario: Final stage triggers completion
- **WHEN** `mesh migrate <name>` is called and the current stage is the final stage for the strategy
- **THEN** the migration is completed: `Migration` condition removed, `status.migration` removed, and the full resource is printed

---

### Requirement: mesh migrate — missing mesh error
If the named mesh does not exist, `mesh migrate` SHALL return a not-found error.

#### Scenario: Missing mesh
- **WHEN** `mesh migrate <name>` is called and no mesh with that name exists
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: mesh migrate — no active migration error
If the named mesh exists but has no active migration, `mesh migrate` SHALL return an error.

#### Scenario: No active migration
- **WHEN** `mesh migrate <name>` is called and the mesh has no `Migration` condition with `status="True"`
- **THEN** output `{"errors":[{"field":"status.migration","type":"invalid","message":"no active migration for mesh '<name>'"}]}`
