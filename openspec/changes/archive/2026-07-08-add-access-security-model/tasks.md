## 1. Access Normalization

- [x] 1.1 Define access constants for allowed authentication digest algorithms, encryption sources, and encryption client modes.
- [x] 1.2 Expand mesh create normalization to default omitted `spec.access` to authentication, permissions, and encryption defaults.
- [x] 1.3 Preserve applicable optional access fields only when explicitly provided.
- [x] 1.4 Update stored mesh upgrade behavior so existing resources receive missing access defaults before describe or update.

## 2. Access Validation

- [x] 2.1 Validate `spec.access` object shape and authentication enabled-state rules.
- [x] 2.2 Validate authentication digest algorithms and forbid digest or credential references when authentication is disabled.
- [x] 2.3 Validate permissions enabled-state rules, required roles, role names, role permissions, and duplicate role names.
- [x] 2.4 Validate encryption source, certificate reference requirements, forbidden certificate references, client modes, and source/client-mode compatibility.
- [x] 2.5 Ensure create and post-merge update validation both enforce the access rules.

## 3. Output And Errors

- [x] 3.1 Ensure mesh create and describe output include all applicable `spec.access` defaults.
- [x] 3.2 Ensure disabled authentication output contains only `authentication.enabled`.
- [x] 3.3 Ensure permission roles are output only when permissions are enabled.
- [x] 3.4 Ensure encryption certificate references are output only for their matching source.
- [x] 3.5 Sort JSON errors by `field`, then `type`, before printing.

## 4. Tests

- [x] 4.1 Add tests for default `spec.access` output on mesh create and describe.
- [x] 4.2 Add tests for authentication digest validation, disabled-authentication forbidden fields, and credential reference preservation.
- [x] 4.3 Add tests for permissions roles required fields and duplicate role names.
- [x] 4.4 Add tests for encryption source/client-mode validation and conditional certificate reference requirements.
- [x] 4.5 Add tests proving validation failures remain atomic on update.
- [x] 4.6 Add tests for deterministic JSON error ordering by `field`, then `type`.

## 5. Verification

- [x] 5.1 Run the meshctl test suite.
- [x] 5.2 Run OpenSpec validation for `add-access-security-model`.
