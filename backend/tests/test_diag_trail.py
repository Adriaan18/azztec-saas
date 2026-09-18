"""
Azztec_SaaS_test_diag_trail_v1_0_1.py  ->  backend/tests/test_diag_trail.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md §5 · pair of app/diag/sql.py + repo.py + router.py 1.0.0

Six cases need no database: the statements compile, name their binds, carry their PG-CONVERT tags and
keep colons out of SQL comments (Landmines §B - text() reads one as a bind). Four need one, and they run
inside a transaction that is rolled back, so the marker row exists only for the length of the test;
delete_by_id is still exercised, because Marker Law is the habit, not the rollback.

The connection fixture is the planner's: unreachable database -> skip with the driver's own message.

Changelog:
  1.0.1  Ruff SIM115 on the first run: the module source is read with Path.read_text, not a bare open().
         Ten cases, unchanged.
  1.0.0  Initial D1a. 10 cases.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core import db, diag
from app.diag import repo
from app.diag import sql as dsql

os.environ.setdefault("WORKMATE_ENV", "test")

TEST_VERSION = "1.0.1"

MARKER_RID = "d1a-marker-rid"
MARKER_ACTOR = 21  # Azzmax logon (OD-56) - the row says who, which is the whole point of the slice


# ---------------------------------------------------------------------------
# no database
# ---------------------------------------------------------------------------


# 1
def test_versions_and_the_statement_set() -> None:
    assert dsql.__version__ == "1.0.0" and repo.__version__ == "1.0.0"
    assert set(dsql.STATEMENTS) == {
        "INSERT",
        "TRAIL",
        "PROBLEMS",
        "BY_RID",
        "WHOISON",
        "USERS",
        "PURGE_COUNT",
        "PURGE_BATCH",
        "DELETE_BY_ID",
    }


# 2
def test_every_statement_compiles_and_names_its_binds() -> None:
    expected = {
        "INSERT": {
            "session_id",
            "wm_user_id",
            "site_code",
            "source",
            "tier",
            "msg_level",
            "message",
            "detail",
        },
        "TRAIL": {"user_id", "minutes_back", "problems_only", "row_limit"},
        "PROBLEMS": {"hours_back", "row_limit"},
        "BY_RID": {"session_id", "row_limit"},
        "WHOISON": {"minutes_back"},
        "USERS": {"minutes_back"},
        "PURGE_COUNT": {"days"},
        "PURGE_BATCH": {"days", "batch"},
        "DELETE_BY_ID": {"diag_id"},
    }
    for name, stmt in dsql.STATEMENTS.items():
        binds = set(text(stmt).compile().params)
        assert binds == expected[name], (name, binds)


# 3
def test_no_colon_inside_a_sql_comment() -> None:
    """A colon in a SQL comment is read as a bind parameter. Every tag lives in a Python comment instead."""
    for name, stmt in dsql.STATEMENTS.items():
        for line in stmt.splitlines():
            if "--" in line:
                assert ":" not in line.split("--", 1)[1], (name, line)


# 4
def test_the_trail_is_capped_filtered_and_windowed() -> None:
    s = dsql.TRAIL
    assert "FETCH NEXT :row_limit ROWS ONLY" in s  # the row cap is portable; no dialect-only row limiter
    assert ":user_id = 0 OR L.Wm_User_Id = :user_id" in s  # 0 means everyone, as at KT
    assert ":problems_only = 0 OR L.Tier IN ('E', 'G')" in s
    assert "DATEADD(minute, -:minutes_back, CURRENT_TIMESTAMP)" in s
    assert "LEFT JOIN dbo.Users" in s and "RTRIM(U.User_Name)" in s  # a row with no user still comes back


# 5
def test_problems_and_whoison_match_the_kt_routines() -> None:
    assert "L.Tier IN ('E', 'G')" in dsql.PROBLEMS
    assert "DATEADD(hour, -:hours_back, CURRENT_TIMESTAMP)" in dsql.PROBLEMS
    assert "MAX(L.Logged_At)" in dsql.WHOISON and "GROUP BY L.Wm_User_Id" in dsql.WHOISON
    assert "WHEN L.Tier = 'E'" in dsql.WHOISON and "WHEN L.Tier = 'G'" in dsql.WHOISON


# 6
def test_the_purge_is_batched_dated_and_tagged() -> None:
    assert "FETCH NEXT :batch ROWS ONLY" in dsql.PURGE_BATCH
    assert "DATEADD(day, -:days, CURRENT_TIMESTAMP)" in dsql.PURGE_BATCH
    assert "Logged_At <" in dsql.PURGE_BATCH  # never a delete without the date filter
    src = Path(dsql.__file__).read_text(encoding="utf-8")
    assert src.count("PG-CONVERT") >= 5  # every dated statement carries its tag, in a PYTHON comment
    assert dsql.DEFAULT_RETENTION_DAYS == 60 and dsql.PURGE_BATCH_ROWS == 5000


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


def _write_marker(conn, tier: str = "F", message: str = "d1a marker") -> None:
    db.execute(
        conn,
        dsql.INSERT,
        **diag.record(tier, message, actor=MARKER_ACTOR, source="diag", request_id=MARKER_RID),
    )


# 7
def test_a_row_written_the_way_the_writer_writes_it_reads_back(conn) -> None:
    _write_marker(conn)
    found = repo.by_rid(conn, MARKER_RID)
    assert len(found) == 1
    row = found[0]
    assert row["Message"] == "d1a marker"
    assert row["Wm_User_Id"] == MARKER_ACTOR
    assert row["Tier"] == "F" and row["Msg_Level"] == "info" and row["Source"] == "diag"
    assert row["Logged_At"] is not None  # the database clock stamped it, not the app
    assert re.match(r"^\d{4}-\d{2}-\d{2}", str(row["Logged_At"]))


# 8
def test_the_trail_finds_it_by_person_and_problems_only_filters(conn) -> None:
    _write_marker(conn, "E", "d1a marker crash")
    mine = repo.trail(conn, user_id=MARKER_ACTOR, minutes_back=5)
    assert any(r["Message"] == "d1a marker crash" for r in mine)
    assert all(r["Wm_User_Id"] == MARKER_ACTOR for r in mine)
    problems = repo.trail(conn, user_id=MARKER_ACTOR, minutes_back=5, problems_only=True)
    assert all(r["Tier"] in ("E", "G") for r in problems)
    assert any(r["Message"] == "d1a marker crash" for r in problems)
    assert any(r["Message"] == "d1a marker crash" for r in repo.problems(conn, hours_back=1))


# 9
def test_who_is_on_and_users_report_the_person(conn) -> None:
    _write_marker(conn)
    on = repo.who_is_on(conn, minutes_back=5)
    mine = [r for r in on if r["Wm_User_Id"] == MARKER_ACTOR]
    assert mine and mine[0]["Rows_Window"] >= 1
    assert mine[0]["User_Name"]  # the join resolved a real name - Azzmax logon
    assert any(r["Wm_User_Id"] == MARKER_ACTOR for r in repo.users(conn, minutes_back=60))


# 10
def test_purge_counts_without_deleting_and_the_marker_goes_by_id(conn) -> None:
    _write_marker(conn)
    before = repo.trail(conn, user_id=MARKER_ACTOR, minutes_back=5)
    dry = repo.purge(conn, days=60, dry_run=True)
    assert dry["dryRun"] is True and dry["deleted"] == 0 and dry["cutoffDays"] == 60
    after = repo.trail(conn, user_id=MARKER_ACTOR, minutes_back=5)
    assert len(after) == len(before)  # a dry run deletes nothing, ever
    assert repo.retention_days(conn) == 60  # no DIAG_RETENTION_DAYS row on RST, so the default stands
    # Marker Law: the only row this file removes is the one it wrote
    removed = repo.delete_by_id(conn, int(before[0]["Diag_Id"]))
    assert removed == 1
