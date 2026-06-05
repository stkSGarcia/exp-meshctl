## Why

The mesh resource currently has no mechanism for configuring external network access, computing connection details, or managing a dedicated administrative endpoint. Operators need a structured way to expose meshes via Gateway, DirectPort, or Balancer modes—and a `mesh shell` command to retrieve connectivity details for a live mesh.

### Related Changes

**`implement-meshctl`** — A CLI tool for managing mesh resources from YAML spec files with create/list/describe/delete operations, strict validation, and structured JSON output.

**`security-model`** — Adds the complete `spec.access` contract (authentication digest settings, role-based permissions, certificate-based encryption) so operators can configure secure mesh deployments.

### Related Specs

No existing specs were found covering exposure or connectivity.

This change builds directly on the mesh management foundation from `implement-meshctl` by adding the `spec.exposure` and `spec.management` sections to the mesh resource contract, and complements the `security-model` change by defining how a running mesh is accessed from outside the cluster.

## What Changes

- Add `spec.exposure` to the mesh resource spec (optional; omitting it means no external access).
- Add `spec.exposure.type` validation: accepted values are `"Gateway"`, `"DirectPort"`, and `"Balancer"`, each with their own allowed sub-fields.
- Add computed `status.connectionDetails` to `create` and `describe` output when exposure is configured.
- Add `spec.management.enabled` (boolean, default `false`, **immutable after create**).
- Add `status.managementConnectionDetails` to output when management is enabled.
- Add `meshctl mesh shell <name>` command that returns `connectionDetails` for a named mesh.
- **BREAKING**: Forbidden sub-fields for each exposure type produce validation errors.

## Capabilities

### New Capabilities
- `mesh-exposure`: Exposure type validation, allowed sub-field enforcement, and connection detail computation for Gateway, DirectPort, and Balancer modes.
- `mesh-shell`: The `meshctl mesh shell <name>` command that outputs connection details for a mesh with exposure configured.

### Modified Capabilities
- `mesh-management`: Add `spec.exposure`, `spec.management.enabled`, `status.connectionDetails`, and `status.managementConnectionDetails` to the mesh resource contract; add `immutable` error type for management field mutation.

## Impact

- `meshctl.py` — new routing for `mesh shell` subcommand; updates to create/describe output builders.
- Mesh resource schema — new fields `spec.exposure`, `spec.management`, `status.connectionDetails`, `status.managementConnectionDetails`.
- Error handling — new `immutable` error type already introduced by `security-model`; forbidden-field path construction for exposure sub-fields.
