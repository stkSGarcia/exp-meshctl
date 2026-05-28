## ADDED Requirements

### Requirement: mesh shell command
The system SHALL support `meshctl mesh shell <name>` as a subcommand. It SHALL look up the named mesh and, if found and configured with exposure, print only the `connectionDetails` object to stdout — without a resource envelope.

#### Scenario: Successful shell output
- **WHEN** a mesh named `"my-mesh"` exists and has `spec.exposure` configured
- **THEN** stdout is the `connectionDetails` object, e.g. `{"host":"my-mesh","port":443,"protocol":"https"}`, with no surrounding `metadata`, `spec`, or `status` wrapper

---

### Requirement: mesh shell — mesh not found
When the named mesh does not exist, `mesh shell` SHALL use the standard not-found error shape.

#### Scenario: Missing mesh rejected
- **WHEN** `meshctl mesh shell <name>` is called for a name that does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: mesh shell — no exposure configured
When the named mesh exists but has no `spec.exposure`, `mesh shell` SHALL reject the request with a specific invalid error.

#### Scenario: No exposure configured
- **WHEN** `meshctl mesh shell <name>` is called and the mesh has no `spec.exposure`
- **THEN** output `{"errors":[{"field":"spec.exposure","type":"invalid","message":"mesh '<name>' has no exposure configured"}]}`
