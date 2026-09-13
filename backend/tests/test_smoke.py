"""
Azztec_SaaS_test_smoke_v1_1_1.py  ->  backend/tests/test_smoke.py
Version:  1.1.1
Author:   Adriaan
Spec:     Planner Port Spec S0 smoke + Azztec_SaaS_S1d_Diag_Chunk_Spec_v1_0_0.md §7.3. Pair of main.py 0.4.0.

Boots the app through the lifespan (real engine, real .env) and proves: health JSON shape, db ok,
request-id header, JSON 404 under /api, diag self-test, and the OD-19/OD-20 additions.

Changelog:
  1.1.1  S1i. HEADER ONLY - the Pair line followed main.py to 0.4.0 (OD-38). No assertion changed:
         test_health_versions_match_the_modules compares db / diag / config / planner and never main,
         so nothing here pinned 0.3.0. That gap (/health's own `version` is the one version nobody
         asserts) is open item 39, deliberately not closed inside a header-only edit.
  1.1.0  S1d. test_api_404_is_json_not_spa GOES GREEN - the one red carried since 2026-09-10, cleared by
         the conditional SPA mount (OD-19), not by building a frontend; it now also asserts the flat
         OD-15 body. New: diagWired (OD-20); versions must match the modules' own __version__ so a
         hardcoded literal cannot drift again; root reflects the frontend state; POST /planner/range is
         still 405 - the regression guard for the catch-all route that was deliberately NOT added.
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
    """OD-19. Red from 2026-09-10 to 2026-09-11: StaticFiles raised on the missing web/dist and the miss
    surfaced as a 500. The API no longer depends on the SPA mount being healthy."""
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    body = r.json()
    assert body["ok"] is False and body["code"] == "NOT_FOUND"  # flat OD-15 shape
    assert "error" not in body


def test_diag_self_test(client: TestClient) -> None:
    r = client.get("/api/v1/_diag/self-test")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["record"]["tag"] == "[F]"  # the RETURN VALUE; emission is proved in test_diag_wiring.py
    assert body["persist"] in ("stdout", "diag_log")
    assert body["wired"] is True


def test_health_reports_diag_wired(client: TestClient) -> None:
    """OD-20. `diag` says where records persist; `diagWired` says whether anything is printing. Reporting
    only the first is what let the silent logger look healthy for three slices."""
    body = client.get("/api/v1/health").json()
    assert body["diagWired"] is True
    assert body["diag"] in ("stdout", "diag_log")


def test_health_versions_match_the_modules(client: TestClient) -> None:
    """WoW §2: the constant is bumped with the header, 'or /api/v1/health lies'. main.py 0.2.1 carried a
    hardcoded config version that was stale the moment config.py bumped. This makes that impossible."""
    from app.core import config, db, diag  # noqa: PLC0415 - after env is set
    from app.planner import router as planner_router  # noqa: PLC0415

    versions = client.get("/api/v1/health").json()["versions"]
    assert versions["db"] == db.__version__
    assert versions["diag"] == diag.__version__
    assert versions["config"] == config.__version__
    assert versions["planner"] == planner_router.__version__


def test_root_matches_the_frontend_state(client: TestClient) -> None:
    """Survives the frontend arriving: asserts the coupling, not the current absence."""
    frontend = client.get("/api/v1/health").json()["frontend"]
    r = client.get("/")
    if frontend == "missing":
        assert r.status_code == 404
        assert r.headers["content-type"].startswith("application/json")
    else:
        assert r.status_code == 200


def test_planner_range_post_is_still_405(client: TestClient) -> None:
    """Regression guard for S1d §5.2. A catch-all /api/{rest:path} route would FULL-match this path and
    return 404, because Starlette only uses its Match.PARTIAL 405 fallback when nothing full-matches.
    Asserted here as well as in test_planner_api.py so it cannot be lost with the planner suite."""
    r = client.post("/api/v1/planner/range", json={"from": "2026-09-14", "to": "2026-09-20"})
    assert r.status_code == 405
    assert r.json()["code"] == "METHOD_NOT_ALLOWED"
