## ADDED Requirements

### Requirement: Exposure block is optional
The mesh spec SHALL support an optional `spec.exposure` block. When `spec.exposure` is absent, no external access is configured and `status.connectionDetails` SHALL be absent from all outputs.

#### Scenario: No exposure — connectionDetails absent
- **WHEN** a mesh is created or described with no `spec.exposure`
- **THEN** `status.connectionDetails` is absent from the output

---

### Requirement: Exposure type is required when exposure block is present
When `spec.exposure` is present, `spec.exposure.type` SHALL be required and SHALL be one of `"Gateway"`, `"DirectPort"`, or `"Balancer"`. Missing, null, or empty values and unrecognized values SHALL each produce an error.

#### Scenario: Missing exposure type
- **WHEN** `spec.exposure` is present but `spec.exposure.type` is absent or null
- **THEN** output error `{"field":"spec.exposure.type","type":"required","message":"<msg>"}`

#### Scenario: Invalid exposure type
- **WHEN** `spec.exposure.type` is a non-empty string that is not one of the three valid values
- **THEN** output error `{"field":"spec.exposure.type","type":"invalid","message":"<msg>"}`

#### Scenario: Valid exposure types accepted
- **WHEN** `spec.exposure.type` is `"Gateway"`, `"DirectPort"`, or `"Balancer"`
- **THEN** the type value is accepted and no type error is produced

---

### Requirement: Gateway mode field rules
When `spec.exposure.type` is `"Gateway"`, the allowed sub-fields are `hostname` (string, optional) and `annotations` (map of string to string, optional). All other sub-fields under `spec.exposure` are forbidden.

#### Scenario: Gateway with valid fields accepted
- **WHEN** `spec.exposure.type` is `"Gateway"` and only `hostname` and/or `annotations` are present
- **THEN** the exposure block is accepted

#### Scenario: Gateway forbidden field rejected
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.port` is present
- **THEN** output error `{"field":"spec.exposure.port","type":"forbidden","message":"<msg>"}`

#### Scenario: Gateway forbidden directPort rejected
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.directPort` is present
- **THEN** output error `{"field":"spec.exposure.directPort","type":"forbidden","message":"<msg>"}`

#### Scenario: Gateway annotations mapping preserved
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.annotations` contains key-value string pairs
- **THEN** the annotations mapping is preserved as-is in the output

---

### Requirement: DirectPort mode field rules
When `spec.exposure.type` is `"DirectPort"`, the allowed sub-fields are `port` (integer, has a default) and `directPort` (integer, optional). All other sub-fields under `spec.exposure` are forbidden.

#### Scenario: DirectPort with valid fields accepted
- **WHEN** `spec.exposure.type` is `"DirectPort"` and only `port` and/or `directPort` are present
- **THEN** the exposure block is accepted

#### Scenario: DirectPort forbidden hostname rejected
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.hostname` is present
- **THEN** output error `{"field":"spec.exposure.hostname","type":"forbidden","message":"<msg>"}`

#### Scenario: DirectPort forbidden annotations rejected
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.annotations` is present
- **THEN** output error `{"field":"spec.exposure.annotations","type":"forbidden","message":"<msg>"}`

---

### Requirement: Balancer mode field rules
When `spec.exposure.type` is `"Balancer"`, the only allowed sub-field is `port` (integer, has a default). All other sub-fields under `spec.exposure` are forbidden.

#### Scenario: Balancer with port accepted
- **WHEN** `spec.exposure.type` is `"Balancer"` and only `port` is present
- **THEN** the exposure block is accepted

#### Scenario: Balancer forbidden hostname rejected
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.hostname` is present
- **THEN** output error `{"field":"spec.exposure.hostname","type":"forbidden","message":"<msg>"}`

#### Scenario: Balancer forbidden annotations rejected
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.annotations` is present
- **THEN** output error `{"field":"spec.exposure.annotations","type":"forbidden","message":"<msg>"}`

#### Scenario: Balancer forbidden directPort rejected
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.directPort` is present
- **THEN** output error `{"field":"spec.exposure.directPort","type":"forbidden","message":"<msg>"}`

---

### Requirement: Connection details computed for Gateway mode
When `spec.exposure.type` is `"Gateway"`, `status.connectionDetails` SHALL be computed as: `host` = `spec.exposure.hostname` if set, else a default hostname; `port` = `443`; `protocol` = `"https"`.

#### Scenario: Gateway connectionDetails with explicit hostname
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.hostname` is `"my.host.example"`
- **THEN** `status.connectionDetails` is `{"host":"my.host.example","port":443,"protocol":"https"}`

#### Scenario: Gateway connectionDetails with default hostname
- **WHEN** `spec.exposure.type` is `"Gateway"` and `spec.exposure.hostname` is absent
- **THEN** `status.connectionDetails.host` is a non-empty default string and `port` is `443`

---

### Requirement: Connection details computed for DirectPort mode
When `spec.exposure.type` is `"DirectPort"`, `status.connectionDetails` SHALL be computed as: `host` = the mesh name; `port` = `spec.exposure.directPort` if set, else the default port value; `protocol` = `"https"`.

#### Scenario: DirectPort connectionDetails with explicit directPort
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.directPort` is `8443`
- **THEN** `status.connectionDetails` is `{"host":"<name>","port":8443,"protocol":"https"}`

#### Scenario: DirectPort connectionDetails with default port
- **WHEN** `spec.exposure.type` is `"DirectPort"` and `spec.exposure.directPort` is absent
- **THEN** `status.connectionDetails.host` is the mesh name, `port` is the default, and `protocol` is `"https"`

---

### Requirement: Connection details computed for Balancer mode
When `spec.exposure.type` is `"Balancer"`, `status.connectionDetails` SHALL be computed as: `host` = `"<name>-external"`; `port` = `spec.exposure.port` if set, else the default port value; `protocol` = `"https"`.

#### Scenario: Balancer connectionDetails with explicit port
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.port` is `9443`
- **THEN** `status.connectionDetails` is `{"host":"<name>-external","port":9443,"protocol":"https"}`

#### Scenario: Balancer connectionDetails with default port
- **WHEN** `spec.exposure.type` is `"Balancer"` and `spec.exposure.port` is absent
- **THEN** `status.connectionDetails.host` is `"<name>-external"`, `port` is the default, and `protocol` is `"https"`
