"""
Azztec_SaaS_test_planner_move_v1_0_0.py  ->  backend/tests/test_planner_move.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §5.7 (OD-110, OD-111, OD-116, OD-117)
Pair of:  backend/app/planner/service.py 1.1.0 (the move) + backend/app/planner/repo.py 1.2.0 (load_wo, the
          writers) + backend/app/planner/schemas.py 1.2.0 (the move models)

Two halves, as test_planner_repo.py:
  - no DB: the helpers that decide what a move writes and when it asks - the Workmate.NET date text
    (OD-117, against DP3-E P5's own strings), the 990 cap, the clsSimpleComparer shape, the collision-safe
    subtask order, CONFIRM_REASONS (OD-116) - and two guards on the API tests' tripwire: every writer is
    named in repo.WRITERS, and the service reaches the writers through the repo MODULE, which is what lets
    a monkeypatch see them.
  - RST DB: load_wo, move_preview and move_wo on a rolled-back connection, DRY ONLY. Nothing here passes
    dry_run=False (CLAUDE.md #2, the tests rule): the write itself is proven by DP3a's smoke on
    dbWorkmate_DP1_Test, with every move undone. The WOs are chosen by query, never by a pinned id, and
    every target day is computed from the configured "today", so the suite means the same next month.
    The DB half SKIPS with the reason when SQL Server is unreachable.

Changelog:
  1.0.0  Initial DP3a.
"""

from __future__ import annotations

import inspect
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

os.environ.setdefault("WORKMATE_ENV", "test")

from app.core import db, weekno  # noqa: E402 - after env is set
from app.planner import repo, rules, service  # noqa: E402
from app.planner.schemas import MovePreview, MoveResult  # noqa: E402

__version__ = "1.0.0"


# ---------------------------------------------------------------------------
# no DB - the helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (datetime(2026, 8, 26), "26/08/2026 12:00:00 am"),  # DP3-E P5, verbatim
        (datetime(2026, 9, 2), "2/09/2026 12:00:00 am"),  # one-digit day, two-digit month
        (datetime(2026, 12, 5), "5/12/2026 12:00:00 am"),
        (datetime(2026, 9, 2, 12, 0), "2/09/2026 12:00:00 pm"),  # noon is pm
        (datetime(2026, 12, 23, 8, 5, 9), "23/12/2026 8:05:09 am"),
        (datetime(2026, 12, 23, 15, 18), "23/12/2026 3:18:00 pm"),  # candidate A's end
        (date(2026, 12, 22), "22/12/2026 12:00:00 am"),  # a plain date reads as midnight
    ],
)
def test_net_datetime_is_workmate_nets_text(value, text) -> None:
    assert service._net_datetime(value) == text


def test_net_datetime_of_none_is_empty() -> None:
    assert service._net_datetime(None) == ""


def test_field_diff_detail_is_the_clssimplecomparer_shape() -> None:
    got = service._field_diff_detail("Request_Start_Date", "26/08/2026 12:00:00 am", "2/09/2026 12:00:00 am")
    assert got == "{Request_Start_Date} changed from {26/08/2026 12:00:00 am} to {2/09/2026 12:00:00 am}"


def test_details_cap_is_990_with_an_ellipsis() -> None:
    long = service._cap("x" * 5000)
    assert len(long) == service.EVENT_DETAILS_MAX == 990
    assert long.endswith("...")
    assert service._cap("short") == "short"
    assert service._cap(None) == ""


def test_shift_order_is_collision_safe() -> None:
    """Later moves walk latest-first, earlier moves earliest-first: a row shifted onto a later (or earlier)
    day is never picked up again by that day's own update (moveWO 1000)."""
    days = ["2026-12-15", "2026-12-14", "2026-12-15", "2026-12-16"]
    assert service._shift_order(days, 1) == ["2026-12-16", "2026-12-15", "2026-12-14"]
    assert service._shift_order(days, -1) == ["2026-12-14", "2026-12-15", "2026-12-16"]
    assert service._shift_order([], 7) == []


