"""
Azztec_SaaS_test_planner_api_v1_0_1.py  ->  backend/tests/test_planner_api.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md §7. Pair of router.py 1.0.1 + service.py 1.0.1 + schemas.py 1.0.0
          + deps.py 1.0.0 + main.py 0.3.0.

TestClient over the real app, DB dependency overridden with one RST connection inside a transaction that is
rolled back (D-10), actor dependency overridden (OD-12). Standing window 2026-09-14..2026-09-20 (Raw Log
2026-09-11 §5). Zero skips - every assertion is written to hold on dbWorkmate as restored.

Twenty tests from spec §7 plus one for the [F] line (§9 acceptance). Env trap: WORKMATE_ENV=test under
pytest and get_settings() is lru_cached, so the un-overridden actor is a 401 by design (§7.4 #19).
Trip-wire: #12 asserts pinTable is False (OD-1) and flips when S3 migration 0002 lands.

Changelog:
  1.0.1  S1d instrument migration, assertions unchanged. diag.py 1.1.0 sets propagate=False on
         'workmate.diag' (OD-18), so caplog - whose handler sits on root - no longer sees the record.
         test_range_forensic_line_once reads capfd instead, which is the stronger test anyway: caplog
         proved diag.log() was CALLED, capfd proves the line reached stdout. `import logging` dropped,
         `import json` added.
  1.0.0  Initial S1c.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection

os.environ.setdefault("WORKMATE_ENV", "test")

from app.core import db, deps  # noqa: E402 - after env is set
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.planner import repo, rules  # noqa: E402
from app.planner import router as planner_router  # noqa: E402

RANGE = "/api/v1/planner/range"
FROM, TO = "2026-09-14", "2026-09-20"
ACTOR = 1  # only echoed as `actor` this slice; never stamped on anything until S2

CONTRACT_KEYS = frozenset(
    {
        "from", "to", "today", "wos", "labour", "workers", "teams", "priorities", "colours", "weeks",
        "load", "counts", "pinTable", "workerWeeks", "uomHours", "libVersion",
        "ok", "apiVersion", "actor", "ms",  # OD-14 envelope, no gate
    }
)  # fmt: skip


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def conn() -> Iterator[Connection]:
    repo.clear_caches()  # test order must not decide what hours_uom_id / pin_table_exists cached
    with db.get_engine().connect() as c:
        tx = c.begin()
        try:
            yield c
        finally:
            tx.rollback()


@pytest.fixture(scope="module")
def client(conn: Connection) -> Iterator[TestClient]:
    def _conn() -> Iterator[Connection]:
        yield conn

    app.dependency_overrides[db.get_conn] = _conn
    app.dependency_overrides[deps.get_current_actor] = lambda: ACTOR
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def body(client: TestClient) -> dict:
    r = client.get(RANGE, params={"from": FROM, "to": TO})
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# §7.2 contract
# ---------------------------------------------------------------------------


def test_range_200_shape_on_standing_window(body: dict) -> None:
    assert body["from"] == FROM and body["to"] == TO
    assert body["counts"]["total"] > 0, "standing window is dense (Raw Log 2026-09-11 §5)"
    assert isinstance(body["wos"], list) and isinstance(body["labour"], list)
    assert isinstance(body["workers"], list) and isinstance(body["teams"], list)
    assert body["colours"] == {"DONE": "#81C784", "PM": "#4DD0E1", "REQ": "#F48FB1", "WO": "#FFC65C"}


def test_range_keys_match_contract(body: dict) -> None:
    assert set(body.keys()) == CONTRACT_KEYS, sorted(set(body.keys()) ^ CONTRACT_KEYS)
    assert "gate" not in body


def test_range_from_key_is_literal_from(body: dict) -> None:
    assert "from" in body
    assert "from_" not in body


def test_range_lib_version_is_rules_version(body: dict) -> None:
    assert body["libVersion"] == rules.__version__
    assert rules.PORTED_FROM == "workmate.planner 1.3.1"


def test_range_envelope(body: dict) -> None:
    assert body["ok"] is True
    assert body["apiVersion"] == planner_router.__version__
    assert body["actor"] == ACTOR
    assert isinstance(body["ms"], int) and body["ms"] >= 0


# ---------------------------------------------------------------------------
# §7.3 data behaviour
# ---------------------------------------------------------------------------


def test_range_counts_are_consistent(body: dict) -> None:
    c = body["counts"]
    cats = [w["cat"] for w in body["wos"]]
    assert c["total"] == len(body["wos"])
    assert c["wo"] == sum(1 for x in cats if x in ("WO", "REQ"))
    assert c["pm"] == sum(1 for x in cats if x == "PM")
    assert c["done"] == sum(1 for x in cats if x == "DONE")
    assert c["wo"] + c["pm"] + c["done"] == c["total"]


def test_range_today_is_configured_tz(body: dict) -> None:
    expect = datetime.now(ZoneInfo(get_settings().tz)).date().isoformat()
    assert body["today"] == expect


def test_range_load_keys_are_strings(body: dict) -> None:
    assert body["load"], "window has labour or estimates"
    assert all(isinstance(k, str) for k in body["load"])
    assert all(isinstance(v, int | float) for v in body["load"].values())


def test_range_worker_weeks_keys_are_strings(body: dict) -> None:
    for k, rows in body["workerWeeks"].items():
        assert isinstance(k, str)
        assert all(r["flag"] in ("over", "ok", "under", "empty") for r in rows)


def test_range_weeks_cover_window(body: dict) -> None:
    f, t = date.fromisoformat(FROM), date.fromisoformat(TO)
    weeks = body["weeks"]
    assert weeks
    w0 = date.fromisoformat(weeks[0]["weekStart"])
    assert w0.weekday() == 0 and w0 <= f and (f - w0).days < 7
    assert date.fromisoformat(weeks[-1]["weekStart"]) <= t
    assert sum(w["count"] for w in weeks) == body["counts"]["total"]


def test_range_by_wo_index_matches_full_scan(body: dict) -> None:
    """Spec §3.3: the per-WO labour subset must give exactly what the Ignition full-list scan gives."""
    full = body["labour"]
    for wo in body["wos"]:
        h, src = rules.hoursFor(wo, full)
        assert (wo["hrs"], wo["hrsSrc"]) == (h, src), wo["id"]
        assert wo["assigned"] == rules.assignedFor(wo, full), wo["id"]


def test_range_pin_table_false_on_rst(body: dict) -> None:
    """OD-1 ground truth. Trip-wire: flips to True when S3 migration 0002 lands - update then."""
    assert body["pinTable"] is False
    assert all(w["pinned"] is False and w["engineDate"] == "" and w["pinnedOn"] == "" for w in body["wos"])


# ---------------------------------------------------------------------------
# §7.4 guards and routing
# ---------------------------------------------------------------------------


def _assert_bad_window(r) -> None:
    assert r.status_code == 400, r.text
    b = r.json()
    assert b["ok"] is False and b["code"] == "BAD_WINDOW"
    assert isinstance(b["message"], str) and b["message"]
    assert "error" not in b  # flat (OD-15), not the nested Ignition shape


def test_range_bad_iso_is_400(client: TestClient) -> None:
    _assert_bad_window(client.get(RANGE, params={"from": "2026-02-31", "to": TO}))


def test_range_reversed_window_is_400(client: TestClient) -> None:
    _assert_bad_window(client.get(RANGE, params={"from": TO, "to": FROM}))


def test_range_exactly_400_days_is_200(client: TestClient) -> None:
    r = client.get(RANGE, params={"from": "2025-09-14", "to": "2026-10-19"})
    assert r.status_code == 200, r.text
    assert r.json()["counts"]["total"] > 0


def test_range_401_days_is_400(client: TestClient) -> None:
    _assert_bad_window(client.get(RANGE, params={"from": "2025-09-14", "to": "2026-10-20"}))


def test_range_missing_params_is_422(client: TestClient) -> None:
    assert client.get(RANGE, params={"from": FROM}).status_code == 422
    assert client.get(RANGE).status_code == 422


def test_range_post_is_405(client: TestClient) -> None:
    r = client.post(RANGE, json={"from": FROM, "to": TO})
    assert r.status_code == 405
    b = r.json()
    assert b["ok"] is False and b["code"] == "METHOD_NOT_ALLOWED"


def test_range_401_without_actor(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKMATE_ENV", "test")
    get_settings.cache_clear()
    saved = app.dependency_overrides.pop(deps.get_current_actor)
    try:
        r = client.get(RANGE, params={"from": FROM, "to": TO})
    finally:
        app.dependency_overrides[deps.get_current_actor] = saved
        get_settings.cache_clear()
    assert r.status_code == 401, r.text
    b = r.json()
    assert b["ok"] is False and b["code"] == "NO_IDENTITY"


def test_range_response_model_rejects_drift(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """extra="forbid": a key the service adds must be a loud 500, never silently dropped."""
    real = planner_router.service.range_data

    def drifted(conn, f, t):
        d = real(conn, f, t)
        d["gate"] = True
        return d

    monkeypatch.setattr(planner_router.service, "range_data", drifted)
    r = client.get(RANGE, params={"from": FROM, "to": TO})
    assert r.status_code == 500
    assert r.json()["code"] == "INTERNAL"


# ---------------------------------------------------------------------------
# §9 acceptance - one [F] line per request, Ignition text
# ---------------------------------------------------------------------------


def test_range_forensic_line_once(client: TestClient, capfd: pytest.CaptureFixture[str]) -> None:
    """capfd, not caplog (S1d OD-18). diag.py 1.1.0 sets propagate=False, so caplog's root handler sees
    nothing - and caplog only ever proved diag.log() was CALLED. This proves the line reached stdout.
    The middleware's own outcome line is in the same capture but carries no `rows=`, so the count holds."""
    r = client.get(RANGE, params={"from": FROM, "to": TO})
    assert r.status_code == 200
    lines = [x.strip() for x in capfd.readouterr().out.splitlines() if x.strip().startswith("{")]
    hits = [json.loads(x)["message"] for x in lines if f"range {FROM}..{TO} rows=" in x]
    assert len(hits) == 1, hits
    assert "labour=" in hits[0] and "workers=" in hits[0] and "pinTable=" in hits[0] and " ms" in hits[0]
