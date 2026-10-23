"""Tests for FastAPI entrypoint with PoisonGuard runtime enforcement."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main_api import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "mcore-ai-orchestrator"


def test_check_whitelisted(client: TestClient) -> None:
    r = client.post("/tool/check", json={"tool": "read_file"})
    assert r.status_code == 200
    d = r.json()
    assert d["allowed"] is True
    assert d["requires_approval"] is False


def test_check_blocked(client: TestClient) -> None:
    r = client.post("/tool/check", json={"tool": "drop_table"})
    assert r.status_code == 200
    assert r.json()["allowed"] is False


def test_invoke_blocked_returns_403(client: TestClient) -> None:
    r = client.post("/tool/invoke", json={"tool": "drop_table"})
    assert r.status_code == 403


def test_invoke_approval_returns_409(client: TestClient) -> None:
    r = client.post("/tool/invoke", json={"tool": "push_to_main"})
    assert r.status_code == 409


def test_invoke_whitelisted_returns_200(client: TestClient) -> None:
    r = client.post("/tool/invoke", json={"tool": "read_file", "args": {"path": "/etc/hostname"}})
    assert r.status_code == 200
    assert r.json()["status"] == "executed_stub"


def test_empty_tool_rejected(client: TestClient) -> None:
    r = client.post("/tool/check", json={"tool": ""})
    assert r.status_code == 422
