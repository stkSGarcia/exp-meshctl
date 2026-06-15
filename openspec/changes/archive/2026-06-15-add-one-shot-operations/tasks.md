## 1. Store and CLI Surface

- [x] 1.1 Update `meshctl.py` `main()` and `build_parser()` to add `task`, `snapshot`, and `recovery` subcommands with `create -f`, `list`, `describe`, `update -f`, `delete`, and `run` dispatch, starting from the existing mesh/vault parser functions. [extends `mesh-resource-management/add-mesh-lifecycle-topology`]
- [x] 1.2 Update `meshctl.py` `empty_store()`, `load_store()`, and `save_store()` assumptions so stores include `tasks`, `snapshots`, and `recoveries` while preserving legacy mesh/vault store loading.
- [x] 1.3 Add shared one-shot collection helpers in `meshctl.py` for kind lookup, duplicate checks, not-found errors, sorted list output, describe output, and delete output.

## 2. Validation and Normalization

- [x] 2.1 Add `meshctl.py` normalization for task creation that validates `metadata.name`, `spec.meshRef`, exactly one non-empty `spec.inline` or `spec.bundleRef`, and initializes `status.state = "Initializing"`.
- [x] 2.2 Add `meshctl.py` normalization for snapshot creation that validates `metadata.name`, `spec.meshRef`, optional storage fields, optional scope, CPU/memory quantity formats, and default memory `{"limit": "1Gi", "request": "1Gi"}`.
- [x] 2.3 Add `meshctl.py` normalization for recovery creation that validates `metadata.name`, `spec.meshRef`, `spec.snapshotRef`, snapshot mesh ownership, optional scope, CPU/memory quantity formats, and default memory `{"limit": "1Gi", "request": "1Gi"}`.
- [x] 2.4 Add shared `meshctl.py` one-shot update validation that rejects any changed or newly added `spec` field with `type = "immutable"`, starting from vault immutable-field validation. [extends `vault-resource-management/add-vault-resource-management`]

## 3. Run Semantics and Dependency Protection

- [x] 3.1 Add `meshctl.py` run-state validation for task, snapshot, and recovery so only `Initializing` can run and all other states return the required `status.state` invalid error.
- [x] 3.2 Implement `meshctl.py` task run simulation: transition through `Running`, execute inline lines in order, fail on `FAIL:` with `status.detail = "command <index> failed: <reason>"`, and otherwise finish `Succeeded`.
- [x] 3.3 Implement `meshctl.py` snapshot run simulation: transition through `Running`, return `Unknown` with non-empty detail when the referenced mesh has `status.stable = false`, otherwise finish `Succeeded` with a stable non-empty `status.storageRef`.
- [x] 3.4 Implement `meshctl.py` recovery run simulation: transition through `Running`, return `Unknown` with non-empty detail when the referenced mesh has `status.stable = false`, otherwise finish `Succeeded`.
- [x] 3.5 Update `meshctl.py` snapshot deletion to reject deletes when recoveries reference the snapshot, using `metadata.name` conflict errors that name dependent recoveries. [extends `mesh-resource-management/add-vault-resource-management`]

## 4. Public Output

- [x] 4.1 Add `meshctl.py` public projection helpers for task, snapshot, and recovery that include `status.state`, include `status.detail` only for `Failed` or `Unknown`, and include `status.storageRef` only for succeeded snapshots.
- [x] 4.2 Ensure `meshctl.py` list output for each one-shot kind prints a JSON array sorted by resource name ascending.

## 5. Tests

- [x] 5.1 Add `tests/test_meshctl_cli.py` coverage for task create/list/describe/update/delete/run success, source exclusivity errors, invalid mesh references, inline `FAIL:` behavior, and invalid rerun state.
- [x] 5.2 Add `tests/test_meshctl_cli.py` coverage for snapshot create defaults, scope behavior, quantity validation, successful run storageRef, unstable mesh `Unknown`, immutable spec updates, dependency-protected delete, and sorted list output.
- [x] 5.3 Add `tests/test_meshctl_cli.py` coverage for recovery create validation, snapshot mesh mismatch errors, default memory, scope behavior, successful run, unstable mesh `Unknown`, immutable spec updates, and sorted list output.
- [x] 5.4 Update `tests/test_meshctl_cli.py` legacy store compatibility assertions so stores missing one-shot collections still load and save with empty one-shot collections.
- [x] 5.5 Run `python -m pytest` or the repository test command and fix regressions.
