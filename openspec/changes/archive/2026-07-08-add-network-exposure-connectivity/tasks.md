## 1. Connectivity Model

- [x] 1.1 In `meshctl.py`, add shared constants and helpers for exposure modes, allowed fields, default exposure ports, and connection detail calculation. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 1.2 In `meshctl.py`, update `normalize_mesh_for_create()` and related mesh normalization helpers to preserve valid `spec.exposure` data and default `spec.management.enabled` to `false`. [extends mesh-resource-management/add-mesh-lifecycle-topology]
- [x] 1.3 In `meshctl.py`, update `upgrade_stored_resource()` and `public_resource()` so legacy meshes gain default management state and derived connectivity status is recomputed or removed consistently. [extends mesh-resource-management/add-mesh-lifecycle-topology]

## 2. Validation

- [x] 2.1 In `meshctl.py`, validate required and invalid `spec.exposure.type` values with the required JSON error fields and types. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.2 In `meshctl.py`, reject exposure sub-fields that are forbidden for the selected mode using full `spec.exposure.<field>` dot-path errors. [extends mesh-resource-management/add-mesh-migration-strategies]
- [x] 2.3 In `meshctl.py`, validate exposure port, direct port, hostname, and annotations types while preserving Gateway annotations in public output. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 2.4 In `meshctl.py`, reject updates that change `spec.management.enabled` after creation with the exact immutable error message. [extends mesh-resource-management/add-mesh-lifecycle-topology]

## 3. Command Surface

- [x] 3.1 In `meshctl.py`, extend `build_parser()` and `main()` with `mesh shell <name>`. [extends mesh-resource-management/add-meshctl-mesh-crud]
- [x] 3.2 In `meshctl.py`, implement `mesh_shell()` beside `mesh_migrate()` with standard missing-mesh errors, no-exposure rejection, and connectionDetails-only success output. [extends one-shot-operations/add-one-shot-operations]

## 4. Tests

- [x] 4.1 In `tests/test_meshctl_cli.py`, add create and describe tests for omitted exposure, Gateway, DirectPort, Balancer, default ports, and Gateway annotations.
- [x] 4.2 In `tests/test_meshctl_cli.py`, add validation tests for missing exposure type, invalid exposure type, forbidden mode fields, invalid field types, and sorted JSON error output.
- [x] 4.3 In `tests/test_meshctl_cli.py`, add management endpoint tests for default disabled state, enabled status output, and immutable update rejection.
- [x] 4.4 In `tests/test_meshctl_cli.py`, add `mesh shell` tests for missing mesh, mesh without exposure, and successful connectionDetails-only output.
- [x] 4.5 Run `uv run pytest` and confirm the existing CLI regression suite passes.
