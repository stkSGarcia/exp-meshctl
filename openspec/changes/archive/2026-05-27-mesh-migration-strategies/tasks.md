## 1. Runtime Catalog

- [x] 1.1 Define the runtime version catalog as an in-code dict mapping version strings to status (`supported`, `deprecated`, `skipped`), populated with at least `3.0.0` (deprecated), `3.1.0` (skipped), `3.1.1` (supported), `4.0.0` (supported)
- [x] 1.2 Add catalog lookup helper that returns the status for a given version string, or `None` if not in catalog
- [x] 1.3 Add `validate_runtime_catalog(version)` that returns an error if the version is skipped or not in catalog, and a warning if deprecated
- [x] 1.4 Wire catalog validation into `mesh create`: call `validate_runtime_catalog` when `spec.runtime` is present, accumulate errors/warnings
- [x] 1.5 Wire catalog validation into `mesh update`: call `validate_runtime_catalog` when `spec.runtime` is present after merge

## 2. Warnings Output

- [x] 2.1 Add a `collect_warnings()` / warnings accumulation mechanism in the request handler (parallel to error accumulation)
- [x] 2.2 Update success response serialization to include `"warnings":[...]` key when warnings list is non-empty, omitting the key when empty
- [x] 2.3 Ensure warnings are sorted by `field` ascending, then `message` ascending before output
- [x] 2.4 Confirm warnings are suppressed entirely when any errors are present (no partial-success warnings)

## 3. Strategy Expansion

- [x] 3.1 Update `spec.migration.strategy` validation to accept `"LiveMigration"` and `"RollingPatch"` in addition to `"FullStop"`
- [x] 3.2 Confirm invalid strategy still produces `{"field":"spec.migration.strategy","type":"invalid","message":"<msg>"}`

## 4. Version-Change Rules

- [x] 4.1 Add `parse_version(v)` helper returning `(major, minor, patch)` tuple
- [x] 4.2 Add downgrade check: if `spec.runtime` is changing and target tuple < source tuple, produce error `{"field":"spec.runtime","type":"invalid","message":"version downgrade from '<current>' to '<target>' is not allowed"}`; apply for all three strategies
- [x] 4.3 Add `RollingPatch` constraints: check source and target share same major+minor; check target major >= 4; report both errors independently when applicable
- [x] 4.4 Add `LiveMigration` multi-region check: if `spec.regions` is configured, produce error `{"field":"spec.migration.strategy","type":"invalid","message":"LiveMigration strategy is not supported with multi-region topology"}`
- [x] 4.5 Ensure all version-change rule errors are accumulated alongside catalog and other validation errors

## 5. Migration Lifecycle — Start

- [x] 5.1 Detect a version change: `spec.runtime` present, stored mesh already has a runtime set, and the values differ
- [x] 5.2 On migration start, set `status.migration` with `sourceRuntime` (old value), `targetRuntime` (new value), and `stage` (first stage for the chosen strategy)
- [x] 5.3 On migration start, upsert `Migration` condition in `status.conditions` with `status = "True"` and `message = ""`
- [x] 5.4 Confirm that first assignment (runtime was absent) does NOT start a migration
- [x] 5.5 Define stage sequences: `FullStop` → `["Migrate"]`, `RollingPatch` → `["Migrate"]`, `LiveMigration` → `["Prepare", "Migrate", "Cutover"]`

## 6. Active Migration Locks

- [x] 6.1 In `mesh update`, detect active migration by checking for `Migration` condition with `status = "True"`
- [x] 6.2 When active migration exists and `spec.runtime` differs from stored value, produce error `{"field":"spec.runtime","type":"invalid","message":"cannot change runtime version while a migration is in progress"}`
- [x] 6.3 When active migration exists and `spec.migration.strategy` differs from stored value, produce error `{"field":"spec.migration.strategy","type":"invalid","message":"cannot change migration strategy while a migration is in progress"}`
- [x] 6.4 Confirm that updates to other spec fields (e.g., `spec.instances`) succeed during an active migration

## 7. mesh migrate Command

- [x] 7.1 Add `mesh migrate <name>` subcommand dispatcher in `meshctl.py`
- [x] 7.2 Implement missing mesh check: return `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`
- [x] 7.3 Implement no-active-migration check: return `{"errors":[{"field":"status.migration","type":"invalid","message":"no active migration for mesh '<name>'"}]}`
- [x] 7.4 Implement stage advance: look up current stage in strategy's stage sequence, set `status.migration.stage` to the next stage, persist and print full resource
- [x] 7.5 Implement completion: when current stage is the final stage, remove `Migration` condition and `status.migration`, persist and print full resource

## 8. LiveMigration Rollback

- [x] 8.1 Implement rollback trigger (resolve open question from design; implement as `mesh migrate --rollback <name>`)
- [x] 8.2 On rollback for `LiveMigration`: remove `Migration` condition and `status.migration`, persist and print full resource
- [x] 8.3 Reject rollback when strategy is `FullStop` or `RollingPatch`

## 9. Stability Update

- [x] 9.1 Update `compute_stable()` to include `Migration` condition: stable is `false` when `Migration` has `status = "True"`
- [x] 9.2 Verify that the complete stability formula covers: `Healthy=True`, `PrechecksPassed=True`, `GracefulShutdown` absent or `False`, `Scaling` absent or `False`, `Migration` absent or `False`
