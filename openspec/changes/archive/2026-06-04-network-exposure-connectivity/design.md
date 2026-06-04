## Context

The mesh tool is a Python CLI (`meshctl.py`) that manages mesh resources persisted as JSON files. It currently supports create, list, describe, delete, update, migrate, and lifecycle operations. This change adds:

1. An optional `spec.exposure` block that selects an exposure mode and carries mode-specific fields.
2. A computed `status.connectionDetails` object derived from the exposure configuration.
3. An `spec.management.enabled` flag (immutable after create) with a corresponding `status.managementConnectionDetails`.
4. A new `mesh shell <name>` subcommand that returns only the connection details.

## Related Work

**`spec:mesh-management`**: Core mesh CRUD — informs the input schema extension and output format because `spec.management` and `spec.exposure` are new optional `spec` sub-keys; `status.connectionDetails` and `status.managementConnectionDetails` are new optional `status` sub-keys. _(see `spec:mesh-management`)_

**`spec:mesh-migrate-command`**: The `mesh migrate` command pattern — informs the `mesh shell` subcommand routing and not-found error shape; both commands follow the same `meshctl mesh <subcommand> <name>` dispatch pattern. _(see `spec:mesh-migrate-command`)_

## Goals / Non-Goals

**Goals:**
- Validate `spec.exposure` type and per-mode allowed fields
- Compute `status.connectionDetails` at create and describe time
- Enforce `spec.management.enabled` immutability on update
- Implement `mesh shell` returning only the connection details object

**Non-Goals:**
- Actual network provisioning or gateway configuration
- Changing existing create/list/delete/update behavior beyond output additions
- Supporting additional exposure types beyond Gateway, DirectPort, Balancer

## Decisions

### Exposure validation order
Validate `spec.exposure.type` presence and validity first, then check forbidden fields per mode. This order lets the handler report a clean `required`/`invalid` error before checking field allowlists — consistent with how the existing `migration.strategy` validation works.

### Connection details computation at response time
`status.connectionDetails` is computed when building the JSON response (not stored). This avoids stale computed values in the store if `spec.exposure` fields change on update and keeps the persisted document minimal.

*Alternative considered*: Store computed details. Rejected because they are fully derivable from `spec.exposure` and the mesh name.

### Management immutability check
Apply the immutability check during the update merge phase — after loading stored state but before field-level merge — by comparing the incoming `spec.management.enabled` value against the stored value. This is the same pattern used for other immutable fields.

### mesh shell output envelope
Return only the `connectionDetails` object (no `metadata`/`spec`/`status` wrapper). This matches the checkpoint spec and keeps the command output directly usable as a connection config.

## Risks / Trade-offs

- **Port default values** — the spec says `port` has a default but does not specify the value. → Use a sensible default (e.g., `8080` for DirectPort and Balancer) and document it in implementation; keep it consistent across modes.
- **Gateway host default** — when `hostname` is absent, the default host is implementation-defined. → Use `"<name>-gateway"` as the default, consistent with the `"<name>-external"` pattern for Balancer.
- **Update + exposure** — if `spec.exposure` fields change on update the connection details will change on the next describe. This is expected behavior and requires no special handling.

## Migration Plan

No data migration required. Existing stored meshes without `spec.exposure` or `spec.management` continue to work; their responses simply omit the new status fields.
