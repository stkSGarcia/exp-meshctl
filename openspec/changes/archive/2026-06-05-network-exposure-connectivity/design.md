## Context

`meshctl.py` is a Python CLI that manages mesh resources stored in a JSON flat-file store. The current implementation handles create/list/describe/delete for mesh resources and a growing list of dependent resource types (vaults, snapshots, recoveries, tasks). The mesh resource spec has no concept of external network exposure — there is no way to configure how a mesh is reached from outside the cluster, nor is there a management endpoint.

This design covers adding `spec.exposure`, `spec.management`, the `status.connectionDetails` and `status.managementConnectionDetails` computed fields, and the `mesh shell` sub-command.

## Related Work

**`implement-meshctl`**: Original CLI for mesh CRUD with YAML validation and JSON output — informs the validation pipeline and output builder patterns because all new fields follow the same field-path error shape _(see `implement-meshctl`)_.

**`security-model`**: Adds `spec.access` and introduces the `immutable` error type for `update` operations — informs the `spec.management.enabled` immutability design because the same guard-on-update pattern is already present for `spec.access` fields _(see `security-model`)_.

## Goals / Non-Goals

**Goals:**
- Add `spec.exposure` with type-dispatch validation (Gateway / DirectPort / Balancer).
- Add `spec.management.enabled` with immutability enforcement on update.
- Compute `status.connectionDetails` and `status.managementConnectionDetails` at create/describe time.
- Add `meshctl mesh shell <name>` that returns raw `connectionDetails`.

**Non-Goals:**
- No actual network provisioning — all exposure data is stored and echoed back.
- No validation of hostname DNS format or port range beyond integer type.
- No interaction with other resource types (vaults, snapshots, etc.).

## Decisions

### Decision 1: Type-dispatch for exposure field validation

Each exposure type has a distinct allowed-field set. A dispatch table (dict keyed by type string) maps each type to its set of permitted sub-fields. Unknown sub-fields for the active type emit `forbidden` errors using full dot-paths.

**Alternative considered**: A flat validator that checks each field individually regardless of type. Rejected because it would require per-field type-awareness spread across the validator rather than a single dispatch table.

### Decision 2: connectionDetails computed at persist/read time, not stored

`status.connectionDetails` is derived entirely from `spec.exposure` fields and `metadata.name`. It is recomputed each time `create` or `describe` outputs the resource, rather than serialised into the store.

**Alternative considered**: Store `connectionDetails` in the persisted JSON. Rejected — it introduces redundancy and the risk of stale data if spec fields were ever mutable.

### Decision 3: spec.management.enabled immutability via update guard

The existing `update` path in `meshctl.py` already checks for immutable fields (introduced by the `security-model` change). `spec.management.enabled` is added to that guard list with the prescribed error message.

### Decision 4: mesh shell as a new sub-command in the mesh dispatcher

`mesh shell` is added as a new branch in the existing `mesh` sub-command router alongside `create`, `list`, `describe`, `delete`, and `update`. It reads from the store, validates exposure presence, and prints only the `connectionDetails` dict.

## Risks / Trade-offs

- **Port defaults are implementation-defined** — The checkpoint spec says `port` has a default but does not specify the value. The implementation must choose a sensible default (e.g., `8080`). → Mitigation: pick a reasonable default and document it in code comments.
- **Gateway hostname default is unspecified** — When `hostname` is absent in Gateway mode, the host in `connectionDetails` falls back to a default. → Mitigation: use `"<name>"` (the mesh name) as the hostname default for consistency with DirectPort mode.
- **Forbidden-field error paths must use full dot-notation** — If a helper constructs field paths incorrectly, error messages will be wrong. → Mitigation: build field paths with a utility that prepends `spec.exposure.` to sub-field names.
