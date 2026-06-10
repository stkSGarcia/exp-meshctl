## 1. Store and CLI Structure

- [x] 1.1 Add `task`, `snapshot`, and `recovery` argparse command groups with `create -f`, `list`, `describe <name>`, `update -f`, `delete <name>`, and `run <name>` operations.
- [x] 1.2 Extend store loading and saving to support `tasks`, `snapshots`, and `recoveries` collections while preserving existing mesh/vault and legacy flat mesh store compatibility.
- [x] 1.3 Add common one-shot command helpers for create, list, describe, update, delete, run, JSON output, duplicate detection, and not-found errors.
- [x] 1.4 Reuse existing YAML input loading, metadata name validation, quantity validation, deep merge, JSON success output, and JSON error output conventions.

## 2. Resource Normalization and Validation

- [x] 2.1 Implement task create normalization for `metadata.name`, required existing `spec.meshRef`, and exactly one non-empty source from `spec.inline` or `spec.bundleRef`.
- [x] 2.2 Implement snapshot create normalization for `metadata.name`, required existing `spec.meshRef`, optional storage fields, optional scope, defaulted memory, and optional CPU.
- [x] 2.3 Implement recovery create normalization for `metadata.name`, required existing `spec.meshRef`, required existing `spec.snapshotRef`, optional scope, defaulted memory, and optional CPU.
- [x] 2.4 Validate recovery snapshot/mesh consistency with the required `spec.snapshotRef` invalid error and mismatch message.
- [x] 2.5 Validate snapshot and recovery resource quantities with the same memory and CPU rules used by mesh resources.
- [x] 2.6 Initialize successful task, snapshot, and recovery creates with `status.state` equal to `"Initializing"`.

## 3. CRUD Operations and Immutability

- [x] 3.1 Implement `task`, `snapshot`, and `recovery` create commands to validate, persist, and print full resources.
- [x] 3.2 Implement list commands sorted by `name` ascending with JSON resource summaries.
- [x] 3.3 Implement describe commands that print full resources or return `metadata.name` `not_found`.
- [x] 3.4 Implement update commands that select by `metadata.name`, merge input with the stored resource, and preserve all-or-nothing persistence on validation failure.
- [x] 3.5 Enforce full `spec` immutability for task, snapshot, and recovery updates, including newly added spec fields, with `immutable` errors.
- [x] 3.6 Implement delete commands that remove resources and print confirmation objects, or return `metadata.name` `not_found`.

## 4. Run Lifecycle and Status Output

- [x] 4.1 Implement shared run preflight to allow execution only from `"Initializing"` and reject other states with the required `status.state` invalid error message.
- [x] 4.2 Implement task run transitions through `"Running"` to `"Succeeded"` for bundle tasks and inline tasks without failing lines.
- [x] 4.3 Implement task inline failure handling for lines starting with `FAIL:`, including `status.state` `"Failed"` and the required `status.detail` format.
- [x] 4.4 Implement snapshot run transitions through `"Running"` to `"Succeeded"` with a stable non-empty `status.storageRef` when the referenced mesh is stable.
- [x] 4.5 Implement snapshot run transition to `"Unknown"` with non-empty `status.detail` when the referenced mesh is unstable at run time.
- [x] 4.6 Implement recovery run transitions through `"Running"` to `"Succeeded"` when the referenced mesh is stable and `"Unknown"` with non-empty `status.detail` when it is unstable.
- [x] 4.7 Ensure `status.detail` appears only for `"Failed"` or `"Unknown"` states and `status.storageRef` appears only for succeeded snapshots.

## 5. Dependency Protection

- [x] 5.1 Block `snapshot delete` when one or more recoveries reference the snapshot through `spec.snapshotRef`.
- [x] 5.2 Return a `metadata.name` `conflict` error for blocked snapshot deletion and include the dependent recovery names in the message.
- [x] 5.3 Preserve the snapshot unchanged when dependency protection rejects deletion.

## 6. Tests and Verification

- [x] 6.1 Add CLI tests for task create, describe, sorted list, idempotent update, delete, duplicate metadata, source exclusivity, empty source values, missing mesh references, successful run, inline failure, and invalid re-run.
- [x] 6.2 Add CLI tests for snapshot create, describe, sorted list, idempotent update, delete, duplicate metadata, storage/scope preservation, memory defaulting, quantity validation, missing mesh references, succeeded run, unknown run, storageRef output, and invalid re-run.
- [x] 6.3 Add CLI tests for recovery create, describe, sorted list, idempotent update, delete, duplicate metadata, scope preservation, memory defaulting, quantity validation, missing mesh references, missing snapshot references, snapshot mesh mismatch, succeeded run, unknown run, and invalid re-run.
- [x] 6.4 Add CLI tests for task/snapshot/recovery parse errors, non-mapping input, not-found describe/update/delete/run, spec immutability, atomic update failures, JSON error shape, and no-stderr output.
- [x] 6.5 Add CLI tests for snapshot delete conflicts while recoveries reference the snapshot and successful snapshot delete after dependent recoveries are removed.
- [x] 6.6 Run the full test suite and `openspec validate add-one-shot-operations`.
