## Context

Mesh resources already have create, list, describe, delete, update, migration, status, and JSON error handling in `meshctl.py`. The new network connectivity contract adds optional exposure configuration, computed status fields, an immutable management flag, and a `mesh shell` command that reads an existing mesh endpoint.

## Related Work

**`one-shot-operations/add-one-shot-operations`**: Defines command flows that operate against existing meshes and return JSON errors consistently - informs the `mesh shell` command shape because this change adds another existing-mesh operation without creating a persisted child resource.

**`mesh-resource-management/add-meshctl-mesh-crud`**: Defines `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` through `meshctl.py` - informs where exposure data is accepted and shown because connection details are emitted from create and describe output.

**`mesh-resource-management/add-mesh-lifecycle-topology`**: Defines `mesh update -f <path>`, merged-resource validation, and status reconciliation - informs management immutability because `spec.management.enabled` must be compared against the stored mesh during update.

**`vault-resource-management/add-vault-resource-management`**: Establishes adjacent resource-management validation and not-found behavior - informs error formatting because connectivity errors should use the same JSON envelope and sorted field/type ordering.

## Goals / Non-Goals

**Goals:**
- Add `spec.exposure` validation for `Gateway`, `DirectPort`, and `Balancer` modes.
- Preserve accepted exposure fields, including Gateway annotations.
- Compute `status.connectionDetails` and `status.managementConnectionDetails` deterministically for public resource output.
- Enforce `spec.management.enabled` as immutable after creation.
- Add `mesh shell <name>` as a read-only endpoint lookup command.
- Cover the behavior in `tests/test_meshctl_cli.py`.

**Non-Goals:**
- Open real network listeners, gateways, balancers, or direct ports.
- Add authentication, authorization, or certificate behavior beyond existing access specs.
- Change mesh list summaries or migration status semantics.
- Persist generated endpoint status as a separate source of truth.

## Decisions

### Normalize connectivity fields with the mesh spec

`spec.exposure` and `spec.management` should be normalized by the same create/update path that handles `spec.access`, `spec.network`, and `spec.migration`. This keeps manifest validation in one place and lets create and update share the same accumulated error behavior. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

Alternative considered: handle exposure only while printing public resources. That would make invalid persisted state possible and would miss create/update validation scenarios.

### Validate exposure by mode-specific allowlists

The exposure validator should require a non-empty `type` when `spec.exposure` is present, accept only `Gateway`, `DirectPort`, and `Balancer`, and reject fields outside the selected mode using the complete `spec.exposure.<field>` path. Port-like fields should be integers when present, and annotations should remain a string-to-string map.

Alternative considered: silently dropping unknown mode fields. The checkpoint requires explicit forbidden-field errors, and retaining bad input would make endpoint computation ambiguous.

### Derive connection details from public output

Connection details should be produced by a helper that reads the normalized mesh name and exposure mode, then attaches `status.connectionDetails` inside `public_resource`. The helper should remove the field when exposure is omitted so stored legacy meshes and updated meshes cannot retain stale endpoint data. _(see `mesh-resource-management/add-meshctl-mesh-crud`)_

Alternative considered: persist `status.connectionDetails` during create and update. Derived output is safer because host and port are fully determined by the current spec and mesh name.

### Treat management details as derived status with immutable spec input

`spec.management.enabled` should default to `false` during create normalization and should be preserved during update unless explicitly changed. Update validation should compare the stored and candidate values and emit the exact immutable error when they differ. `status.managementConnectionDetails` should be computed from the mesh name only when enabled. _(see `mesh-resource-management/add-mesh-lifecycle-topology`)_

Alternative considered: model management as an exposure subtype. The checkpoint gives it a separate spec path, immutable behavior, and status field, so keeping it separate avoids coupling user access to admin access.

### Add `mesh shell` as a read-only mesh command

The parser and dispatcher should add `mesh shell <name>`. The handler should load the mesh, return the standard not-found shape when absent, compute public resource output, reject missing `status.connectionDetails`, and print that object alone on success. _(see `one-shot-operations/add-one-shot-operations`)_

Alternative considered: make shell print the full mesh. The contract requires only the connection details object, without a resource envelope.

## Risks / Trade-offs

- Default host and port choices could become hidden compatibility assumptions -> Keep defaults as named constants near the exposure modes and cover each mode in tests.
- Computing status during public output can mask stale persisted status -> Explicitly remove derived connectivity status before recomputing public fields.
- Field allowlists can drift as future exposure modes are added -> Centralize allowed fields per mode so updates touch one table.
- Management immutability might interact with partial update merging -> Test both omitted management updates and explicit changed values.

## Migration Plan

Existing stored meshes without `spec.exposure` remain valid and should not show `status.connectionDetails`. Existing stored meshes without `spec.management.enabled` should be upgraded to the default `false` behavior through the normal public/upgrade path. Rollback is limited to removing the new validation, derived status helpers, command routing, and tests because no external systems are provisioned.

## Open Questions

- What exact default host should Gateway use when `spec.exposure.hostname` is omitted?
- What exact default port should DirectPort and Balancer use when their port fields are omitted?
