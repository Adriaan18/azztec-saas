"""
Azztec_SaaS_test_workorders_repo_v1_0_0.py  ->  backend/tests/test_workorders_repo.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_0.md §5
Pair of app/workorders/repo.py 1.0.0 and app/workorders/sql.py 1.0.0. Two halves:
  - no DB: the PG-CONVERT / dialect gate over sql.py (the test_planner_repo pattern - ALL_STATEMENTS and
    the whole module source), colon-free comments, named binds only, and three structural checks
  - RST DB, one connection inside a transaction that is rolled back (D-10): every statement runs once
    on dbWorkmate as restored 2026-09-19 - WO 662704 (the newest header), the seven headers without
    a details row, an archive-only id, a linked child, a WO with queries and one with PO lines, all
    found by control queries so the tests hold when the ids move
Skips only when the database is unreachable (the repo-test precedent); no other skip.

Changelog:
  1.0.0  Initial W1a.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("WORKMATE_ENV", "test")

from app.core import db  # noqa: E402 - after env is set
from app.workorders import repo, rules  # noqa: E402
from app.workorders import sql as wsql  # noqa: E402

__version__ = "1.0.0"

WO_662704 = 662704  # the newest live header on RST as restored (Block W1-E, 2026-09-19)
NOT_A_WO = 999_999_999

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

LIST_KEYS = {"id", "sid", "title", "asset", "loc", "status", "prog", "hasPO", "entry", "badge"}
EVENT_KEYS = {
    "seq", "eventId", "event", "detail", "date", "editorId", "editor", "siteCode", "siteName",
    "source", "server",
}  # fmt: skip
LINKED_KEYS = {
    "id", "sid", "title", "status", "prog", "hasPO", "badge", "level", "rel", "parentId", "parentSid",
    "start", "entry", "selected",
}  # fmt: skip
QUERY_KEYS = {"id", "type", "typeLabel", "queryFrom", "queryTo", "desc", "date", "pairId", "emailed"}
PO_KEYS = {"poSid", "status", "badge", "due", "supplier", "description", "qty", "unitCost"}
RESOURCE_KEYS = {"type", "item", "planQty", "planCost", "actQty", "actCost", "delta"}


def _badge(row: dict) -> str:
    return f"{row['status']}|{row['sid']}|{row['prog']}|{1 if row['hasPO'] else 0}"


# ---------------------------------------------------------------------------
# no DB - the dialect gate
# ---------------------------------------------------------------------------

MSSQL_ONLY = re.compile(r"ISNULL\s*\(|GETDATE\s*\(|SELECT\s+TOP|\[dbo\]", re.IGNORECASE)


@pytest.mark.parametrize("name", sorted(wsql.ALL_STATEMENTS))
def test_sql_has_no_mssql_only_idioms(name):
    statement = wsql.ALL_STATEMENTS[name]
    hits = [ln.strip() for ln in statement.splitlines() if MSSQL_ONLY.search(ln)]
    untagged = [ln for ln in hits if "PG-CONVERT" not in ln]
    assert not untagged, f"{name}: {untagged}"


def test_sql_module_source_is_gate_clean():
    """The CI gate greps the WHOLE sql.py - comments and docstring included."""
    source = Path(wsql.__file__).read_text(encoding="utf-8")
    hits = [
        f"{n}: {ln.strip()}"
        for n, ln in enumerate(source.splitlines(), start=1)
        if MSSQL_ONLY.search(ln) and "PG-CONVERT" not in ln
    ]
    assert not hits, hits


@pytest.mark.parametrize("name", sorted(wsql.ALL_STATEMENTS))
def test_sql_has_no_colon_in_comments(name):
    """SQLAlchemy text() reads :name inside a SQL comment as a bind (Landmines §B)."""
    for ln in wsql.ALL_STATEMENTS[name].splitlines():
        if "--" in ln:
            assert ":" not in ln.split("--", 1)[1], f"{name}: {ln.strip()}"


def test_sql_uses_named_binds_only():
    for name, statement in wsql.ALL_STATEMENTS.items():
        assert "?" not in statement, name


def test_search_variants_differ_in_the_arms_only():
    assert "WO_N_Header" in wsql.SEARCH_LIVE and "WO_C_header" not in wsql.SEARCH_LIVE
    assert "WO_C_header" in wsql.SEARCH_ARCHIVE and "WO_N_Header" not in wsql.SEARCH_ARCHIVE
    assert "UNION ALL" in wsql.SEARCH_BOTH and "UNION ALL" not in wsql.SEARCH_LIVE
    assert ":closed" in wsql.SEARCH_LIVE and ":closed" not in wsql.SEARCH_ARCHIVE  # trap 3, parity
    for statement in (wsql.SEARCH_LIVE, wsql.SEARCH_ARCHIVE, wsql.SEARCH_BOTH):
        assert "ORDER BY s.Entry_date DESC, s.WO_ID DESC" in statement  # the tie-break the NQ lacks
        assert "OFFSET :offset ROWS FETCH NEXT :take ROWS ONLY" in statement


def test_item_left_joins_the_details():
    """OD-65: INNER JOIN in the oracle's Item, LEFT here - and the D_WO_ID sentinel is selected."""
    assert "LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID" in wsql.WO_ITEM
    assert "INNER JOIN dbo.WO_N_Details" not in wsql.WO_ITEM
    assert "d.WO_ID AS D_WO_ID" in wsql.WO_ITEM


