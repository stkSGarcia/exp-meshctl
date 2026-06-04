## ADDED Requirements

### Requirement: mesh migrate command
The system SHALL support `meshctl mesh migrate <name>` to advance an active migration by one stage. After the transition, the system SHALL print the full mesh resource JSON.

#### Scenario: Advance migration by one stage
- **WHEN** `mesh migrate` is called on a mesh with an active migration and the current stage is not the final stage
- **THEN** `status.migration.stage` advances to the next stage in the strategy's sequence and the full resource JSON is printed

#### Scenario: Complete migration on final stage
- **WHEN** `mesh migrate` is called on a mesh whose current stage is the final stage for its strategy
- **THEN** the migration is completed: `status.migration` is removed, the `Migration` condition is removed, and the full resource JSON is printed

#### Scenario: LiveMigration advances through all stages
- **WHEN** `mesh migrate` is called on a `LiveMigration` mesh in stage `Prepare`
- **THEN** `status.migration.stage` becomes `Migrate`; calling again advances to `Complete`; calling again completes the migration

### Requirement: mesh migrate error — mesh not found
When the named mesh does not exist, `mesh migrate` SHALL output a not-found error.

#### Scenario: Missing mesh rejected
- **WHEN** `mesh migrate` is called with a name not in the store
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

### Requirement: mesh migrate error — no active migration
When the named mesh exists but has no active migration, `mesh migrate` SHALL output an invalid error.

#### Scenario: No active migration rejected
- **WHEN** `mesh migrate` is called on a mesh with no `Migration` condition active
- **THEN** output `{"errors":[{"field":"status.migration","type":"invalid","message":"no active migration for mesh '<name>'"}]}`
