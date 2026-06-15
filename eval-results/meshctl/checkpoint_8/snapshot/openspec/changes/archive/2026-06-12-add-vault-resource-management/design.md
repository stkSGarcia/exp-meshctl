## Context

`meshctl.py` currently manages mesh resources through a compact argparse CLI backed by the JSON store selected by `MESHCTL_STORE`. Mesh create, list, describe, update, and delete already share conventions for YAML loading, JSON success output, JSON error output, validation error shapes, status fields, and deterministic list ordering.

Checkpoint 3 adds a second resource kind, `vault`, that depends on an existing mesh. The implementation should preserve the single-command local CLI model while making the store capable of representing both meshes and vaults and checking cross-resource constraints.

## Goals / Non-Goals

**Goals:**

- Add a `vault` command group with create, list, describe, update, and delete operations.
- Persist vault resources with create-time defaults and update-time immutability checks.
- Validate vault references against stored meshes and reject duplicate vault identities.
- Derive vault readiness and state from the referenced mesh status.
- Prevent mesh deletion while dependent vaults reference the mesh.
- Keep JSON output, error shape, exit code behavior, and deterministic ordering aligned with mesh commands.

**Non-Goals:**

- Add real secret storage, template rendering, or external vault integrations.
- Add asynchronous reconciliation, background status updates, or remote APIs.
- Change mesh lifecycle semantics except for deletion conflict checks.
- Guarantee exact human-readable wording for conflict messages beyond naming the relevant resource identities.

## Decisions

1. Store meshes and vaults as separate named collections in the same JSON store.

   Rationale: Vaults need duplicate checks within their own kind and cross-resource checks against meshes. Separate collections such as `{"meshes": {...}, "vaults": {...}}` make kind boundaries explicit while keeping persistence local and test-isolatable.

   Alternative considered: Keep the current top-level dictionary for meshes and encode vaults beside them. That risks name collisions between resource kinds and makes old mesh iteration paths harder to reason about.

2. Add compatibility loading for the existing mesh-only store shape.

   Rationale: Current tests and existing local stores use a top-level mesh-name mapping. Loading that shape as the `meshes` collection avoids breaking existing mesh behavior while allowing new stores to use the multi-kind format.

   Alternative considered: Migrate the store in one step before any command. That is also viable, but compatibility loading keeps migration logic small and allows saving only after successful commands.

3. Reuse mesh validation and output conventions for vaults.

   Rationale: Vaults use the same `metadata.name` naming rule, the same JSON error envelope, and the same no-stderr command behavior. Shared helpers reduce divergence in CLI behavior.

   Alternative considered: Implement fully separate vault parsing and error paths. That would be simpler locally at first but would duplicate contract-sensitive behavior.

4. Normalize vault create input separately from vault update input.

   Rationale: Create applies defaults for `spec.vaultName` and `spec.updatePolicy`; update merges changes into an existing vault and must enforce immutability for `spec.meshRef` and `spec.vaultName` after the merge candidate is built.

   Alternative considered: Treat update as full replacement. That would be less consistent with mesh update behavior and would make omitted optional fields easier to accidentally erase.

5. Compute vault status at output time from the parent mesh.

   Rationale: The vault `Ready` condition reflects parent mesh stability. Computing it during create, update, describe, and list keeps vault status current when mesh lifecycle state changes.

   Alternative considered: Persist vault status once and update it only on vault commands. That could leave stale readiness after mesh updates or describe reconciliation.

6. Check dependent vaults before deleting a mesh.

   Rationale: The mesh deletion contract requires preserving the mesh when any vault has `spec.meshRef` pointing to it. A pre-delete scan over vaults is straightforward and keeps the operation atomic.

   Alternative considered: Delete the mesh and mark vaults pending. That contradicts the checkpoint contract.

## Risks / Trade-offs

- Store shape migration can break existing mesh tests if callers still expect a flat dictionary -> Keep `load_store` tolerant of both flat and multi-kind shapes and update all command paths to go through collection helpers.
- Cross-resource validation can produce stale results if mesh status reconciliation only happens during mesh describe -> Reuse the same mesh upgrade/status projection helper when vault status reads the parent mesh.
- Update merge behavior can accidentally allow immutable changes if defaults are applied before comparison -> Compare effective stored and candidate `spec.meshRef`/`spec.vaultName` after defaults are established.
- Duplicate `(meshRef, vaultName)` checks can accidentally flag the vault being updated -> Exclude the current `metadata.name` from pair-conflict scans during update.
- Conflict messages name dependent vaults but order is not contractual -> Sort names for deterministic output while keeping tests focused on field/type and presence of names.

## Migration Plan

No explicit user-facing migration command is required. On load, treat a legacy top-level mesh mapping as the `meshes` collection with an empty `vaults` collection. On save after any successful command, write the multi-kind store shape.

Rollback is limited to reverting the implementation and tests. Stores saved in the new multi-kind shape would need compatibility handling if older code is used again, so the change should keep the loader small and obvious.
