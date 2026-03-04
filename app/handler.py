import json
from typing import Any

from app.repository import LocalRepository
from app.service import (
    ServiceError,
    ingest_workflow_failures,
    list_todos,
    parse_json_body,
    patch_todo_status,
)

# Default storage for local dev. In tests we inject a fresh FakeRepository.
_DEFAULT_REPO = LocalRepository()


def response(status_code: int, body: dict) -> dict:
    """
    Build an API Gateway (HTTP API v2) Lambda proxy response.

    Why:
    - Keeps response formatting consistent across all routes.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            # CORS headers so browser UI can call the API later
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Workflow-Secret",
            "Access-Control-Allow-Methods": "GET,POST,PATCH,OPTIONS",
        },
        "body": json.dumps(body),
    }


def error(status_code: int, code: str, message: str, details: Any = None) -> dict:
    """
    Standard error response shape required by your contract:
      { "error": { "code": "...", "message": "...", "details": ... } }

    Why:
    - UI/clients can reliably handle errors without special-casing.
    """
    err_obj = {"code": code, "message": message}
    if details is not None:
        err_obj["details"] = details
    return response(status_code, {"error": err_obj})


def lambda_handler(event: dict, context: Any, repo=_DEFAULT_REPO) -> dict:
    """
    Lambda entrypoint (thin router).

    Why this stays thin:
    - Handler should do HTTP plumbing only (method/path/body parsing).
    - Business rules live in service.py so they are easy to unit test.
    - Storage details live in repository.py.
    """
    try:
        http = event.get("requestContext", {}).get("http", {}) or {}
        method = (http.get("method") or "").upper()

        # For HTTP API v2, rawPath is a reliable path field.
        path = event.get("rawPath") or http.get("path") or "/"

        headers = event.get("headers") or {}

        # CORS preflight
        if method == "OPTIONS":
            return response(204, {})

        # POST /workflow-failure (batch)
        if method == "POST" and path == "/workflow-failure":
            payload = parse_json_body(event.get("body"))
            out = ingest_workflow_failures(repo, headers, payload)
            return response(202, out)

        # GET /todos (optional ?status=open|done)
        if method == "GET" and path == "/todos":
            qs = event.get("queryStringParameters") or {}
            status = qs.get("status") if isinstance(qs, dict) else None
            out = list_todos(repo, status)
            return response(200, out)

        # PATCH /todos/{id}
        if method == "PATCH" and path.startswith("/todos/"):
            ticket_id = path.split("/todos/", 1)[1]
            payload = parse_json_body(event.get("body"))
            out = patch_todo_status(repo, ticket_id, payload)
            return response(200, out)

        return error(405, "METHOD_NOT_ALLOWED", f"No route for {method} {path}")

    except ServiceError as se:
        # Map service errors to HTTP status codes.
        status_code = {
            "INVALID_JSON": 400,
            "VALIDATION_ERROR": 400,
            "UNAUTHORIZED": 403,  # contract: 403 for bad/missing secret
            "NOT_FOUND": 404,
        }.get(se.code, 500)

        return error(status_code, se.code, se.message, se.details)

    except Exception as ex:
        # Catch-all: prevents raw stack traces leaking to the client.
        return error(500, "INTERNAL_ERROR", "Unexpected error", str(ex))
