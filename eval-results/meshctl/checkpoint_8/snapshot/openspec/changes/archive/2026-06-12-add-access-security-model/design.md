## Context

Mesh resources already normalize core spec fields, apply create-time defaults, validate post-merge updates, persist canonical resources, and project public JSON for create, describe, update, and list commands. The current access handling is intentionally small: it defaults `spec.access.authentication.enabled` to `true` but does not validate authentication details, role permissions, encryption certificate source rules, or sorted access-related errors.

This change expands `spec.access` into a full security model while keeping it part of the existing mesh resource contract. It does not introduce a new resource type or external security provider integration; the CLI stores and returns declarative security configuration only.

## Goals / Non-Goals

**Goals:**

- Default omitted `spec.access` to the complete documented authentication, permissions, and encryption baseline.
- Validate authentication, permission roles, and encryption source/client-mode combinations during create and post-merge update validation.
- Preserve optional access fields only when explicitly set and applicable.
- Keep persisted mesh resources canonical so describe and update behavior remain stable across older stored resources.
- Sort JSON validation errors by `field`, then `type`.

**Non-Goals:**

- Implement actual credential lookup, certificate fetching, authorization enforcement, or cryptographic operations.
- Add new CLI subcommands for credentials, roles, or certificates.
- Change vault resource security behavior.
- Make JSON object key order contractual.

## Decisions

- Treat `spec.access` as part of `mesh-resource-management` rather than a separate capability. The fields are nested in mesh specs and affect mesh create, describe, update, validation, persistence, and public projection paths.
- Normalize access configuration through the same create/update pipeline used by resources, migration, and network fields. Create applies defaults; update deep-merges into the stored resource, then validates the resulting candidate without reapplying create-only defaults to omitted fields.
- Store only applicable fields in the canonical resource. Authentication disabled stores only `authentication.enabled`; digest algorithm and credential reference are forbidden in that state. Permission roles are emitted only when permissions are enabled. Encryption certificate references are emitted only for their matching source.
- Validate access after merge so update behavior matches the rest of mesh validation. This catches a stored valid configuration becoming invalid after a partial update, such as switching encryption source without supplying the matching certificate reference.
- Sort errors in `print_errors` before rendering so all commands using the shared JSON error path become deterministic. Existing callers that ignored error order remain compatible; tests can now assert ordered access errors.

## Risks / Trade-offs

- Older stored meshes may contain only `spec.access.authentication.enabled` or no `spec.access`. Mitigation: continue using stored-resource upgrade before describe/update and fill missing access defaults in that upgrade path.
- Deep-merge updates can leave fields that become forbidden after a mode switch, such as changing authentication to disabled while a stored digest algorithm remains. Mitigation: validate the post-merge candidate and require callers to clear or avoid forbidden fields according to the existing merge model.
- Sorting all errors changes previously non-contractual ordering. Mitigation: make ordering deterministic in the shared error output path and update tests that previously treated order as irrelevant only where useful.
- The checkpoint does not require exact message wording for some invalid combinations. Mitigation: assert field/type contracts in tests and keep messages concise but non-contractual where specified.
