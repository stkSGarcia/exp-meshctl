## Why

The initial `mesh-management` capability covers CRUD operations but lacks a way to mutate existing meshes, and the resource model is missing topology fields (`storage`, `replicationFactor`) and the operational status model (conditions, instance lifecycle, stable/stopped state). Adding `mesh update` with a proper lifecycle state machine enables the tool to reflect real cluster operations.

## What Changes

- Add `mesh update -f <path>` subcommand that applies partial updates using field-level merge semantics
- Introduce `spec.network.storage` (size, ephemeral, className) and `spec.network.replicationFactor` with defaults, validation, and immutability rules
- Add `status.conditions` array (Healthy, PrechecksPassed, Scaling, GracefulShutdown) with sort and uniqueness guarantees
- Add `status.instances` (ready/starting/stopped), `status.stable`, and `status.desiredInstancesOnResume`
- Implement instance lifecycle state machine: scale up, scale down, stop (to 0), resume (from 0)
- Add `immutable` error type for fields that cannot change after creation; tighten post-merge constraint validation with descriptive `invalid` messages

## Capabilities

### New Capabilities

### Modified Capabilities
- `mesh-management`: Extend with `mesh update`, network topology fields, conditions, instance lifecycle state transitions, enriched status model, and new error types (`immutable`, post-merge `invalid`)

## Impact

- `meshctl.py`: add `cmd_update`, update `validate_and_build` to handle network fields and conditions, update status construction, add merge logic and immutability checks
- `openspec/specs/mesh-management/spec.md`: delta with all new requirements
- No new dependencies; persistence store format will gain new status and spec fields
