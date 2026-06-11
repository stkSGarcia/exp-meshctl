## Why

The mesh CLI already supports basic create, list, describe, and delete flows, but checkpoint 2 expands the resource contract into update semantics, topology validation, and lifecycle-aware status. Capturing those rules now gives implementation and tests a single contract for partial updates, transient scaling state, storage behavior, replication factor limits, and condition output.

## What Changes

- Add `mesh update -f <path>` to apply partial YAML updates to an existing stored mesh selected by `metadata.name`.
- Define merge behavior where provided leaf fields replace stored values, omitted fields are preserved, nested objects merge field-by-field, and create-time defaults are not re-applied to omitted update fields.
- Add condition output under `status.conditions`, including default `Healthy` and `PrechecksPassed` conditions, sorted unique condition types, and clearing semantics.
- Add lifecycle transitions for scaling up, scaling down, stopping, and resuming meshes, including transient `Scaling`, persistent `GracefulShutdown`, `desiredInstancesOnResume`, and instance readiness counters.
- Add `spec.network.storage` with defaulted immutable `size`, mutable `ephemeral` and `className`, quantity validation, and output rules that hide `size` when storage is ephemeral.
- Add `spec.network.replicationFactor` with computed defaulting and validation against `spec.instances`.
- Expand status output for create, update, and describe with `state`, `stable`, `instances`, and `desiredInstancesOnResume` when stopped.
- Add `immutable` validation errors and post-merge `invalid` errors while preserving all-or-nothing persistence on validation failure.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mesh-resource-management`: Extend the existing mesh CLI resource model with update operations, partial merge behavior, topology fields, lifecycle status transitions, condition handling, and additional validation/error requirements.

## Impact

- Affected code: `meshctl.py` and any supporting helpers for CLI parsing, validation, defaulting, merge logic, status transition calculation, persistence, and JSON output.
- Affected interface: `uv run --project /app meshctl.py mesh update -f <path>` plus updated output for `mesh create`, `mesh describe`, and existing operations that expose resource status.
- Affected tests: CLI tests should cover successful updates, all-or-nothing validation failures, lifecycle transitions, storage immutability/output, replication factor validation/defaults, and condition ordering/uniqueness.
- Dependencies: no new external dependency is expected beyond the existing YAML parsing support.
