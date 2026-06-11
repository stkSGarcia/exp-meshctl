## Context

`meshctl.py` currently manages mesh resources with YAML-backed create/update flows, a JSON store selected by `MESHCTL_STORE`, shared validation helpers, computed lifecycle status, and public JSON shaping through `public_resource()`. Mesh status already changes as runtime, scaling, and migration workflows advance, but there is no first-class connection endpoint model for an operator to use after creating or describing a mesh.

The new connectivity behavior belongs inside the existing mesh resource model. `spec.exposure` is optional, and when present it determines `status.connectionDetails`. `spec.management.enabled` is a create-time flag that controls a separate management endpoint status object. `mesh shell` is a lookup command over the same persisted mesh state rather than an interactive shell runner.

## Goals / Non-Goals

**Goals:**
- Add exposure validation and output for `Gateway`, `DirectPort`, and `Balancer` modes.
- Preserve mode-specific exposure fields in successful output and reject fields that are not allowed for the selected mode.
- Compute deterministic connection details during create, describe, and shell output without persisting duplicated status data unnecessarily.
- Add management endpoint defaults, output, and immutability checks.
- Add `mesh shell <name>` with the standard missing mesh error and an exposure-specific invalid error.
- Reuse existing JSON error shape, sorting, YAML parsing, store compatibility, and public resource normalization patterns.

**Non-Goals:**
- Open an actual interactive network shell or subprocess.
- Provision gateways, node ports, load balancers, DNS records, TLS assets, or any external infrastructure.
- Validate real hostname ownership, port availability, or Kubernetes annotation semantics.
- Add management endpoint commands beyond exposing computed management connection details.

## Decisions

### Compute connectivity details from spec during public output

Add helper functions that derive `status.connectionDetails` and `status.managementConnectionDetails` from the mesh `metadata.name` and normalized `spec`. Call them from `public_resource()` after status refresh so create and describe stay consistent even for older stored resources.

Alternative considered: persist connection details at create/update time. Deriving them avoids stale status if future normalization upgrades stored resources, and the values are deterministic from the spec.

### Normalize exposure as an optional spec object

Keep `spec.exposure` absent when omitted. When present, require a non-empty `type` and preserve only fields valid for the selected mode. Gateway allows `hostname` and `annotations`; DirectPort allows `port` and `directPort`; Balancer allows `port`.

Alternative considered: default every mesh to a private exposure mode. The checkpoint explicitly says omitted exposure means no external access and no `status.connectionDetails`, so absence should remain meaningful.

### Use small policy tables for exposure modes

Represent each mode's allowed fields and connection detail derivation in centralized mappings or helper branches. This keeps forbidden-field validation, output preservation, and host/port computation aligned.

Alternative considered: scatter mode checks through normalization and output functions. That would make it easier for validation and computed status to drift.

### Treat management endpoint enablement as immutable

Default `spec.management.enabled` to `false` at create, validate it as a boolean when provided, and compare the stored and candidate values on update. Changing the value after creation returns the documented immutable error.

Alternative considered: make the entire `spec.management` object immutable. The checkpoint only marks `enabled` as immutable, so the implementation should keep the narrower rule.

### Implement `mesh shell` as a connection detail read

Add a mesh subcommand that loads and upgrades the named mesh, returns the standard `metadata.name` `not_found` error when missing, rejects unexposed meshes with the documented `spec.exposure` invalid error, and prints only the `connectionDetails` object on success.

Alternative considered: return the whole mesh resource with a selected status field. The checkpoint requires the connection details object without the resource envelope.

## Risks / Trade-offs

- Exposure validation can accidentally leave disallowed fields in persisted specs -> Validate forbidden fields before saving and add tests for every mode-specific forbidden path.
- Deriving connection details at output time can diverge from create-time storage expectations -> Keep derivation deterministic and test create output, describe output, and shell output from the same stored mesh.
- The default host and port values are exercise-specific, not infrastructure-backed -> Encapsulate defaults as constants so tests and future changes have one place to update.
- Management immutability interacts with deep merge updates -> Compare the post-merge candidate against the stored resource so omitted management fields keep the stored value while actual changes are rejected.
