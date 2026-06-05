# Vault Management

## Purpose

TBD — Defines the requirements for the `meshctl` CLI tool's vault management operations, including creating, listing, describing, updating, and deleting vault resources, along with all input validation rules, default-application logic, and output format contracts.

## Requirements

### Requirement: CLI entry point for vault
The tool SHALL be invokable as `uv run --project /app meshctl.py vault <operation> [arguments]` and SHALL route to the correct vault operation handler.

#### Scenario: Valid vault subcommand dispatched
- **WHEN** the user runs `meshctl.py vault create -f <path>`
- **THEN** the vault create handler is invoked with the given file path

#### Scenario: Unknown vault subcommand
- **WHEN** the user runs `meshctl.py vault <unknown>`
- **THEN** the tool exits with a non-success indicator

---

### Requirement: Vault create
The system SHALL read a YAML document from the file path given by `-f`, apply all defaults, validate all fields, and — if valid and all uniqueness constraints pass — persist the vault resource and print the full vault as JSON to stdout.

#### Scenario: Valid create
- **WHEN** a valid YAML file is provided with a unique name and a valid meshRef
- **THEN** the vault is persisted with defaults applied and the full resource JSON is printed

#### Scenario: Invalid YAML file
- **WHEN** the file cannot be read or is not valid YAML
- **THEN** output `{"errors":[{"field":"","type":"parse","message":"<msg>"}]}`

---

### Requirement: Vault list
The system SHALL print a JSON array of vault summaries sorted by `name` ascending lexicographically (case-sensitive).

#### Scenario: Non-empty vault store
- **WHEN** one or more vaults exist
- **THEN** output a JSON array of `{"name":"<string>","status":{"state":"<string>"}}` objects sorted by name ascending

#### Scenario: Empty vault store
- **WHEN** no vaults exist
- **THEN** output `[]`

---

### Requirement: Vault describe
The system SHALL print the full resource JSON for the vault identified by `<name>`.

#### Scenario: Existing vault
- **WHEN** the named vault exists
- **THEN** output the full resource JSON including all defaulted spec fields and `status`

#### Scenario: Unknown vault
- **WHEN** the named vault does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Vault update
The system SHALL read a YAML document from the file path given by `-f`, merge its fields into the stored vault, validate all constraints, enforce immutability, and — if valid — persist the updated vault and print the full resource JSON to stdout.

#### Scenario: Valid update persists and prints
- **WHEN** a valid YAML file is provided whose `metadata.name` matches a stored vault
- **THEN** the merged vault is persisted and the full resource JSON is printed

#### Scenario: Unknown vault on update
- **WHEN** `update` is called with a name that does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}` and persist nothing

#### Scenario: Validation error rolls back entire update
- **WHEN** the update YAML produces any validation error after merging
- **THEN** output all errors and persist nothing

---

### Requirement: Vault delete
The system SHALL remove the named vault from the store and print a confirmation JSON object.

#### Scenario: Existing vault deleted
- **WHEN** the named vault exists
- **THEN** remove it from the store and output `{"message":"<non-empty>","metadata":{"name":"<string>"}}`

#### Scenario: Unknown vault
- **WHEN** the named vault does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: Vault name validation
`metadata.name` SHALL be required, non-null, non-empty, and SHALL match `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (minimum length 2), identical to the mesh naming rule.

#### Scenario: Valid name accepted
- **WHEN** `metadata.name` is `"my-vault"`
- **THEN** name validation passes

#### Scenario: Missing name rejected
- **WHEN** `metadata.name` is absent or null
- **THEN** output error `{"field":"metadata.name","type":"required","message":"<msg>"}`

#### Scenario: Invalid name format rejected
- **WHEN** `metadata.name` is `"My_Vault"` or `"a"` or `"-bad"`
- **THEN** output error `{"field":"metadata.name","type":"invalid","message":"<msg>"}`

---

### Requirement: meshRef validation and cross-resource check
`spec.meshRef` SHALL be required. Its value SHALL match an existing mesh name on both create and update.

#### Scenario: meshRef required on create
- **WHEN** `spec.meshRef` is absent or null
- **THEN** output error `{"field":"spec.meshRef","type":"required","message":"<msg>"}`

#### Scenario: meshRef points to unknown mesh
- **WHEN** `spec.meshRef` names a mesh that does not exist in the mesh store
- **THEN** output error `{"field":"spec.meshRef","type":"invalid","message":"<msg>"}` naming the missing mesh

#### Scenario: meshRef points to existing mesh
- **WHEN** `spec.meshRef` names a mesh that exists
- **THEN** validation passes for this field

---

### Requirement: vaultName default
`spec.vaultName` SHALL default to the value of `metadata.name` when absent.

#### Scenario: vaultName absent defaults to metadata.name
- **WHEN** `spec.vaultName` is not provided
- **THEN** the persisted vault has `spec.vaultName` equal to `metadata.name`

#### Scenario: Explicit vaultName accepted
- **WHEN** `spec.vaultName` is provided with a non-empty string
- **THEN** the persisted vault has `spec.vaultName` equal to the provided value

---

### Requirement: updatePolicy validation and default
`spec.updatePolicy` SHALL default to `"retain"` when absent. Only `"retain"` and `"recreate"` are valid values.

