## 1. Store and Routing Setup

- [x] 1.1 Add `tasks`, `snapshots`, and `recoveries` keys to the JSON store initializer
- [x] 1.2 Add CLI routing for `meshctl task <op>`, `meshctl snapshot <op>`, and `meshctl recovery <op>` sub-commands
- [x] 1.3 Wire `create`, `list`, `describe`, `update`, `delete`, and `run` operations for all three kinds

## 2. Shared Validation Utilities

- [x] 2.1 Extract (or confirm reuse of) name validation (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`, min length 2) for new kinds
- [x] 2.2 Confirm memory and CPU quantity parsers from mesh-management are reused for snapshot and recovery `spec.resources`
- [x] 2.3 Implement `meshRef` existence check helper (returns `invalid` error if mesh not found)

## 3. Task Resource

- [x] 3.1 Implement `task create`: validate `metadata.name`, `spec.meshRef`, exclusive `inline`/`bundleRef` fields; set `status.state = "Initializing"` on success
- [x] 3.2 Implement `task list`: return JSON array sorted by `name` ascending
- [x] 3.3 Implement `task describe`: return full resource JSON or `not_found` error
- [x] 3.4 Implement `task update`: reject any spec change with `type = "immutable"`; allow metadata-only changes
- [x] 3.5 Implement `task delete`: remove resource and return confirmation JSON
- [x] 3.6 Implement `task run`: validate state is `"Initializing"`; execute inline lines; fail on `FAIL:` prefix with `status.detail = "command <index> failed: <reason>"`; succeed otherwise; set final `status.state`

## 4. Snapshot Resource

- [x] 4.1 Implement `snapshot create`: validate `metadata.name`, `spec.meshRef`, memory/CPU quantities; apply memory defaults; set `status.state = "Initializing"` on success
- [x] 4.2 Implement `snapshot list`: return JSON array sorted by `name` ascending
- [x] 4.3 Implement `snapshot describe`: return full resource JSON or `not_found` error
- [x] 4.4 Implement `snapshot update`: reject any spec change with `type = "immutable"`
- [x] 4.5 Implement `snapshot delete`: scan recoveries for `spec.snapshotRef` match; reject with `conflict` error naming dependents; otherwise remove and confirm
- [x] 4.6 Implement `snapshot run`: validate state is `"Initializing"`; check mesh `status.stable`; on `false` set `"Unknown"` with detail; on `true` set `"Succeeded"` with a non-empty `status.storageRef`

## 5. Recovery Resource

- [x] 5.1 Implement `recovery create`: validate `metadata.name`, `spec.meshRef`, `spec.snapshotRef` existence, snapshot–mesh cross-reference match; apply memory defaults; set `status.state = "Initializing"` on success
- [x] 5.2 Implement `recovery list`: return JSON array sorted by `name` ascending
- [x] 5.3 Implement `recovery describe`: return full resource JSON or `not_found` error
- [x] 5.4 Implement `recovery update`: reject any spec change with `type = "immutable"`
- [x] 5.5 Implement `recovery delete`: remove resource and return confirmation JSON
- [x] 5.6 Implement `recovery run`: validate state is `"Initializing"`; check mesh `status.stable`; on `false` set `"Unknown"` with detail; on `true` set `"Succeeded"`

## 6. Output Format Compliance

- [x] 6.1 Ensure all three kinds use the existing JSON error format (`{"errors":[{"field":…,"type":…,"message":…}]}`) with error array sorted by `field` then `type`
- [x] 6.2 Ensure `status.detail` is included only in `"Failed"` or `"Unknown"` states
- [x] 6.3 Ensure `status.storageRef` is included only on a succeeded snapshot
- [x] 6.4 Verify `task delete` and `recovery delete` return the same confirmation shape as `mesh delete`
