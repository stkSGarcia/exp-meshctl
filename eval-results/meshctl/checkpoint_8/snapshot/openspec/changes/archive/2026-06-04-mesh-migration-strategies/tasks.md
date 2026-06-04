## 1. Runtime Catalog

- [x] 1.1 Define the runtime version catalog as a dict constant in `meshctl.py` mapping version strings to `"supported"`, `"deprecated"`, or `"skipped"`
- [x] 1.2 Add a `validate_runtime_catalog(version)` helper that checks catalog status and returns an error tuple or warning tuple as appropriate
- [x] 1.3 Call catalog validation in the `create` path after the format check when `spec.runtime` is present
- [x] 1.4 Call catalog validation in the `update` path (post-merge) after the format check when `spec.runtime` is present

## 2. Warning Output

- [x] 2.1 Add a `warnings` list to the success response builder; only include the `warnings` key when the list is non-empty
- [x] 2.2 Sort warnings by `field` ascending, then `message` ascending before output
- [x] 2.3 Ensure warnings are suppressed (not emitted) when any validation error exists

## 3. Migration Strategy Expansion

- [x] 3.1 Update strategy validation to accept `"LiveMigration"` and `"RollingPatch"` in addition to `"FullStop"`
- [x] 3.2 Add downgrade check: compare source and target runtime semver tuples; emit downgrade error for all strategies
- [x] 3.3 Add `RollingPatch` rule 1: source and target must share the same major and minor version
- [x] 3.4 Add `RollingPatch` rule 2: target major version must be at least `4`
- [x] 3.5 Ensure both RollingPatch errors are reported independently when both fail
- [x] 3.6 Add `LiveMigration` multi-region check: reject when `spec.regions` is configured

## 4. Migration Lifecycle

- [x] 4.1 Detect first runtime assignment (no stored runtime → new runtime): store version, no migration started
- [x] 4.2 Detect version change (stored runtime differs from new runtime): start a migration
- [x] 4.3 On migration start: store target in `spec.runtime`, add `Migration` condition (`status="True"`, `message=""`), populate `status.migration` with `sourceRuntime`, `targetRuntime`, and initial `stage`
- [x] 4.4 Define stage sequences: `FullStop=["Migrate"]`, `RollingPatch=["Migrate"]`, `LiveMigration=["Prepare","Migrate","Complete"]`
- [x] 4.5 Implement migration completion: remove `Migration` condition, remove `status.migration`

## 5. mesh migrate Command

- [x] 5.1 Register `migrate <name>` as a subcommand under `mesh` in the CLI router
- [x] 5.2 Implement `mesh migrate` handler: look up mesh by name; return not-found error if absent
- [x] 5.3 Check for active migration (`Migration` condition `status="True"`); return no-active-migration error if absent
- [x] 5.4 If current stage is not the last stage: advance `status.migration.stage` to the next stage and print the full resource JSON
- [x] 5.5 If current stage is the last stage: complete the migration (remove condition + `status.migration`) and print the full resource JSON

## 6. Active Migration Guards

- [x] 6.1 In the `update` validation, detect an active migration (`Migration` condition `status="True"`)
- [x] 6.2 Reject `spec.runtime` changes during active migration with the locked-runtime error
- [x] 6.3 Reject `spec.migration.strategy` changes during active migration with the locked-strategy error
- [x] 6.4 Implement `LiveMigration` rollback: remove `Migration` condition and `status.migration`; expose via the appropriate CLI mechanism

## 7. Stability and Status Updates

- [x] 7.1 Update `status.stable` computation to return `false` when the `Migration` condition is `"True"`
- [x] 7.2 Include `status.migration` in the output serializer when it is present on the stored resource
- [x] 7.3 Ensure `status.migration` is absent from output when no migration is active

## 8. Tests

- [x] 8.1 Test: supported, deprecated, skipped, and unlisted runtime versions on create and update
- [x] 8.2 Test: warning emitted for deprecated runtime; warning suppressed on error
- [x] 8.3 Test: `LiveMigration` and `RollingPatch` accepted; invalid strategy rejected
- [x] 8.4 Test: downgrade rejected for all three strategies
- [x] 8.5 Test: RollingPatch dual-rule validation (major/minor mismatch, major < 4, both failing)
- [x] 8.6 Test: LiveMigration rejected with regions configured
- [x] 8.7 Test: first runtime assignment does not start a migration
- [x] 8.8 Test: version change starts migration with correct `status.migration` and `Migration` condition
- [x] 8.9 Test: `mesh migrate` advances stage; `mesh migrate` on final stage completes migration
- [x] 8.10 Test: `mesh migrate` errors for missing mesh and no active migration
- [x] 8.11 Test: runtime and strategy changes blocked during active migration; other fields allowed
- [x] 8.12 Test: `LiveMigration` rollback clears migration state
- [x] 8.13 Test: `status.stable = false` during active migration
