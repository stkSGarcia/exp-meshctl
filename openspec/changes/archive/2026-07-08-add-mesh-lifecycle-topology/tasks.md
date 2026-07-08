## 1. CLI and Input Handling

- [x] 1.1 Add `mesh update -f <path>` argument parsing and route it to an update handler.
- [x] 1.2 Reuse YAML loading for update inputs and reject unreadable, unparsable, multi-document, or non-mapping inputs with the standard JSON error shape.
- [x] 1.3 Validate `metadata.name` for update and return `metadata.name` `not_found` when the selected mesh is absent.

## 2. Resource Model and Defaults

- [x] 2.1 Extend create normalization to allow `spec.instances` equal to `0` while still rejecting negative, boolean, and non-integer values.
- [x] 2.2 Add default `status.conditions`, `status.stable`, and `status.instances` output for newly created meshes.
- [x] 2.3 Add `spec.network.storage` normalization with create defaults for `size` and `ephemeral`, optional `className`, memory quantity validation, and canonical size storage.
- [x] 2.4 Add `spec.network.replicationFactor` normalization with computed create-time default and positive integer validation.
- [x] 2.5 Add public output projection so ephemeral storage hides `spec.network.storage.size` while canonical persisted data keeps it.

## 3. Update Merge and Validation

- [x] 3.1 Implement nested update merge semantics where provided leaves replace stored leaves and omitted fields keep stored values.
- [x] 3.2 Ensure update normalization does not reapply create-time defaults for omitted fields.
- [x] 3.3 Validate the full merged candidate resource before saving and keep the stored mesh unchanged on any validation error.
- [x] 3.4 Reject updates that change `spec.network.storage.size` with an `immutable` error and the required message text.
- [x] 3.5 Validate post-merge constraints, including replication factor limits, with `invalid` errors whose messages name the actual value and limit.

## 4. Lifecycle and Status Reconciliation

- [x] 4.1 Implement status state derivation for running and stopped meshes.
- [x] 4.2 Implement scale-up update responses with transient `Scaling`, previous ready count, and starting count.
- [x] 4.3 Implement scale-down update responses with transient `Scaling`.
- [x] 4.4 Implement describe-time completion for scale and resume transitions, including clearing transient conditions and updating persisted steady state.
- [x] 4.5 Implement stop transitions with `GracefulShutdown`, `desiredInstancesOnResume`, stopped counters, and stable stopped state.
- [x] 4.6 Implement resume transitions using explicit positive `spec.instances` or stored `desiredInstancesOnResume` when `spec.instances` is omitted or null.
- [x] 4.7 Ensure conditions are sorted by type, unique by type, and removed when cleared.

## 5. Tests and Verification

- [x] 5.1 Add CLI tests for successful partial update merge behavior and preservation of omitted defaults.
- [x] 5.2 Add CLI tests for update validation failures, missing update target, immutable storage size, and all-or-nothing persistence.
- [x] 5.3 Add CLI tests for storage defaults, ephemeral output projection, storage class updates, and canonical size preservation.
- [x] 5.4 Add CLI tests for replication factor defaults, invalid values, and post-merge limit failures.
- [x] 5.5 Add CLI tests for create status, condition ordering, scale up/down, stop, resume, and describe-time transition completion.
- [x] 5.6 Run the full test suite and `openspec validate add-mesh-lifecycle-topology`.
