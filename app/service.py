import hashlib
import json
import os
from datetime import UTC, datetime


class ServiceError(Exception):
    """
    Controlled error the handler can convert into a consistent HTTP response.

    code examples:
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
    Current UTC time in ISO format.

    Why:
    - We store timestamps consistently in UTC.
    - Easy to read and compare in logs/data.
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def parse_json_body(raw: str | None) -> dict:
    """
    Parse the raw request body into a dict.

    Raises:
    - ServiceError(INVALID_JSON) if JSON is invalid or not an object.
    """
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ServiceError("INVALID_JSON", "Request body must be valid JSON", str(e)) from e

    if not isinstance(data, dict):
        raise ServiceError("INVALID_JSON", "Body must be a JSON object")

    return data


def require_secret(headers: dict) -> None:
    """
    Enforce the X-Workflow-Secret header for POST /workflow-failure.

    Why:
    - Prevent random users from creating tickets.
    - Matches your intended contract.

    Note:
    - We treat empty WORKFLOW_SECRET as misconfigured and reject (more secure).
    """
    expected = os.getenv("WORKFLOW_SECRET", "")
    provided = ""

    # Headers can come in different casing; we check case-insensitively.
    for k, v in (headers or {}).items():
        if str(k).lower() == "x-workflow-secret":
            provided = str(v)
            break

    if not expected or provided != expected:
        raise ServiceError("UNAUTHORIZED", "Missing or invalid X-Workflow-Secret")


def compute_fingerprint(repo: str, workflow_name: str, job_name: str, summary: str, details: str | None) -> str:
    """
    Compute a deterministic SHA-256 fingerprint.

    Why:
    - Dedupe rule: same failure cause should map to same fingerprint.
    - SHA-256 is reliable and standard.

    Implementation:
    - Normalize inputs: strip + lower
    - Join into one string
    - sha256 → hex
    """
    details = details or ""
    stable = (
        repo.strip().lower()
        + "|" + workflow_name.strip().lower()
        + "|" + job_name.strip().lower()
        + "|" + summary.strip().lower()
        + "|" + details.strip().lower()
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def ingest_workflow_failures(repo_obj, headers: dict, payload: dict) -> dict:
    """
    Implements POST /workflow-failure (batch contract).

    Expected payload:
    {
      repo, workflowName, runId, runUrl,
      failures: [{jobName, summary, details?, severity?}]
    }

    Dedupe rules:
    - If OPEN ticket with same fingerprint exists: update count + lastSeenAt
    - If DONE ticket exists with same id (we use id == fingerprint): reopen
    - Else create a new OPEN ticket

    Returns:
    202 body: {ok:true, created:n, updated:m, reopened:r}
    """
    require_secret(headers)

    # --- basic validation (kept simple and readable) ---
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

    for f in payload["failures"]:
        if not isinstance(f, dict):
            raise ServiceError("VALIDATION_ERROR", "Each failure must be an object")

        # required failure fields
        for key in ["jobName", "summary"]:
            if key not in f or not str(f[key]).strip():
                raise ServiceError("VALIDATION_ERROR", f"failures[].{key} is required")

        fp = compute_fingerprint(
            payload["repo"],
            payload["workflowName"],
            f["jobName"],
            f["summary"],
            f.get("details"),
        )

        # 1) if an OPEN ticket exists, update it (dedupe)
        open_ticket = repo_obj.get_open_by_fingerprint(fp)
        if open_ticket:
            open_ticket["occurrenceCount"] = int(open_ticket.get("occurrenceCount", 1)) + 1
            open_ticket["lastSeenAt"] = now
            open_ticket["updatedAt"] = now
            open_ticket["runId"] = payload["runId"]
            open_ticket["runUrl"] = payload["runUrl"]
            repo_obj.upsert(open_ticket)
            updated += 1
            continue

        # 2) if DONE ticket exists, reopen it (Sprint 2 default)
        existing = repo_obj.get_by_id(fp)  # Sprint 2: id == fingerprint
        if existing and existing.get("status") == "done":
            existing["status"] = "open"
            existing["resolvedAt"] = None
            existing["occurrenceCount"] = int(existing.get("occurrenceCount", 1)) + 1
            existing["lastSeenAt"] = now
            existing["updatedAt"] = now
            existing["runId"] = payload["runId"]
            existing["runUrl"] = payload["runUrl"]
            repo_obj.upsert(existing)
            reopened += 1
            continue

        # 3) create a new ticket
        ticket = {
            "id": fp,  # simplest Sprint 2 approach
            "fingerprint": fp,
            "status": "open",
            "title": f"{f['jobName']} failed: {f['summary']}",
            "summary": f["summary"],
            "details": f.get("details"),
            "severity": f.get("severity"),
            "repo": payload["repo"],
            "workflowName": payload["workflowName"],
            "jobName": f["jobName"],
            "runId": payload["runId"],
            "runUrl": payload["runUrl"],
            "occurrenceCount": 1,
            "firstSeenAt": now,
            "lastSeenAt": now,
            "updatedAt": now,
            "resolvedAt": None,
        }
        repo_obj.upsert(ticket)
        created += 1

    return {"ok": True, "created": created, "updated": updated, "reopened": reopened}


def list_todos(repo_obj, status: str | None) -> dict:
    """
    Implements GET /todos?status=open|done
    """
    if status and status not in ("open", "done"):
        raise ServiceError("VALIDATION_ERROR", "Invalid status filter", ["status must be open|done"])
    return {"items": repo_obj.list_tickets(status=status)}


def patch_todo_status(repo_obj, ticket_id: str, payload: dict) -> dict:
    """
    Implements PATCH /todos/{id}
    Body: {"status":"open"|"done"}
    """
    status = payload.get("status")
    if status not in ("open", "done"):
        raise ServiceError("VALIDATION_ERROR", "Invalid status", ["status must be open|done"])

    t = repo_obj.get_by_id(ticket_id)
    if not t:
        raise ServiceError("NOT_FOUND", "Ticket not found")

    now = now_iso_utc()
    t["status"] = status
    t["updatedAt"] = now
    t["resolvedAt"] = now if status == "done" else None
    repo_obj.upsert(t)
    return t