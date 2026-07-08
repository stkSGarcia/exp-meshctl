## Why

`meshctl.py` needs a clear, testable contract for managing mesh resources from YAML definitions. This change captures the required CRUD behavior, validation rules, defaulting, persistence, and JSON output expected by the checkpoint.

## What Changes

- Add a `mesh` command group with `create`, `list`, `describe`, and `delete` operations.
- Accept one YAML document for `create`, apply documented defaults, validate fields, persist valid resources, and reject duplicate mesh names.
- Return successful command output as JSON on stdout with no stderr output.
- Return structured JSON error objects on stdout for parse, validation, duplicate, and not-found failures.
- Ensure mesh summaries list in case-sensitive lexicographic order by resource name.
- Forbid any `autoScaling` field under `spec`.

## Capabilities

### New Capabilities

- `mesh-resource-management`: Defines the mesh CLI resource model, operations, validation, defaulting, persistence behavior, and JSON output contract.

### Modified Capabilities

None.

## Impact

- Affected code: `meshctl.py` entry point and any supporting modules added for parsing, validation, persistence, or command handling.
- Affected interface: `uv run --project /app meshctl.py mesh <operation> [arguments]`.
- Dependencies: YAML parsing support must be available for reading mesh specs.
- Tests should cover successful CRUD flows, defaulted output, validation errors, parse errors, duplicate creates, not-found operations, and sorted list output.
