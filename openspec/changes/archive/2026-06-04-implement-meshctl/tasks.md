## 1. Project Setup

- [x] 1.1 Create `pyproject.toml` with project metadata and PyYAML dependency
- [x] 1.2 Create `meshctl.py` entry file with CLI skeleton using `argparse` (`mesh` command with `create`, `list`, `describe`, `delete` subcommands)
- [x] 1.3 Implement file-based JSON store (read/write with atomic rename) at a well-known path

## 2. Input Parsing and Validation

- [x] 2.1 Implement YAML file loader using `yaml.safe_load`; return `parse` error on file-not-found or YAML error
- [x] 2.2 Validate top-level document structure (must be a mapping with `metadata` and `spec` keys)
- [x] 2.3 Implement `metadata.name` validation: required, non-null, non-empty, matches `^[a-z0-9][a-z0-9-]*[a-z0-9]$`, min length 2
- [x] 2.4 Implement recursive scan of `spec` for any key named `autoScaling` and emit `forbidden` error with full dot-path
- [x] 2.5 Implement `spec.instances` validation: positive integer, default `1`
- [x] 2.6 Implement `spec.runtime` validation: optional, must match `major.minor.patch` with non-negative integer parts
- [x] 2.7 Implement resource quantity parser: memory (integer with optional `Ki`/`Mi`/`Gi`/`Ti` suffix) and CPU (integer with optional `m` suffix)
- [x] 2.8 Implement `spec.resources.memory` validation: absent → default `{"limit":"1Gi","request":"1Gi"}`; present → `limit` required, `request` defaults to `limit`, `request` ≤ `limit`
- [x] 2.9 Implement `spec.resources.cpu` validation: absent → omit; present → `limit` required, `request` defaults to `limit`, `request` ≤ `limit`
- [x] 2.10 Implement `spec.access.authentication.enabled` default: `true`
- [x] 2.11 Implement `spec.migration.strategy` validation: default `"FullStop"`, only accepted value `"FullStop"`

## 3. Command Handlers

- [x] 3.1 Implement `mesh create -f <path>`: load YAML, run full validation, check duplicate name, persist, print full resource JSON
- [x] 3.2 Implement `mesh list`: read store, emit sorted array of `{"name":..., "status":{...}}` summaries (empty array when empty)
- [x] 3.3 Implement `mesh describe <name>`: look up name in store, print full resource JSON or `not_found` error
- [x] 3.4 Implement `mesh delete <name>`: look up name in store, remove it, print confirmation JSON or `not_found` error

## 4. Output Formatting

- [x] 4.1 Implement `print_json(obj)` helper that serializes to stdout with `json.dumps` and prints nothing to stderr
- [x] 4.2 Implement `error_response(errors)` that wraps error list in `{"errors":[...]}` and passes to `print_json`
- [x] 4.3 Ensure full resource output for create/describe includes all defaulted spec fields with `status.state = "Running"`
- [x] 4.4 Ensure delete output matches `{"message":"<non-empty>","metadata":{"name":"<string>"}}`

## 5. Verification

- [x] 5.1 Smoke-test `mesh create` with a minimal valid YAML file and verify JSON output
- [x] 5.2 Smoke-test `mesh list` (empty store, then after create)
- [x] 5.3 Smoke-test `mesh describe` (hit and miss)
- [x] 5.4 Smoke-test `mesh delete` (hit and miss)
- [x] 5.5 Verify validation errors: bad name, invalid instances, bad memory quantity, request > limit, forbidden `autoScaling`, duplicate name
- [x] 5.6 Verify default application: omitted memory defaults to `1Gi`/`1Gi`, omitted `authentication.enabled` is `true`, omitted `migration.strategy` is `"FullStop"`
