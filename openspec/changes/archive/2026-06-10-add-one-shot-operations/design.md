## Context

`meshctl.py` currently exposes mesh and vault resource groups from a single argparse entry point, persists resources in a JSON store selected by `MESHCTL_STORE`, and shares helper functions for YAML input, JSON output, validation errors, name validation, quantity validation, deep merge, and dependency checks. This change adds three persisted operational resource kinds: `task`, `snapshot`, and `recovery`.

The new resources are one-shot operations. They are created in `Initializing`, can be executed once with `run`, and then move into terminal phases that cannot be re-run. Their specs are immutable after creation, so update support is limited to detecting and rejecting spec changes while preserving the same command shape as other resources.

## Goals / Non-Goals

**Goals:**
- Add complete CLI routing for `task`, `snapshot`, and `recovery` with CRUD plus `run`.
- Reuse existing resource storage, validation, YAML parsing, JSON output, and structured error conventions.
- Persist one-shot resources in separate store collections so list, describe, update, delete, and run operate independently by kind.
- Validate cross-resource references to meshes and snapshots at create time and where required at run time.
- Make run transitions deterministic and easy to test.

**Non-Goals:**
- Execute real shell commands or external workload runners for task inline content.
- Create real snapshots, storage volumes, or restore operations.
- Add asynchronous execution, polling, retries, rollback, or cancellation.
- Add mesh delete protection for these new resources unless a later requirement explicitly defines it.

## Decisions

- Store one-shot resources in separate top-level collections named `tasks`, `snapshots`, and `recoveries`.
  - Rationale: the existing store already separates `meshes` and `vaults`; separate collections keep duplicate checks, list output, and dependency lookup simple.
  - Alternative considered: a generic resources map keyed by kind. That would reduce repeated code but require larger refactoring of the current store shape.

- Implement a small generic operation path for repeated create/list/describe/update/delete behavior, with per-kind normalization, validation, summary, public output, and dependency hooks.
  - Rationale: the three new kinds share most lifecycle and error behavior, and a narrow helper can avoid copy-paste without changing existing mesh and vault behavior.
  - Alternative considered: write separate full functions for each kind. That is straightforward but increases the chance of inconsistent output and validation drift.

- Treat `update -f` as a full spec immutability check after merging the incoming document with the stored resource.
  - Rationale: this preserves the CLI's partial update style while meeting the requirement to reject any changed or newly added spec field.
  - Alternative considered: reject any update containing `spec`. That would be simpler but would incorrectly reject idempotent updates that repeat the existing spec.

- Model `run` as an in-process deterministic state transition persisted immediately.
  - Rationale: tests can assert final persisted states without timing dependencies, and the checkpoint only requires simulated phase transitions.
  - Alternative considered: persist an intermediate `Running` state and require a later describe to complete. That matches earlier mesh lifecycle behavior but adds ambiguity that the checkpoint does not require.

- Validate mesh stability at snapshot and recovery run time using the referenced mesh's current public status.
  - Rationale: the checkpoint requires unstable mesh handling at run time, so using current mesh state avoids stale decisions from create time.
  - Alternative considered: store parent stability on create. That would be simpler but would not reflect runtime changes.

## Risks / Trade-offs

- Spec immutability comparisons may be sensitive to defaulting shape -> Normalize resources before persistence and compare normalized stored specs against normalized update candidates.
- Generic helpers may hide kind-specific details -> Keep per-kind normalization and run functions explicit, and reserve generic code for common command plumbing.
- Simulated `Running` transitions are not directly observable if the final state is persisted immediately -> Treat `Running` as an internal transition and assert final states plus invalid re-run behavior.
- Existing store files may lack the new collections -> Extend store loading to default missing collections to empty dictionaries while preserving legacy mesh-store compatibility.

## Migration Plan

No data migration command is required. Existing stores that contain only `meshes` and `vaults` continue to load, and missing `tasks`, `snapshots`, or `recoveries` collections default to empty dictionaries. Rollback is to remove the new command groups and ignore the extra top-level collections in the JSON store.

## Open Questions

- None.
