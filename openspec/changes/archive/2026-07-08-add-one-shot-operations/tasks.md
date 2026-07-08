## 1. Store and Command Surface

- [x] 1.1 Update `meshctl.py` command routing to add `task`, `snapshot`, and `recovery` subcommands with `create -f`, `list`, `describe`, `update -f`, `delete`, and `run` operations. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 Extend `meshctl.py` store loading/saving helpers so existing stores load safely while new `tasks`, `snapshots`, and `recoveries` collections are persisted. [extends vault-resource-management/add-vault-resource-management]
- [x] 1.3 Add shared `meshctl.py` helpers for one-shot collection lookup, duplicate/not-found errors, sorted list output, full-resource describe output, and public status projection. [extends mesh-resource-management/add-meshctl-mesh-crud]

## 2. Create and Update Validation

- [x] 2.1 Implement task normalization and create validation in `meshctl.py`, including required `spec.meshRef`, exactly one non-empty `spec.inline` or `spec.bundleRef`, duplicate names, and initial `Initializing` status.
- [x] 2.2 Implement snapshot normalization and create validation in `meshctl.py`, including required `spec.meshRef`, optional `spec.storage`, optional `spec.scope`, resource defaults, mesh quantity validation, and initial `Initializing` status. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 2.3 Implement recovery normalization and create validation in `meshctl.py`, including required `spec.meshRef`, required `spec.snapshotRef`, snapshot existence, snapshot/mesh ownership checks, optional `spec.scope`, resource defaults, and initial `Initializing` status. [extends vault-resource-management/add-vault-resource-management]
- [x] 2.4 Implement one-shot `update -f` behavior in `meshctl.py` that rejects changed or newly added `spec` fields with `type = "immutable"` and leaves stored resources unchanged on validation errors. [extends mesh-resource-management/add-mesh-lifecycle-topology]

## 3. Run and Delete Behavior

- [x] 3.1 Implement `meshctl task run <name>` in `meshctl.py`, including `Initializing` precondition errors, inline line execution, `FAIL:` failure detection, `Succeeded`/`Failed` terminal states, and `status.detail` cleanup.
- [x] 3.2 Implement `meshctl snapshot run <name>` in `meshctl.py`, including `Initializing` precondition errors, unstable-mesh `Unknown` results with detail, stable-mesh `Succeeded` results, and stable non-empty `status.storageRef`.
- [x] 3.3 Implement `meshctl recovery run <name>` in `meshctl.py`, including `Initializing` precondition errors, unstable-mesh `Unknown` results with detail, and stable-mesh `Succeeded` results.
- [x] 3.4 Implement snapshot delete dependency protection in `meshctl.py` so snapshots referenced by recoveries fail with `field = "metadata.name"` and `type = "conflict"`. [extends vault-resource-management/add-vault-resource-management]

## 4. Tests

- [x] 4.1 Add `tests/test_meshctl_cli.py` coverage for task create/list/describe/update/delete/run happy paths and validation errors.
- [x] 4.2 Add `tests/test_meshctl_cli.py` coverage for snapshot create/list/describe/update/delete/run behavior, resource validation, unstable mesh `Unknown` results, storage references, and dependency protection.
- [x] 4.3 Add `tests/test_meshctl_cli.py` coverage for recovery create/list/describe/update/delete/run behavior, snapshot mesh mismatch validation, missing references, and unstable mesh `Unknown` results.
- [x] 4.4 Add `tests/test_meshctl_cli.py` coverage for legacy store loading with missing one-shot collections and sorted list JSON output for all new kinds.

## 5. Verification

- [x] 5.1 Run `uv run pytest` and fix any regressions.
- [x] 5.2 Run `openspec status --change add-one-shot-operations` and confirm proposal, specs, design, and tasks are complete.
