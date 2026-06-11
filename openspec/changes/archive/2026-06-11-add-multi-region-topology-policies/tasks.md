## 1. Core Mesh Model

- [x] 1.1 Add constants and helpers for placement affinity values, region exposure values, encryption protocols, telemetry tag keys, and extension source validation.
- [x] 1.2 Normalize and persist optional `metadata.tags` as provided string key/value pairs.
- [x] 1.3 Add `spec.placement.affinity` defaulting and output projection so every successful mesh output includes placement defaults.
- [x] 1.4 Add `status.telemetryProbe` projection from `metadata.tags`, including enabled defaults, explicit disablement, and ordered label categories.

## 2. Multi-Region Topology

- [x] 2.1 Validate `spec.regions.local` requirements, local name, local expose type, and optional positive `maxRelayNodes`.
- [x] 2.2 Normalize and validate `spec.regions.local.encryption`, including protocol defaults, Gateway transport key store requirement, key store required fields, and missing trust store warnings.
- [x] 2.3 Normalize and validate `spec.regions.local.discovery`, including relay defaults, object/type validation, and heartbeat interval/timeout constraints.
- [x] 2.4 Preserve ordered `spec.regions.remotes` entries, omit unset optional fields, allow empty arrays, and reject later duplicate remote names.
- [x] 2.5 Add multi-region `DiscoveryRelayReady` and `RegionViewFormed` conditions, sorted with all conditions and excluded from `status.stable` calculation.

## 3. Operational Policies

- [x] 3.1 Enforce `LiveMigration` rejection with `spec.regions` on both create and update using the required field, type, and message.
- [x] 3.2 Add create and update handling for `spec.configBundleRef`, including omission preservation, null clearing, and transient `status.configRefresh` output only on changing update responses.
- [x] 3.3 Add ordered `spec.extensions` normalization and exactly-one `url` or `artifact` validation with optional `integrity`.
- [x] 3.4 Ensure warnings continue to appear only on successful mesh create/update responses and remain sorted with existing warning behavior.

## 4. Tests

- [x] 4.1 Update existing mesh output expectations for always-present `spec.placement` and `status.telemetryProbe`.
- [x] 4.2 Add tests for metadata tags and telemetry probe enabled, disabled, and ordered label projection.
- [x] 4.3 Add tests for placement defaults, accepted values, and invalid object/type/scope cases.
- [x] 4.4 Add tests for multi-region create output, local validation, encryption validation and warning behavior, discovery defaults, remote ordering, duplicate remote names, and region conditions.
- [x] 4.5 Add tests for create/update `LiveMigration` restriction with regions.
- [x] 4.6 Add tests for `configBundleRef` create validation, update preservation, null clearing, transient refresh output, and later describe omission.
- [x] 4.7 Add tests for extension ordering, optional integrity omission, and exactly-one source validation.

## 5. Verification

- [x] 5.1 Run the full test suite with `uv run pytest`.
- [x] 5.2 Run `openspec status --change "add-multi-region-topology-policies"` and confirm the change is apply-ready.
