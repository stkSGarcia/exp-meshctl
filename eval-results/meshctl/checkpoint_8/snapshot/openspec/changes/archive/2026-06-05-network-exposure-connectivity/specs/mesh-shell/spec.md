## ADDED Requirements

### Requirement: mesh shell command routing
The tool SHALL support `meshctl mesh shell <name>` and SHALL route to the shell handler with the given mesh name.

#### Scenario: Valid shell subcommand dispatched
- **WHEN** the user runs `meshctl mesh shell <name>`
- **THEN** the shell handler is invoked with the given name

---

### Requirement: mesh shell — not found
When the named mesh does not exist, `mesh shell` SHALL produce the standard `not_found` error shape.

#### Scenario: Unknown mesh
- **WHEN** `meshctl mesh shell <name>` is called with a name that does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: mesh shell — no exposure rejection
When the named mesh exists but has no `spec.exposure` configured, `mesh shell` SHALL be rejected.

#### Scenario: Mesh with no exposure
- **WHEN** `meshctl mesh shell <name>` is called and the mesh has no `spec.exposure`
- **THEN** output `{"errors":[{"field":"spec.exposure","type":"invalid","message":"mesh '<name>' has no exposure configured"}]}`

---

### Requirement: mesh shell — success output
When the named mesh exists and has exposure configured, `mesh shell` SHALL output the `connectionDetails` object directly, without a resource envelope.

#### Scenario: Mesh with exposure
- **WHEN** `meshctl mesh shell <name>` is called and the mesh has exposure configured
- **THEN** output only the `connectionDetails` object (e.g., `{"host":"...","port":443,"protocol":"https"}`) with no surrounding `metadata`, `spec`, or `status` wrapper

### Related Scenarios

**`implement-meshctl/mesh-management/cli-entry-point/unknown-subcommand`** — When the user runs `meshctl.py mesh <unknown>`, the tool exits with a non-success indicator. _(matched on: network_exposure:mesh shell command)_
