## ADDED Requirements

### Requirement: mesh shell command routing
`meshctl mesh shell <name>` SHALL be routed to the shell handler.

(adapts mesh-management/cli-entry-point)

#### Scenario: Shell subcommand dispatched
- **WHEN** the user runs `meshctl.py mesh shell <name>`
- **THEN** the shell handler is invoked with the given mesh name

---

### Requirement: mesh shell not-found error
When the named mesh does not exist, `mesh shell` SHALL output the standard not-found error shape.

(adapts mesh-migrate-command/mesh-migrate-error-mesh-not-found)

#### Scenario: Shell on nonexistent mesh
- **WHEN** `mesh shell` is called with a name that does not exist
- **THEN** output `{"errors":[{"field":"metadata.name","type":"not_found","message":"<msg>"}]}`

---

### Requirement: mesh shell requires exposure
When the named mesh has no `spec.exposure` configured, `mesh shell` SHALL reject the request.

- `field = "spec.exposure"`
- `type = "invalid"`
- `message = "mesh '<name>' has no exposure configured"`

#### Scenario: Shell on mesh without exposure
- **WHEN** `mesh shell` is called for a mesh that has no `spec.exposure`
- **THEN** output `{"errors":[{"field":"spec.exposure","type":"invalid","message":"mesh '<name>' has no exposure configured"}]}`

---

### Requirement: mesh shell success output
On success, `mesh shell` SHALL output only the `connectionDetails` object — without a resource envelope.

#### Scenario: Shell on mesh with exposure
- **WHEN** `mesh shell` is called for a mesh that has `spec.exposure` configured
- **THEN** output only the `status.connectionDetails` object (e.g., `{"host":"...","port":443,"protocol":"https"}`)

