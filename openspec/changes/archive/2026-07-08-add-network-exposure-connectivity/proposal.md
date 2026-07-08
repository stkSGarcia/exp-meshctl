## Why

Meshes can currently be managed as resources, but their external reachability is not represented as part of the mesh contract. Operators need a consistent way to declare how a mesh is exposed, see the computed endpoint after create and describe operations, opt into a management endpoint at creation time, and retrieve shell connection details without reverse-engineering resource state.

## What Changes

- Add optional `spec.exposure` configuration with explicit `Gateway`, `DirectPort`, and `Balancer` exposure modes.
- Validate exposure mode, mode-specific allowed fields, required type presence, and forbidden sub-fields with sorted JSON errors.
- Preserve Gateway annotations in output.
- Add derived `status.connectionDetails` for exposed meshes on create and describe output.
- Add optional `spec.management.enabled`, defaulting to `false`, with immutable-after-create validation.
- Add derived `status.managementConnectionDetails` when management access is enabled.
- Add `meshctl mesh shell <name>` to return only the computed connection details for an exposed mesh.

## Capabilities

### New Capabilities
- `network-exposure-connectivity`: Covers mesh exposure configuration, computed connection details, management endpoint state, and shell connection retrieval.

### Modified Capabilities
- None.

## Related Work

### Related Changes
- No prior intent nodes were returned by the shallow KG search.

### Related Specs
- `one-shot-operations/add-one-shot-operations`: Defines one-shot command behavior that extends existing mesh, vault, policy, and credential command surfaces. This change complements that work by adding another single-purpose mesh command, `mesh shell`, with a narrow output contract.
- `mesh-resource-management/add-mesh-lifecycle-topology`: Adds mesh update behavior and lifecycle/topology fields. This change builds on the same mesh resource shape by adding exposure, management, and derived status fields that create and describe must surface.
- `mesh-resource-management/add-mesh-migration-strategies`: Extends mesh resource management with additional runtime command behavior. This change follows that extension pattern for connectivity-oriented runtime access while leaving migration behavior unchanged.
- `mesh-resource-management/add-meshctl-mesh-crud`: Establishes `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` through `meshctl.py`. This change builds directly on create and describe output, and adds validation to the same resource-management flow.

## Impact

- Affected CLI surface: `meshctl mesh create`, `meshctl mesh describe`, `meshctl mesh update`, and new `meshctl mesh shell`.
- Affected resource model: mesh `spec.exposure`, `spec.management.enabled`, `status.connectionDetails`, and `status.managementConnectionDetails`.
- Affected validation: exposure type required/invalid errors, forbidden exposure fields, immutable management enablement, no-exposure shell rejection, and sorted JSON error output.
- No external dependencies are expected.
