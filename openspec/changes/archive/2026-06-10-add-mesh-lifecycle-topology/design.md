## Context

The current CLI keeps mesh state in a JSON store and implements `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` in `meshctl.py`. Checkpoint 2 extends the same resource model with partial updates, lifecycle-derived status, topology fields under `spec.network`, and stricter post-merge validation.

The implementation should preserve the small local CLI shape, keep persistence test-isolatable through `MESHCTL_STORE`, and continue returning JSON on stdout for both success and error results.

## Goals / Non-Goals

**Goals:**

- Add `mesh update -f <path>` with all-or-nothing persistence.
- Support partial update merge semantics without re-running create defaults for omitted fields.
- Normalize and validate `spec.network.storage` and `spec.network.replicationFactor`.
- Produce deterministic status, conditions, and lifecycle transition output for create, update, and describe.
- Add focused tests for merge behavior, validation failures, lifecycle transitions, storage output, and replication constraints.

**Non-Goals:**

- Add real asynchronous orchestration, background workers, or time-based reconciliation.
- Add remote storage, multi-user access control, or a service API.
- Change the JSON store format beyond adding the new persisted resource fields.
- Implement autoscaling or rolling migration strategies.

## Decisions

1. Keep command handling in `meshctl.py` with helper functions for merge, validation, and status reconciliation.

   Rationale: The project is still a compact CLI, and the current tests execute the entry point directly. Focused helpers can contain the new complexity without adding module packaging overhead.

   Alternative considered: Split the CLI into a package immediately. That would be cleaner if the tool grows substantially, but it adds movement unrelated to the checkpoint contract.

2. Treat create and update as separate normalization modes.

   Rationale: Create must apply defaults such as `spec.instances`, memory, storage size, and replication factor. Update must merge onto the stored resource and must not apply create-time defaults to omitted fields, so separate modes make the defaulting rules explicit.

   Alternative considered: Use one normalizer with many optional flags. That risks subtle defaulting bugs around omitted update fields.

3. Implement update as load input, validate `metadata.name`, deep-merge into the stored resource, validate the merged result, then persist only after success.

   Rationale: Post-merge validation is required for constraints such as replication factor not exceeding instances. Building the candidate resource first also makes the all-or-nothing persistence rule straightforward.

   Alternative considered: Validate only the incoming patch. That cannot catch constraints that depend on stored values.

4. Model lifecycle transitions synchronously with transient describe reconciliation.

   Rationale: The checkpoint defines update responses that may show transitional state and the next `describe` resolving that state. Persisting a small marker for pending scale/resume completion allows a later `describe` to return the steady state and update the store without background work.

   Alternative considered: Return transient state without persisting transition metadata. That would make the next `describe` unable to know whether it should complete a scale or resume transition.

5. Store canonical storage values even when output hides ephemeral size.

   Rationale: `spec.network.storage.size` remains immutable and must be preserved for later validation, while output rules require omitting `size` only when `ephemeral` is `true`. A resource-to-output projection can hide the field without losing persisted data.

   Alternative considered: Remove size from stored ephemeral resources. That would make immutability checks unreliable.

## Risks / Trade-offs

- Transient lifecycle state in a local JSON store can be awkward to inspect manually -> Keep internal transition markers minimal and exclude them from public output.
- Update merge semantics can blur the difference between omitted fields and explicit `null` -> Tests should cover omitted fields, explicit `null` resume behavior, and nested object merges.
- Output projection for ephemeral storage may diverge from stored canonical data -> Centralize resource serialization for create, update, describe, and list.
- Replication factor defaults depend on the effective instance count -> Compute defaults after create defaults and after update merge, then validate against the merged `spec.instances`.

## Migration Plan

No data migration is required for test-created stores. Existing stored meshes that lack the new status or network fields can be upgraded opportunistically when described or updated by applying the create-era defaults that would have been present for checkpoint 2 resources.

Rollback is limited to reverting the code and tests. Stores containing checkpoint 2 fields remain JSON objects and should not prevent older read paths from loading them, though older code may ignore or expose extra fields differently.
