## 1. Storage and Shared Infrastructure

- [x] 1.1 Add `TASK_STORE_PATH`, `SNAPSHOT_STORE_PATH`, `RECOVERY_STORE_PATH` constants and `load_<kind>_store` / `save_<kind>_store` helpers following the `vault_store.json` pattern
- [x] 1.2 Add a shared `validate_ops_name` helper (or reuse `NAME_RE`) and a shared `ops_not_found_error` helper for the not-found error shape used by all three new kinds
- [x] 1.3 Add `check_ops_spec_immutable(stored_spec, new_spec)` helper that compares the full spec dict and returns `immutable` errors for any differing or newly added field

## 2. Task Implementation

- [x] 2.1 Implement `validate_task(doc, mesh_store)`: validate `metadata.name`, `spec.meshRef` (must reference existing mesh), and exclusive `spec.inline` / `spec.bundleRef` field; return normalized resource dict on success
- [x] 2.2 Implement `task_cmd_create(args)`: load YAML, validate, check duplicate name, set `status.state = "Initializing"`, persist, print JSON
- [x] 2.3 Implement `task_cmd_list(args)`: load task store, print JSON array sorted by name ascending
- [x] 2.4 Implement `task_cmd_describe(args)`: load task store, return not-found error or print full resource
- [x] 2.5 Implement `task_cmd_update(args)`: load YAML, look up stored task, call `check_ops_spec_immutable`, reject any spec change, persist unchanged resource
- [x] 2.6 Implement `task_cmd_delete(args)`: load task store, return not-found or remove and print confirmation
- [x] 2.7 Implement `task_cmd_run(args)`: validate state is `"Initializing"`, transition through `"Running"`, execute inline lines (fail on `FAIL:` prefix), set terminal state (`"Succeeded"` or `"Failed"` with `status.detail`), persist and print

## 3. Snapshot Implementation

- [x] 3.1 Implement `validate_snapshot(doc, mesh_store)`: validate `metadata.name`, `spec.meshRef`, optional `spec.storage` (size as memory quantity), optional `spec.resources.memory` and `spec.resources.cpu` using existing quantity validators; default memory to `{"limit": "1Gi", "request": "1Gi"}`
- [x] 3.2 Implement `snapshot_cmd_create(args)`: load YAML, validate, check duplicate name, set `status.state = "Initializing"`, persist, print JSON
- [x] 3.3 Implement `snapshot_cmd_list(args)`: load snapshot store, print JSON array sorted by name ascending
- [x] 3.4 Implement `snapshot_cmd_describe(args)`: load snapshot store, return not-found error or print full resource
- [x] 3.5 Implement `snapshot_cmd_update(args)`: load YAML, look up stored snapshot, call `check_ops_spec_immutable`, reject any spec change
- [x] 3.6 Implement `snapshot_cmd_delete(args)`: load snapshot store and recovery store; reject with `conflict` error if any recovery references this snapshot (naming dependents); otherwise remove and print confirmation
- [x] 3.7 Implement `snapshot_cmd_run(args)`: validate state is `"Initializing"`, check referenced mesh `status.stable`; if unstable set `"Unknown"` with non-empty `status.detail`; if stable set `"Succeeded"` with `status.storageRef = "snapshot/<name>"`; persist and print

## 4. Recovery Implementation

- [x] 4.1 Implement `validate_recovery(doc, mesh_store, snapshot_store)`: validate `metadata.name`, `spec.meshRef`, `spec.snapshotRef` (must reference existing snapshot), verify snapshot's `spec.meshRef` matches recovery's `spec.meshRef` (mismatch message: `"snapshot '<name>' belongs to mesh '<X>', not '<Y>'"`); default memory to `{"limit": "1Gi", "request": "1Gi"}`
- [x] 4.2 Implement `recovery_cmd_create(args)`: load YAML, validate, check duplicate name, set `status.state = "Initializing"`, persist, print JSON
- [x] 4.3 Implement `recovery_cmd_list(args)`: load recovery store, print JSON array sorted by name ascending
- [x] 4.4 Implement `recovery_cmd_describe(args)`: load recovery store, return not-found error or print full resource
- [x] 4.5 Implement `recovery_cmd_update(args)`: load YAML, look up stored recovery, call `check_ops_spec_immutable`, reject any spec change
- [x] 4.6 Implement `recovery_cmd_delete(args)`: load recovery store, return not-found or remove and print confirmation
- [x] 4.7 Implement `recovery_cmd_run(args)`: validate state is `"Initializing"`, check referenced mesh `status.stable`; if unstable set `"Unknown"` with non-empty `status.detail`; if stable set `"Succeeded"`; persist and print

## 5. CLI Wiring

- [x] 5.1 Add `task` subparser to `main()` with sub-operations: `create -f`, `list`, `describe <name>`, `update -f`, `delete <name>`, `run <name>`; route to task command handlers
- [x] 5.2 Add `snapshot` subparser to `main()` with sub-operations: `create -f`, `list`, `describe <name>`, `update -f`, `delete <name>`, `run <name>`; route to snapshot command handlers
- [x] 5.3 Add `recovery` subparser to `main()` with sub-operations: `create -f`, `list`, `describe <name>`, `update -f`, `delete <name>`, `run <name>`; route to recovery command handlers
