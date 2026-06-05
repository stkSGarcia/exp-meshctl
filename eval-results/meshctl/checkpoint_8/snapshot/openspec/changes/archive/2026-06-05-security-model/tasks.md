## 1. Authentication — digest and credential fields

- [x] 1.1 Read `spec.access.authentication.digestAlgorithm` from the raw access block; validate it is one of `"SHA-256"`, `"SHA-384"`, `"SHA-512"` and append an `invalid` error if not
- [x] 1.2 Read `spec.access.credentialRef` from the raw access block; store as given (no validation beyond presence check)
- [x] 1.3 When `authentication.enabled` is `false`, check that `digestAlgorithm` is absent and `credentialRef` is absent; append a `forbidden` error for each that is present
- [x] 1.4 Default `digestAlgorithm` to `"SHA-256"` when auth is enabled and the field is absent

## 2. Permissions

- [x] 2.1 Read `spec.access.permissions.enabled` (default `false`)
- [x] 2.2 When `permissions.enabled` is `true`, require `spec.access.permissions.roles` to be a non-empty list; append `required` error on `spec.access.permissions.roles` if absent or empty
- [x] 2.3 Iterate roles: for each role missing or having an empty `name`, append `required` error on `spec.access.permissions.roles[<index>].name`
- [x] 2.4 Iterate roles: for each role missing or having an empty `permissions` array, append `required` error on `spec.access.permissions.roles[<index>].permissions`
- [x] 2.5 Check for duplicate role names across the roles list; append `duplicate` error on `spec.access.permissions.roles` if any duplicates exist

## 3. Encryption

- [x] 3.1 Read `spec.access.encryption.source` (default `"None"`); validate it is one of `"None"`, `"Secret"`, `"Service"`; append `invalid` error on `spec.access.encryption.source` if not
- [x] 3.2 Read `spec.access.encryption.clientMode` (default `"None"`); validate it is a recognized value; append `invalid` error on `spec.access.encryption.clientMode` if not
- [x] 3.3 Apply conditional `certRef` rules: required when `source="Secret"`, forbidden when `source="None"` or `"Service"`
- [x] 3.4 Apply conditional `certServiceRef` rules: required when `source="Service"`, forbidden when `source="None"` or `"Secret"`
- [x] 3.5 When `source="None"`, validate that `clientMode` is also `"None"`; append an error on `spec.access.encryption.clientMode` if not

## 4. Output — defaults and structure

- [x] 4.1 Build the `authentication` output dict: when auth enabled, include `enabled` and `digestAlgorithm`; when disabled, include only `enabled: false`
- [x] 4.2 Include `credentialRef` in the top-level `access` output when it was explicitly provided
- [x] 4.3 Build the `permissions` output dict: always include `enabled`; include `roles` only when `permissions.enabled` is `true` (and validation passed)
- [x] 4.4 Build the `encryption` output dict: always include `source` and `clientMode`; include `certRef` only when `source="Secret"`, `certServiceRef` only when `source="Service"`
- [x] 4.5 Assemble the full `spec.access` dict from authentication, permissions, and encryption sub-dicts and include it in the output spec

## 5. Error sort order

- [x] 5.1 After all validation, sort the errors list by `field` ascending then `type` ascending before returning

## 6. Spec update

- [x] 6.1 Archive the delta spec into `openspec/specs/mesh-management/spec.md` by syncing the change (run `/opsx:sync` when implementation is complete)
