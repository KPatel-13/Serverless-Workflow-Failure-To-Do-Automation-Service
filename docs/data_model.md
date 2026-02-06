# Data model (DynamoDB) —> (repo-level incidents)

## Purpose
Store To-Do tickets representing workflow failures so engineers can:
- see which repos currently have failures (open tickets)
- mark a repo as resolved (done)
- automatically stop repeated tickets from the same failure while a ticket is already open

## Assumptions
- Each producer repository has **one** workflow.
- Producers only report **status**: `success` or `failure`.
- We only create/update tickets for `status="failure"`.

## Table
**Table name:** `to-dos` (final name set by Terraform)  
**Primary key:** `id`

## Item fields

### Core ticket fields
- `id`:str UUID
- `status`:st ("open" | "done")
- `title`: str - e.g. "`org/repo` workflow failing"
- `description`: str — optional context (latest failure message/run URL - will vary depending on the error message)
- `createdAt`: DATE
- `updatedAt`: DATE
- `lastSeenAt`: DATE
- `occurrenceCount`: int default to 1

### Producer/workflow metadata
- `source`: str - e.g. "github-actions"
- `repo`: str - e.g. "org/repo"
- `workflowName`: str
- `runId`: str - latest run id
- `runUrl`: str - latest run url

### Event details (repo-level)
- `lastStatus` ("failure" | "success") -> will store "failure" events only
- `message`: str - optional summary from producer (latest)

### Lookup
- `fingerprint`: str - set to `repo`

## Anti-Duplication strategy (repo-level incident model)

### Fingerprint
- `fingerprint = repo`

Rationale: we want **at most one OPEN ticket per repo** representing the current “repo is failing” incident.

### Behaviour
if ingest event `status="failure"` for a repo:
- if an open ticket exists for that repo:
  - increment `occurrenceCount` (+=1)
  - set `lastSeenAt = now`
  - set `updatedAt = now`
  - update latest `runId/runUrl/message`
- else:
  - create a new ticket for that repo with `occurrenceCount = 1` (similiar to how a hash map is often used as a counter)

if ingest event `status="success"`:
- do nothing (no ticket created/updated)

### Repeated failure after resolution (v1 decision)
- If a ticket for that repo is `done` and a new failure arrives:
  - **reopen** the ticket (status -> `open`) and continue incrementing `occurrenceCount`

## Indexing (planned)
To find an open ticket by repo efficiently, adding 'additional' search criteria:
- `repo`
- `status`

Query pattern:
- `repo = <repo>` AND `status = "open"` → returns the single active ticket (if any)

