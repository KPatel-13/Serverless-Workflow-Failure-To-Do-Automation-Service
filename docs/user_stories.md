# User stories (POV: Other engineers within my team)

These stories are written from the perspective of engineers within my team who need clear visibility of workflow failures and a simple way to manage the resulting operational workload.

## Must-have

### 1) Workflow failure ingestion → create an actionable ticket
**Story:** I want workflow failures to be reported to a single endpoint so they become trackable To-Do tickets instead of just getting lost in logs.

**Acceptance (Given/When/Then):**
- Given a workflow sends a failure request in JSON format
- When the request is accepted by the API
- Then the API returns `202 Accepted`
- And a ticket is stored with `status="open"`
- And the ticket includes the workflow and failure context

---

### 2) Duplication handling for repeated failures so we do not drown in noise
**Story:** I want repeated identical failures to update one existing open ticket so I can focus on fixing the problem rather than looking through multiple duplicates whixh would clog the page.

**Acceptance:**
- Given an `OPEN` ticket exists with the same failure fingerprint
- When the same failure is received again
- Then the existing ticket is updated by incrementing `occurrenceCount`
- And `lastSeenAt` is updated
- And no new duplicate ticket is created

---

### 3) View open and resolved tickets to manage operational workload
**Story:** I want to view a list of open and resolved tickets so I can prioritise and track what needs attention.

**Acceptance:**
- Given tickets exist
- When the UI or API requests tickets
- And results can be filtered by ticket status such as `open` or `done`

---

### 4) Resolve tickets to reflect the real state of work
**Story:** I want to mark tickets as resolved so the ticket list stays accurate.

**Acceptance:**
- Given a ticket exists
- When `PATCH /todos/{id}` is called with `{"status":"done"}`
- Then the ticket becomes `done`

---

### 5) Reopen resolved tickets if the same failure happens again
**Story:** I want a previously resolved ticket to reopen if the same failure repeats so the backlog reflects the current real problem state.

**Acceptance:**
- Given a matching ticket exists with `status="done"`
- When the same failure is received again
- Then the ticket is changed back to `open`
- And `occurrenceCount` is incremented
- And `lastSeenAt` is updated

---

### 6) Protect the workflow-failure endpoint from unauthorised requests
**Story:** I want the workflow-failure endpoint to require a secret so only trusted workflow sources can create or update tickets.

**Acceptance:**
- Given a request is sent to `/workflow-failure`
- When the `X-Workflow-Secret` header is missing or incorrect
- Then the API returns `403 Forbidden`
- And no ticket is created or updated
- When the correct secret is supplied
- Then the request can be processed normally

---


### 7) Show recurrence and latest run context in the UI
**Story:** I want to see how many times a failure has happened and when it was last seen so I can judge urgency more easily.

**Acceptance:**
- Given a ticket has repeated failures
- When it is shown in the UI
- Then `occurrenceCount` is displayed
- And `lastSeenAt` is displayed
- And `runUrl` is shown when present

---

### 8) Log retention to control cost while keeping enough troubleshooting history
**Story:** I want logs to be retained for a limited period so the service remains cost-effective while still supporting investigation.

**Acceptance:**
- Given application and API logs are created
- Then log retention is configured
- And logs are not stored indefinitely
- And the chosen retention period supports troubleshooting needs
