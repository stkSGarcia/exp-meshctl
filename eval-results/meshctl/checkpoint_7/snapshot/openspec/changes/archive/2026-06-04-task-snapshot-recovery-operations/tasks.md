## 1. Shared Infrastructure

- [x] 1.1 Add shared `run_state_guard` helper that validates `status.state == "Initializing"` and returns the standard `status.state` invalid error with the correct message format
- [x] 1.2 Add shared `full_spec_immutability_check` helper that diffs the incoming spec fields against the stored spec and returns `immutable` errors for any change
- [x] 1.3 Verify that the existing resource-quantity validator (memory/CPU) is importable and reusable for snapshot and recovery

## 2. Task Resource

- [x] 2.1 Add in-memory store for task resources
- [x] 2.2 Implement `meshctl task create -f <path>`: parse YAML, validate `metadata.name` (same rules as mesh), validate `spec.meshRef` exists, enforce exclusive `spec.inline`/`spec.bundleRef` constraint (exactly one, non-empty), persist with `status.state = "Initializing"`, print full JSON
- [x] 2.3 Implement `meshctl task list`: print JSON array sorted by `name` ascending
- [x] 2.4 Implement `meshctl task describe <name>`: print full resource JSON or not-found error
- [x] 2.5 Implement `meshctl task update -f <path>`: apply `full_spec_immutability_check`, reject any spec change with `type = "immutable"`
- [x] 2.6 Implement `meshctl task delete <name>`: remove from store, print confirmation JSON
- [x] 2.7 Implement `meshctl task run <name>`: use `run_state_guard`, transition to `Running`, execute inline lines, detect `FAIL:` prefix, set `status.state` and `status.detail`, transition to `Succeeded` or `Failed`
- [x] 2.8 Wire `meshctl task` into the CLI entry point router

## 3. Snapshot Resource

- [x] 3.1 Add in-memory store for snapshot resources
- [x] 3.2 Implement `meshctl snapshot create -f <path>`: parse YAML, validate `metadata.name`, validate `spec.meshRef` exists, apply default `spec.resources.memory = {"limit": "1Gi", "request": "1Gi"}` if absent, validate memory/CPU quantity formats, persist with `status.state = "Initializing"`, print full JSON
- [x] 3.3 Implement `meshctl snapshot list`: print JSON array sorted by `name` ascending
- [x] 3.4 Implement `meshctl snapshot describe <name>`: print full resource JSON or not-found error
- [x] 3.5 Implement `meshctl snapshot update -f <path>`: apply `full_spec_immutability_check`, reject any spec change with `type = "immutable"`
- [x] 3.6 Implement `meshctl snapshot delete <name>`: scan recovery store for references; reject with `field = "metadata.name"`, `type = "conflict"` naming dependent recoveries; otherwise remove and print confirmation
- [x] 3.7 Implement `meshctl snapshot run <name>`: use `run_state_guard`, transition to `Running`, check mesh `status.stable`; if `false` set `status.state = "Unknown"` with non-empty `status.detail`; if `true` set `status.state = "Succeeded"` and `status.storageRef` to a stable non-empty string
- [x] 3.8 Wire `meshctl snapshot` into the CLI entry point router

## 4. Recovery Resource

- [x] 4.1 Add in-memory store for recovery resources
- [x] 4.2 Implement `meshctl recovery create -f <path>`: parse YAML, validate `metadata.name`, validate `spec.meshRef` exists, validate `spec.snapshotRef` points to an existing snapshot, validate the snapshot's `spec.meshRef` matches the recovery's `spec.meshRef` (emit mesh-ownership mismatch error if not), apply default `spec.resources.memory` if absent, persist with `status.state = "Initializing"`, print full JSON
- [x] 4.3 Implement `meshctl recovery list`: print JSON array sorted by `name` ascending
- [x] 4.4 Implement `meshctl recovery describe <name>`: print full resource JSON or not-found error
- [x] 4.5 Implement `meshctl recovery update -f <path>`: apply `full_spec_immutability_check`, reject any spec change with `type = "immutable"`
- [x] 4.6 Implement `meshctl recovery delete <name>`: remove from store, print confirmation JSON
- [x] 4.7 Implement `meshctl recovery run <name>`: use `run_state_guard`, transition to `Running`, check mesh `status.stable`; if `false` set `status.state = "Unknown"` with non-empty `status.detail`; if `true` set `status.state = "Succeeded"`
- [x] 4.8 Wire `meshctl recovery` into the CLI entry point router

## 5. Output Format and Error Validation

- [x] 5.1 Confirm all three kinds use the same JSON error shape as mesh/vault: `{"errors":[{"field":"...","type":"...","message":"..."}]}`
- [x] 5.2 Confirm `status.detail` is present only in `"Failed"` or `"Unknown"` states for all three kinds
- [x] 5.3 Confirm `status.storageRef` is present only on succeeded snapshot resources
- [x] 5.4 Confirm terminal states are irreversible (a second `run` on any terminal state returns the state-guard error)

## 6. Tests

- [x] 6.1 Test task create: valid, invalid meshRef, both inline+bundleRef set, neither set, empty inline
- [x] 6.2 Test task run: success path, FAIL: line detection, non-Initializing rejection
- [x] 6.3 Test task spec immutability on update
- [x] 6.4 Test snapshot create: valid, invalid meshRef, memory default, invalid quantity
- [x] 6.5 Test snapshot run: stable mesh succeeds with storageRef, unstable mesh sets Unknown, non-Initializing rejection
- [x] 6.6 Test snapshot delete: unreferenced succeeds, referenced by recovery returns conflict error
- [x] 6.7 Test snapshot spec immutability on update
- [x] 6.8 Test recovery create: valid, invalid meshRef, missing snapshotRef, snapshot meshRef mismatch, memory default
- [x] 6.9 Test recovery run: stable mesh succeeds, unstable mesh sets Unknown, non-Initializing rejection
- [x] 6.10 Test recovery spec immutability on update
