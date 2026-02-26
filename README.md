# Serverless-Workflow-Failure-To-Do-Automation-Service
EPA project for DevOps apprenticeship

# Serverless Workflow Failure → To-Do Automation Service

Automatically converts workflow failure events (e.g., CI/CD failures) into actionable To-Do “tickets” that can be viewed and resolved via a lightweight API and simple UI.

## Problem
Workflow failures are often discovered late (manual log checking or user reports). This project aims to improve awareness and tracking by:
- ingesting workflow failure events automatically
- deduplicating repeated failures into the same open ticket
- enabling users to view and resolve/unresolve tickets

## High-level architecture (v1)
**Inputs**
- Human users via a simple browser UI (frontend)
- Upstream workflows (simulated via GitHub Actions) sending failure events

**Processing**
- API Gateway (HTTP API) routes requests and handles CORS
- AWS Lambda (Python 3.11) validates requests, applies dedupe rules, and performs CRUD

**Storage**
- Database stores ticket records and workflow metadata

See: `docs/architecture.md`

## API contract (planned)
Target endpoints:
- `POST /workflow-failure` (requires header `X-Workflow-Secret`)
- `GET /todos` (optional `?status=open|done`)
- `PATCH /todos/{id}` (resolve/unresolve)
- Optional: `DELETE /todos/{id}` (later)

See: `docs/api-contract.md`

## Dedupe strategy (planned)
Repeated identical failures should update the existing OPEN ticket instead of creating duplicates:
- `occurrenceCount` increments
- `lastSeenAt` updates
- (Reopen behavior for resolved tickets can be decided later / documented as TBD)

See: `docs/data-model.md`
