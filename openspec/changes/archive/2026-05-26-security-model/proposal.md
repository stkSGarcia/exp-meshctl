## Why

The mesh resource has a stub for `spec.access.authentication.enabled` but lacks the full security model. This change adds the complete `spec.access` contract — authentication digest settings, role-based permissions, and certificate-based encryption — so operators can configure secure mesh deployments.

## What Changes

- Expand `spec.access.authentication` to include `digestAlgorithm` (SHA-256/384/512) and `credentialRef`, with conditional validation rules when authentication is disabled.
- Add `spec.access.permissions` with role-based access control: enabled flag, role list (name + permissions array), uniqueness and presence validation.
- Add `spec.access.encryption` with `source` (None/Secret/Service), `certRef`, `certServiceRef`, and `clientMode`, all with source-conditional required/forbidden rules.
- Define full defaults for `spec.access` when the section is omitted entirely.
- Enforce sorted-by-field error output for all `spec.access` validation failures.

## Capabilities

### New Capabilities
<!-- None — this change extends an existing capability -->

### Modified Capabilities
- `mesh-management`: Extends `spec.access` requirements with full authentication, permissions, and encryption validation rules, defaults, and output contracts.

## Impact

- `meshctl.py` — validation and defaulting logic for `spec.access`
- `openspec/specs/mesh-management/spec.md` — new and updated requirements for the `spec.access` section
- `store.json` / `vault_store.json` — no schema changes required; fields stored as provided
