## ADDED Requirements

### Requirement: One-shot CLI command surface
The system SHALL expose `task`, `snapshot`, and `recovery` resource operations through `meshctl.py`.

#### Scenario: Create command accepts a YAML file
- **WHEN** the user runs `uv run --project /app meshctl.py <kind> create -f <path>` for `<kind>` equal to `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL read `<path>` as the resource YAML input and attempt to create the resource.

#### Scenario: List command returns existing resource summaries
- **WHEN** the user runs `uv run --project /app meshctl.py <kind> list` for `<kind>` equal to `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL print a JSON array of resource summaries sorted by `name` ascending.

#### Scenario: Describe command returns a named resource
- **WHEN** the user runs `uv run --project /app meshctl.py <kind> describe <name>` for `<kind>` equal to `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL print the full persisted resource for `<name>`.

#### Scenario: Update command accepts a YAML file
- **WHEN** the user runs `uv run --project /app meshctl.py <kind> update -f <path>` for `<kind>` equal to `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL read `<path>` as the resource update YAML input and attempt to update the named resource.

#### Scenario: Delete command removes a named resource
- **WHEN** the user runs `uv run --project /app meshctl.py <kind> delete <name>` for `<kind>` equal to `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL remove the resource and print a JSON confirmation object.

#### Scenario: Run command executes a named resource
- **WHEN** the user runs `uv run --project /app meshctl.py <kind> run <name>` for `<kind>` equal to `task`, `snapshot`, or `recovery`
- **THEN** the system SHALL execute the named resource according to that kind's run rules.

### Requirement: One-shot input format and metadata
The system SHALL accept exactly one YAML document whose root value is a mapping with supported top-level `metadata` and `spec` content for `task`, `snapshot`, and `recovery`.

#### Scenario: YAML read or parse failure
- **WHEN** the input file cannot be read or parsed as YAML
- **THEN** the system SHALL print a JSON error object containing an error with field `""` and type `parse`.

#### Scenario: YAML document is not a mapping
- **WHEN** the input parses but the YAML document root is not a mapping
- **THEN** the system SHALL print a JSON error object and SHALL NOT persist the resource.

#### Scenario: Metadata name is required
- **WHEN** a create input omits `metadata.name` or provides it as null or an empty string
- **THEN** the system SHALL report field `metadata.name` with type `required`.

#### Scenario: Metadata name uses mesh naming rule
- **WHEN** a create input provides `metadata.name` that does not satisfy the mesh naming rule
- **THEN** the system SHALL report field `metadata.name` with type `invalid`.

#### Scenario: Duplicate metadata name on create
- **WHEN** a create request uses `metadata.name` that already exists for the same resource kind
- **THEN** the system SHALL report field `metadata.name` with type `duplicate` and SHALL NOT overwrite the existing resource.

### Requirement: One-shot create lifecycle
The system SHALL initialize every successfully created `task`, `snapshot`, and `recovery` resource with `status.state` equal to `"Initializing"`.

#### Scenario: Task create starts initializing
- **WHEN** a task is created successfully
- **THEN** the returned and persisted task SHALL include `status.state` equal to `"Initializing"`.

#### Scenario: Snapshot create starts initializing
- **WHEN** a snapshot is created successfully
- **THEN** the returned and persisted snapshot SHALL include `status.state` equal to `"Initializing"`.

#### Scenario: Recovery create starts initializing
- **WHEN** a recovery is created successfully
- **THEN** the returned and persisted recovery SHALL include `status.state` equal to `"Initializing"`.

### Requirement: Task spec validation
The system SHALL support task specs with required `spec.meshRef` and exactly one non-empty source field from `spec.inline` or `spec.bundleRef`.

#### Scenario: Task mesh reference is required
- **WHEN** a task create input omits `spec.meshRef` or provides it as null or an empty string
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Task mesh reference must exist
- **WHEN** a task create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Task inline source is accepted
- **WHEN** a valid task create input includes non-empty `spec.inline` and omits `spec.bundleRef`
- **THEN** the created task SHALL include the provided `spec.inline`.

#### Scenario: Task bundle source is accepted
- **WHEN** a valid task create input includes non-empty `spec.bundleRef` and omits `spec.inline`
- **THEN** the created task SHALL include the provided `spec.bundleRef`.

#### Scenario: Task rejects missing source
- **WHEN** a task create input omits both `spec.inline` and `spec.bundleRef`
- **THEN** the system SHALL report field `spec` with type `invalid` and message `"exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`.

