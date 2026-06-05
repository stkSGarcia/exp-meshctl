## Context

`meshctl.py` is a single-file CLI that manages mesh resources through a flat JSON store (`store.json`). The mesh command group covers create/list/describe/update/delete with full validation, lifecycle state, and structured error output. Vaults are a dependent resource that reference a parent mesh and must share the same error-output conventions and exit-code rules.

## Goals / Non-Goals

**Goals:**
- Add a `vault` subcommand group with the same five operations as `mesh`.
- Enforce referential integrity: vault commands verify the parent mesh exists; mesh delete blocks when vaults depend on it.
- Keep the store flat and addable without migrating existing mesh data.

**Non-Goals:**
- Persistent vault status updates over time (status is computed at create/update time from the parent mesh snapshot).
- Multi-file or remote storage backends.
- Vault lifecycle transitions analogous to mesh scale/stop/resume.

## Decisions

### Separate vault store file

Use a dedicated `vault_store.json` file (same directory as `store.json`) instead of namespacing keys inside `store.json` (e.g., `"vault::name"`) or restructuring `store.json` into `{"meshes": {}, "vaults": {}}`.

**Why:** A separate file requires zero migration of existing mesh data, keeps `load_store` / `save_store` untouched, and avoids the risk of corrupting the mesh store if vault code has a bug. The cost is two file reads for operations that need both resources (vault create/update, mesh delete), which is acceptable for a CLI tool with a small in-memory store.

**Alternatives considered:**
- Single structured store (`{"meshes": {}, "vaults": {}}`): Cleaner long-term but requires a one-time migration of the existing flat mesh store.
- Key-prefixed flat store (`"vault::name"`): No migration needed but is fragile (name parsing, collision if a mesh is named `"vault::..."`).

### Shared validation primitives, vault-specific validator

Add a `validate_vault` function parallel to `validate_and_build` for mesh. Both share the same `make_error`, quantity parsers, and `NAME_RE`. Vault validation covers: name format, `meshRef` presence and format, `vaultName` default, `updatePolicy` enum, and template exclusivity.

**Why:** Vault fields are structurally simpler than mesh fields (no resources, no network topology), so a separate function is cleaner than extending the mesh validator with conditionals.

### Status computed from parent mesh snapshot

On vault create and update, look up the parent mesh's `status.stable`. If `stable = true`, set `Ready = "True"` and `state = "Ready"`. Otherwise `Ready = "False"` and `state = "Pending"`.

**Why:** The spec defines vault status as derived from the parent mesh. A snapshot at write time is sufficient — the spec does not require vault status to auto-update when the mesh state changes later.

### Mesh delete guard in existing `cmd_delete`

Modify `cmd_delete` to load the vault store before deleting. If any vault has `spec.meshRef == name`, return a `conflict` error on `metadata.name`.

**Why:** The guard is a single load + filter at the top of an existing function. The vault store is cheap to load. No new abstraction is needed.

## Risks / Trade-offs

- **Two-file read on mesh delete** → Reads are cheap; risk is negligible. Mitigation: none needed.
- **Status snapshot can drift** → A vault created while a mesh is stable will show `Ready = "True"` even if the mesh later degrades. This is acceptable per spec (vault status is not a live view). Mitigation: document in spec as intended behavior.
- **Vault store file absent on first vault list** → Treat a missing `vault_store.json` as an empty store (same as `store.json` today). Mitigation: handled by the `load_vault_store` helper.

## Migration Plan

No data migration required. `store.json` is unchanged. `vault_store.json` is created on the first `vault create`.

Rollback: delete `vault_store.json` and remove the vault command group from `meshctl.py`.