def test_events_keep_a_deterministic_order():
    assert "ORDER BY e.Edited_Date DESC, e.Sys_WO_Event_Id DESC" in wsql.EVENTS
    assert "ORDER BY Progress_Id" in wsql.PROGRESS_ALL  # OD-67, by id not title


# ---------------------------------------------------------------------------
# RST DB - rolled back
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def conn():
    try:
        engine = db.get_engine()
        c = engine.connect()
    except Exception as e:  # noqa: BLE001 - reported as a skip reason
        pytest.skip(f"database unreachable: {db.db_error(e)}")
    trans = c.begin()
    try:
        yield c
    finally:
        trans.rollback()
        c.close()


def _one(conn, statement: str, **params) -> int:
    rows = db.rows(conn, statement, **params)
    assert rows, f"control query returned nothing: {statement.strip()[:80]}"
    return int(next(iter(rows[0].values())))


def test_search_default_is_open_normal_wos(conn):
    rows, more = repo.search(conn)
    assert len(rows) == 200 and more is True
    for r in rows:
        assert set(r) == LIST_KEYS
        assert r["status"] not in ("C", "D")
        assert r["badge"] == _badge(r)
        assert STAMP.match(r["entry"]), r["entry"]
    assert rows[0]["id"] == WO_662704  # the newest header, the first row


def test_search_closed_only(conn):
    rows, _ = repo.search(conn, closed=2, limit=50)
    assert rows and all(r["status"] in ("C", "D") for r in rows)


def test_search_archive_only(conn):
    rows, _ = repo.search(conn, archive=2, limit=20)
    assert rows
    for r in rows[:5]:
        assert repo.archived_exists(conn, r["id"]) is True
        assert repo.live_exists(conn, r["id"]) is False


def test_search_both_arms(conn):
    """closed=1 + archive=1 is the handoff's 'everything' (Search v12 mode 1 on both)."""
    rows, more = repo.search(conn, closed=1, archive=1, limit=20)
    assert len(rows) == 20 and more is True


def test_search_term_matches_sid_or_title(conn):
    term = "3CL-260826-01"
    rows, _ = repo.search(conn, q=term, closed=1)
    assert any(r["id"] == WO_662704 for r in rows)
    for r in rows:
        assert term.lower() in r["sid"].lower() or term.lower() in r["title"].lower()
    rows2, _ = repo.search(conn, q="bin 16", closed=1)
    assert rows2 and all("bin 16" in (r["sid"] + " " + r["title"]).lower() for r in rows2)


