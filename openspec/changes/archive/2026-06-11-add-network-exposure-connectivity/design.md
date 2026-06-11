## Context

`meshctl.py` currently owns mesh parsing, defaulting, validation, persistence, status reconciliation, and public JSON projection in one module. Mesh resources already support create, update, list, describe, delete, and migrate operations, with structured JSON errors sorted by field and type. The new checkpoint extends the mesh resource model with optional service exposure, computed connection details, an optional management endpoint, and a `mesh shell` command.

The implementation should follow the existing resource flow: normalize create input, merge update input, validate post-merge state atomically, persist canonical resources, and apply public projection for command output.

## Goals / Non-Goals

**Goals:**

- Support optional `spec.exposure` without changing existing meshes that omit it.
- Validate exposure mode requiredness, mode-specific fields, field types, and forbidden fields.
- Compute `status.connectionDetails` for exposed meshes in create and describe output.
- Add `spec.management.enabled` with create-time defaulting and immutability on update.
- Compute `status.managementConnectionDetails` when management is enabled.
- Add `mesh shell <name>` to return only the connection details object and standard errors.

**Non-Goals:**

- No real network provisioning, DNS allocation, port binding, or shell process execution.
- No changes to vault, task, snapshot, or recovery resource semantics.
- No dependency changes or background services.

## Decisions

1. Keep exposure and management under existing mesh normalization and validation paths.

   Add `normalize_exposure`, `validate_exposure_object`, `normalize_management`, and `validate_management_object` helpers alongside the existing access, migration, and network helpers. This keeps create defaulting, update merge behavior, and atomic validation consistent with the rest of the mesh model.

   Alternative considered: compute and validate exposure only in public projection. That would make invalid persisted state easier to create during updates and would bypass the current validation contract.

2. Persist canonical spec fields but compute connection details from spec during status/projection.

   `spec.exposure` and `spec.management` should be persisted as canonical spec data. `status.connectionDetails` and `status.managementConnectionDetails` should be recomputed from the current spec before successful create/describe/update/migrate output and before `mesh shell`. This avoids stale derived status when update changes exposure fields.

   Alternative considered: store status details only at create/update time. That would require extra migration and upgrade handling for older resources and transient lifecycle paths.

3. Treat omitted exposure as absent, not defaulted.

   `spec.exposure` remains absent when omitted, and `status.connectionDetails` remains absent. When exposure exists, `type` is required and mode-specific defaults are applied only for computed connection details, such as default host or port values.

   Alternative considered: default to a specific exposure mode. The checkpoint explicitly says omitted exposure means no external access.

4. Implement `mesh shell` as a JSON lookup command.

   Add an argparse subcommand and `mesh_shell(name)` handler. The handler should load and upgrade the mesh, return `metadata.name` not-found errors for missing meshes, reject unexposed meshes with `spec.exposure` invalid, and print only `status.connectionDetails` on success.

   Alternative considered: route through `mesh describe` output and let callers extract the field. The checkpoint requires the command output to be the connection details object only.

## Risks / Trade-offs

- Derived status can drift if not centralized -> compute connection details from helper functions used by public projection and `mesh shell`.
- Update merge can leave now-forbidden fields from a previous exposure mode -> validate the merged `spec.exposure` object against the selected mode and report full dot-path forbidden errors.
- Existing persisted meshes lack management defaults -> `upgrade_stored_resource` should default `spec.management.enabled` to `false` while keeping `spec.exposure` absent.
- Management immutability depends on upgraded stored state -> compare stored and candidate `spec.management.enabled` after upgrade and merge.
