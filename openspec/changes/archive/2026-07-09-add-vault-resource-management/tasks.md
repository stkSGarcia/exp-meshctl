## 1. Store and CLI Structure

- [x] 1.1 Add a `vault` argparse command group with `create -f`, `list`, `describe <name>`, `update -f`, and `delete <name>` operations.
- [x] 1.2 Refactor store loading and saving to support separate `meshes` and `vaults` collections while preserving compatibility with the legacy flat mesh store shape.
- [x] 1.3 Update existing mesh command paths to read and write through the mesh collection helper without changing public mesh output.
- [x] 1.4 Reuse YAML input loading, JSON success output, JSON error output, and shared metadata name validation for vault commands.

## 2. Vault Resource Model

- [x] 2.1 Implement vault create normalization for `metadata.name`, required `spec.meshRef`, defaulted `spec.vaultName`, defaulted `spec.updatePolicy`, optional `spec.template`, and optional `spec.templateRef`.
- [x] 2.2 Validate `spec.updatePolicy` as only `"retain"` or `"recreate"`.
- [x] 2.3 Enforce template exclusivity so at most one of `spec.template` and `spec.templateRef` is set.
- [x] 2.4 Validate `spec.meshRef` against existing meshes on create and update with `spec.meshRef` `invalid` errors that name the missing mesh.
- [x] 2.5 Reject duplicate vault `metadata.name` values and duplicate `(spec.meshRef, spec.vaultName)` identity pairs with the required field/type mappings.

## 3. Vault Operations

- [x] 3.1 Implement `vault create -f <path>` to validate, persist, and print the full vault resource with status.
- [x] 3.2 Implement `vault list` to print summaries sorted by `name` ascending with `name`, `meshRef`, `vaultName`, and `status.state`.
- [x] 3.3 Implement `vault describe <name>` to print the full vault or `metadata.name` `not_found`.
- [x] 3.4 Implement `vault update -f <path>` with partial merge semantics and all-or-nothing persistence on validation failure.
- [x] 3.5 Enforce update immutability for `spec.meshRef` and `spec.vaultName` with `immutable` errors on the changed field.
- [x] 3.6 Implement `vault delete <name>` to remove the vault and print a confirmation object, or return `metadata.name` `not_found`.

## 4. Status and Mesh Dependency Behavior

- [x] 4.1 Derive vault `status.conditions` with a single `Ready` condition from the parent mesh `status.stable`.
- [x] 4.2 Map vault `Ready` status `"True"` to `status.state` `"Ready"` and `"False"` to `"Pending"`.
- [x] 4.3 Ensure vault create, describe, update, and list outputs compute status from the current parent mesh state.
- [x] 4.4 Block `mesh delete` when dependent vaults reference the mesh through `spec.meshRef`, preserve the mesh, and return `metadata.name` `conflict`.
- [x] 4.5 Include dependent vault names in the mesh delete conflict message without making name order part of the contract.

## 5. Tests and Verification

- [x] 5.1 Add CLI tests for successful vault create, describe, list sorting, update, and delete flows.
- [x] 5.2 Add CLI tests for vault parse errors, invalid/non-mapping input, not-found describe/update/delete, and no-stderr JSON error behavior.
- [x] 5.3 Add CLI tests for vault defaults, invalid `updatePolicy`, template/templateRef exclusivity, missing parent mesh, and parent-derived status.
- [x] 5.4 Add CLI tests for duplicate metadata names, duplicate `(meshRef, vaultName)` pairs, immutable update fields, and atomic update failures.
- [x] 5.5 Add CLI tests for mesh delete conflicts when vaults reference the mesh and successful mesh delete after dependent vaults are removed.
- [x] 5.6 Run the full test suite and `openspec validate add-vault-resource-management`.
