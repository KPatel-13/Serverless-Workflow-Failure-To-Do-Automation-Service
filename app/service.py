import hashlib
import json
import os
import re
from datetime import UTC, datetime


class ServiceError(Exception):
    """
    Small custom exception used for expected service-level errors.

    The handler catches this and turns it into a consistent HTTP response.

    Example codes used elsewhere:
    - INVALID_JSON
    - VALIDATION_ERROR
    - UNAUTHORIZED
    - NOT_FOUND
    """

    def __init__(self, code: str, message: str, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def now_iso_utc() -> str:
    """
    Return the current UTC time in ISO format.

    Why this exists:
    - keeps timestamps consistent across the whole service
    - avoids mixing local time and UTC
    - makes values easier to compare in logs / DynamoDB
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def parse_json_body(raw: str | None) -> dict:
    """
    Parse the raw Lambda/API body into a Python dict.

    Notes:
    - empty body becomes an empty dict
    - invalid JSON is treated as a controlled client error
    - body must be a JSON object, not a list/string/etc.
    """
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ServiceError(
            "INVALID_JSON",
            "Request body must be valid JSON",
            str(exc),
        ) from exc

    if not isinstance(data, dict):
        raise ServiceError("INVALID_JSON", "Body must be a JSON object")

    return data


def require_secret(headers: dict) -> None:
    """
    Enforce the X-Workflow-Secret header on protected routes.

    Why:
    - POST /workflow-failure should only be callable by the simulator/upstream workflow
    - the secret is read from the Lambda environment variable WORKFLOW_SECRET

    Notes:
    - browser PATCH updates intentionally do not use this shared secret
    - treat an empty/missing env var as a security failure as well
    - never log the provided secret value
    """
    expected = os.getenv("WORKFLOW_SECRET", "")
    provided = ""

    # Headers can come through with different casing depending on the client,
    # so compare in a case-insensitive way.
    for key, value in (headers or {}).items():
        if str(key).lower() == "x-workflow-secret":
            provided = str(value)
            break

    if not expected or provided != expected:
        raise ServiceError("UNAUTHORIZED", "Missing or invalid X-Workflow-Secret")


def _norm(value: str | None) -> str:
    """
    Normalise text before fingerprinting.

    Why:
    We want small formatting differences to not create a brand new ticket.

    For example:
    - extra spaces
    - different capitalisation
    - inconsistent line spacing
    """
    if value is None:
        return ""

    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def compute_fingerprint(
    repo: str,
    workflow_name: str,
    job_name: str,
    summary: str,
    details: str | None,
) -> str:
    """
    Build a stable SHA-256 fingerprint for a failure.

    The fingerprint is based on the fields that define "same logical failure":
    - repo
    - workflow name
    - job name
    - summary
    - details
    """
    stable = (
        _norm(repo)
        + "|"
        + _norm(workflow_name)
        + "|"
        + _norm(job_name)
        + "|"
        + _norm(summary)
        + "|"
        + _norm(details)
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def ingest_workflow_failures(repo_obj, headers: dict, payload: dict) -> dict:
    """
    Implements POST /workflow-failure.

    Expected payload shape:
    {
      "repo": "...",
      "workflowName": "...",
      "runId": "...",
      "runUrl": "...",
      "failures": [
        {
          "jobName": "...",
          "summary": "...",
          "details": "...",   # optional
          "severity": "..."   # optional
        }
      ]
    }

    Returns a summary so the caller can see what happened in the batch:
    - created
    - updated
    - reopened
    """
    require_secret(headers)

    required_top = ["repo", "workflowName", "runId", "runUrl", "failures"]
    missing = []

    for key in required_top:
        if key not in payload or payload[key] in [None, "", []]:
            missing.append(key)

    if missing:
        raise ServiceError("VALIDATION_ERROR", "Missing required fields", missing)

    if not isinstance(payload["failures"], list):
        raise ServiceError("VALIDATION_ERROR", "failures must be a list")

    created = 0
    updated = 0
    reopened = 0
    now = now_iso_utc()

    for failure in payload["failures"]:
        if not isinstance(failure, dict):
            raise ServiceError("VALIDATION_ERROR", "Each failure must be an object")

        for key in ["jobName", "summary"]:
            if key not in failure or not str(failure[key]).strip():
                raise ServiceError(
                    "VALIDATION_ERROR",
                    f"failures[].{key} is required",
                )

        fingerprint = compute_fingerprint(
            payload["repo"],
            payload["workflowName"],
            failure["jobName"],
            failure["summary"],
            failure.get("details"),
        )

        open_ticket = repo_obj.get_open_by_fingerprint(fingerprint)
        if open_ticket:
            # Same failure while the ticket is still open:
            # - keep the existing board position if it is valid
            # - bump occurrence count and last seen details
            open_ticket["occurrenceCount"] = int(open_ticket.get("occurrenceCount", 1)) + 1
            open_ticket["lastSeenAt"] = now
            open_ticket["updatedAt"] = now
            open_ticket["runId"] = payload["runId"]
            open_ticket["runUrl"] = payload["runUrl"]

            if open_ticket.get("workflowState") not in ("todo", "in_progress"):
                open_ticket["workflowState"] = "todo"

            repo_obj.upsert(open_ticket)
            print(json.dumps({"ingest_result": {"action": "updated", "id": open_ticket["id"]}}))
            updated += 1
            continue

        existing = repo_obj.get_by_id(fingerprint)
        if existing and existing.get("status") == "done":
            # Same failure after the ticket was closed:
            # - reopen the same ticket
            # - send it back to To Do
            existing["status"] = "open"
            existing["workflowState"] = "todo"
            existing["resolvedAt"] = None
            existing["occurrenceCount"] = int(existing.get("occurrenceCount", 1)) + 1
            existing["lastSeenAt"] = now
            existing["updatedAt"] = now
            existing["runId"] = payload["runId"]
            existing["runUrl"] = payload["runUrl"]

            repo_obj.upsert(existing)
            print(json.dumps({"ingest_result": {"action": "reopened", "id": existing["id"]}}))
            reopened += 1
            continue

        # Otherwise create a brand new ticket.
        # New tickets always start as:
        # - status = open
        # - workflowState = todo
        ticket = {
            "id": fingerprint,
            "fingerprint": fingerprint,
            "status": "open",
            "workflowState": "todo",
            "title": f"{failure['jobName']} failed: {failure['summary']}",
            "summary": failure["summary"],
            "details": failure.get("details"),
            "severity": failure.get("severity"),
            "repo": payload["repo"],
            "workflowName": payload["workflowName"],
            "jobName": failure["jobName"],
            "runId": payload["runId"],
            "runUrl": payload["runUrl"],
            "occurrenceCount": 1,
            "firstSeenAt": now,
            "lastSeenAt": now,
            "updatedAt": now,
            "resolvedAt": None,
        }
        repo_obj.upsert(ticket)
        print(json.dumps({"ingest_result": {"action": "created", "id": ticket["id"]}}))
        created += 1

    return {
        "ok": True,
        "created": created,
        "updated": updated,
        "reopened": reopened,
    }


def list_todos(repo_obj, status: str | None) -> dict:
    """
    Implements GET /todos?status=open|done

    Notes:
    - if no status filter is provided, return all tickets
    - if status is provided, only allow the known lifecycle values
    """
    if status and status not in ("open", "done"):
        raise ServiceError(
            "VALIDATION_ERROR",
            "Invalid status filter",
            ["status must be open|done"],
        )

    return {"items": repo_obj.list_tickets(status=status)}


def patch_todo_status(repo_obj, headers: dict, ticket_id: str, payload: dict) -> dict:
    """
    Implements PATCH /todos/{id}

    Supported request bodies:
    - {"status": "done"}
    - {"status": "open"}
    - {"status": "open", "workflowState": "todo"}
    - {"status": "open", "workflowState": "in_progress"}

    Notes:
    - this route is used by the browser board
    - keep headers in the signature for compatibility with the current handler/tests
    - PATCH does not use the shared workflow secret now
    """
    status = payload.get("status")
    workflow_state = payload.get("workflowState")

    if status not in ("open", "done"):
        raise ServiceError(
            "VALIDATION_ERROR",
            "Invalid status",
            ["status must be open|done"],
        )

    if workflow_state is not None and workflow_state not in ("todo", "in_progress"):
        raise ServiceError(
            "VALIDATION_ERROR",
            "Invalid workflowState",
            ["workflowState must be todo|in_progress"],
        )

    ticket = repo_obj.get_by_id(ticket_id)
    if not ticket:
        raise ServiceError("NOT_FOUND", "Ticket not found")

    now = now_iso_utc()
    ticket["status"] = status
    ticket["updatedAt"] = now

    if status == "done":
        # Resolved / closed ticket:
        # - mark resolvedAt
        # - keep workflowState predictable for later reopen logic
        ticket["resolvedAt"] = now
        ticket["workflowState"] = "todo"
    else:
        # Reopened / still-open ticket:
        # - clear resolvedAt
        # - keep or update the board position
        # - default to todo if nothing valid exists yet
        ticket["resolvedAt"] = None
        ticket["workflowState"] = workflow_state or ticket.get("workflowState") or "todo"

    repo_obj.upsert(ticket)
    return ticket
