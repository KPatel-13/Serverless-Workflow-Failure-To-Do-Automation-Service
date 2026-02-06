# User stories (POV: Other engineers within my team)

These stories are written from the perspective of senior engineers within my team.

## Must-have

### 1) Workflow failure ingestion → create an actionable ticket
**Story:** I want workflow failures to be reported to a single endpoint so they become trackable To-Do tickets instead of just getting lost in logs.

**Acceptance (Given/When/Then):**
- Given a workflow sends a request with e.g. a JSON
- Then the API returns `202 Accepted`
- And a ticket is stored with somethign like `status="open"` and includes the workflow and the  failure context

---

### 2) Duplication handling for repeated failures so we don’t drown in noise
**Story:** I want repeated identical failures to update one existing open ticket so I can focus on fixing the problem rather than looking through multiple duplicates of the same error.

**Acceptance:**
- Given an OPEN ticket exists with the same identifier
- When the same failure is received again
- Then the existing ticket is updated by incrementing the occurence
- And no new duplicate ticket is created

---

### 3) View open/resolved tickets to manage operational workload
**Story:** I want to view a list of open and resolved tickets so I can prioritise and track what needs attention.

**Acceptance:**
- Given tickets exist
- Then the API returns `OK` and a JSON list of tickets
- And filter results based on ticket status (to-do or resolved)

---

### 4) Resolve / unresolve to reflect the real state of work
**Story:** I want to mark tickets as resolved (and re-open if needed) so the ticket list stays accurate.

**Acceptance:**
- Given a ticket exists
- Then the ticket becomes `done` and `updatedAt` changes
- When called with `{"status":"open"}`
- Then the ticket becomes `open` and `updatedAt` changes

---

### 5) Only failures create tickets (avoid false work)
**Story:** I want only failure events to create/update tickets so the system doesn’t generate noise for successful runs as theres no need to alarm if the workflow hasnt failed.

**Acceptance:**
- Given the ingestion endpoint is for failures only
- When workflows succeed
- Then no ticket is created (success reporting is out of scope for v1)

## Should-have (later sprints)
- CloudWatch alarms for: Lambda errors
- Log retention 7–14 days to control cost
- Decide behaviour if a resolved ticket repeats (reopen vs create new) — TBC (Need a follow up with stakeholders)

## Could-have (nice-to-have)
- Delete/hide to-do's once they are done
- Batch ingestion endpoint (send multiple failures in one request)
