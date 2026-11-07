"""
Azztec_SaaS_test_planner_repo_v1_0_4.py  ->  backend/tests/test_planner_repo.py
Version:  1.0.4
Author:   Adriaan
Spec:     Azztec_SaaS_S1b_Data_Chunk_Spec_v1_0_0.md §6
Pair of:  backend/app/planner/sql.py 1.2.0 + backend/app/planner/repo.py 1.2.0 (the read path and every
          statement's gates; the move's load and dry plans are in test_planner_move.py 1.0.0)

Two halves:
  - no DB: the PG-CONVERT / dialect gate, run as a unit test so a bad
    statement fails on a laptop, not in CI.
  - RST DB: every fetch inside a transaction that is ROLLED BACK (Ways of
    Working §4). The DB half never writes: test_all_statements_compile runs
    only the statements that start with SELECT; each writer goes to the
    server inside a branch that can never be taken, so it is compiled and
    nothing runs (OD-111).

The DB half SKIPS with a clear reason when SQL Server is unreachable - a red
suite on a box without the database is noise, not signal.

Data-fact discipline: these tests check the PORT, not the data. RST-specific
numbers (uomHours = 12, 2,364 locked PMs, four-way Sort_Sequence ties) live
in the raw log; here they are derived from control queries so the suite still
means something when it is pointed at the KT dev copy.

Changelog:
  1.0.4  DP3a, Block 1 run 1 (1 failed, 485 passed). test_all_statements_compile handed every
         ALL_STATEMENTS entry to db.rows with the range binds or none; LOAD_WO_PINNED binds wo_id, so it
         failed on the missing bind before anything reached the server. The obvious fix - pass the
         binds - would have sent the seven writers to the server to RUN, which no test may do (OD-111).
         1.0.3's "no assertion changed" was wrong: this test executes the statements, it is not a gate.
         Now every bind comes from _bind_samples by the names the statement uses (an unknown name fails
         with its own message); only a statement that starts with SELECT runs; any other statement is
         sent inside IF 1 = 0, so the server compiles it - an unknown column fails the batch - and runs
         nothing (no row, no lock, no identity value), after its target table is checked to exist
         (deferred name resolution would let a missing table through). New, no DB:
         test_only_selects_run_in_the_compile_check pins the seven writers to the compile-only side.
  1.0.3  DP3a. HEADER ONLY - the Pair line follows sql.py / repo.py 1.2.0. No assertion changed: the
         dialect gate and the colon gate are parametrised over sql.ALL_STATEMENTS, so they run over the
         eleven new entries by registration (18 statements, 36 cases), and test_sql_module_source_is_gate_clean
         reads the whole new file. Checked by hand against sql.py 1.2.0 before the card was cut.
  1.0.2  S1h. HEADER ONLY - the Pair line pointed at sql.py 1.0.1 and repo.py
         1.0.0, both of which moved to 1.1.0 when PRIORITIES gained Colour. No
         assertion changed and none needed to: this file checks the port, not
         the data, so the added column touches nothing -
         test_fetch_priorities_matches_control_order compares Priority_Id order
         only, and test_sql_module_source_is_gate_clean was re-run by hand
         against sql.py 1.1.0 (clean: the new comment prose carries none of the
         four banned tokens).
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
from decimal import Decimal
from pathlib import Path

import pytest

os.environ.setdefault("WORKMATE_ENV", "test")

from app.core import db  # noqa: E402 - after env is set
from app.planner import repo  # noqa: E402
from app.planner import sql as psql  # noqa: E402
from app.planner.rules import buildWorkers, hoursFor  # noqa: E402

__version__ = "1.0.4"

# The project's canonical planner window (Ways of Working §6, Architecture §6).
FROM_D = date(2026, 9, 14)
TO_D = date(2026, 9, 20)

# Every contract key a WO dict must carry (port spec §3).
WO_KEYS = {
    "id",
    "sid",
    "title",
    "status",
    "statusTitle",
    "type",
    "cat",
    "start",
    "startTime",
    "end",
    "days",
    "weekNo",
    "prog",
    "priId",
    "pri",
    "estimate",
    "resp",
    "asset",
    "assetTitle",
    "loc",
    "locTitle",
    "hasPO",
    "engineOwned",
    "pinned",
    "pinnedOn",
    "engineDate",
    "locked",
    "movable",
    "hrs",
    "hrsSrc",
    "assigned",
}
LABOUR_KEYS = {"resId", "woId", "userId", "hours", "rate", "note", "date", "skillId", "skillTitle", "uomId"}

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


# test_all_statements_compile's machinery. SQL_BIND is the pattern SQLAlchemy text() itself uses, so
# the names found here are exactly the binds the driver will ask for.
SQL_BIND = re.compile(r"(?<![:\w\x5c]):(\w+)(?!:)")
WRITE_TARGET = re.compile(
    r"\b(?:UPDATE|INSERT\s+INTO|DELETE\s+FROM|MERGE\s+INTO)\s+dbo\.(\w+)", re.IGNORECASE
)
DP3A_WRITERS = {
    "MOVE_HEADER",
    "SHIFT_SUBTASKS",
    "SHIFT_LABOUR",
    "PIN_UPDATE",
    "PIN_INSERT",
    "PIN_CLEAR",
    "EVENT_INSERT",
}


def _first_keyword(statement: str) -> str:
    for ln in statement.splitlines():
        s = ln.strip()
        if s and not s.startswith("--"):
            return s.split()[0].upper()
    return ""


def _runs(statement: str) -> bool:
    """Only a statement that starts with SELECT is run. Anything else - a writer, or a read that opens
    with WITH - is compiled and never run: a misread can only make a read compile-only, never make a
    writer run."""
    return _first_keyword(statement) == "SELECT"


def _never_run(statement: str) -> str:
    """The server compiles the whole batch, so an unknown column in the dead branch still fails it;
    the branch itself is never taken, so nothing is written, locked or numbered.
    PG-CONVERT: PostgreSQL has no IF outside a function - use EXPLAIN <statement> (plans, never runs)."""
    return f"IF 1 = 0\nBEGIN\n{statement}\nEND"


def _bind_samples() -> dict:
    """A value of the type the repo passes, for every bind name sql.py uses. wo_id and user_id 0 match
    no row, so the reads return nothing."""
    day = repo._bound(FROM_D)
    return {
        "from_d": day,
        "to_d": repo._exclusive_end(FROM_D),
        "wo_id": 0,
        "user_id": 0,
        "delta": 0,
        "week_no": Decimal("2026.38"),
        "new_start": day,
        "new_end": day,
        "day_from": day,
        "day_to": repo._exclusive_end(FROM_D),
        "engine_date": day,
        "note": "",
        "server_name": "SaaS",
        "source_form": "Planner",
        "event_name": "Rescheduled",
        "details": "",
    }


def test_only_selects_run_in_the_compile_check():
    """The DB half runs the reads and only compiles the writers - pinned here, without a database."""
    compiled_only = {name for name, statement in psql.ALL_STATEMENTS.items() if not _runs(statement)}
    assert compiled_only == DP3A_WRITERS
    for name in DP3A_WRITERS:
        statement = psql.ALL_STATEMENTS[name]
        assert WRITE_TARGET.search(statement), name
        assert set(SQL_BIND.findall(statement)) <= set(_bind_samples()), name


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
    """Every statement compiles on the live server, and the reads run. Each gets the binds it names,
    with the repo's own types. A writer is compiled inside IF 1 = 0 and never run (OD-111): rowcount
    stays at or below 0. A statement on WO_N_Plan is skipped where that table does not exist - the
    server cannot compile a reference to it."""
    samples = _bind_samples()
    pin_table = repo.pin_table_exists(conn)
    for name, statement in psql.ALL_STATEMENTS.items():
        if repo.PIN_TABLE in statement and not pin_table:
            continue
        names = set(SQL_BIND.findall(statement))
        unknown = names - set(samples)
        assert not unknown, f"{name}: add a sample for {sorted(unknown)} to _bind_samples"
        binds = {k: samples[k] for k in names}
        if _runs(statement):
            db.rows(conn, statement, **binds)
            continue
        target = WRITE_TARGET.search(statement)
        assert target, f"{name}: no dbo. target table found"
        assert db.table_exists(conn, target.group(1)), f"{name}: dbo.{target.group(1)} does not exist"
        n = db.execute(conn, _never_run(statement), **binds)
        assert n <= 0, f"{name}: rowcount {n} - the never-taken branch ran"


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
    assert [w["internal"] for w in workers] == sorted((w["internal"] for w in workers), reverse=True), (
        "internal workers must sort first"
    )
    for wo in wos[:50]:
        hrs, src = hoursFor(wo, labour)
        assert isinstance(hrs, float)
        assert src in ("labour", "estimate", "")
