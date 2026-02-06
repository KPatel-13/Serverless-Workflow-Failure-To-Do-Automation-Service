# Architecture

## Architecture diagram
![Serverless Workflow Failure → To-Do Automation Service architecture](./EPA%20Architecture%20diagram.png)

## Overview
This service converts workflow failures from multiple producer repositories into actionable To-Do tickets.

### Inputs
- **Producer repos (GitHub Actions)**: On failure, a workflow sends a payload with:
  - `repo`, `status="failure"`, and optional context like `errorMessage`, `runUrl`
- **UI (engineers/users)**: Users interact with tickets via:
  - `GET /to-dos` (list)
  - `PATCH /to-dos/{id}` (resolved/unresolved)

### Processing
- **API Gateway** exposes HTTPS endpoints and handles routing/CORS.
- **Lambda (Python 3.11)**:
  - validates requests
  - checks for ingestion
  - applies duplication handling (repo-level “one open ticket per error message under repo”)
  - updates DynamoDB (`occurrenceCount`, `lastSeenAt`, latest error context)

### Storage
- **DynamoDB** stores ticket records (open/done), timestamps, occurrence counts, and latest error context.

### Observability
- **CloudWatch Logs** receive application logs emitted by Lambda (requestId, repo, action taken, errors).
