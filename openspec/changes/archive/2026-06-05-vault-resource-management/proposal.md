## Why

`meshctl` currently only manages mesh resources. Vaults are a second resource kind that enable logical storage stores inside a mesh, and operators need the same CRUD lifecycle (create, list, describe, update, delete) with cross-resource referential integrity enforced at the CLI layer.

## What Changes

- Add a `vault` subcommand group to `meshctl.py` with the five operations: `create`, `list`, `describe`, `update`, `delete`.
- Introduce vault resource persistence alongside mesh persistence.
- Enforce that `spec.meshRef` points to an existing mesh on create and update.
- Enforce uniqueness on `metadata.name` and on the `(spec.meshRef, spec.vaultName)` identity pair.
- Mark `spec.meshRef` and `spec.vaultName` immutable after creation.
- Block `mesh delete` when dependent vaults exist.
- Compute `status.state` and `status.conditions[Ready]` from the parent mesh's stability.

## Capabilities

### New Capabilities

- `vault-management`: Full CRUD lifecycle for vault resources, including field validation, cross-resource referential integrity against mesh, immutability enforcement, status derivation from parent mesh, and deletion conflict guard on the parent mesh.

### Modified Capabilities

- `mesh-management`: Add a deletion conflict check — `mesh delete` must be rejected when one or more vaults reference that mesh via `spec.meshRef`.

## Impact

- `meshctl.py`: New `vault` command group; modification to mesh delete handler to check for dependent vaults.
- In-memory / persistent store: Needs a vault store alongside the mesh store.
- Existing mesh tests: `mesh delete` success scenarios are unaffected when no vaults exist; new conflict scenarios must be covered.