#### Scenario: updatePolicy absent defaults to retain
- **WHEN** `spec.updatePolicy` is not provided
- **THEN** the persisted vault has `spec.updatePolicy = "retain"`

#### Scenario: Valid updatePolicy accepted
- **WHEN** `spec.updatePolicy` is `"retain"` or `"recreate"`
- **THEN** validation passes for this field

#### Scenario: Invalid updatePolicy rejected
- **WHEN** `spec.updatePolicy` is any other string
- **THEN** output error `{"field":"spec.updatePolicy","type":"invalid","message":"<msg>"}`

---

### Requirement: Template exclusivity
At most one of `spec.template` and `spec.templateRef` SHALL be set. Setting both is invalid.

#### Scenario: Only template set
- **WHEN** `spec.template` is set and `spec.templateRef` is absent
- **THEN** validation passes for this constraint

#### Scenario: Only templateRef set
- **WHEN** `spec.templateRef` is set and `spec.template` is absent
- **THEN** validation passes for this constraint

#### Scenario: Neither set
- **WHEN** both `spec.template` and `spec.templateRef` are absent
- **THEN** validation passes for this constraint

#### Scenario: Both set rejected
- **WHEN** both `spec.template` and `spec.templateRef` are provided
- **THEN** output error `{"field":"spec.template","type":"invalid","message":"<msg>"}`

---

### Requirement: Duplicate metadata name rejected
`metadata.name` SHALL be unique across all vaults.

#### Scenario: Duplicate vault name rejected on create
- **WHEN** `create` is called with a `metadata.name` that already exists in the vault store
- **THEN** output `{"errors":[{"field":"metadata.name","type":"duplicate","message":"<msg>"}]}` and persist nothing

---

### Requirement: Duplicate identity pair rejected
The combination of `spec.meshRef` and `spec.vaultName` SHALL be unique across all vaults. A create that would produce an identical pair to an existing vault SHALL be rejected.

#### Scenario: Duplicate meshRef+vaultName pair rejected on create
- **WHEN** `create` is called and an existing vault has the same `spec.meshRef` and `spec.vaultName`
- **THEN** output `{"errors":[{"field":"spec.vaultName","type":"duplicate","message":"<msg>"}]}` naming the conflicting identity and persist nothing

#### Scenario: Same meshRef with different vaultName accepted
- **WHEN** `create` is called with the same `spec.meshRef` but a different `spec.vaultName` from any existing vault
- **THEN** the pair uniqueness check passes

---

### Requirement: Immutability of meshRef and vaultName
`spec.meshRef` and `spec.vaultName` SHALL be immutable after creation. Any update that changes either field SHALL be rejected.

#### Scenario: Changing meshRef on update rejected
- **WHEN** `update` provides a `spec.meshRef` that differs from the stored value
- **THEN** output `{"errors":[{"field":"spec.meshRef","type":"immutable","message":"field 'spec.meshRef' is immutable after creation"}]}`

#### Scenario: Changing vaultName on update rejected
- **WHEN** `update` provides a `spec.vaultName` that differs from the stored value
- **THEN** output `{"errors":[{"field":"spec.vaultName","type":"immutable","message":"field 'spec.vaultName' is immutable after creation"}]}`

#### Scenario: Omitting meshRef on update keeps stored value
- **WHEN** `update` omits `spec.meshRef`
- **THEN** the stored `spec.meshRef` is retained unchanged

---

### Requirement: Vault status — Ready condition
`status.conditions` SHALL include exactly one condition of type `"Ready"`. Its `status` SHALL be `"True"` when the parent mesh has `status.stable = true`, and `"False"` otherwise.

#### Scenario: Ready True when parent mesh is stable
- **WHEN** a vault is created and the parent mesh has `status.stable = true`
- **THEN** `status.conditions` contains `{"type":"Ready","status":"True","message":""}`

#### Scenario: Ready False when parent mesh is not stable
- **WHEN** a vault is created and the parent mesh has `status.stable = false`
- **THEN** `status.conditions` contains `{"type":"Ready","status":"False","message":""}`

---

### Requirement: Vault status — state field
`status.state` SHALL be `"Ready"` when the `Ready` condition is `"True"`, and `"Pending"` otherwise.

#### Scenario: state Ready when Ready condition is True
- **WHEN** the vault's `Ready` condition has `status = "True"`
- **THEN** `status.state = "Ready"`

#### Scenario: state Pending when Ready condition is False
- **WHEN** the vault's `Ready` condition has `status = "False"`
- **THEN** `status.state = "Pending"`

---

### Requirement: Vault error output format
All vault validation and operational errors SHALL use the same JSON error shape as mesh errors: `{"errors":[{"field":"<path>","type":"<type>","message":"<msg>"}]}` printed to stdout. Exit codes and formatting rules are identical to mesh commands.

#### Scenario: Single vault error
- **WHEN** one validation rule fails on a vault command
- **THEN** output `{"errors":[{"field":"<path>","type":"<type>","message":"<msg>"}]}`

#### Scenario: Multiple vault errors
- **WHEN** multiple validation rules fail simultaneously on a vault command
- **THEN** output `{"errors":[...]}` containing all violations; order is not significant
