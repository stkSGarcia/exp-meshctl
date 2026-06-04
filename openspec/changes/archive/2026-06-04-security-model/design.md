## Context

`meshctl.py` currently reads `spec.access.authentication.enabled` and passes it through to the output with a hardcoded default of `true`. Everything else under `spec.access` is ignored — no validation, no defaults, no output. Checkpoint 4 defines a complete security model across three sub-sections: `authentication`, `permissions`, and `encryption`.

The implementation lives in a single function (`validate_and_build` or similar) in `meshctl.py`. The pattern already established is: read raw value → validate → collect errors → build output dict. We follow the same pattern for all new `spec.access` fields.

## Goals / Non-Goals

**Goals:**
- Implement full `spec.access` validation: authentication digest/credential, permissions roles, encryption source/cert/clientMode
- Apply correct defaults when `spec.access` (or its sub-sections) are absent
- Enforce conditional required/forbidden rules across all three sub-sections
- Output `spec.access` on `create` and `describe` with all applicable defaults
- Sort errors by `field`, then `type`

**Non-Goals:**
- Persistence schema changes — fields are stored as-is, no migration needed
- Actual credential or certificate verification — this is config validation only
- Changes to `vault-management` or any other command

## Decisions

### 1. Process all three sub-sections independently, then merge
Each of `authentication`, `permissions`, and `encryption` is validated in its own block, accumulating errors into the shared list. This keeps the logic readable and mirrors how other `spec.*` sections are handled (resources, migration, network each have their own block).

**Alternative considered:** A single nested validator function. Rejected — the existing style is flat sequential blocks, and introducing a new pattern for one change adds unnecessary abstraction.

### 2. Error sort at the end, not during accumulation
The spec requires errors sorted by `field` then `type`. We sort the entire error list once before returning, which is simpler than maintaining sorted insertion order.

**Alternative considered:** Sort on append. Rejected — O(n) appends are fine at validation scale and sorting once at the end is cleaner.

### 3. Conditional field presence via explicit `in` checks
For `digestAlgorithm` and `credentialRef` forbidden-when-disabled rules, we check `"digestAlgorithm" in raw_auth` (key presence) rather than checking for a non-None value. This correctly rejects explicitly-set-to-null values too, and matches the "must be absent" wording in the spec.

### 4. `clientMode` validation for `source = "None"`
The spec says `clientMode = "Authenticate"` or `"Validate"` with `source = "None"` is invalid, but exact message wording is not part of the contract. We use `type = "invalid"` on `spec.access.encryption.clientMode` for consistency with other invalid-value errors.

## Risks / Trade-offs

- **Existing stored resources lack encryption/permissions fields** → On `describe`, defaults are applied at read time (the function builds the full output dict), so old resources get the correct default output without a migration.
- **Output key order is not contractual** → Python dicts (3.7+) preserve insertion order; we build output sub-dicts in a consistent order for readability but tests must not rely on it.

## Migration Plan

No data migration. Deploy is a single-file change to `meshctl.py`. Rollback by reverting the file. No external dependencies change.