def test_search_paging_and_order(conn):
    first, more1 = repo.search(conn, limit=5)
    second, _ = repo.search(conn, limit=5, offset=5)
    assert len(first) == 5 and more1 is True and len(second) == 5
    assert {r["id"] for r in first}.isdisjoint({r["id"] for r in second})
    page, _ = repo.search(conn, limit=100)
    keys = [(r["entry"], r["id"]) for r in page]
    assert keys == sorted(keys, reverse=True)  # Entry_date DESC, WO_ID DESC


def test_fetch_item_662704(conn):
    rec = repo.fetch_item(conn, WO_662704)
    assert rec is not None
    assert rec["sid"] == "3CL-260826-010" and rec["status"] == "V" and rec["statusTitle"] == "Active"
    assert rec["type"] == "N" and rec["prog"] == 6 and rec["priId"] == 1
    assert rec["progTitle"] == "100% Complete"
    assert rec["start"] == "2026-08-26" and rec["startTime"] == "19:17"
    assert rec["end"] == "2026-09-02" and rec["completeWithin"] == "week"
    assert rec["weekNo"] == 2026.35
    assert rec["lastSaveDate"] == "2026-08-26 19:19:04"  # milliseconds dropped
    assert rec["hierarchy"] == (
        "Red Stag Timber Waipa > 3 Secondary Processing > 08 Coastal > 090 Viking Bins > 170 Bin 16"
    )
    assert rec["hierarchyRaw"].startswith("{(1)(RST-00)(Red Stag Timber Waipa)}")
    assert rec["detailsMissing"] is False
    assert rec["respUsers"] == []  # WO_Responsible_User is empty on RST as restored
    assert rec["filtersFor"] == {
        "includeClosed": 0, "includeArchive": 0, "woType": "N", "search": "", "limit": 200, "offset": 0,
    }  # fmt: skip
    assert rec["asset"] and rec["assetTitle"] and rec["loc"].startswith("3CL-")


def test_fetch_item_without_details_row(conn):
    """OD-65: seven live headers have no WO_N_Details row on RST; the record still reads."""
    wo_id = _one(
        conn,
        "SELECT h.WO_ID FROM dbo.WO_N_Header h LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID "
        "WHERE d.WO_ID IS NULL ORDER BY h.WO_ID OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY",
    )
    rec = repo.fetch_item(conn, wo_id)
    assert rec is not None and rec["detailsMissing"] is True
    assert rec["prog"] == 0 and rec["priId"] == 0 and rec["notes"] == "" and rec["lastSaveDate"] == ""
    assert rec["progTitle"] == "" and rec["completeWithin"] in rules.SEGMENTS  # the dates are on the header


def test_exists_helpers_and_the_archive_split(conn):
    assert repo.live_exists(conn, WO_662704) is True
    assert repo.archived_exists(conn, WO_662704) is False
    assert repo.live_exists(conn, NOT_A_WO) is False and repo.archived_exists(conn, NOT_A_WO) is False
    archived = _one(
        conn,
        "SELECT c.WO_ID FROM dbo.WO_C_header c WHERE NOT EXISTS "
        "(SELECT 1 FROM dbo.WO_N_Header h WHERE h.WO_ID = c.WO_ID) "
        "ORDER BY c.WO_ID DESC OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY",
    )
    assert repo.archived_exists(conn, archived) is True and repo.live_exists(conn, archived) is False
    assert repo.fetch_item(conn, archived) is None