#### Scenario: Task rejects both sources
- **WHEN** a task create input includes both `spec.inline` and `spec.bundleRef`
- **THEN** the system SHALL report field `spec` with type `invalid` and message `"exactly one of 'spec.inline' or 'spec.bundleRef' must be set"`.

#### Scenario: Task rejects empty source values
- **WHEN** a task create input includes an empty value for `spec.inline` or `spec.bundleRef`
- **THEN** the system SHALL reject the input as invalid.

### Requirement: Snapshot spec validation
The system SHALL support snapshot specs with required `spec.meshRef`, optional `spec.storage.size`, optional `spec.storage.className`, optional `spec.scope`, defaulted `spec.resources.memory`, and optional `spec.resources.cpu`.

#### Scenario: Snapshot mesh reference is required
- **WHEN** a snapshot create input omits `spec.meshRef` or provides it as null or an empty string
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Snapshot mesh reference must exist
- **WHEN** a snapshot create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Snapshot memory defaults
- **WHEN** a valid snapshot create input omits `spec.resources.memory`
- **THEN** the created snapshot SHALL include `spec.resources.memory` equal to `{"limit": "1Gi", "request": "1Gi"}`.

#### Scenario: Snapshot resource quantities validate like mesh quantities
- **WHEN** a snapshot create input includes invalid memory or CPU quantity formats under `spec.resources`
- **THEN** the system SHALL reject the invalid quantity fields using the same validation rules as mesh resources.

#### Scenario: Snapshot scope captures all when omitted
- **WHEN** a valid snapshot create input omits `spec.scope`
- **THEN** the snapshot SHALL represent capture of all mesh data.

#### Scenario: Snapshot scope preserves named data subsets
- **WHEN** a valid snapshot create input includes `spec.scope` with keys from `stores`, `blueprints`, `tallies`, `definitions`, and `procedures`
- **THEN** the created snapshot SHALL preserve the provided scope so only the named items are captured.

#### Scenario: Snapshot storage fields are optional
- **WHEN** a valid snapshot create input includes `spec.storage.size` or `spec.storage.className`
- **THEN** the created snapshot SHALL preserve the provided storage fields.

### Requirement: Recovery spec validation
The system SHALL support recovery specs with required `spec.meshRef`, required `spec.snapshotRef`, optional `spec.scope`, defaulted `spec.resources.memory`, and optional `spec.resources.cpu`.

#### Scenario: Recovery mesh reference is required
- **WHEN** a recovery create input omits `spec.meshRef` or provides it as null or an empty string
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Recovery mesh reference must exist
- **WHEN** a recovery create input has `spec.meshRef` that does not match an existing mesh name
- **THEN** the system SHALL report field `spec.meshRef` with type `invalid`.

#### Scenario: Recovery snapshot reference is required
- **WHEN** a recovery create input omits `spec.snapshotRef` or provides it as null or an empty string
- **THEN** the system SHALL report field `spec.snapshotRef` with type `invalid`.

#### Scenario: Recovery snapshot reference must exist
- **WHEN** a recovery create input has `spec.snapshotRef` that does not match an existing snapshot name
- **THEN** the system SHALL report field `spec.snapshotRef` with type `invalid`.

#### Scenario: Recovery snapshot must belong to same mesh
- **WHEN** a recovery create input references snapshot `<name>` whose `spec.meshRef` is `<X>` and the recovery `spec.meshRef` is `<Y>`
- **THEN** the system SHALL report field `spec.snapshotRef` with type `invalid` and message `"snapshot '<name>' belongs to mesh '<X>', not '<Y>'"`.

#### Scenario: Recovery memory defaults
- **WHEN** a valid recovery create input omits `spec.resources.memory`
- **THEN** the created recovery SHALL include `spec.resources.memory` equal to `{"limit": "1Gi", "request": "1Gi"}`.

#### Scenario: Recovery resource quantities validate like mesh quantities
- **WHEN** a recovery create input includes invalid memory or CPU quantity formats under `spec.resources`
- **THEN** the system SHALL reject the invalid quantity fields using the same validation rules as mesh resources.

