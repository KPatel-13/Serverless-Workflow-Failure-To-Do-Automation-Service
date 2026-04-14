# Serverless Workflow Failure To-Do Automation Service

This is a serverless application that converts workflow failures into actionable To-Do tickets, stores them in DynamoDB, and provides a simple frontend for users to view, resolve, and reopen tasks.

This project was built as part of a **BCS Level 4 DevOps Engineer Apprenticeship** work-based project. It demonstrates how **automation, observability, security, infrastructure as code, and CI/CD** can be combined to reduce manual operational effort and improve visibility of failures.

---

## Overview

In many teams, workflow failures are discovered too late or require manual checking of logs and pipelines. This project reduces that overhead by automatically turning failures into tracked To-Do items.

### Core outcomes
- Automatically convert workflow failures into To-Do tickets
- Deduplicate repeated failures using a deterministic fingerprint
- Reopen previously resolved tickets if the same failure happens again
- Track recurrence with `occurrenceCount` and `lastSeenAt`
- Provide a minimal UI for viewing, resolving, and reopening tickets
- Deploy infrastructure consistently with Terraform
- Run automated quality and security checks in CI/CD
- Support troubleshooting with structured logs and CloudWatch alarms

---

## Architecture

```text
GitHub Actions / Upstream Workflow
                |
                v
      API Gateway (HTTP API)
                |
                v
        Lambda (Python 3.11)
                |
                v
          DynamoDB Table

Frontend (HTML/CSS/JS) -> S3 + CloudFront
