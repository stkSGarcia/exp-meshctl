## 1. Command And Store Foundations

- [x] 1.1 Extend `meshctl.py` `build_parser()` and `main()` with `task`, `snapshot`, and `recovery` subcommands for `create`, `list`, `describe`, `update`, `delete`, and `run`. [extends `mesh-resource-management/add-mesh-lifecycle-topology`]
- [x] 1.2 Update `meshctl.py` `empty_store()`, `load_store()`, and related collection cleanup so stores always expose `meshes`, `vaults`, `tasks`, `snapshots`, and `recoveries`. [extends `mesh-resource-management/add-vault-resource-management`]
- [x] 1.3 Add shared one-shot helper functions in `meshctl.py` for collection lookup, sorted JSON listing, full JSON describe, duplicate detection, not-found errors, and delete success output.

## 2. Creation And Validation

- [x] 2.1 Implement `normalize_task_for_create()` in `meshctl.py` with `metadata.name`, required `spec.meshRef`, exactly one non-empty `spec.inline` or `spec.bundleRef`, duplicate-name checks, mesh-reference validation, and `Initializing` status.
- [x] 2.2 Implement `normalize_snapshot_for_create()` in `meshctl.py` with required `spec.meshRef`, optional storage fields, optional `scope`, default memory resources, optional CPU resources, quantity validation, duplicate-name checks, mesh-reference validation, and `Initializing` status.
- [x] 2.3 Implement `normalize_recovery_for_create()` in `meshctl.py` with required `spec.meshRef`, required `spec.snapshotRef`, optional `scope`, default memory resources, optional CPU resources, quantity validation, duplicate-name checks, mesh and snapshot validation, snapshot mesh ownership validation, and `Initializing` status.
- [x] 2.4 Add scope validation in `meshctl.py` for snapshot and recovery `spec.scope` keys `stores`, `blueprints`, `tallies`, `definitions`, and `procedures`.

## 3. Update, Delete, And Run Behavior

- [x] 3.1 Implement one-shot update handling in `meshctl.py` that loads YAML, checks `metadata.name`, rejects missing resources, rejects any changed or newly added `spec` field with type `immutable`, and preserves atomic persistence.
- [x] 3.2 Implement `snapshot delete` dependency protection in `meshctl.py` by rejecting deletes when recoveries reference the snapshot and naming dependent recoveries in a `metadata.name` conflict error. [extends `mesh-resource-management/add-vault-resource-management`]
- [x] 3.3 Implement `task run` in `meshctl.py` with `Initializing` state validation, deterministic inline line processing, `Succeeded` output when no line starts with `FAIL:`, and `Failed` detail `command <index> failed: <reason>` for the first failing line.
- [x] 3.4 Implement `snapshot run` in `meshctl.py` with `Initializing` state validation, run-time mesh stability checks, `Unknown` detail for unstable meshes, and stable non-empty `status.storageRef` on success.
- [x] 3.5 Implement `recovery run` in `meshctl.py` with `Initializing` state validation, run-time mesh stability checks, `Unknown` detail for unstable meshes, and `Succeeded` for stable meshes.
- [x] 3.6 Ensure public status output in `meshctl.py` only includes valid one-shot status fields, including no `status.storageRef` for tasks or recoveries.

## 4. Tests

- [x] 4.1 Add `tests/test_meshctl_cli.py` coverage for task create/list/describe/delete, mesh-reference validation, exclusive inline/bundle validation, successful inline run, failing inline run, and rerun rejection.
- [x] 4.2 Add `tests/test_meshctl_cli.py` coverage for snapshot create defaults, scope preservation, quantity validation, stable-mesh success with `storageRef`, unstable-mesh `Unknown`, immutable update rejection, and dependency-protected delete.
- [x] 4.3 Add `tests/test_meshctl_cli.py` coverage for recovery create defaults, missing snapshot validation, snapshot mesh mismatch validation, stable-mesh success, unstable-mesh `Unknown`, immutable update rejection, and sorted listing.
- [x] 4.4 Add `tests/test_meshctl_cli.py` coverage proving legacy stores without one-shot collections load and save with the expanded collection shape.

## 5. Verification

- [x] 5.1 Run `uv run pytest`.
- [x] 5.2 Run `openspec status --change "add-one-shot-operations"` and confirm the proposal is complete.
