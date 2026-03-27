import json
import logging
import os
from typing import Any

from app.repository import LocalRepository
from app.service import (
    ServiceError,
    ingest_workflow_failures,
    list_todos,
    parse_json_body,
    patch_todo_status,
)

# Root logger used by Lambda -> CloudWatch Logs
logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def get_repo():
    """
    Choose repository implementation based on environment.

    Why:
    - Local development and tests should stay fast and AWS-free.
    - Deployed Lambda should use DynamoDB automatically when TODOS_TABLE is set.
    - This keeps one codebase for both local and AWS execution.
    """
    table_name = os.getenv("TODOS_TABLE")

    if table_name:
        # Imported lazily so local-only test runs do not require boto3 wiring here.
        from app.dynamodb_repository import DynamoDBRepository

        return DynamoDBRepository(table_name=table_name)

    return LocalRepository()


def response(status_code: int, body: dict) -> dict:
    """
    Build a consistent HTTP API v2 Lambda proxy response.

    Why:
    - Keeps every route returning the same structure.
    - Includes CORS headers so a later browser UI can call the API.
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


def error(status_code: int, code: str, message: str, details: Any = None) -> dict:
    """
    Build the contract error shape:
      { "error": { "code": "...", "message": "...", "details": ... } }

    Why:
    - Clients and the future UI can handle errors consistently.
    """
    err_obj = {"code": code, "message": message}
    if details is not None:
        err_obj["details"] = details
    return response(status_code, {"error": err_obj})


def lambda_handler(event: dict, context: Any, repo=None) -> dict:
    """
    Lambda entrypoint.

    Why this stays thin:
    - handler.py does HTTP/Lambda plumbing only
    - service.py owns business logic
    - repository classes own storage details

    repo=None is kept so:
    - Tests can inject a local/fake repo directly
    - AWS runtime can auto-select DynamoDB via get_repo()
    """
    if repo is None:
        repo = get_repo()

    try:
        http = event.get("requestContext", {}).get("http", {}) or {}
        method = (http.get("method") or "").upper()
        path = event.get("rawPath") or http.get("path") or "/"
        headers = event.get("headers") or {}

        # Structured logs are easier to search in CloudWatch.
        logger.info(
            json.dumps(
                {
                    "msg": "request_received",
                    "method": method,
                    "path": path,
                    "using_dynamodb": bool(os.getenv("TODOS_TABLE")),
                }
            )
        )

        # CORS preflight
        if method == "OPTIONS":
            return response(204, {})

        # POST /workflow-failure
        if method == "POST" and path == "/workflow-failure":
            payload = parse_json_body(event.get("body"))
            out = ingest_workflow_failures(repo, headers, payload)
            logger.info(json.dumps({"msg": "workflow_failure_processed", **out}))
            return response(202, out)

        # GET /todos?status=open|done
        if method == "GET" and path == "/todos":
            qs = event.get("queryStringParameters") or {}
            status = qs.get("status") if isinstance(qs, dict) else None
            out = list_todos(repo, status)
            logger.info(json.dumps({"msg": "todos_listed", "count": len(out["items"])}))
            return response(200, out)

        # PATCH /todos/{id}
        if method == "PATCH" and path.startswith("/todos/"):
            ticket_id = path.split("/todos/", 1)[1]
            payload = parse_json_body(event.get("body"))
            out = patch_todo_status(repo, ticket_id, payload)
            logger.info(
                json.dumps(
                    {
                        "msg": "todo_patched",
                        "ticket_id": ticket_id,
                        "status": out.get("status"),
                    }
                )
            )
            return response(200, out)

        return error(405, "METHOD_NOT_ALLOWED", f"No route for {method} {path}")

    except ServiceError as se:
        # Map controlled service-layer errors to HTTP status codes.
        status_code = {
            "INVALID_JSON": 400,
            "VALIDATION_ERROR": 400,
            "UNAUTHORIZED": 403,
            "NOT_FOUND": 404,
        }.get(se.code, 500)

        logger.warning(
            json.dumps(
                {
                    "msg": "service_error",
                    "code": se.code,
                    "message": se.message,
                    "details": se.details,
                }
            )
        )
        return error(status_code, se.code, se.message, se.details)

    except Exception as e:
        logger.exception("unhandled_exception")
        return error(500, "INTERNAL_ERROR", "Unexpected error", str(e))