#### Scenario: Recovery scope restores all when omitted
- **WHEN** a valid recovery create input omits `spec.scope`
- **THEN** the recovery SHALL represent restore of all snapshot data.

#### Scenario: Recovery scope preserves named data subsets
- **WHEN** a valid recovery create input includes `spec.scope` with keys from `stores`, `blueprints`, `tallies`, `definitions`, and `procedures`
- **THEN** the created recovery SHALL preserve the provided scope so only the named items are restored.

### Requirement: One-shot update immutability
The system SHALL treat the entire `spec` section of `task`, `snapshot`, and `recovery` resources as immutable after creation.

#### Scenario: Update rejects changed spec field
- **WHEN** an update would change any stored `spec` field on a task, snapshot, or recovery
- **THEN** the system SHALL reject the update with at least one error of type `immutable`.

#### Scenario: Update rejects newly added spec field
- **WHEN** an update would add a `spec` field that was previously omitted on a task, snapshot, or recovery
- **THEN** the system SHALL reject the update with at least one error of type `immutable`.

#### Scenario: Update validation failure is atomic
- **WHEN** any validation error occurs while processing a task, snapshot, or recovery update
- **THEN** the system SHALL reject the whole update and SHALL NOT persist any field from that update.

#### Scenario: Idempotent spec update is allowed
- **WHEN** an update repeats the stored `spec` content without changing it
- **THEN** the system SHALL NOT reject the update for spec immutability.

### Requirement: One-shot not-found handling
The system SHALL reject missing named task, snapshot, and recovery resources using structured JSON errors.

#### Scenario: Missing resource on describe
- **WHEN** the user describes a task, snapshot, or recovery name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing resource on update
- **WHEN** the user updates a task, snapshot, or recovery name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing resource on delete
- **WHEN** the user deletes a task, snapshot, or recovery name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

#### Scenario: Missing resource on run
- **WHEN** the user runs a task, snapshot, or recovery name that does not exist
- **THEN** the system SHALL report field `metadata.name` with type `not_found`.

### Requirement: One-shot run lifecycle
The system SHALL allow `task`, `snapshot`, and `recovery` resources to run only from `"Initializing"` and SHALL treat terminal states as irreversible.

#### Scenario: Run rejects non-initializing state
- **WHEN** the user runs a task, snapshot, or recovery whose current `status.state` is not `"Initializing"`
- **THEN** the system SHALL report field `status.state` with type `invalid` and message `"resource is in state '<current>', expected 'Initializing'"`.

#### Scenario: Task run transitions through running
- **WHEN** a task run starts from `"Initializing"`
- **THEN** the system SHALL transition the task through `"Running"` to `"Succeeded"` or `"Failed"`.

#### Scenario: Snapshot run transitions through running
- **WHEN** a snapshot run starts from `"Initializing"`
- **THEN** the system SHALL transition the snapshot through `"Running"` to `"Succeeded"`, `"Failed"`, or `"Unknown"`.

#### Scenario: Recovery run transitions through running
- **WHEN** a recovery run starts from `"Initializing"`
- **THEN** the system SHALL transition the recovery through `"Running"` to `"Succeeded"`, `"Failed"`, or `"Unknown"`.

### Requirement: Task inline run behavior
The system SHALL execute task `spec.inline` content line-by-line when a task with inline content is run.

#### Scenario: Inline task succeeds without failing lines
- **WHEN** a task with inline content has no line starting with `FAIL:` and is run from `"Initializing"`
- **THEN** the system SHALL set `status.state` to `"Succeeded"`.

#### Scenario: Inline task fails on FAIL line
- **WHEN** task inline line `<index>` starts with `FAIL:` during run
- **THEN** the system SHALL set `status.state` to `"Failed"` and `status.detail` to `"command <index> failed: <reason>"`.

#### Scenario: Inline task does not roll back earlier commands
- **WHEN** a task inline run reaches a failing line after earlier successful lines
- **THEN** the system SHALL preserve the failure result without attempting rollback semantics.

#### Scenario: Bundle task succeeds in simulated execution
- **WHEN** a task with `spec.bundleRef` is run from `"Initializing"`
- **THEN** the system SHALL set `status.state` to `"Succeeded"`.

