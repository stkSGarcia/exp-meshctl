## Context

`meshctl.py` currently manages mesh resources from a compact argparse CLI backed by the JSON store selected by `MESHCTL_STORE`. Mesh create, update, describe, migrate, list, and delete already share YAML loading, deep merge, validation, status reconciliation, public output projection, warnings, and deterministic JSON error rendering.

This change adds connectivity metadata to the same mesh resource model. Exposure and management settings are declarative inputs under `spec`, while connection details are computed status fields returned to callers. The new `mesh shell` command is a read-only lookup that exposes the already-computed public connection details without returning the full mesh envelope.

## Goals / Non-Goals

**Goals:**

- Support optional `spec.exposure` with mode-specific validation for `Gateway`, `DirectPort`, and `Balancer`.
- Compute stable `status.connectionDetails` for exposed meshes on create and describe output.
- Support `spec.management.enabled` with a default of `false`, immutability after create, and computed management connection details when enabled.
- Add `mesh shell <name>` with JSON output for connection details and structured errors for missing or unexposed meshes.
- Keep validation atomic on update and reuse existing error ordering and output conventions.

**Non-Goals:**

- Open a real interactive shell or network connection.
- Provision gateways, load balancers, ports, DNS records, or certificates.
- Validate hostname reachability or port availability outside the YAML resource contract.
- Change vault, task, snapshot, or recovery resource behavior.

## Decisions

1. Treat exposure and management as part of `mesh-resource-management`.

   Rationale: Both features are nested mesh fields and affect mesh validation, status, output projection, update immutability, and a mesh subcommand. Keeping them in the existing capability avoids a separate lifecycle or storage model.

   Alternative considered: Create a separate connectivity capability. That would split behavior that is inseparable from mesh resource status and command routing.

2. Store canonical `spec.exposure` and `spec.management` values, but compute connection status during resource normalization/projection.

   Rationale: The user-provided spec should remain the persisted source of intent, while `status.connectionDetails` and `status.managementConnectionDetails` are derived from the mesh name and effective spec. Recomputing during create, describe, update, migrate, and shell keeps older stored resources consistent after upgrade.

   Alternative considered: Persist computed status only once during create. That would make future default changes or stored-resource upgrades harder to reason about.

3. Validate exposure mode fields through a mode-to-allowed-fields table.

   Rationale: `Gateway`, `DirectPort`, and `Balancer` each allow a small different field set. A table makes forbidden-field checks deterministic and makes full dot-path error reporting straightforward.

   Alternative considered: Inline per-mode conditionals. That is simple initially but easier to drift as field rules grow.

4. Keep `mesh shell` read-only and return only `status.connectionDetails`.

   Rationale: The checkpoint defines `mesh shell` as a connectivity lookup, not an actual terminal session. Returning the connection details object directly makes scripting easy and avoids duplicating the full resource envelope.

   Alternative considered: Return the full mesh resource or include management details. That would be noisier and would not match the command contract.

## Risks / Trade-offs

- Exposure defaults could be mistaken for real infrastructure provisioning. Mitigation: keep outputs declarative and avoid claiming external resources are created.
- Update merge semantics can leave fields that become forbidden after switching exposure modes. Mitigation: validate the merged candidate atomically and reject all mode-incompatible fields with full dot paths.
- Management immutability is narrower than full `spec.management` immutability. Mitigation: enforce only `spec.management.enabled` exactly as specified, preserving room for future management fields.
- `mesh shell` depends on public projection matching create/describe output. Mitigation: centralize connection detail computation and have shell read the same derived field.
