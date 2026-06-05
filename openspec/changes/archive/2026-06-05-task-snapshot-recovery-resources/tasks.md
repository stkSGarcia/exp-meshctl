## 1. Task Resource — CRUD

- [x] 1.1 Add `task` storage layer (in-memory store keyed by `metadata.name`)
- [x] 1.2 Implement `meshctl task create -f <path>`: parse YAML, validate `meshRef`, validate exclusive `inline`/`bundleRef`, set `status.state = "Initializing"`, persist and print JSON
- [x] 1.3 Implement `meshctl task list`: return JSON array sorted by `metadata.name` ascending
- [x] 1.4 Implement `meshctl task describe <name>`: print full resource JSON or `not_found` error
- [x] 1.5 Implement `meshctl task update -f <path>`: enforce spec immutability (reject any spec field change/add/remove with `type: "immutable"`), persist metadata-only changes
- [x] 1.6 Implement `meshctl task delete <name>`: remove from store and print confirmation JSON or `not_found` error

## 2. Task Resource — Run

- [x] 2.1 Implement `meshctl task run <name>`: gate on `status.state = "Initializing"`, reject with `status.state` / `invalid` error otherwise
- [x] 2.2 Implement inline execution: iterate lines of `spec.inline`, detect `FAIL:` prefix, set `status.state = "Failed"` and `status.detail = "command <index> failed: <reason>"` on failure
- [x] 2.3 Implement success path: all lines pass → `status.state = "Succeeded"` (no `status.detail`)
- [x] 2.4 Implement `bundleRef` run path: no inline content → `status.state = "Succeeded"`
- [x] 2.5 Verify state transition goes through `"Running"` before terminal state

## 3. Snapshot Resource — CRUD

- [x] 3.1 Add `snapshot` storage layer (in-memory store keyed by `metadata.name`)
- [x] 3.2 Implement `meshctl snapshot create -f <path>`: validate `meshRef`, validate resource quantities, apply memory default `{"limit":"1Gi","request":"1Gi"}`, accept optional `scope`, set `status.state = "Initializing"`, persist and print JSON
- [x] 3.3 Implement `meshctl snapshot list`: return JSON array sorted by `metadata.name` ascending
- [x] 3.4 Implement `meshctl snapshot describe <name>`: print full resource JSON or `not_found` error
- [x] 3.5 Implement `meshctl snapshot update -f <path>`: enforce spec immutability, persist metadata-only changes
- [x] 3.6 Implement `meshctl snapshot delete <name>`: check for referencing recoveries; reject with `field="metadata.name"`, `type="conflict"` naming dependent recoveries; otherwise remove and confirm

## 4. Snapshot Resource — Run

- [x] 4.1 Implement `meshctl snapshot run <name>`: gate on `status.state = "Initializing"`, reject otherwise
- [x] 4.2 At run time, check `mesh.status.stable`; if `false` → `status.state = "Unknown"`, `status.detail = <non-empty>`
- [x] 4.3 Implement success path: stable mesh → `status.state = "Succeeded"`, set stable non-empty `status.storageRef`
- [x] 4.4 Verify state transition goes through `"Running"` before terminal state
- [x] 4.5 Verify output shape: `storageRef` present only on `"Succeeded"`, `detail` present only on `"Failed"`/`"Unknown"`

## 5. Recovery Resource — CRUD

- [x] 5.1 Add `recovery` storage layer (in-memory store keyed by `metadata.name`)
- [x] 5.2 Implement `meshctl recovery create -f <path>`: validate `meshRef`, validate `snapshotRef` exists and its `spec.meshRef` matches; validate resource quantities; apply memory default; accept optional `scope`; set `status.state = "Initializing"`; persist and print JSON
- [x] 5.3 Implement snapshot mesh mismatch error: `field="spec.snapshotRef"`, `type="invalid"`, `message="snapshot '<name>' belongs to mesh '<X>', not '<Y>'"`
- [x] 5.4 Implement `meshctl recovery list`: return JSON array sorted by `metadata.name` ascending
- [x] 5.5 Implement `meshctl recovery describe <name>`: print full resource JSON or `not_found` error
- [x] 5.6 Implement `meshctl recovery update -f <path>`: enforce spec immutability, persist metadata-only changes
- [x] 5.7 Implement `meshctl recovery delete <name>`: remove from store and print confirmation JSON or `not_found` error

## 6. Recovery Resource — Run

- [x] 6.1 Implement `meshctl recovery run <name>`: gate on `status.state = "Initializing"`, reject otherwise
- [x] 6.2 At run time, check `mesh.status.stable`; if `false` → `status.state = "Unknown"`, `status.detail = <non-empty>`
- [x] 6.3 Implement success path: stable mesh → `status.state = "Succeeded"`
- [x] 6.4 Verify state transition goes through `"Running"` before terminal state
- [x] 6.5 Verify output shape: `detail` present only on `"Failed"`/`"Unknown"`, absent on `"Succeeded"`

## 7. Cross-Cutting Validation

- [x] 7.1 Verify `metadata.name` validation and `not_found` error shape match existing mesh/vault conventions for all three kinds
- [x] 7.2 Verify error envelope format (`{"errors":[...]}`) is consistent across all create/update/delete/run error paths
- [x] 7.3 Verify spec immutability rejects field addition (was omitted at create) as well as field change and removal
- [x] 7.4 Verify snapshot `conflict` delete message names the specific dependent recovery resources
- [x] 7.5 Verify phase names are exactly: `"Initializing"`, `"Running"`, `"Succeeded"`, `"Failed"`, `"Unknown"` (no other strings)