def test_events_662704(conn):
    rows, more = repo.fetch_events(conn, WO_662704)
    assert len(rows) >= 5 and more is False
    assert [r["seq"] for r in rows] == list(range(1, len(rows) + 1))
    for r in rows:
        assert set(r) == EVENT_KEYS
        assert "{" not in r["detail"] and "}" not in r["detail"]
        assert STAMP.match(r["date"]), r["date"]
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates, reverse=True)
    assert rows[0]["source"] == "WO Maintenance" and rows[0]["server"] == ""
    page, more2 = repo.fetch_events(conn, WO_662704, limit=2)
    assert len(page) == 2 and more2 is True and page[0]["seq"] == 1
    page2, _ = repo.fetch_events(conn, WO_662704, offset=2, limit=2)
    assert page2 and page2[0]["seq"] == 3 and page2[0]["eventId"] != page[0]["eventId"]


def test_linked_family(conn):
    lone = repo.fetch_linked(conn, WO_662704)
    assert lone["count"] >= 1 and lone["root"] and set(lone["rows"][0]) == LINKED_KEYS
    assert sum(1 for r in lone["rows"] if r["selected"]) == 1
    child = _one(
        conn,
        "SELECT h.WO_ID FROM dbo.WO_N_Header h WHERE COALESCE(h.Linked_to_WO, 0) > 0 "
        "AND EXISTS (SELECT 1 FROM dbo.WO_N_Header p WHERE p.WO_ID = h.Linked_to_WO) "
        "ORDER BY h.WO_ID DESC OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY",
    )
    fam = repo.fetch_linked(conn, child)
    assert fam["count"] >= 2
    me = next(r for r in fam["rows"] if r["selected"])
    assert me["id"] == child and me["level"] >= 1 and me["parentId"] > 0 and me["parentSid"]
    assert me["rel"].endswith(" (this WO)")
    assert fam["rows"][0]["level"] == 0 and fam["rows"][0]["rel"] == "Parent"
    assert fam["root"] == fam["rows"][0]["sid"]
    for r in fam["rows"]:
        assert r["badge"] == _badge(r)


def test_queries(conn):
    wo_id = _one(
        conn,
        "SELECT WO_Id FROM dbo.WO_Query WHERE RTRIM(COALESCE(Query_Type, '')) = 'Q' "
        "ORDER BY Query_Date DESC OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY",
    )
    rows = repo.fetch_queries(conn, wo_id)
    assert rows and all(set(r) == QUERY_KEYS for r in rows)
    assert any(r["type"] == "Q" and r["typeLabel"] == "Query" for r in rows)
    assert all(isinstance(r["emailed"], bool) for r in rows)
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates, reverse=True)
    assert repo.fetch_queries(conn, NOT_A_WO) == []


def test_po_lines(conn):
    wo_id = _one(
        conn,
        "SELECT WO_Id FROM dbo.PO_Details WHERE WO_Id IS NOT NULL "
        "ORDER BY PO_Detail_ID DESC OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY",
    )
    rows = repo.fetch_po_lines(conn, wo_id)
    assert rows and all(set(r) == PO_KEYS for r in rows)
    for r in rows:
        assert r["badge"] == f"{r['status']}|{r['poSid']}"
        assert r["due"] == "" or ISO_DATE.match(r["due"]), r["due"]
    assert repo.fetch_po_lines(conn, NOT_A_WO) == []


def test_resources_compare(conn):
    res = repo.fetch_resources(conn, WO_662704)
    assert set(res) == {"rows", "planned", "actual", "diff", "line"}
    assert all(set(r) == RESOURCE_KEYS for r in res["rows"])
    assert res["line"].startswith("Planned $") and "  |  Actual $" in res["line"]
    assert abs(res["diff"] - (res["actual"] - res["planned"])) < 1e-6
    for r in res["rows"]:
        assert r["type"] in ("Part", "Labour", "Service")
        assert (r["planQty"] is None) == r["item"].endswith(" (unplanned)")


def test_progress_all(conn):
    rows = repo.fetch_progress(conn)
    ids = [r["id"] for r in rows]
    assert ids == sorted(ids) and {1, 2, 3, 4, 5, 6} <= set(ids)
    assert all(r["title"] for r in rows)
    assert next(r for r in rows if r["id"] == 1)["title"] == "No Progress"
