## Context

`meshctl` manages mesh resources stored in a JSON file. Currently meshes have no concept of external network access — `spec.exposure` does not exist, `status.connectionDetails` is never populated, and there is no `mesh shell` command. The implementation is a single Python file (`meshctl.py`) with a flat function-based structure; all persistence is handled by reading and writing a JSON store.

## Goals / Non-Goals

**Goals:**
- Add `spec.exposure` with three modes (`Gateway`, `DirectPort`, `Balancer`) including per-mode field allow/forbid rules
- Compute and emit `status.connectionDetails` on `create` and `describe` when exposure is configured
- Add `spec.management.enabled` (immutable after create) and `status.managementConnectionDetails` when enabled
- Add `mesh shell <name>` subcommand returning raw `connectionDetails`

**Non-Goals:**
- Actual network provisioning or Kubernetes resource creation
- Changes to the underlying store format beyond adding new fields
- Modifying any existing commands other than extending create/describe output

## Decisions

### Exposure modes as a discriminated union on `spec.exposure.type`
Three distinct modes require different allowed fields and different `connectionDetails` computation logic. A `type` discriminant keeps validation simple: check type first, then validate/forbid mode-specific fields. Alternative (separate top-level fields per mode) would complicate schema and output serialization without benefit.

### `connectionDetails` computed at read time, not stored
`connectionDetails` derives entirely from `spec.exposure` fields that are already stored. Computing on output (create/describe) avoids stale computed values and keeps the store minimal. Risk: slight extra CPU on every read — acceptable given the small dataset.

### `spec.management.enabled` immutability checked in update path
The immutability check mirrors the existing pattern for `spec.network.storage.size`. On update, compare the incoming (merged) value against the stored value; if different, emit `{"field":"spec.management.enabled","type":"immutable","message":"field 'spec.management.enabled' is immutable after creation"}`.

### `mesh shell` returns raw object, not resource envelope
The spec explicitly requires outputting only the `connectionDetails` object. This is consistent with how the tool already has command-specific output shapes (e.g., `delete` returns `{message, metadata}` rather than a resource envelope).

### Default port values
Gateway mode uses port 443 (HTTPS standard). DirectPort and Balancer use the same default when `port` is not specified (implementation detail — a single constant). The spec says "has a default" without specifying the value; 443 is the natural choice given `protocol` is always `"https"`.

## Risks / Trade-offs

- **Forbidden field enumeration per mode** → Must explicitly list every allowed field per mode at the validation layer; adding a field to one mode risks forgetting to update the forbidden-field check for other modes. Mitigation: define allowed-field sets as constants per mode and derive the forbidden check from the complement.
- **`managementConnectionDetails` always uses fixed port 9990** → Port is hardcoded in the spec; no validation needed but also no flexibility. Mitigation: treat as a constant, no config needed.
- **`mesh shell` reuses `connectionDetails` logic** → If the computation changes, both code paths must be updated. Mitigation: extract `compute_connection_details(mesh)` as a shared helper.
