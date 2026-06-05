## 1. Vault Store

- [x] 1.1 Add `VAULT_STORE_PATH` constant and `load_vault_store` / `save_vault_store` helpers using the same atomic-write pattern as `load_store` / `save_store`

## 2. Vault Validation

- [x] 2.1 Implement `validate_vault` function: validate `metadata.name` (same naming rule as mesh), `spec.meshRef` (required), `spec.vaultName` (default to `metadata.name`), `spec.updatePolicy` (default `"retain"`, enum `retain|recreate`), and template exclusivity (`spec.template` and `spec.templateRef` mutually exclusive)
- [x] 2.2 Implement cross-resource check in `validate_vault`: load mesh store and verify `spec.meshRef` names an existing mesh; return `invalid` error on `spec.meshRef` if not found

## 3. Vault Status

- [x] 3.1 Implement `build_vault_status` helper: look up parent mesh `status.stable`, set `Ready` condition `"True"` or `"False"`, and derive `status.state` (`"Ready"` or `"Pending"`)

## 4. Vault Command Handlers

- [x] 4.1 Implement `vault_cmd_create`: load YAML, validate, check duplicate `metadata.name`, check duplicate `(meshRef, vaultName)` pair, build status, persist, print full vault JSON
- [x] 4.2 Implement `vault_cmd_list`: load vault store, print sorted array of `{"name": ..., "status": {"state": ...}}`
- [x] 4.3 Implement `vault_cmd_describe`: load vault store, return not-found error or print full vault JSON
- [x] 4.4 Implement `vault_cmd_update`: load YAML, lookup stored vault (not-found error if missing), check immutability of `spec.meshRef` and `spec.vaultName`, merge fields, re-validate, rebuild status, persist, print full vault JSON
- [x] 4.5 Implement `vault_cmd_delete`: lookup stored vault (not-found error if missing), delete, print confirmation `{"message": ..., "metadata": {"name": ...}}`

## 5. Mesh Delete Guard

- [x] 5.1 Modify `cmd_delete` (mesh) to load the vault store before deleting; if any vault has `spec.meshRef` equal to the mesh name, return a `conflict` error on `metadata.name` naming the dependent vaults and abort the delete

## 6. CLI Wiring

- [x] 6.1 Add `vault` subparser to `main()` with subcommands `create -f`, `list`, `describe <name>`, `update -f`, `delete <name>`
- [x] 6.2 Update the top-level dispatch in `main()` to route `vault` commands to their handlers alongside the existing `mesh` routing
