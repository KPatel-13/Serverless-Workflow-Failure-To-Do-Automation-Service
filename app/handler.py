import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any


def now_utc_iso() -> str:
    """
    Parameters:
        None

    Process:
        - Gets the current time in UTC.

    Returns:
        str:
            Example: "2026-02-13T12:34:56+00:00"
            Will be used for createdAt/lastSeenAt timestamps and logs.
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """
    Parameters:
        status_code (int):
            HTTP status code to return (e.g. 200, 202, 400, 401, 404).
        body (dict[str, Any]):
            JSON payload to return to the caller.

    Process:
        - Builds the API Gateway Lambda Proxy response object.
        - Adds JSON content header.

    Returns:
        dict[str, Any]:
            API Gateway-compatible response with keys:
              - statusCode: int
              - headers: dict
              - body: str (JSON string)
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Workflow-Secret",
            "Access-Control-Allow-Methods": "GET,POST,PATCH,OPTIONS",
        },
        "body": json.dumps(body),
    }


def error(error_code: str, message: str, status_code: int = 400) -> dict[str, Any]:
    """
    Parameters:
        error_code (str): Short machine-readable error code.
        message (str): Human-readable explanation.
        status_code (int): HTTP status for the error (default 400).

    Process:
        - Wraps errors in a consistent shape for UI and clients.

    Returns:
        dict[str, Any]: API Gateway-compatible error response.
    """
    return response(status_code, {"error": {"code": error_code, "message": message}})


def get_header(headers: dict[str, str] | None, name: str) -> str:
    """
    Parameters:
        headers (dict[str, str] | None): Request headers from API Gateway.
        name (str): Header name to fetch (e.g. 'X-Workflow-Secret').

    Process:
        - Returns header value, handling common case differences.

    Returns:
        str: Header value or "" if missing.
    """
    if not headers:
        return ""
    return headers.get(name) or headers.get(name.lower()) or ""


def require_workflow_secret(headers: dict[str, str] | None) -> bool:
    """
    Parameters:
        headers (dict[str, str] | None): Request headers from API Gateway.

    Process:
        - Reads expected secret from env var WORKFLOW_SECRET.
        - If WORKFLOW_SECRET is empty, allow (dev-friendly).
        - If set, caller must send matching X-Workflow-Secret header.

    Returns:
        bool:
            True  -> authorised
            False -> unauthorised
    """
    expected = os.getenv("WORKFLOW_SECRET", "")
    if not expected:
        return True
    provided = get_header(headers, "X-Workflow-Secret")
    return provided == expected


def parse_json_body(event: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """
    Parameters:
        event (dict[str, Any]): Lambda event.

    Process:
        - Reads event["body"] (string) and attempts json.loads.
        - If parsing fails, returns an error response.

    Returns:
        tuple:
            (data, None) if ok
            (None, error_response) if invalid JSON
    """
    try:
        data = json.loads(event.get("body") or "{}")
        if not isinstance(data, dict):
            return None, error("INVALID_JSON", "Body must be a JSON object", 400)
        return data, None
    except json.JSONDecodeError:
        return None, error("INVALID_JSON", "Request body must be valid JSON", 400)


# ----------------------- DynamoDB placeholders -----------------------
def db_find_open_ticket_for_repo(repo: str) -> dict[str, Any] | None:
    """
    Parameters:
        repo (str): Repo identifier, e.g. "org/repo".

    Process:
        - Query DynamoDB GSI (repo + status) for status="open".
        - Return the open ticket item if found.

    Returns:
        dict[str, Any] | None:
            - dict: existing open ticket item
            - None: no open ticket exists
    """
    # TODO:
    # 1) Create DynamoDB client/resource (boto3)
    # 2) Query table using IndexName="gsi_repo_status"
    # 3) KeyConditionExpression repo=:repo AND status=:status
    # 4) Return first item if present
    return None


def db_update_occurrence(ticket_id: str, repo: str, now_iso: str, run_url: str) -> None:
    """
    Parameters:
        ticket_id (str): Ticket PK ('id').
        repo (str): Repo string (useful for logging/safety).
        now_iso (str): Current UTC timestamp.
        run_url (str): Latest run URL (optional).

    Process:
        - Update existing ticket:
          - occurrenceCount += 1
          - lastSeenAt = now
          - updatedAt = now
          - runUrl = latest (optional)

    Returns:
        None
    """
    # TODO: DynamoDB UpdateItem with ADD/SET expressions
    return None


def db_close_ticket(ticket_id: str, now_iso: str) -> None:
    """
    Parameters:
        ticket_id (str): Ticket PK ('id').
        now_iso (str): Current UTC timestamp.

    Process:
        - Marks a ticket as no longer open (e.g. done/superseded).
        - Keeps history but removes it from the "open" queue.

    Returns:
        None
    """
    # TODO: UpdateItem SET status="done" (or "superseded"), updatedAt=now
    return None


def db_create_ticket(repo: str, error_message: str, run_url: str, now_iso: str) -> dict[str, Any]:
    """
    Parameters:
        repo (str): Repo identifier.
        error_message (str): Failure message used for dedupe comparison.
        run_url (str): Link to the failing workflow run.
        now_iso (str): Timestamp to use for createdAt/lastSeenAt.

    Process:
        - Creates a new ticket item:
          - id = uuid4()
          - status = "open"
          - occurrenceCount = 1
          - createdAt/lastSeenAt/updatedAt set to now
          - stores errorMessage and runUrl

    Returns:
        dict[str, Any]:
            The created ticket item (what you inserted).
    """
    new_item: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "repo": repo,
        "status": "open",
        "errorMessage": error_message,
        "runUrl": run_url,
        "occurrenceCount": 1,
        "createdAt": now_iso,
        "lastSeenAt": now_iso,
        "updatedAt": now_iso,
    }

    # TODO: PutItem into DynamoDB table
    return new_item


