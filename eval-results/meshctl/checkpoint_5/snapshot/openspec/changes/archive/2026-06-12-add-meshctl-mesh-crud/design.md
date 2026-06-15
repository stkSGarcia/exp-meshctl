## Context

The repository currently contains the checkpoint contract and OpenSpec planning files, but no implementation. The required entry point is `meshctl.py`, invoked as `uv run --project /app meshctl.py mesh <operation> [arguments]`. The tool manages mesh resources defined by YAML input and prints JSON to stdout for both success and error responses.

The implementation should be small enough to keep in `meshctl.py` initially, with helper functions for parsing, defaulting, validation, storage, and output. If the code grows during implementation, helpers can be moved into focused modules without changing the CLI contract.

## Goals / Non-Goals

**Goals:**

- Implement `mesh create`, `mesh list`, `mesh describe`, and `mesh delete`.
- Parse one YAML document for create operations.
- Apply all documented defaults before persisting and returning resources.
- Validate names, instance counts, runtime versions, resource quantities, migration strategy, duplicate names, missing names, not-found resources, and forbidden `spec.autoScaling` fields.
- Persist resources across commands in a local store suitable for CLI tests.
- Print JSON to stdout and keep stderr empty for both success and error responses.

**Non-Goals:**

- Support multiple YAML documents in a single input file.
- Add mesh update, patch, status transitions, async operations, or autoscaling support.
- Implement compatibility with external control planes or remote APIs.
- Guarantee a stable JSON key order or exact error ordering beyond the documented contract.

## Decisions

1. Use `argparse` or equivalent standard-library CLI parsing for the `mesh` command group.

   Rationale: The required command surface is small and does not need an external CLI framework. This keeps setup minimal for the checkpoint.

   Alternative considered: Add a CLI framework. Rejected because it adds dependency and behavior surface without clear benefit for four commands.

2. Store mesh resources as JSON in a deterministic local data file.

   Rationale: Commands must persist resources across invocations. A JSON document keyed by mesh name is easy to inspect, update, and reset in tests. The implementation can choose a path relative to the project or an environment-overridable path so tests can isolate state.

   Alternative considered: In-memory storage. Rejected because it would not survive separate CLI invocations. SQLite is unnecessary for the small resource model.

3. Normalize and default input into the persisted resource shape before validation-dependent persistence.

   Rationale: Successful create and describe output must include defaulted fields, while omitted fields without defaults must remain absent. Keeping one canonical persisted representation makes describe and list behavior simple.

   Alternative considered: Persist raw input and default on read. Rejected because it duplicates defaulting logic and risks inconsistent output.

4. Represent validation failures as structured error dictionaries and aggregate them before output.

   Rationale: Error order is not part of the contract, but callers need `field`, `message`, and `type`. Collecting errors supports reporting multiple independent validation failures in one response.

   Alternative considered: Raise exceptions for the first validation error. Rejected because it provides a poorer user experience and makes error aggregation harder.

5. Parse resource quantities into comparable integer base units.

   Rationale: Memory and CPU requests must not exceed limits. Parsing memory units into bytes and CPU units into millicores allows simple numeric comparison while preserving original strings in output.

   Alternative considered: Compare raw strings. Rejected because unit suffixes make lexical comparison incorrect.

## Risks / Trade-offs

- Local store path conflicts between tests or user runs -> Mitigate by allowing tests to run with an isolated working directory or environment-configured store path.
- YAML parser availability may vary -> Mitigate by declaring or using the project’s available YAML dependency and mapping parser/read failures to a `parse` JSON error.
- Aggregated validation can accidentally continue through malformed intermediate structures -> Mitigate by validating document and object types before descending into nested fields.
- Forbidden `autoScaling` requires nested path reporting under `spec` -> Mitigate with a recursive scan that reports the full dot path for every matching field name under `spec`.
