## 1. Store and Command Surface

- [x] 1.1 In `meshctl.py`, extend `empty_store()` and `load_store()` from the mesh/vault resource map pattern to preserve `tasks`, `snapshots`, and `recoveries` collections. [extends vault-resource-management/add-vault-resource-management]
- [x] 1.2 In `meshctl.py`, add `task`, `snapshot`, and `recovery` subparsers with `create -f`, `list`, `describe <name>`, `update -f`, `delete <name>`, and `run <name>` operations. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 1.3 In `meshctl.py`, route the new parser operations from `main()` to one-shot handlers without changing existing `mesh` or `vault` command behavior. [extends mesh-resource-management/add-mesh-lifecycle-topology]

## 2. Resource Normalization and Validation

- [x] 2.1 In `meshctl.py`, add shared one-shot helpers for name validation, collection lookup, duplicate detection, not-found errors, sorted list output, full describe output, and JSON delete confirmations. [extends vault-resource-management/add-vault-resource-management]
- [x] 2.2 In `meshctl.py`, implement task normalization and validation for `spec.meshRef`, exclusive non-empty `spec.inline`/`spec.bundleRef`, duplicate names, and `status.state = "Initializing"`. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 2.3 In `meshctl.py`, implement snapshot normalization and validation for `spec.meshRef`, optional `spec.storage`, optional `spec.scope`, `spec.resources.memory` defaults, and memory/CPU quantity checks using existing resource quantity helpers. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 2.4 In `meshctl.py`, implement recovery normalization and validation for `spec.meshRef`, `spec.snapshotRef`, recovery/snapshot mesh matching, optional `spec.scope`, resource defaults, and duplicate names. [extends mesh-resource-management/add-vault-resource-management]

## 3. Update, Run, and Dependency Rules

- [x] 3.1 In `meshctl.py`, implement one-shot `update -f` so any changed, added, or removed `spec` field is rejected with `type = "immutable"` while allowed non-spec changes are persisted. [extends vault-resource-management/add-vault-resource-management]
- [x] 3.2 In `meshctl.py`, implement task `run` with the `Initializing` guard, synchronous `Running` transition, inline line processing, `FAIL:` failure detail, and `Succeeded`/`Failed` terminal states. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.3 In `meshctl.py`, implement snapshot `run` with the `Initializing` guard, stable-mesh success including non-empty `status.storageRef`, unstable-mesh `Unknown` including non-empty `status.detail`, and allowed terminal phases. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.4 In `meshctl.py`, implement recovery `run` with the `Initializing` guard, stable-mesh success, unstable-mesh `Unknown`, and allowed terminal phases. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 3.5 In `meshctl.py`, implement `snapshot delete` dependency protection by scanning `recoveries` and returning a `metadata.name` conflict naming dependent recoveries. [extends mesh-resource-management/add-vault-resource-management]
- [x] 3.6 In `meshctl.py`, ensure printed one-shot resources only include `status.detail` for `Failed` or `Unknown`, and only include `status.storageRef` for succeeded snapshots. [extends mesh-resource-management/add-mesh-lifecycle-topology]

## 4. Tests

- [x] 4.1 In `tests/test_meshctl_cli.py`, add coverage for task create/list/describe/update/delete/run success paths, inline failure handling, invalid mesh references, and inline/bundle exclusivity errors. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 4.2 In `tests/test_meshctl_cli.py`, add coverage for snapshot create defaults, scoped snapshots, resource quantity validation, run success/unknown outcomes, storageRef output, immutable spec updates, and dependency-protected deletes. [extends mesh-resource-management/add-vault-resource-management]
- [x] 4.3 In `tests/test_meshctl_cli.py`, add coverage for recovery create validation, snapshotRef not found, mesh mismatch error message, run success/unknown outcomes, immutable spec updates, and sorted list output. [extends vault-resource-management/add-vault-resource-management]
- [x] 4.4 Run the existing test suite and update expectations only for behavior intentionally introduced by `one-shot-operations`.