@pytest.mark.parametrize(
    ("codes", "asks"),
    [
        ([], False),
        (["SPAN"], False),  # OD-116 - shown, never asked
        (["PAST"], True),
        (["ACTIVE"], True),
        (["LABOUR_MULTI"], True),
        (["SPAN", "PAST"], True),
        (["SPAN", "LABOUR_MULTI"], True),
    ],
)
def test_confirm_reasons(codes, asks) -> None:
    assert service.needs_confirm([{"code": c, "text": ""} for c in codes]) is asks


def test_provenance_constants() -> None:
    """OD-108: what tells our rows apart at RST, where server_name is NULL on every row."""
    assert service.SERVER_NAME == "SaaS"
    assert service.SOURCE_FORM == "Planner"
    assert service.CONFIRM_REASONS == ("PAST", "ACTIVE", "LABOUR_MULTI")


def test_every_writer_is_named_for_the_tripwire() -> None:
    """repo.WRITERS is what test_planner_api.py patches to raise. A writer missing from it would be
    invisible to the tripwire."""
    names = set(repo.WRITERS)
    assert names == {
        "move_header",
        "shift_subtasks",
        "shift_labour",
        "upsert_pin",
        "clear_pin",
        "insert_event",
    }
    for name in names:
        assert callable(getattr(repo, name)), name


def test_service_reaches_the_writers_through_the_repo_module() -> None:
    """A monkeypatch on repo.<writer> only works while the service looks the writer up on the module at
    call time. `from app.planner.repo import move_header` would bind the real function and walk past the
    tripwire - so it must never appear."""
    source = Path(inspect.getfile(service)).read_text(encoding="utf-8")
    assert "from app.planner.repo import" not in source
    assert "from app.planner import repo, rules" in source


def test_every_move_function_defaults_to_dry_run() -> None:
    """CLAUDE.md #2: the library writes only when told to."""
    for fn in (service.move_wo, service.undo_move):
        assert inspect.signature(fn).parameters["dry_run"].default is True, fn.__name__


# ---------------------------------------------------------------------------
# RST DB - rolled back, dry only
# ---------------------------------------------------------------------------

# An open, non-PM, not-Active work order whose planned labour sits on at most one day: a move of it to a
# future day asks nothing (SPAN alone never asks - OD-116), so the dry plan comes back ok.
OPEN_PLAIN_WO = """
SELECT h.WO_ID
  FROM dbo.WO_N_Header h
 WHERE RTRIM(COALESCE(h.Status, '')) NOT IN ('C', 'D', 'V')
   AND RTRIM(COALESCE(h.WO_Type_Flag, '')) <> 'M'
   AND h.Request_Start_Date IS NOT NULL
   AND (SELECT COUNT(DISTINCT r.Res_Date) FROM dbo.WO_N_Resource r
         WHERE r.WO_Id = h.WO_ID AND RTRIM(COALESCE(r.Resource_Type, '')) = 'L'
           AND r.Res_Date IS NOT NULL) <= 1
 ORDER BY h.WO_ID DESC
OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
"""

CLOSED_WO = """
SELECT h.WO_ID
  FROM dbo.WO_N_Header h
 WHERE RTRIM(COALESCE(h.Status, '')) = 'C'
   AND h.Request_Start_Date IS NOT NULL
 ORDER BY h.WO_ID DESC
OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY
"""


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
def plain(conn) -> dict:
    wo_id = db.scalar(conn, OPEN_PLAIN_WO)
    if not wo_id:
        pytest.skip("no open, non-PM, not-Active WO with labour on at most one day")
    wo = repo.load_wo(conn, int(wo_id))
    assert wo is not None
    return wo


def _day(offset: int, avoid: str) -> str:
    """today + offset days, stepped one further if it lands on `avoid` (the WO's own start)."""
    d = date.fromisoformat(service.today_iso()) + timedelta(days=offset)
    if rules.iso(d) == avoid:
        d += timedelta(days=1 if offset >= 0 else -1)
    return rules.iso(d)


