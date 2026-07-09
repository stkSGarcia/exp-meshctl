## Why

Mesh resources currently expose only a minimal access default, leaving authentication details, permission roles, and encryption certificate selection underspecified. Defining the full `spec.access` contract now gives create and describe output a stable security model and makes validation errors predictable for callers.

## What Changes

- Expand mesh `spec.access.authentication` to include enabled-state rules, digest algorithm defaults, allowed digest algorithms, and credential reference restrictions.
- Add mesh `spec.access.permissions` with an enable switch, required role definitions when enabled, role shape validation, and duplicate role-name detection.
- Add mesh `spec.access.encryption` with certificate source selection, conditional certificate reference requirements, client mode validation, and source/client-mode compatibility rules.
- Extend mesh defaulting so omitted `spec.access` produces the complete default access section.
- Extend successful `mesh create` and `mesh describe` output to include applicable `spec.access` defaults while omitting optional unset fields.
- Require access validation errors to use the established JSON error format and sort errors by `field`, then `type`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mesh-resource-management`: Define the full mesh `spec.access` security model, defaulting, validation, and output contract.

## Impact

- `meshctl.py` mesh create, describe, update merge/defaulting, validation, and JSON rendering paths.
- Mesh resource tests covering access defaults, authentication validation, permission role validation, encryption validation, and error ordering.
- No new runtime dependencies are expected.
