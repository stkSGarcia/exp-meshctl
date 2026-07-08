## ADDED Requirements

> Extends: mesh-resource-management/add-meshctl-mesh-crud

### Requirement: Mesh runtime migration command integration
The mesh resource management command surface SHALL apply runtime catalog validation, warning emission, migration strategy validation, and active migration update restrictions to mesh create and update operations, and SHALL expose `mesh migrate` as the operator command for advancing active mesh migrations.

#### Scenario: Create applies runtime validation
- **WHEN** `mesh create` receives a resource with `spec.runtime`
- **THEN** the create operation applies runtime catalog validation before persisting the mesh

#### Scenario: Update applies migration rules
- **WHEN** `mesh update` changes `spec.runtime` or `spec.migration.strategy`
- **THEN** the update operation applies migration strategy validation and active migration restrictions before persisting the mesh

#### Scenario: Migrate command is routed
- **WHEN** an operator runs `meshctl mesh migrate <name>`
- **THEN** the command is routed to the mesh migration transition behavior
