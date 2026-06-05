## Why

A CLI tool (`meshctl.py`) is needed to manage mesh resources from YAML spec files, providing create/list/describe/delete operations with strict validation and structured JSON output. This is a greenfield implementation with no existing code.

## What Changes

- Add `meshctl.py` — the CLI entry point supporting `mesh create`, `mesh list`, `mesh describe`, and `mesh delete` subcommands
- Read mesh resources from YAML files, apply field defaults, validate all constraints, and persist resources locally
- Print all output (success and errors) as JSON to stdout; nothing to stderr
- Enforce a strict resource schema: name format, instance count, resource quantities, migration strategy, forbidden fields

## Capabilities

### New Capabilities

- `mesh-management`: Full CRUD lifecycle for mesh resources — create from YAML, list summaries, describe full resource, delete by name — with validation, defaulting, and structured JSON output/errors

### Modified Capabilities

## Impact

- New file: `meshctl.py` at project root
- New dependency: `uv` project runtime (run via `uv run --project /app meshctl.py`)
- Local persistence store required (in-process or file-based) for mesh resources
- No external APIs or services; self-contained CLI tool
