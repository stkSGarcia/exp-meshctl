## 1. Store and CLI Surface

- [x] 1.1 Extend `meshctl.py` store loading/saving so `empty_store()` and `load_store()` support `tasks`, `snapshots`, and `recoveries` while preserving existing mesh/vault stores. [extends vault-resource-management/add-vault-resource-management]
- [x] 1.2 Add `task`, `snapshot`, and `recovery` subcommands in `meshctl.py` with create, list, describe, update, delete, and run operations. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.3 Add shared one-shot CRUD helpers in `meshctl.py` for sorted list output, full describe output, common not-found errors, duplicate detection, and delete success messages. [extends mesh-resource-management/add-meshctl-mesh-crud]

## 2. Resource Validation and Normalization

- [x] 2.1 Implement task create normalization in `meshctl.py` for `metadata.name`, `spec.meshRef`, and exactly one non-empty `spec.inline` or `spec.bundleRef`.
- [x] 2.2 Implement snapshot create normalization in `meshctl.py` for `metadata.name`, `spec.meshRef`, optional `spec.storage`, optional scoped capture keys, default memory resources, and memory/CPU quantity validation. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.3 Implement recovery create normalization in `meshctl.py` for `metadata.name`, `spec.meshRef`, `spec.snapshotRef`, matching snapshot mesh ownership, optional scoped restore keys, default memory resources, and memory/CPU quantity validation. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.4 Implement task, snapshot, and recovery update validation in `meshctl.py` so any changed, added, or removed `spec` field returns an `immutable` error.
- [x] 2.5 Implement snapshot delete dependency protection in `meshctl.py` so recoveries referencing a snapshot cause a `metadata.name` conflict error naming those recoveries.

## 3. Run Lifecycle

- [x] 3.1 Implement task run behavior in `meshctl.py`: require `Initializing`, transition through `Running`, succeed for non-failing inline or bundle references, fail on `FAIL:` inline lines, and set exact failure detail.
- [x] 3.2 Implement snapshot run behavior in `meshctl.py`: require `Initializing`, check referenced mesh stability at run time, return `Unknown` with detail for unstable meshes, and set stable non-empty `status.storageRef` on success. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.3 Implement recovery run behavior in `meshctl.py`: require `Initializing`, check referenced mesh stability at run time, and return `Unknown` with detail for unstable meshes. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.4 Ensure public status output in `meshctl.py` uses only `Initializing`, `Running`, `Succeeded`, `Failed`, and `Unknown`, with `detail` only for failed/unknown outcomes and `storageRef` only for succeeded snapshots.

## 4. Tests

- [x] 4.1 Add `tests/test_meshctl_cli.py` coverage for task create/list/describe/update/delete/run success, exclusive source validation, inline failure detail, and invalid rerun state.
- [x] 4.2 Add `tests/test_meshctl_cli.py` coverage for snapshot create defaults, scoped capture, quantity validation, run success storageRef, unstable mesh `Unknown`, immutable spec updates, and dependency-protected delete.
- [x] 4.3 Add `tests/test_meshctl_cli.py` coverage for recovery create defaults, snapshot reference validation, mesh mismatch errors, scoped restore, run success, unstable mesh `Unknown`, and immutable spec updates.
- [x] 4.4 Run the project test suite with `uv run pytest` and fix any regressions in existing mesh/vault behavior.
