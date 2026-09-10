"""
Azztec_SaaS_test_smoke_v1_0_0.py  ->  backend/tests/test_smoke.py
Version:  1.0.0
Author:   Adriaan
Spec:     Planner Port Spec S0 smoke. Pair of app/main.py 0.1.0.

Boots the app through the lifespan (real engine, real .env) and proves: health JSON shape, db ok,
request-id header, JSON 404 under /api, diag self-test.

Changelog:
  1.0.0  Initial.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("WORKMATE_ENV", "test")


@pytest.fixture(scope="module")
def client():
    from app.main import app  # noqa: PLC0415 - after env is set

    with TestClient(app) as c:
        yield c


def test_health_shape_and_db(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["app"] == "workmate-saas"
    assert body["dbKind"] in ("mssql", "postgresql")
    assert body["db"] == "ok", body["db"]  # the exact driver message shows here when it is not
    assert "X-Request-Id" in r.headers


def test_api_404_is_json_not_spa(client: TestClient) -> None:
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")


def test_diag_self_test(client: TestClient) -> None:
    r = client.get("/api/v1/_diag/self-test")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["record"]["tag"] == "[F]"
    assert body["persist"] in ("stdout", "diag_log")
