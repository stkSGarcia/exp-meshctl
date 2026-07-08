## ADDED Requirements

### Requirement: Vault CLI command surface
The system SHALL expose `vault create`, `vault list`, `vault describe`, `vault update`, and `vault delete` operations through `meshctl.py`.

#### Scenario: Create command accepts a YAML file
- **WHEN** the user runs `uv run --project /app meshctl.py vault create -f <path>`
- **THEN** the system SHALL read `<path>` as the vault YAML input and attempt to create the resource.

#### Scenario: List command returns existing vault summaries
- **WHEN** the user runs `uv run --project /app meshctl.py vault list`
- **THEN** the system SHALL print a JSON array of vault summaries.

#### Scenario: Describe command returns a named vault
- **WHEN** the user runs `uv run --project /app meshctl.py vault describe <name>`
- **THEN** the system SHALL print the full vault resource for `<name>`.

#### Scenario: Update command accepts a YAML file
- **WHEN** the user runs `uv run --project /app meshctl.py vault update -f <path>`
- **THEN** the system SHALL read `<path>` as the vault update YAML input and attempt to update the named resource.

#### Scenario: Delete command removes a named vault
- **WHEN** the user runs `uv run --project /app meshctl.py vault delete <name>`
- **THEN** the system SHALL remove the vault and print a JSON confirmation object.

### Requirement: Vault input format
The system SHALL accept exactly one YAML document whose root value is a mapping with supported top-level `metadata` and `spec` content.

#### Scenario: YAML read or parse failure
- **WHEN** the vault input file cannot be read or parsed as YAML
- **THEN** the system SHALL print a JSON error object containing an error with field `""` and type `parse`.

#### Scenario: YAML document is not a mapping
- **WHEN** the vault input parses but the YAML document root is not a mapping
- **THEN** the system SHALL print a JSON error object and SHALL NOT persist a vault.

### Requirement: Vault spec fields and defaults
The system SHALL support `metadata.name`, required `spec.meshRef`, optional `spec.vaultName`, optional `spec.updatePolicy`, optional `spec.template`, and optional `spec.templateRef`.

#### Scenario: Metadata name is required
- **WHEN** a vault create input omits `metadata.name` or provides it as null or an empty string
- **THEN** the system SHALL report field `metadata.name` with type `required`.

#### Scenario: Metadata name uses mesh naming rule
- **WHEN** a vault create input provides `metadata.name` that does not satisfy the mesh naming rule
- **THEN** the system SHALL report field `metadata.name` with type `invalid`.

#### Scenario: Mesh reference is required
- **WHEN** a vault create input omits `spec.meshRef` or provides it as null or an empty string
- **THEN** the system SHALL report field `spec.meshRef` with type `required`.

#### Scenario: Vault name defaults from metadata name
- **WHEN** a valid vault create input omits `spec.vaultName`
- **THEN** the created vault SHALL include `spec.vaultName` equal to `metadata.name`.

#### Scenario: Update policy defaults to retain
- **WHEN** a valid vault create input omits `spec.updatePolicy`
- **THEN** the created vault SHALL include `spec.updatePolicy` equal to `"retain"`.

#### Scenario: Update policy validates allowed values
- **WHEN** `spec.updatePolicy` is present and is not `"retain"` or `"recreate"`
- **THEN** the system SHALL report field `spec.updatePolicy` with type `invalid`.

#### Scenario: Optional template fields are preserved
- **WHEN** a valid vault create input includes exactly one of `spec.template` or `spec.templateRef`
- **THEN** the created vault SHALL include the provided template field.

### Requirement: Vault parent mesh validation
The system SHALL require `spec.meshRef` to reference an existing mesh on create and update.