# ----------------------- Route handlers -----------------------
def handle_workflow_failure(event: dict[str, Any]) -> dict[str, Any]:
    """
    Parameters:
        event (dict[str, Any]): Lambda event for POST /workflow-failure.

    Expected JSON body:
        - repo (str) REQUIRED
        - status (str) REQUIRED: "failure" or "success"
        - errorMessage (str) OPTIONAL
        - runUrl (str) OPTIONAL

    Process:
        1) Check shared secret header (X-Workflow-Secret) if enabled.
        2) Parse JSON body + validate required fields.
        3) If status == "success": return 202 ignored.
        4) If status == "failure":
           - Find existing OPEN ticket for this repo.
           - If none: create a new ticket.
           - If exists:
               - If errorMessage is the same: update occurrenceCount + lastSeenAt.
               - If errorMessage is different: close old + create new ticket.

    Returns:
        dict[str, Any]: API Gateway response acknowledging what happened.
    """
    if not require_workflow_secret(event.get("headers")):
        return error("UNAUTHORIZED", "Missing or invalid X-Workflow-Secret", 401)

    body, err_resp = parse_json_body(event)
    if err_resp:
        return err_resp

    repo = str(body.get("repo") or "").strip()
    status = str(body.get("status") or "").strip()
    error_message = str(body.get("errorMessage") or "").strip()
    run_url = str(body.get("runUrl") or "").strip()
    now_iso = now_utc_iso()

    if not repo:
        return error("VALIDATION_ERROR", "`repo` is required", 400)

    if status not in ["failure", "success"]:
        return error("VALIDATION_ERROR", "`status` must be 'failure' or 'success'", 400)

    if status == "success":
        return response(202, {"status": "ignored", "repo": repo})

    existing = db_find_open_ticket_for_repo(repo)

    if not existing:
        created = db_create_ticket(repo, error_message, run_url, now_iso)
        return response(202, {"status": "created", "ticket": {"id": created["id"], "repo": repo}})

    existing_id = str(existing.get("id", ""))
    existing_error = str(existing.get("errorMessage") or "").strip()

    if error_message == existing_error:
        db_update_occurrence(existing_id, repo, now_iso, run_url)
        return response(202, {"status": "updated", "ticket": {"id": existing_id, "repo": repo}})

    # Different error -> new ticket (close old open ticket first to keep one active per repo)
    db_close_ticket(existing_id, now_iso)
    created = db_create_ticket(repo, error_message, run_url, now_iso)

    return response(
        202,
        {
            "status": "created_new",
            "previousTicketId": existing_id,
            "newTicketId": created["id"],
            "repo": repo,
        },
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Parameters:
        event (dict[str, Any]):
            API Gateway HTTP API (payload v2) event. We read:
              - requestContext.http.method
              - requestContext.http.path (or rawPath fallback)
              - headers
              - body
        context (Any):
            Lambda context (we log aws_request_id for tracing).

    Process:
        - Extract method/path
        - Handle OPTIONS (CORS)
        - Route to:
            POST /workflow-failure
            GET /todos
            PATCH /todos/{id}
        - Return 404 if unknown route

    Returns:
        dict[str, Any]:
            API Gateway Lambda Proxy response: statusCode + headers + body(string).
    """
    http_info = event.get("requestContext", {}).get("http", {})
    method = (http_info.get("method") or "").upper()
    path = http_info.get("path") or event.get("rawPath") or ""

    print(
        json.dumps(
            {
                "msg": "request",
                "method": method,
                "path": path,
                "requestId": getattr(context, "aws_request_id", None),
                "at": now_utc_iso(),
            }
        )
    )

    if method == "OPTIONS":
        return response(204, {})

    if method == "POST" and path.endswith("/workflow-failure"):
        return handle_workflow_failure(event)

    if method == "GET" and path.endswith("/todos"):
        # TODO: implement list tickets from DynamoDB
        return response(200, {"items": []})

    if method == "PATCH" and "/todos/" in path:
        # TODO: implement resolve/unresolve update in DynamoDB
        return response(200, {"status": "ok"})

    return error("NOT_FOUND", f"No route for {method} {path}", 404)