def test_load_wo_keys_and_raw_dates(plain: dict) -> None:
    assert set(plain) == {
        "id", "sid", "title", "status", "type", "cat", "startDate", "endDate", "start", "end", "weekNo",
        "estimate", "hasDetails", "engineOwned", "pinned", "pinTable", "hasPinRow", "engineDate",
        "engineDateValue", "locked", "subtaskDates", "labourDates",
    }  # fmt: skip
    assert isinstance(plain["startDate"], datetime), "the writer needs the raw datetime"
    assert plain["start"] == rules.iso(plain["startDate"])
    assert plain["end"] == (rules.iso(plain["endDate"]) if plain["endDate"] is not None else "")
    assert plain["pinTable"] is True, "WO_N_Plan missing: alembic upgrade head has not run"
    assert all(isinstance(d, str) and isinstance(n, int) for d, n in plain["labourDates"])


def test_load_wo_unknown_id_is_none(conn) -> None:
    assert repo.load_wo(conn, 0) is None


def test_preview_matches_the_model_and_asks_nothing_for_a_future_day(conn, plain: dict) -> None:
    to = _day(14, plain["start"])
    pv = service.move_preview(conn, plain["id"], to)
    assert pv["ok"] is True, pv
    MovePreview.model_validate(pv)  # extra="forbid": the dict and the contract are one shape
    assert pv["newStart"] == to
    assert pv["delta"] == rules.civilDays(plain["start"], to)
    assert pv["confirm"] is False, pv["reasons"]
    assert "PAST" not in [r["code"] for r in pv["reasons"]]


def test_dry_move_plans_and_writes_nothing(conn, plain: dict) -> None:
    to = _day(14, plain["start"])
    plan = service.move_wo(plain["id"], to, 21, expect_start_iso=plain["start"], conn=conn)
    assert plan["ok"] is True and plan["dryRun"] is True, plan
    MoveResult.model_validate({**plan, "actor": 21})
    assert plan["events"] == 0
    assert plan["prevStart"] == plain["start"] and plan["newStart"] == to
    assert plan["weekNo"] == float(weekno.week_no(date.fromisoformat(to)))
    assert plan["undo"] == {"woId": plain["id"], "toIso": plain["start"], "expectStartIso": to}
    assert plan["labourRows"] == sum(n for _, n in plain["labourDates"])
    again = repo.load_wo(conn, plain["id"])
    assert again is not None and again["startDate"] == plain["startDate"], "a dry run moved the WO"


def test_dry_undo_plans_back(conn, plain: dict) -> None:
    to = _day(14, plain["start"])
    plan = service.undo_move(plain["id"], to, 21, expect_start_iso=plain["start"], conn=conn)
    assert plan["ok"] is True and plan["dryRun"] is True, plan


def test_stale_when_the_client_saw_another_start(conn, plain: dict) -> None:
    res = service.move_wo(plain["id"], _day(14, plain["start"]), 21, expect_start_iso="1999-01-01", conn=conn)
    assert res["code"] == "STALE" and res["currentStart"] == plain["start"], res


def test_no_change_on_its_own_day(conn, plain: dict) -> None:
    assert service.move_wo(plain["id"], plain["start"], 21, conn=conn)["code"] == "NO_CHANGE"


def test_past_day_asks_with_a_preview(conn, plain: dict) -> None:
    res = service.move_wo(plain["id"], _day(-30, plain["start"]), 21, conn=conn)
    assert res["ok"] is False and res["code"] == "CONFIRM", res
    assert "PAST" in [r["code"] for r in res["preview"]["reasons"]]
    assert res["preview"]["confirm"] is True
    MovePreview.model_validate(res["preview"])


def test_no_identity_at_user_zero(conn, plain: dict) -> None:
    assert service.move_wo(plain["id"], _day(14, plain["start"]), 0, conn=conn)["code"] == "NO_IDENTITY"


def test_closed_work_order_does_not_move(conn) -> None:
    wo_id = db.scalar(conn, CLOSED_WO)
    if not wo_id:
        pytest.skip("no closed WO with a start date")
    res = service.move_wo(int(wo_id), "2030-01-07", 21, conn=conn)
    assert res["code"] == "LOCKED_STATUS", res


def test_unknown_work_order(conn) -> None:
    assert service.move_wo(0, "2030-01-07", 21, conn=conn)["code"] == "NOT_FOUND"
    assert service.move_wo("x", "2030-01-07", 21, conn=conn)["code"] == "BAD_REQUEST"
