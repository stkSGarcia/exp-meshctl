## Context

Greenfield Python CLI (`meshctl.py`) that manages mesh resources. Invoked via `uv run --project /app meshctl.py mesh <operation> [args]`. No external services — all persistence is local. Output is always JSON to stdout; nothing to stderr.

## Goals / Non-Goals

**Goals:**
- Implement the four mesh operations: `create`, `list`, `describe`, `delete`
- Apply defaults, validate fully, and persist resources across CLI invocations
- Structured JSON error output matching the specified error schema
- Single self-contained Python file with a `uv`-compatible project layout

**Non-Goals:**
- Authentication or authorization
- Remote persistence or network I/O
- Concurrent access safety
- Pagination or filtering for `list`

## Decisions

### Language and runtime: Python via uv
The entry point is `uv run --project /app meshctl.py`, which implies a `pyproject.toml` at the project root. Standard library only (no third-party deps beyond PyYAML for YAML parsing). Keeps the tool portable and fast to install.

**Alternatives considered:** Shell script — rejected because YAML parsing and JSON output with full validation logic is unwieldy in shell.

### Persistence: single JSON file on disk
Resources are stored in a local JSON file (e.g., `~/.meshctl/store.json` or `/app/store.json`). On each command, read the file, perform the operation, write back. Simple and inspectable.

**Alternatives considered:** SQLite — adds complexity for a small key-value store. In-memory — data lost between invocations, breaking `list` and `describe`.

### Validation strategy: collect all errors, return together
Validate all fields before attempting persistence. Collect every violation and return them in a single `{"errors": [...]}` response. Error order is explicitly not part of the contract.

**Alternatives considered:** Fail-fast on first error — rejected because the spec does not require it and collecting all errors is more useful to callers.

### CLI parsing: stdlib `argparse`
Subcommand tree: `mesh {create,list,describe,delete}`. `create` takes `-f <path>`; `describe` and `delete` take `<name>` positional.

### Output: always `json.dumps` to stdout, `sys.exit(0)`
Even error responses exit 0 — exit codes are not part of the contract and error JSON is the communication channel.

**Alternatives considered:** Non-zero exit on error — not specified, and callers must parse JSON anyway.

## Risks / Trade-offs

- **File-based store is not atomic** → Mitigation: write to a temp file then rename (atomic on POSIX). Acceptable for single-user CLI.
- **PyYAML loads arbitrary Python objects by default** → Mitigation: use `yaml.safe_load` throughout.
- **Store path hardcoded** → Mitigation: use a well-known path relative to the project directory (`/app/store.json`), acceptable for the constrained execution environment.
