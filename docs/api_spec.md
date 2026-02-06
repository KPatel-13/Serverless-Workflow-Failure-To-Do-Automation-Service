# API Specification — Workflow Failure → To-Do Service

This document defines the HTTP interface for the service.
It is the contract between:
- **Producer repos (multiple):** GitHub Actions workflows that emit failure events (will kick off this service)
- **This service:** API Gateway → Lambda → DynamoDB
- **Consumers:** UI / engineers updating tickets

## Environments
The contract is identical across environments; only base URL + secrets differ.
- Dev base URL: TBD (Terraform output)
- Prod base URL: TBD (Terraform output)

## Conventions

### Content type
All requests/responses use JSON

### Multi-repo support
The ingestion endpoint supports events from multiple repositories.
Requests MUST include `workflow.repo` so tickets can be made on behalf of the repo upon failures.

### Status filtering
Requests may include `status: "failure" | "success"`.
behaviour: only create/update tickets for `status="failure"`.
(Recommended operational approach: producer repos only POST failures using `if: failure()`.)

### Standard error format
All error responses MUST follow a format liek this:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable message",
    "requestId": "optional"
  }
}
