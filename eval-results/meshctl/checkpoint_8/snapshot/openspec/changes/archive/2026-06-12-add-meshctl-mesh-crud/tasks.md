## 1. Project Setup

- [x] 1.1 Create the `meshctl.py` entry point with `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` argument parsing.
- [x] 1.2 Add or confirm YAML parsing support needed by `mesh create`.
- [x] 1.3 Add test scaffolding that can run CLI commands with an isolated mesh store.

## 2. Persistence and Output

- [x] 2.1 Implement local mesh resource loading and saving with a test-isolatable store path.
- [x] 2.2 Implement success JSON output helpers that write only to stdout.
- [x] 2.3 Implement structured error output helpers with `errors[].field`, `errors[].message`, and `errors[].type`.

## 3. Create Flow

- [x] 3.1 Implement YAML file reading, parse failure handling, and root mapping validation for `mesh create`.
- [x] 3.2 Implement resource normalization and defaults for instances, memory request/limit, authentication enabled, and migration strategy.
- [x] 3.3 Preserve omitted fields that have no defaults, including runtime and CPU resources.
- [x] 3.4 Add new mesh status defaulting with `status.state` equal to `"Running"`.
- [x] 3.5 Reject duplicate mesh names without overwriting the existing persisted resource.

## 4. Validation

- [x] 4.1 Validate `metadata.name` required, minimum length, and format rules.
- [x] 4.2 Validate `spec.instances`, `spec.runtime`, and `spec.migration.strategy`.
- [x] 4.3 Validate memory and CPU limits, requests, accepted quantity formats, and request-not-greater-than-limit constraints.
- [x] 4.4 Recursively reject every `autoScaling` field under `spec` and report the full dot path.
- [x] 4.5 Ensure validation failures return documented error fields and types while leaving stderr empty.

## 5. Read and Delete Flows

- [x] 5.1 Implement `mesh describe <name>` to return the full persisted resource or a `not_found` error.
- [x] 5.2 Implement `mesh list` to return only `name` and `status.state` summaries sorted by name ascending.
- [x] 5.3 Implement `mesh delete <name>` to remove an existing resource and return a confirmation object.
- [x] 5.4 Ensure describe and delete return `metadata.name` `not_found` errors for missing resources.

## 6. Verification

- [x] 6.1 Add tests for successful create, describe, list, and delete flows.
- [x] 6.2 Add tests for defaulting behavior and fields without defaults remaining absent.
- [x] 6.3 Add tests for validation errors, parse errors, duplicate creates, not-found describe/delete, and forbidden `autoScaling`.
- [x] 6.4 Add tests that confirm JSON is printed to stdout and stderr remains empty.
- [x] 6.5 Run the full test suite and `openspec validate add-meshctl-mesh-crud`.
