import json

import pytest

from app.handler import get_repo, lambda_handler
from app.repository import LocalRepository
from app.service import compute_fingerprint


@pytest.fixture()
def repo():
    # fresh in-memory repo per test
    return LocalRepository()


def api_event(method, path, body=None, headers=None, query=None):
    """
    Create a minimal API Gateway HTTP API v2 event for unit tests.
    """
    return {
        "requestContext": {"http": {"method": method, "path": path}},
        "rawPath": path,
        "headers": headers or {},
        "queryStringParameters": query or None,
        "body": json.dumps(body) if isinstance(body, (dict, list)) else body,
        "isBase64Encoded": False,
    }


def test_get_repo_returns_local_repository_when_no_todos_table(monkeypatch):
    """
    Sprint 3 wiring test.

    Why:
    - Confirms local runs still use LocalRepository when TODOS_TABLE is not set.
    - Keeps unit tests AWS-free.
    """
    monkeypatch.delenv("TODOS_TABLE", raising=False)
    repo_obj = get_repo()
    assert isinstance(repo_obj, LocalRepository)


def test_fingerprint_deterministic():
    # same meaning, different whitespace/case => same fingerprint
    a = compute_fingerprint("Owner/Repo", "WF", "Job", "Summary", "Details\nx")
    b = compute_fingerprint("owner/repo ", "wf", " job ", "summary", "details  x")
    assert a == b


def test_post_unauthorized(repo, monkeypatch):
    monkeypatch.setenv("WORKFLOW_SECRET", "expected")
    evt = api_event("POST", "/workflow-failure", body={"repo": "a/b"})
    res = lambda_handler(evt, None, repo=repo)
    assert res["statusCode"] == 403
    assert json.loads(res["body"])["error"]["code"] == "UNAUTHORIZED"


def test_post_invalid_json(repo, monkeypatch):
    monkeypatch.setenv("WORKFLOW_SECRET", "expected")
    evt = api_event(
        "POST",
        "/workflow-failure",
        body="{not-json",
        headers={"X-Workflow-Secret": "expected"},
    )
    res = lambda_handler(evt, None, repo=repo)
    assert res["statusCode"] == 400
    assert json.loads(res["body"])["error"]["code"] == "INVALID_JSON"


def test_create_then_dedupe_update(repo, monkeypatch):
    monkeypatch.setenv("WORKFLOW_SECRET", "expected")

    body = {
        "repo": "owner/repo",
        "workflowName": "CI",
        "runId": "1",
        "runUrl": "https://example/run/1",
        "failures": [{"jobName": "build", "summary": "failed", "details": "x"}],
    }

    res1 = lambda_handler(
        api_event(
            "POST",
            "/workflow-failure",
            body=body,
            headers={"X-Workflow-Secret": "expected"},
        ),
        None,
        repo=repo,
    )
    assert res1["statusCode"] == 202
    assert json.loads(res1["body"]) == {
        "ok": True,
        "created": 1,
        "updated": 0,
        "reopened": 0,
    }

    body["runId"] = "2"
    body["runUrl"] = "https://example/run/2"

    res2 = lambda_handler(
        api_event(
            "POST",
            "/workflow-failure",
            body=body,
            headers={"X-Workflow-Secret": "expected"},
        ),
        None,
        repo=repo,
    )
    assert json.loads(res2["body"]) == {
        "ok": True,
        "created": 0,
        "updated": 1,
        "reopened": 0,
    }

    fp = compute_fingerprint("owner/repo", "CI", "build", "failed", "x")
    t = repo.get_by_id(fp)
    assert t["occurrenceCount"] == 2
    assert t["runId"] == "2"


def test_patch_resolve_and_unresolve(repo, monkeypatch):
    monkeypatch.setenv("WORKFLOW_SECRET", "expected")

    body = {
        "repo": "owner/repo",
        "workflowName": "CI",
        "runId": "1",
        "runUrl": "https://example/run/1",
        "failures": [{"jobName": "build", "summary": "failed"}],
    }

    lambda_handler(
        api_event(
            "POST",
            "/workflow-failure",
            body=body,
            headers={"X-Workflow-Secret": "expected"},
        ),
        None,
        repo=repo,
    )

    fp = compute_fingerprint("owner/repo", "CI", "build", "failed", None)

    res_done = lambda_handler(
        api_event(
            "PATCH",
            f"/todos/{fp}",
            body={"status": "done"},
            headers={"X-Workflow-Secret": "expected"},
        ),
        None,
        repo=repo,
    )
    done_ticket = json.loads(res_done["body"])
    assert done_ticket["status"] == "done"
    assert done_ticket["resolvedAt"] is not None

    res_open = lambda_handler(
        api_event(
            "PATCH",
            f"/todos/{fp}",
            body={"status": "open"},
            headers={"X-Workflow-Secret": "expected"},
        ),
        None,
        repo=repo,
    )
    open_ticket = json.loads(res_open["body"])
    assert open_ticket["status"] == "open"
    assert open_ticket["resolvedAt"] is None


def test_get_todos_empty(repo):
    res = lambda_handler(api_event("GET", "/todos"), None, repo=repo)
    assert res["statusCode"] == 200
    assert json.loads(res["body"]) == {"items": []}
