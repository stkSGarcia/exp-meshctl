## 1. Network Topology Fields

- [x] 1.1 Add `parse_memory_quantity` reuse for storage size validation (already exists — wire into storage validator)
- [x] 1.2 Add `spec.network.storage` parsing: read `size`, `ephemeral`, `className`; default `size = "1Gi"` and `ephemeral = false` on create
- [x] 1.3 Add `spec.network.replicationFactor` parsing: default to `min(spec.instances, 3)` on create; validate >= 1 and <= instances
- [x] 1.4 Add `format_storage(storage)` helper: omit `size` when `ephemeral = true`, include both when `false`
- [x] 1.5 Include `spec.network` in the output of `validate_and_build` for create

## 2. Enriched Status Model

- [x] 2.1 Add `build_initial_status(instances)` helper: returns `state`, `stable`, `instances` dict, and initial `conditions` list (`Healthy` + `PrechecksPassed`)
- [x] 2.2 Update `cmd_create` to use `build_initial_status` and include `status.instances` and `status.conditions` in output and stored resource
- [x] 2.3 Update `cmd_describe` to strip transient `Scaling` condition from the returned resource before printing (do not re-persist)
- [x] 2.4 Update `cmd_list` to pass through the enriched `status` (already reads from store — no change needed if status is stored correctly)

## 3. Merge Logic

- [x] 3.1 Add `deep_merge(stored, update)` — recursively merges update dict into stored dict; `None` values in update are treated as absent
- [x] 3.2 Add `check_immutable(stored_spec, merged_spec)` — returns list of `immutable` errors for any immutable field that changed; initially covers `spec.network.storage.size`
- [x] 3.3 Add `cmd_update(args)` handler: load YAML, load stored mesh, strip transient `Scaling` from stored status, deep-merge spec, check immutables, run validation on merged doc, detect lifecycle transition, persist, print

## 4. Instance Lifecycle State Machine

- [x] 4.1 Add `detect_lifecycle(old_instances, new_instances, old_status)` — returns one of: `scale_up`, `scale_down`, `stop`, `resume`, or `none`
- [x] 4.2 Add `apply_lifecycle(transition, old_status, old_instances, new_instances)` — returns updated status dict with correct `instances`, `state`, `stable`, `conditions`, and `desiredInstancesOnResume`
  - Scale up: add `Scaling` (True, non-empty message), set `ready = old`, `starting = new - old`
  - Scale down: add `Scaling` (True), counts unchanged until next describe
  - Stop: add `GracefulShutdown` (True, ""), set `ready=0, starting=0, stopped=old`, `state="Stopped"`, `desiredInstancesOnResume=old`, `stable=false`
  - Resume: remove `GracefulShutdown`, remove `desiredInstancesOnResume`, set `ready=0, starting=target, stopped=0`, `state="Running"`, add `Scaling` (True, non-empty)
- [x] 4.3 Wire `detect_lifecycle` and `apply_lifecycle` into `cmd_update`

## 5. CLI Wiring

- [x] 5.1 Add `mesh update` subcommand to the argparse setup with `-f` argument
- [x] 5.2 Register `cmd_update` in the operation dispatch table

## 6. Validation Updates

- [x] 6.1 Add `immutable` to the set of recognized error types (documentation only — no code gate needed)
- [x] 6.2 Ensure replication factor post-merge constraint error message names both the actual value and the limit (e.g., `"replicationFactor 5 exceeds instances 3"`)
- [x] 6.3 Add storage size validation path in the unified validator (called by both create and update)