### Requirement: Snapshot run behavior
The system SHALL execute snapshot resources according to the referenced mesh stability at run time.

#### Scenario: Snapshot run succeeds for stable mesh
- **WHEN** a snapshot references a mesh whose `status.stable` is `true` at run time
- **THEN** the system SHALL set `status.state` to `"Succeeded"` and set a stable, non-empty `status.storageRef`.

#### Scenario: Snapshot run becomes unknown for unstable mesh
- **WHEN** a snapshot references a mesh whose `status.stable` is `false` at run time
- **THEN** the system SHALL set `status.state` to `"Unknown"` and set `status.detail` to a non-empty string.

### Requirement: Recovery run behavior
The system SHALL execute recovery resources according to the referenced mesh stability at run time.

#### Scenario: Recovery run succeeds for stable mesh
- **WHEN** a recovery references a mesh whose `status.stable` is `true` at run time
- **THEN** the system SHALL set `status.state` to `"Succeeded"`.

#### Scenario: Recovery run becomes unknown for unstable mesh
- **WHEN** a recovery references a mesh whose `status.stable` is `false` at run time
- **THEN** the system SHALL set `status.state` to `"Unknown"` and set `status.detail` to a non-empty string.

### Requirement: Snapshot deletion dependency protection
The system SHALL reject `snapshot delete` when one or more recovery resources reference that snapshot.

#### Scenario: Snapshot delete blocked by dependent recovery
- **WHEN** the user deletes a snapshot that is referenced by at least one recovery through `spec.snapshotRef`
- **THEN** the system SHALL NOT delete the snapshot and SHALL report field `metadata.name` with type `conflict`.

#### Scenario: Snapshot delete conflict names dependent recoveries
- **WHEN** snapshot deletion is blocked by dependent recoveries
- **THEN** the error message SHALL name the dependent recovery resources.

### Requirement: One-shot status output
The system SHALL use the exact phase names `"Initializing"`, `"Running"`, `"Succeeded"`, `"Failed"`, and `"Unknown"` in task, snapshot, and recovery status output.

#### Scenario: Task terminal phases
- **WHEN** a task reaches a terminal phase
- **THEN** `status.state` SHALL be `"Succeeded"` or `"Failed"`.

#### Scenario: Snapshot terminal phases
- **WHEN** a snapshot reaches a terminal phase
- **THEN** `status.state` SHALL be `"Succeeded"`, `"Failed"`, or `"Unknown"`.

#### Scenario: Recovery terminal phases
- **WHEN** a recovery reaches a terminal phase
- **THEN** `status.state` SHALL be `"Succeeded"`, `"Failed"`, or `"Unknown"`.

#### Scenario: Detail appears only for failed or unknown states
- **WHEN** a task, snapshot, or recovery output includes `status.detail`
- **THEN** `status.state` SHALL be `"Failed"` or `"Unknown"`.

#### Scenario: Storage reference appears only for succeeded snapshots
- **WHEN** a task, snapshot, or recovery output includes `status.storageRef`
- **THEN** the resource SHALL be a snapshot with `status.state` equal to `"Succeeded"`.

### Requirement: One-shot JSON output and errors
The system SHALL print successful task, snapshot, and recovery command results as JSON to stdout and SHALL use the established JSON error shape for all validation, parse, duplicate, not-found, immutable, and dependency errors.

#### Scenario: Create describe update and run return full resource
- **WHEN** `create`, `describe`, `update`, or `run` succeeds for a task, snapshot, or recovery
- **THEN** the system SHALL print the full resource including `metadata.name`, `spec`, and `status.state`.

#### Scenario: Delete returns confirmation object
- **WHEN** a task, snapshot, or recovery is deleted successfully
- **THEN** the system SHALL print a JSON object containing a non-empty `message` and `metadata.name`.

#### Scenario: Error object shape
- **WHEN** any task, snapshot, or recovery validation, parse, duplicate, not-found, immutable, or dependency error occurs
- **THEN** the system SHALL print an object with `errors`, where each error includes `field`, `message`, and `type`.

#### Scenario: Error order is not contractual
- **WHEN** multiple task, snapshot, or recovery errors are returned
- **THEN** callers SHALL NOT rely on the order of errors in the `errors` array.
