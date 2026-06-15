## Why

Meshes can be managed today, but dependent vault resources are only described outside the formal OpenSpec contract. Adding vault resource management gives the CLI a second persisted resource type with clear validation, status, and dependency behavior before implementation begins.

## What Changes

- Add `vault create -f <path>` to read YAML, apply defaults, validate the referenced mesh, persist the vault, and print the full vault resource.
- Add `vault list`, `vault describe <name>`, `vault update -f <path>`, and `vault delete <name>` with JSON output and error handling aligned with mesh resources.
- Define the vault spec fields, including required `metadata.name`, required `spec.meshRef`, defaulted `spec.vaultName`, defaulted `spec.updatePolicy`, and optional template fields.
- Enforce vault cross-resource validation, duplicate metadata names, duplicate `(spec.meshRef, spec.vaultName)` identity pairs, template exclusivity, and immutability of `spec.meshRef` and `spec.vaultName`.
- Derive vault `Ready` condition and `status.state` from the parent mesh stability.
- Block `mesh delete` when one or more vaults reference the mesh.

## Capabilities

### New Capabilities
- `vault-resource-management`: Defines vault CLI operations, vault spec/defaulting/validation, persistence, status derivation from parent meshes, and vault JSON output contracts.

### Modified Capabilities
- `mesh-resource-management`: Add mesh deletion conflict behavior when dependent vaults reference the mesh.

## Impact

- Affected code: `meshctl.py` and any supporting helpers for CLI routing, validation, defaulting, update merge behavior, persistence, status calculation, dependency lookup, and JSON output.
- Affected interface: new `uv run --project /app meshctl.py vault ...` commands plus a new conflict path for `mesh delete`.
- Affected tests: CLI coverage for vault CRUD, list sorting, parent mesh validation, duplicate rules, template exclusivity, immutable update fields, parent-derived status, not-found errors, and mesh deletion conflicts.
- Dependencies: no new external dependency is expected beyond the existing YAML parsing and JSON output support.
