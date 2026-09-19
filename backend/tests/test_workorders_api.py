"""
Azztec_SaaS_test_workorders_api_v1_0_0.py  ->  backend/tests/test_workorders_api.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_0.md §5
Pair of app/workorders/router.py 1.0.0 + schemas.py 1.0.0 (+ main.py 0.5.0).
TestClient over the real app, DB dependency overridden with one RST connection inside a transaction that
is rolled back (D-10), actor dependency overridden (OD-12). WO 662704 is the newest live header on RST as
restored 2026-09-19; the archive-only and detail-less ids come from control queries. Zero skips.
Env trap: WORKMATE_ENV=test under pytest and get_settings() is lru_cached, so the un-overridden actor is a
401 by design. Persistence is off under test, so `persist=False` (OD-69) is proven by a spy on diag.log,
not by counting rows.

Changelog:
  1.0.0  Initial W1a.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection

os.environ.setdefault("WORKMATE_ENV", "test")

from app.core import db, deps, diag  # noqa: E402 - after env is set
from app.main import app  # noqa: E402
from app.workorders import repo  # noqa: E402
from app.workorders import router as wo_router  # noqa: E402
from app.workorders.schemas import WoRecord  # noqa: E402

__version__ = "1.0.0"

BASE = "/api/v1/workorders"
WO = 662704
NOT_A_WO = 999_999_999
ACTOR = 21  # Azzmax logon - the dev actor (log 09-19 §7)

ENVELOPE = {"ok", "apiVersion", "actor", "ms"}
LIST_KEYS = {"rows", "count", "more", "filters"} | ENVELOPE
ROW_KEYS = {"id", "sid", "title", "asset", "loc", "status", "prog", "hasPO", "entry", "badge"}
RECORD_KEYS = set(WoRecord.model_fields)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def conn() -> Iterator[Connection]:
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
def listing(client: TestClient) -> dict:
    r = client.get(BASE)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def record(client: TestClient) -> dict:
    r = client.get(f"{BASE}/{WO}")
    assert r.status_code == 200, r.text
    return r.json()


def _first(conn: Connection, statement: str) -> int:
    rows = db.rows(conn, statement)
    assert rows, statement
    return int(next(iter(rows[0].values())))


def _assert_flat(r, status: int, code: str) -> None:
    assert r.status_code == status, r.text
    b = r.json()
    assert b["ok"] is False and b["code"] == code and b["message"] and "rid" in b


# ---------------------------------------------------------------------------
# the list
# ---------------------------------------------------------------------------


def test_list_envelope_and_defaults(listing: dict) -> None:
    assert set(listing) == LIST_KEYS
    assert listing["ok"] is True and listing["apiVersion"] == wo_router.__version__
    assert listing["actor"] == ACTOR and isinstance(listing["ms"], int)
    assert listing["filters"] == {
        "woType": "N", "includeClosed": 0, "includeArchive": 0, "search": "", "limit": 200, "offset": 0,
    }  # fmt: skip
    assert listing["count"] == 200 == len(listing["rows"]) and listing["more"] is True


def test_list_rows_are_open_normal_wos(listing: dict) -> None:
    for row in listing["rows"]:
        assert set(row) == ROW_KEYS
        assert row["status"] not in ("C", "D")
        assert row["badge"] == f"{row['status']}|{row['sid']}|{row['prog']}|{1 if row['hasPO'] else 0}"
    assert listing["rows"][0]["id"] == WO


def test_list_bad_wo_type_is_400_bad_filter(client: TestClient) -> None:
    _assert_flat(client.get(BASE, params={"woType": "X"}), 400, "BAD_FILTER")


def test_list_all_types_and_cp(client: TestClient) -> None:
    r = client.get(BASE, params={"woType": "", "limit": 5})
    assert r.status_code == 200 and r.json()["count"] == 5 and r.json()["filters"]["woType"] == ""
    r = client.get(BASE, params={"woType": "CP"})
    assert r.status_code == 200 and r.json()["count"] == 0  # RST has no CP location (Block W1-E)
    r = client.get(BASE, params={"woType": "M", "limit": 5})
    assert r.status_code == 200 and r.json()["count"] == 5


def test_list_range_violations_are_422(client: TestClient) -> None:
    assert client.get(BASE, params={"includeClosed": 3}).status_code == 422
    assert client.get(BASE, params={"includeArchive": -1}).status_code == 422
    assert client.get(BASE, params={"limit": 1001}).status_code == 422
    assert client.get(BASE, params={"limit": 0}).status_code == 422
    assert client.get(BASE, params={"offset": -1}).status_code == 422


def test_list_paging(client: TestClient) -> None:
    a = client.get(BASE, params={"limit": 3}).json()
    b = client.get(BASE, params={"limit": 3, "offset": 3}).json()
    assert a["count"] == 3 and a["more"] is True and b["count"] == 3 and b["filters"]["offset"] == 3
    assert {r["id"] for r in a["rows"]}.isdisjoint({r["id"] for r in b["rows"]})


def test_list_search_term(client: TestClient) -> None:
    r = client.get(BASE, params={"search": " 3CL-260826-01 ", "includeClosed": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["filters"]["search"] == "3CL-260826-01"  # trimmed
    assert any(row["id"] == WO for row in body["rows"])


def test_list_closed_and_archive_modes(client: TestClient) -> None:
    closed = client.get(BASE, params={"includeClosed": 2, "limit": 10}).json()
    assert closed["count"] == 10 and all(r["status"] in ("C", "D") for r in closed["rows"])
    archive = client.get(BASE, params={"includeArchive": 2, "limit": 10}).json()
    assert archive["count"] == 10 and archive["filters"]["includeArchive"] == 2


# ---------------------------------------------------------------------------
# the record
# ---------------------------------------------------------------------------


def test_record_keys_match_the_schema(record: dict) -> None:
    assert set(record) == RECORD_KEYS
    assert record["ok"] is True and record["apiVersion"] == wo_router.__version__ and record["actor"] == ACTOR


def test_record_values_662704(record: dict) -> None:
    assert record["id"] == WO and record["sid"] == "3CL-260826-010" and record["status"] == "V"
    assert record["completeWithin"] == "week" and record["prog"] == 6 and record["detailsMissing"] is False
    assert record["progTitle"] == "100% Complete"
    assert [p["id"] for p in record["progressAll"]] == sorted(p["id"] for p in record["progressAll"])
    assert {1, 2, 3, 4, 5, 6} <= {p["id"] for p in record["progressAll"]}
    assert record["filtersFor"]["woType"] == "N" and record["filtersFor"]["includeClosed"] == 0
    assert record["hierarchy"].startswith("Red Stag Timber Waipa > ")
    assert set(record["resources"]) == {"rows", "planned", "actual", "diff", "line"}
    assert record["respUsers"] == []


def test_record_not_found_is_404_flat(client: TestClient) -> None:
    _assert_flat(client.get(f"{BASE}/{NOT_A_WO}"), 404, "NOT_FOUND")


def test_record_archived_is_404_archived(client: TestClient, conn: Connection) -> None:
    archived = _first(
        conn,
        "SELECT c.WO_ID FROM dbo.WO_C_header c WHERE NOT EXISTS "
        "(SELECT 1 FROM dbo.WO_N_Header h WHERE h.WO_ID = c.WO_ID) "
        "ORDER BY c.WO_ID DESC OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY",
    )
    _assert_flat(client.get(f"{BASE}/{archived}"), 404, "ARCHIVED")


def test_record_bad_ids_are_422(client: TestClient) -> None:
    assert client.get(f"{BASE}/0").status_code == 422
    assert client.get(f"{BASE}/-1").status_code == 422
    assert client.get(f"{BASE}/abc").status_code == 422


def test_record_without_details_row_logs_a_g(
    client: TestClient, conn: Connection, capfd: pytest.CaptureFixture[str]
) -> None:
    """OD-65: the record reads, detailsMissing is true, and one [G] line names the WO."""
    wo_id = _first(
        conn,
        "SELECT h.WO_ID FROM dbo.WO_N_Header h LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID "
        "WHERE d.WO_ID IS NULL ORDER BY h.WO_ID OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY",
    )
    capfd.readouterr()
    r = client.get(f"{BASE}/{wo_id}")
    assert r.status_code == 200, r.text
    assert r.json()["detailsMissing"] is True and r.json()["prog"] == 0
    lines = [x for x in capfd.readouterr().out.splitlines() if x.strip().startswith("{")]
    gs = [json.loads(x) for x in lines if f"wo {wo_id} has no WO_N_Details row" in x]
    assert len(gs) == 1 and gs[0]["tag"] == "[G]" and gs[0]["actor"] == ACTOR


# ---------------------------------------------------------------------------
# the tabs
# ---------------------------------------------------------------------------


def test_events_shape_and_paging(client: TestClient) -> None:
    body = client.get(f"{BASE}/{WO}/events").json()
    assert set(body) == {"rows", "count", "more", "offset"} | ENVELOPE
    assert body["count"] >= 5 and body["more"] is False and body["offset"] == 0
    assert body["rows"][0]["seq"] == 1 and "{" not in body["rows"][0]["detail"]
    page = client.get(f"{BASE}/{WO}/events", params={"limit": 2, "offset": 2}).json()
    assert page["count"] == 2 and page["more"] is True and page["rows"][0]["seq"] == 3
    assert client.get(f"{BASE}/{WO}/events", params={"limit": 0}).status_code == 422


def test_linked_shape(client: TestClient) -> None:
    body = client.get(f"{BASE}/{WO}/linked").json()
    assert set(body) == {"rows", "count", "root"} | ENVELOPE
    assert body["count"] >= 1 and body["root"] == "3CL-260826-010"
    assert sum(1 for r in body["rows"] if r["selected"]) == 1


def test_queries_shape(client: TestClient) -> None:
    body = client.get(f"{BASE}/{WO}/queries").json()
    assert set(body) == {"rows", "count"} | ENVELOPE and body["count"] == len(body["rows"])
    keys = {"id", "type", "typeLabel", "queryFrom", "queryTo", "desc", "date", "pairId", "emailed"}
    for r in body["rows"]:
        assert set(r) == keys


def test_pos_shape(client: TestClient) -> None:
    body = client.get(f"{BASE}/{WO}/pos").json()
    assert set(body) == {"rows", "count"} | ENVELOPE and body["count"] == len(body["rows"])
    for r in body["rows"]:
        assert set(r) == {"poSid", "status", "badge", "due", "supplier", "description", "qty", "unitCost"}


def test_tabs_404_for_an_unknown_wo(client: TestClient) -> None:
    for tab in ("events", "linked", "queries", "pos"):
        _assert_flat(client.get(f"{BASE}/{NOT_A_WO}/{tab}"), 404, "NOT_FOUND")


# ---------------------------------------------------------------------------
# the edges the planner's tests pinned, repeated here
# ---------------------------------------------------------------------------


def test_post_is_405(client: TestClient) -> None:
    assert client.post(BASE).status_code == 405
    assert client.post(f"{BASE}/{WO}").status_code == 405


def test_401_without_actor(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKMATE_ENV", "test")
    saved = app.dependency_overrides.pop(deps.get_current_actor)
    try:
        _assert_flat(client.get(BASE), 401, "NO_IDENTITY")
    finally:
        app.dependency_overrides[deps.get_current_actor] = saved


def test_response_model_rejects_drift(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """extra="forbid": a key the repo adds must be a loud 500, never silently dropped."""
    real = repo.fetch_item

    def drifted(conn, wo_id):
        rec = real(conn, wo_id)
        rec["gate"] = True
        return rec

    monkeypatch.setattr(wo_router.repo, "fetch_item", drifted)
    r = client.get(f"{BASE}/{WO}")
    assert r.status_code == 500 and r.json()["code"] == "INTERNAL"


def test_forensic_line_once_and_not_persisted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    """One [F] per request on stdout (capfd - diag propagates nowhere, S1d OD-18) and OD-69: the read's
    own line passes persist=False. Persistence is off under test, so the flag is proven by a spy."""
    calls: list[tuple[tuple, dict]] = []
    real_log = diag.log

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return real_log(*args, **kwargs)

    monkeypatch.setattr(diag, "log", spy)
    capfd.readouterr()
    r = client.get(f"{BASE}/{WO}")
    assert r.status_code == 200
    lines = [x.strip() for x in capfd.readouterr().out.splitlines() if x.strip().startswith("{")]
    hits = [json.loads(x)["message"] for x in lines if f"wo {WO} 3CL-260826-010 status=" in x]
    assert len(hits) == 1, hits
    assert "within=week" in hits[0] and "details=ok" in hits[0] and " ms" in hits[0]
    mine = [kw for a, kw in calls if a and a[0] == "F" and str(a[1]).startswith(f"wo {WO} ")]
    assert mine and all(kw.get("persist") is False for kw in mine)


def test_health_reports_the_workorders_version(client: TestClient) -> None:
    body = client.get("/api/v1/health").json()
    assert body["version"] == "0.5.0"
    assert body["versions"]["workorders"] == wo_router.__version__