#### Scenario: Create rejects missing parent mesh
- **WHEN** a vault create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid` and a message that names the missing mesh.

#### Scenario: Update rejects missing parent mesh
- **WHEN** a vault update would result in `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid` and a message that names the missing mesh.

### Requirement: Vault duplicate handling
The system SHALL reject duplicate vault metadata names and duplicate vault identities for the same mesh and vault name pair.

#### Scenario: Duplicate metadata name on create
- **WHEN** a vault create request uses `metadata.name` that already exists as a vault
- **THEN** the system SHALL report field `metadata.name` with type `duplicate` and SHALL NOT overwrite the existing vault.

#### Scenario: Duplicate mesh and vault name pair on create
- **WHEN** a vault create request has `spec.meshRef` and `spec.vaultName` that exactly match an existing vault
- **THEN** the system SHALL report field `spec.vaultName` with type `duplicate` and a message that names the conflicting identity.

#### Scenario: Duplicate mesh and vault name pair on update
- **WHEN** a vault update would result in `spec.meshRef` and `spec.vaultName` that exactly match a different existing vault
- **THEN** the system SHALL report field `spec.vaultName` with type `duplicate` and SHALL NOT persist the update.

### Requirement: Vault template exclusivity
The system SHALL allow at most one of `spec.template` and `spec.templateRef` to be set on a vault.

#### Scenario: Create rejects both template fields
- **WHEN** a vault create input includes both `spec.template` and `spec.templateRef`
- **THEN** the system SHALL report field `spec.template` with type `invalid`.

#### Scenario: Update rejects both template fields
- **WHEN** a vault update would result in both `spec.template` and `spec.templateRef` being set
- **THEN** the system SHALL report field `spec.template` with type `invalid` and SHALL NOT persist the update.

### Requirement: Vault update operation
The system SHALL expose `vault update -f <path>` to apply a partial YAML update to an existing vault selected by `metadata.name`.

#### Scenario: Update selects the stored vault by name
- **WHEN** the update input contains `metadata.name`
- **THEN** the system SHALL use that value to select the stored vault being updated.

#### Scenario: Missing vault on update
- **WHEN** the user updates a vault name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Update validation failure is atomic
- **WHEN** any validation error occurs while processing a vault update
- **THEN** the system SHALL reject the whole update and SHALL NOT persist any field from that update.

#### Scenario: Omitted field keeps stored value
- **WHEN** a vault update omits a field that exists on the stored resource
- **THEN** the system SHALL keep the stored value for that field.

#### Scenario: Provided mutable leaf replaces stored leaf
- **WHEN** a vault update provides a mutable leaf field that already exists on the stored resource
- **THEN** the system SHALL replace the stored leaf value with the provided value.

### Requirement: Vault immutable fields
The system SHALL treat `spec.meshRef` and `spec.vaultName` as immutable after vault creation.

#### Scenario: Mesh reference is immutable
- **WHEN** a vault update changes the stored `spec.meshRef`
- **THEN** the system SHALL report field `spec.meshRef` with type `immutable` and SHALL NOT persist the update.

#### Scenario: Vault name is immutable
- **WHEN** a vault update changes the stored `spec.vaultName`
- **THEN** the system SHALL report field `spec.vaultName` with type `immutable` and SHALL NOT persist the update.

### Requirement: Vault status
The system SHALL return vault status derived from the parent mesh.

#### Scenario: Ready condition is true for stable parent mesh
- **WHEN** a vault references a mesh whose `status.stable` is `true`
- **THEN** the returned vault SHALL include `status.conditions` with one condition of type `Ready`, status `"True"`, and message `""`.

#### Scenario: Ready condition is false for unstable parent mesh
- **WHEN** a vault references a mesh whose `status.stable` is `false`
- **THEN** the returned vault SHALL include `status.conditions` with one condition of type `Ready` and status `"False"`.

#### Scenario: Ready state maps to Ready
- **WHEN** a returned vault has `Ready` condition status `"True"`
- **THEN** `status.state` SHALL be `"Ready"`.

#### Scenario: Not ready state maps to Pending
- **WHEN** a returned vault has `Ready` condition status `"False"`
- **THEN** `status.state` SHALL be `"Pending"`.

### Requirement: Successful vault output
The system SHALL print successful vault command results as JSON to stdout, print nothing to stderr, and include defaulted spec fields and required status fields.

#### Scenario: Create returns full vault
- **WHEN** a vault is created successfully
- **THEN** the system SHALL print the full vault with `metadata.name`, the defaulted `spec`, `status.state`, and `status.conditions`.

#### Scenario: Describe returns full vault
- **WHEN** an existing vault is described
- **THEN** the system SHALL print the full vault with status derived from the parent mesh.

#### Scenario: Update returns full vault
- **WHEN** an existing vault is updated successfully
- **THEN** the system SHALL print the full updated vault with status derived from the parent mesh.

#### Scenario: Delete returns confirmation object
- **WHEN** an existing vault is deleted
- **THEN** the system SHALL print a JSON object containing a non-empty `message` and `metadata.name`.

### Requirement: Vault list output
The system SHALL list vault summaries sorted by `name` ascending using lexicographic, case-sensitive ordering.

#### Scenario: List returns sorted summaries
- **WHEN** vaults named `beta`, `alpha`, and `gamma` exist
- **THEN** `vault list` SHALL print summaries in the order `alpha`, `beta`, `gamma`.

#### Scenario: List summary shape
- **WHEN** `vault list` returns a vault
- **THEN** each array item SHALL contain only the vault `name`, `meshRef`, `vaultName`, and `status.state` summary fields.

### Requirement: Vault not-found handling
The system SHALL reject missing named vault resources using structured JSON errors.

#### Scenario: Missing vault on describe
- **WHEN** the user describes a vault name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing vault on delete
- **WHEN** the user deletes a vault name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing vault on update
- **WHEN** the user updates a vault name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

### Requirement: Vault error output
The system SHALL use the JSON error shape, exit codes, and formatting rules established for mesh resources.

#### Scenario: Error object shape
- **WHEN** any vault validation, parse, duplicate, not-found, immutable, or dependency error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.

#### Scenario: Error order is not contractual
- **WHEN** multiple vault errors are returned
- **THEN** callers SHALL NOT rely on the order of errors in the `errors` array.
