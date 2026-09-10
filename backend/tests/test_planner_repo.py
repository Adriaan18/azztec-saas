"""
workmate_test_planner_repo_v1_0_1.py  ->  backend/tests/test_planner_repo.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_S1b_Data_Chunk_Spec_v1_0_0.md §6
Pair of:  backend/app/planner/sql.py 1.0.1 + backend/app/planner/repo.py 1.0.0

Two halves:
  - no DB: the PG-CONVERT / dialect gate, run as a unit test so a bad
    statement fails on a laptop, not in CI.
  - RST DB: every fetch inside a transaction that is ROLLED BACK (Ways of
    Working §4). This chunk is read-only, but dbWorkmate holds real RST data
    and the fixture is written now so S2 inherits it.

The DB half SKIPS with a clear reason when SQL Server is unreachable - a red
suite on a box without the database is noise, not signal.

Data-fact discipline: these tests check the PORT, not the data. RST-specific
numbers (uomHours = 12, 2,364 locked PMs, four-way Sort_Sequence ties) live
in the raw log; here they are derived from control queries so the suite still
means something when it is pointed at the KT dev copy.

Changelog:
  1.0.1  Ruff I001 on the app imports. Adds test_sql_module_source_is_gate_clean:
         1.0.0 only scanned ALL_STATEMENTS, so a banned token in sql.py's own
         docstring passed here and failed the CI grep. The unit test now reads
         the same thing CI reads - the whole file.
  1.0.0  Initial.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

os.environ.setdefault("WORKMATE_ENV", "test")

from app.core import db  # noqa: E402 - after env is set
from app.planner import repo  # noqa: E402
from app.planner import sql as psql  # noqa: E402
from app.planner.rules import buildWorkers, hoursFor  # noqa: E402

__version__ = "1.0.1"

# The project's canonical planner window (Ways of Working §6, Architecture §6).
FROM_D = date(2026, 9, 14)
TO_D = date(2026, 9, 20)

# Every contract key a WO dict must carry (port spec §3).
WO_KEYS = {
    "id", "sid", "title", "status", "statusTitle", "type", "cat", "start", "startTime",
    "end", "days", "weekNo", "prog", "priId", "pri", "estimate", "resp", "asset",
    "assetTitle", "loc", "locTitle", "hasPO", "engineOwned", "pinned", "pinnedOn",
    "engineDate", "locked", "movable", "hrs", "hrsSrc", "assigned",
}
LABOUR_KEYS = {"resId", "woId", "userId", "hours", "rate", "note", "date",
               "skillId", "skillTitle", "uomId"}

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HHMM = re.compile(r"^\d{2}:\d{2}$")


# ---------------------------------------------------------------------------
# no DB - the dialect gate
# ---------------------------------------------------------------------------

MSSQL_ONLY = re.compile(r"ISNULL\s*\(|GETDATE\s*\(|SELECT\s+TOP|\[dbo\]", re.IGNORECASE)


@pytest.mark.parametrize("name", sorted(psql.ALL_STATEMENTS))
def test_sql_has_no_mssql_only_idioms(name):
    """The CI grep gate, as a unit test. Anything caught here needs either a
    portable rewrite or an explicit PG-CONVERT tag on the line."""
    statement = psql.ALL_STATEMENTS[name]
    hits = [ln.strip() for ln in statement.splitlines() if MSSQL_ONLY.search(ln)]
    untagged = [ln for ln in hits if "PG-CONVERT" not in ln]
    assert not untagged, f"{name}: {untagged}"


def test_sql_module_source_is_gate_clean():
    """The CI gate greps the WHOLE sql.py file, comments and docstring
    included - not just the statements. Scan what CI scans, or a banned token
    in prose passes here and fails there (it did, in sql.py 1.0.0)."""
    source = Path(psql.__file__).read_text(encoding="utf-8")
    hits = [
        f"{n}: {ln.strip()}"
        for n, ln in enumerate(source.splitlines(), start=1)
        if MSSQL_ONLY.search(ln) and "PG-CONVERT" not in ln
    ]
    assert not hits, hits


@pytest.mark.parametrize("name", sorted(psql.ALL_STATEMENTS))
def test_sql_has_no_colon_in_comments(name):
    """SQLAlchemy text() reads :name inside a SQL comment as a bind parameter
    (Landmines §B). No comment in a statement may contain a colon."""
    for ln in psql.ALL_STATEMENTS[name].splitlines():
        if "--" in ln:
            assert ":" not in ln.split("--", 1)[1], f"{name}: {ln.strip()}"


def test_sql_uses_named_binds_only():
    """No leftover ? positional params from the Jython source."""
    for name, statement in psql.ALL_STATEMENTS.items():
        assert "?" not in statement, name


def test_priorities_keeps_the_second_sort_key():
    """RST has four-way ties on Sort_Sequence (raw log 8.2f). Priority_Id is
    the only thing making the contract order deterministic."""
    assert "ORDER BY Sort_Sequence, Priority_Id" in psql.PRIORITIES


def test_uom_modal_has_the_od11_tie_break():
    assert "ORDER BY COUNT(*) DESC, UOM_Id" in psql.UOM_MODAL


def test_pin_variants_differ_only_in_the_pin_columns():
    assert psql.WO_RANGE_PINNED != psql.WO_RANGE_NOPIN
    assert "WO_N_Plan" in psql.WO_RANGE_PINNED
    assert "WO_N_Plan" not in psql.WO_RANGE_NOPIN
    for statement in (psql.WO_RANGE_PINNED, psql.WO_RANGE_NOPIN):
        for col in ("AS Pinned", "AS Prev_Start", "AS Pinned_On"):
            assert col in statement


def test_exclusive_end_adds_one_day():
    """to_d is inclusive at the API, exclusive in the SQL."""
    assert repo._exclusive_end(TO_D).date() == TO_D + timedelta(days=1)
    assert repo._bound(FROM_D).date() == FROM_D


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
    repo.clear_caches()
    try:
        yield c
    finally:
        trans.rollback()
        c.close()
        repo.clear_caches()


@pytest.fixture(scope="module")
def wos(conn):
    rows = repo.fetch_wos(conn, FROM_D, TO_D)
    if not rows:
        pytest.skip(f"no work orders in {FROM_D}..{TO_D} - pick a denser window")
    return rows


def test_all_statements_compile(conn):
    """Both pin variants and every other statement parse on the live dialect.
    The pinned variant has no rows to return on RST (no WO_N_Plan) but it must
    still compile - it ships untested against real data until S3."""
    params = {"from_d": repo._bound(FROM_D), "to_d": repo._exclusive_end(FROM_D)}
    for name, statement in psql.ALL_STATEMENTS.items():
        binds = params if ":from_d" in statement else {}
        if name == "WO_RANGE_PINNED" and not repo.pin_table_exists(conn):
            continue  # cannot compile a reference to a table that does not exist
        db.rows(conn, statement, **binds)


def test_fetch_wos_shape(wos):
    for wo in wos[:50]:
        assert set(wo) == WO_KEYS
        assert ISO_DATE.match(wo["start"]), wo["start"]
        assert wo["startTime"] == "" or HHMM.match(wo["startTime"]), wo["startTime"]
        assert wo["end"] == "" or ISO_DATE.match(wo["end"])
        assert isinstance(wo["weekNo"], float)
        assert isinstance(wo["hasPO"], bool)
        assert wo["cat"] in ("DONE", "PM", "REQ", "WO")
        assert isinstance(wo["assigned"], list)


def test_window_is_inclusive_at_both_ends(conn, wos):
    """to_d is inclusive: a WO starting exactly on to_d must come back."""
    starts = {wo["start"] for wo in wos}
    assert min(starts) >= FROM_D.isoformat()
    assert max(starts) <= TO_D.isoformat()
    control = db.rows(
        conn,
        "SELECT COUNT(*) AS n FROM dbo.WO_N_Header "
        "WHERE RTRIM(COALESCE(Status, '')) <> 'D' "
        "AND CAST(Request_Start_Date AS date) = :d",
        d=TO_D,
    )[0]["n"]
    if not control:
        pytest.skip(f"no work order starts exactly on {TO_D} - boundary not exercised")
    assert sum(1 for wo in wos if wo["start"] == TO_D.isoformat()) == control


def test_cancelled_excluded(wos):
    assert not [wo for wo in wos if wo["status"] == "D"]


def test_pin_columns_default_off(conn, wos):
    if repo.pin_table_exists(conn):
        pytest.skip("WO_N_Plan exists - S3 has run, pin defaults no longer apply")
    assert not [wo for wo in wos if wo["pinned"]]
    assert not [wo for wo in wos if wo["pinnedOn"] or wo["engineDate"]]


def test_od1_engine_owned_pms_are_locked(conn, wos):
    """OD-1: without WO_N_Plan an engine-owned PM is locked and immovable.
    This is the decision working, not a defect - S3 unlocks them."""
    if repo.pin_table_exists(conn):
        pytest.skip("WO_N_Plan exists - OD-1 no longer applies")
    pms = [wo for wo in wos if wo["engineOwned"]]
    if not pms:
        pytest.skip("no engine-owned PMs in the window")
    assert all(wo["locked"] and not wo["movable"] for wo in pms)
    assert all(wo["type"] == "M" and wo["status"] not in ("V", "C", "D") for wo in pms)


def test_closed_and_cancelled_are_never_movable(wos):
    assert all(not wo["movable"] for wo in wos if wo["status"] in ("C", "D"))


def test_fetch_labour_shape(conn):
    rows = repo.fetch_labour(conn, FROM_D, TO_D)
    for r in rows[:50]:
        assert set(r) == LABOUR_KEYS
        assert r["date"] == "" or ISO_DATE.match(r["date"])
        assert isinstance(r["hours"], float)
        assert isinstance(r["userId"], int)


def test_fetch_priorities_matches_control_order(conn):
    got = [p["id"] for p in repo.fetch_priorities(conn)]
    control = [
        r["Priority_Id"]
        for r in db.rows(
            conn,
            "SELECT Priority_Id FROM dbo.Priority "
            "WHERE RTRIM(COALESCE(Active, '')) NOT IN ('0', 'N') "
            "ORDER BY Sort_Sequence, Priority_Id",
        )
    ]
    assert got == control
    assert got, "no active priorities"


def test_sort_sequence_ties_exist(conn):
    """Informational guard: the second sort key only matters because ties are
    real. Raw log 8.2f recorded four-way ties on RST."""
    ties = db.rows(
        conn,
        "SELECT Sort_Sequence, COUNT(*) AS n FROM dbo.Priority "
        "WHERE RTRIM(COALESCE(Active, '')) NOT IN ('0', 'N') "
        "GROUP BY Sort_Sequence HAVING COUNT(*) > 1",
    )
    if not ties:
        pytest.skip("no Sort_Sequence ties on this database - key is belt and braces here")
    assert max(t["n"] for t in ties) >= 2


def test_worker_rows_respect_both_active_domains(conn):
    rows = repo.fetch_skill_rows(conn)
    assert rows, "no active workers"
    ids = {r["userId"] for r in rows}
    inactive = db.rows(
        conn,
        "SELECT COUNT(*) AS n FROM dbo.Users "
        "WHERE RTRIM(COALESCE(Active, '')) <> 'Y' AND User_Id IN "
        "(SELECT User_ID FROM dbo.User_Skill)",
    )[0]["n"]
    assert inactive == 0 or not (ids & _inactive_user_ids(conn))
    assert all(r["userId"] > 0 for r in rows)


def _inactive_user_ids(conn) -> set[int]:
    return {
        r["User_Id"]
        for r in db.rows(
            conn,
            "SELECT User_Id FROM dbo.Users WHERE RTRIM(COALESCE(Active, '')) <> 'Y'",
        )
    }


def test_hours_uom_id_resolves_and_caches(conn):
    """Tests the resolution logic, not the RST value. RST answers 12 LABOUR
    HOURS (raw log 8.2d); that fact lives in the log, not in this assert."""
    repo.clear_caches()
    got = repo.hours_uom_id(conn)
    assert got > 0
    control = db.rows(
        conn,
        "SELECT UOM_Id FROM dbo.Unit_of_Measure "
        "WHERE RTRIM(COALESCE(LRStd, '')) IN ('1', 'Y') "
        "AND RTRIM(COALESCE(Active, '')) NOT IN ('0', 'N') "
        "ORDER BY UOM_Id",
    )
    if control:
        assert got == control[0]["UOM_Id"]
    assert repo.hours_uom_id(conn) == got  # cached


def test_rules_consume_repo_output(conn, wos):
    """The S1a/S1b seam - real rows through the pure rules. This is the thing
    most likely to be wrong, and the cheapest place to catch it."""
    labour = repo.fetch_labour(conn, FROM_D, TO_D)
    workers, teams = buildWorkers(repo.fetch_skill_rows(conn))
    assert workers and teams
    assert all(isinstance(w["hrsPerWeek"], float) for w in workers)
    assert [w["internal"] for w in workers] == sorted(
        (w["internal"] for w in workers), reverse=True
    ), "internal workers must sort first"
    for wo in wos[:50]:
        hrs, src = hoursFor(wo, labour)
        assert isinstance(hrs, float)
        assert src in ("labour", "estimate", "")
