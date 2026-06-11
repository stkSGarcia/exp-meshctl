## 1. Store and CLI Structure

- [x] 1.1 Extend store loading/saving helpers to support `tasks`, `snapshots`, and `recoveries` collections while preserving existing mesh and vault behavior.
- [x] 1.2 Add `task`, `snapshot`, and `recovery` argparse command groups with `create -f`, `list`, `describe <name>`, `update -f`, `delete <name>`, and `run <name>`.
- [x] 1.3 Route the new command groups through shared JSON output, JSON error output, YAML loading, metadata name validation, duplicate checks, not-found checks, and deterministic list sorting helpers.
- [x] 1.4 Define full-resource and list-summary output builders for task, snapshot, and recovery resources.

## 2. Shared One-Shot Resource Behavior

- [x] 2.1 Implement create-time initialization so every valid task, snapshot, and recovery is persisted with `status.state` equal to `"Initializing"`.
- [x] 2.2 Implement partial update loading and merge behavior for one-shot resources with all-or-nothing persistence on validation failure.
- [x] 2.3 Enforce full `spec` immutability after create, including rejecting changed existing fields and newly added omitted fields with `immutable` errors.
- [x] 2.4 Implement shared `run` preflight behavior that rejects missing resources and resources whose `status.state` is not `"Initializing"` with the required `status.state` error.
- [x] 2.5 Ensure terminal status output omits `status.detail` except for `"Failed"` or `"Unknown"` resources.

## 3. Task Resource

- [x] 3.1 Implement task create validation for required existing `spec.meshRef`.
- [x] 3.2 Enforce exactly one non-empty task command source: `spec.inline` or `spec.bundleRef`, using the required `spec` invalid error message for exclusivity failures.
- [x] 3.3 Implement task CRUD commands and sorted task list summaries.
- [x] 3.4 Implement task inline run behavior by evaluating each line in order and failing on `FAIL:` lines with `status.detail` equal to `command <index> failed: <reason>`.
- [x] 3.5 Implement successful task run behavior for inline content without failures and for bundle references.

## 4. Snapshot Resource

- [x] 4.1 Implement snapshot create validation for required existing `spec.meshRef`.
- [x] 4.2 Implement snapshot `spec.resources.memory` defaulting to `{"limit": "1Gi", "request": "1Gi"}` and reuse mesh quantity validation for memory and CPU.
- [x] 4.3 Preserve optional snapshot storage fields and scope fields, including omitted scope meaning all data and provided scope meaning only named items.
- [x] 4.4 Implement snapshot CRUD commands and sorted snapshot list summaries.
- [x] 4.5 Implement snapshot run behavior: stable referenced mesh succeeds with a stable non-empty `status.storageRef`; unstable referenced mesh becomes `"Unknown"` with non-empty `status.detail`.
- [x] 4.6 Ensure `status.storageRef` appears only on succeeded snapshots.

## 5. Recovery Resource

- [x] 5.1 Implement recovery create validation for required existing `spec.meshRef`.
- [x] 5.2 Implement required existing `spec.snapshotRef` validation and reject snapshot/mesh mismatches with the required `spec.snapshotRef` invalid message.
- [x] 5.3 Implement recovery `spec.resources.memory` defaulting to `{"limit": "1Gi", "request": "1Gi"}` and reuse mesh quantity validation for memory and CPU.
- [x] 5.4 Preserve optional recovery scope fields, including omitted scope meaning restore all snapshot data.
- [x] 5.5 Implement recovery CRUD commands and sorted recovery list summaries.
- [x] 5.6 Implement recovery run behavior: stable referenced mesh succeeds; unstable referenced mesh becomes `"Unknown"` with non-empty `status.detail`.

## 6. Dependency Protection

- [x] 6.1 Reject `snapshot delete` when one or more recoveries reference the snapshot through `spec.snapshotRef`.
- [x] 6.2 Return `metadata.name` `conflict` errors for blocked snapshot deletes and include dependent recovery names in the conflict message.
- [x] 6.3 Preserve the snapshot when dependency conflict validation fails.

## 7. Tests and Verification

- [x] 7.1 Add CLI tests for task create/list/describe/update/delete/run success paths, inline failure behavior, exclusivity validation, mesh reference validation, rerun rejection, and spec immutability.
- [x] 7.2 Add CLI tests for snapshot create/list/describe/update/delete/run success paths, resource defaulting/validation, scope preservation, unstable-mesh `Unknown`, storageRef output, delete conflicts, and spec immutability.
- [x] 7.3 Add CLI tests for recovery create/list/describe/update/delete/run success paths, snapshot reference validation, snapshot/mesh mismatch validation, resource defaulting/validation, unstable-mesh `Unknown`, and spec immutability.
- [x] 7.4 Add CLI tests for shared one-shot parse errors, non-mapping YAML input, duplicate names, missing describe/update/delete/run targets, sorted list output, JSON error shape, and no-stderr behavior.
- [x] 7.5 Run the full test suite.
- [x] 7.6 Run `openspec validate add-one-shot-operations`.
