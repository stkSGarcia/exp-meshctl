## 1. Command Surface and Storage

- [x] 1.1 Add `task`, `snapshot`, and `recovery` subcommands with create/list/describe/update/delete/run operations.
- [x] 1.2 Extend store initialization and loading to include `tasks`, `snapshots`, and `recoveries` while preserving existing mesh/vault stores.
- [x] 1.3 Add shared helpers for one-shot create, list, describe, update, delete, and run command handling.

## 2. Resource Normalization and Validation

- [x] 2.1 Implement common operation metadata validation, duplicate handling, not-found handling, and `Initializing` status creation.
- [x] 2.2 Implement task spec validation for `spec.meshRef` and exactly one non-empty `spec.inline` or `spec.bundleRef`.
- [x] 2.3 Implement snapshot spec validation for `spec.meshRef`, storage fields, scope preservation, and memory/CPU resources with memory defaults.
- [x] 2.4 Implement recovery spec validation for `spec.meshRef`, `spec.snapshotRef`, matching snapshot mesh ownership, scope preservation, and memory/CPU resources with memory defaults.
- [x] 2.5 Implement whole-spec immutability checks for task, snapshot, and recovery updates.

## 3. Lifecycle and Dependency Behavior

- [x] 3.1 Implement task run transitions, including inline `FAIL:` detection and failed detail formatting.
- [x] 3.2 Implement snapshot run transitions for stable and unstable parent meshes, including successful `status.storageRef`.
- [x] 3.3 Implement recovery run transitions for stable and unstable parent meshes.
- [x] 3.4 Implement snapshot delete dependency protection for recoveries that reference a snapshot.
- [x] 3.5 Ensure status output includes `detail` only for `Failed` or `Unknown` and snapshot `storageRef` only for succeeded snapshots.

## 4. Tests

- [x] 4.1 Add CLI tests for task create/list/describe/update/delete/run success paths and task validation failures.
- [x] 4.2 Add CLI tests for snapshot create/list/describe/update/delete/run success paths, unstable mesh unknown state, storage references, resource validation, and dependency conflicts.
- [x] 4.3 Add CLI tests for recovery create/list/describe/update/delete/run success paths, unstable mesh unknown state, missing/mismatched snapshot references, and resource validation.
- [x] 4.4 Add regression tests that existing mesh and vault commands still work with the extended store shape.
