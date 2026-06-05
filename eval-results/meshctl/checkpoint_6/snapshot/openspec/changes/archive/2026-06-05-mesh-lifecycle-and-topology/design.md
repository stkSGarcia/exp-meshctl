## Context

`meshctl.py` is a single-file Python CLI backed by a JSON file store. The previous change delivered CRUD with validation and defaults. This change adds a `mesh update` command, network topology fields (`spec.network.storage`, `spec.network.replicationFactor`), a conditions array, and an instance lifecycle state machine (scale up/down, stop, resume). The state machine requires distinguishing transient response state (Scaling condition) from durable state (GracefulShutdown, desiredInstancesOnResume), and the store must carry both spec and enriched status across commands.

## Goals / Non-Goals

**Goals:**
- Add `mesh update` with field-level merge semantics and immutability enforcement
- Add `spec.network.storage` and `spec.network.replicationFactor` with validation and defaults
- Add `status.conditions`, `status.instances`, `status.stable`, and `status.desiredInstancesOnResume`
- Implement stop/resume/scale lifecycle transitions driven by `spec.instances` changes

**Non-Goals:**
- Real cluster orchestration — all state is simulated in the local JSON store
- Persisting the `Scaling` condition beyond the update response
- Adding new subcommands beyond `update`

## Decisions

### D1: Lifecycle state encoded in stored status, not derived
The store persists the full status object (including conditions and instance counts). On each `describe`, the status is returned as-is except for resolving the transient `Scaling` condition — which is cleared in the response without re-persisting.

**Alternative considered**: Re-derive status from spec fields on every read. Rejected because stop/resume state (`GracefulShutdown`, `desiredInstancesOnResume`) is not derivable from spec alone.

### D2: Transient Scaling condition stripped at describe time
The `Scaling` condition is written to the store during an update response but removed before returning a `describe` response (and before re-persisting if a subsequent update occurs). This keeps describe idempotent while letting the update response communicate the in-flight transition.

**Alternative considered**: Write a separate "pending" flag. Rejected as more complex than a condition strip.

### D3: Merge implemented as a recursive dict merge in Python
`apply_merge(stored, update)` walks the update dict and replaces stored leaf values. `None` values in the update YAML are treated as absent (field omitted). Post-merge validation runs once on the merged spec, same as create-time validation but with an immutability check layer added before validation runs.

### D4: Immutability checked before validation
Before running the standard validator on the merged doc, compare the merged value of each immutable field against the stored value. Emit `immutable` errors immediately; do not run the rest of validation if immutables are violated. This avoids spurious secondary errors.

**Alternative considered**: Run validation first, check immutability after. Rejected because it can produce misleading errors (e.g., "invalid size" when the real problem is "size is immutable").

### D5: replicationFactor default computed as min(instances, 3)
`min(spec.instances, 3)` gives a sensible default (mirrors common 3-replica topologies) without requiring a separate lookup table.

### D6: Storage output controlled at serialization time
Rather than storing a filtered spec, store the full storage object and apply the ephemeral output filter at `print_json` time (or in a dedicated `format_storage` helper). This avoids losing `size` when `ephemeral` flips between updates.

## Risks / Trade-offs

- [Risk: Store format changes break existing stores] → The new status fields are additive; existing stores without them will behave as if `conditions = []` and `instances = {"ready":0,"starting":0,"stopped":0}`. No migration needed.
- [Risk: Lifecycle correctness edge cases (stop then update non-instances field)] → Lifecycle detection is done by comparing `spec.instances` before and after merge. Non-instances fields do not trigger lifecycle transitions, which is correct per spec.
- [Risk: Scaling condition left in store across two rapid updates] → The Scaling condition is stripped at the start of any subsequent update's merge target read, so it cannot compound.

## Migration Plan

Single-file change to `meshctl.py`. No schema migration required — the store is additive. Existing meshes will gain conditions and instances fields on their next `describe` call (they will be absent until then, which is acceptable for a dev tool with no production guarantee).

## Open Questions

None — all behavior is fully specified in the delta spec.
