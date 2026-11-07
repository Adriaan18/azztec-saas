"""
Azztec_SaaS_app_planner_service_v1_1_0.py  ->  backend/app/planner/service.py
Version:  1.1.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §5.3 (OD-108, OD-110, OD-111, OD-114, OD-116,
          OD-117); earlier: Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md §3 · Planner Port Spec §2/§3
Ported:   workmate.planner 1.3.1 rangeData (src 711-746); DP3: movePreview (923-937), moveWO (940-1052),
          undoMove (1055-1059), _eventRow / _fieldDiffDetail (783-797)

range_data (S1c): read-only, plain def, takes the request Connection (D-2). Returns the Ignition dict in
src key order; the router validates it and adds the OD-14 envelope. Raises WindowError on a bad window
and nothing else on purpose - everything else is a 500 the middleware reports.

Deviation (spec §3.3): labour is indexed by woId once and the per-WO subset is passed to
rules.hoursFor / rules.assignedFor. Both filter on woId internally, so the output is identical and the
cost drops from O(wos x labour) to O(wos + labour). rules.py stays byte-1:1 with the port.
Pinned by tests/test_planner_api.py::test_range_by_wo_index_matches_full_scan.

The move (DP3): move_preview, move_wo, undo_move - the oracle's steps and result dicts, three changes:
  - OD-110: ONE transaction per move, owned here. With conn=None a dry run reads on engine.connect()
    and a real move runs inside engine.begin(); a guard miss or a database error raises _Rollback
    inside that block, so the whole move rolls back, and comes back out as a STALE / WRITE_FAILED
    dict. With conn given the caller owns the transaction (the rolled-back test connection, S6's
    t_rb_move) and gets the dict instead. The header update carries the start-day guard (sql.py).
  - OD-116: a move asks for confirmation only for CONFIRM_REASONS. SPAN stays in `reasons` (shown,
    never asked) - at RST 96 % of open WOs end on a later day than they start. rules.moveRules is
    untouched; its `confirm` is replaced here, in the preview and in the CONFIRM decision.
  - OD-117: the two `Update` rows carry Workmate.NET's date text (_net_datetime), so they read the
    same in a WO's history as the rows Workmate.NET writes; the `Rescheduled` row keeps the ISO text.
Every move function defaults to dry_run=True (CLAUDE.md #2); the router passes the body's dryRun.
Never raises past the boundary except a programming error, which the middleware reports as INTERNAL.
The service is silent; the router logs.

The time zone (OD-6) lives here and only here: today = the civil date now in WORKMATE_TZ.

Changelog:
  1.1.0  DP3a. move_preview, move_wo, undo_move, needs_confirm; SERVER_NAME / SOURCE_FORM (OD-108),
         EVENT_DETAILS_MAX, CONFIRM_REASONS (OD-116); _net_datetime (OD-117), _field_diff_detail, _cap,
         _shift_order. range_data and the time zone untouched.
  1.0.1  Ruff UP031: WindowError messages to f-strings. Text unchanged. No behaviour change.
  1.0.0  Initial S1c.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.core import db, weekno
from app.core.config import get_settings
from app.planner import repo, rules

__version__ = "1.1.0"

MAX_WINDOW_DAYS = 400

# OD-108 - RST's server_name is NULL on every row (Landmines §E), so this is what tells our rows apart;
# Source_Form says where the change came from.
SERVER_NAME = "SaaS"
SOURCE_FORM = "Planner"
# The writer's convention (oracle 93): event_details is varchar(max) at RST (DP3-E P1), the cap is ours.
EVENT_DETAILS_MAX = 990
# OD-116 - the reasons that ask. SPAN is shown, never asked.
CONFIRM_REASONS = ("PAST", "ACTIVE", "LABOUR_MULTI")
NO_IDENTITY_MESSAGE = "your login has no Workmate identity"


class WindowError(ValueError):
    """Bad or too-wide window. The router turns this, and only this, into a 400 (OD-16)."""

    code = "BAD_WINDOW"


# ---------------------------------------------------------------------------
# time zone (OD-6) - the single point where "now" becomes a civil date
# ---------------------------------------------------------------------------


@lru_cache
def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().tz)


def resolve_tz() -> str:
    """Probe the configured zone; raises ZoneInfoNotFoundError on a bad key or a missing tzdata wheel.
    main.py calls this in the lifespan so the cause is one [E] line away from the first 500."""
    return _tz().key


def today_iso() -> str:
    return rules.iso(datetime.now(_tz()).date())


# ---------------------------------------------------------------------------
# range_data
# ---------------------------------------------------------------------------


def range_data(conn: Connection, from_iso: str, to_iso: str) -> dict[str, Any]:
    """Everything one planner window needs, as plain JSON-safe dicts (src 711).
    Raises WindowError on a bad window; the router turns that into a 400."""
    from_d = rules.parseIso(from_iso)
    to_d = rules.parseIso(to_iso)
    if from_d is None or to_d is None or from_d > to_d:
        raise WindowError(f"bad window {from_iso!r}..{to_iso!r} (expected yyyy-MM-dd, from <= to)")
    if (rules.civilDays(rules.iso(from_d), rules.iso(to_d)) or 0) > MAX_WINDOW_DAYS:
        raise WindowError(f"window too wide (max {MAX_WINDOW_DAYS} days)")

    pin_table = repo.pin_table_exists(conn)
    wos = repo.fetch_wos(conn, from_d, to_d)
    labour = repo.fetch_labour(conn, from_d, to_d)
    wlist, teams = rules.buildWorkers(repo.fetch_skill_rows(conn))  # the workers() composition

    # spec §3.3 - index once, hand each WO its own rows
    by_wo: dict[int, list[dict[str, Any]]] = {}
    for r in labour:
        by_wo.setdefault(int(r.get("woId") or 0), []).append(r)
    for wo in wos:
        mine = by_wo.get(int(wo.get("id") or 0), [])
        h, src = rules.hoursFor(wo, mine)
        wo["hrs"] = h
        wo["hrsSrc"] = src
        wo["assigned"] = rules.assignedFor(wo, mine)

    open_wo = len([w for w in wos if w["cat"] == "WO" or w["cat"] == "REQ"])
    open_pm = len([w for w in wos if w["cat"] == "PM"])
    done = len([w for w in wos if w["cat"] == "DONE"])

    f_iso = rules.iso(from_d)
    t_iso = rules.iso(to_d)
    return {
        "from": f_iso,
        "to": t_iso,
        "today": today_iso(),
        "wos": wos,
        "labour": labour,
        "workers": wlist,
        "teams": teams,
        "priorities": repo.fetch_priorities(conn),
        "colours": rules.COLOURS,
        "weeks": rules.capacityByWeek(wos, wlist, f_iso, t_iso),
        "load": dict([(str(k), v) for k, v in rules.workerLoad(wos, labour).items()]),  # src 738
        "counts": {"wo": open_wo, "pm": open_pm, "done": done, "total": len(wos)},
        "pinTable": pin_table,
        "workerWeeks": rules.workerWeeks(wos, labour, wlist, f_iso, t_iso),
        "uomHours": repo.hours_uom_id(conn),
        "libVersion": rules.__version__,  # OD-10
    }


# ---------------------------------------------------------------------------
# the move (DP3) - helpers
# ---------------------------------------------------------------------------


class _Rollback(Exception):
    """Raised inside engine.begin() so the whole move rolls back; carries the dict the caller gets."""

    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__(str(result.get("code", "")))
        self.result = result


class _GuardMiss(Exception):
    """The header update touched 0 rows: another move got there first (OD-110)."""


class _WriteFault(Exception):
    """A write ran but touched an impossible number of rows."""


def needs_confirm(reasons: list[dict[str, Any]] | None) -> bool:
    """OD-116: a move asks only for a CONFIRM_REASONS reason. SPAN alone never asks."""
    return any(r.get("code") in CONFIRM_REASONS for r in reasons or [])


def _cap(details: Any) -> str:
    """_eventRow's cap (oracle 784-786): at most 990 characters, the last three '...'."""
    det = "" if details is None else str(details)
    if len(det) > EVENT_DETAILS_MAX:
        det = det[: EVENT_DETAILS_MAX - 3] + "..."
    return det


def _net_datetime(d: date | datetime | None) -> str:
    """OD-117: a datetime as Workmate.NET writes it into event_details - d/MM/yyyy h:mm:ss am|pm, e.g.
    '2/09/2026 12:00:00 am' (DP3-E P5). A plain date reads as midnight; None as ''."""
    if d is None:
        return ""
    if not isinstance(d, datetime):
        d = datetime.combine(d, time.min)
    hour12 = d.hour % 12 or 12
    half = "am" if d.hour < 12 else "pm"
    return f"{d.day}/{d.month:02d}/{d.year} {hour12}:{d.minute:02d}:{d.second:02d} {half}"


def _field_diff_detail(col: str, old: Any, new: Any) -> str:
    """'{Col} changed from {old} to {new}' - the clsSimpleComparer shape (oracle 794-797)."""
    return f"{{{col}}} changed from {{{old}}} to {{{new}}}"


def _shifted(d: datetime | None, delta: int) -> datetime | None:
    """_shiftDays (770): None stays None; a civil-day delta keeps the time of day."""
    return None if d is None else d + timedelta(days=int(delta))


def _shift_order(days: list[str], delta: int) -> list[str]:
    """moveWO 1000: each distinct old day once, latest-first when moving later and earliest-first when
    moving earlier, so a row already moved onto a later day is never picked up again."""
    return sorted(set(days), reverse=delta > 0)


def _stale(wo: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "code": "STALE",
        "sid": wo["sid"],
        "currentStart": wo["start"],
        "message": f"{wo['sid']} moved since you loaded the planner (now {wo['start']}) - refreshing",
    }


def _preview(wo: dict[str, Any], to_iso: str, today: str) -> dict[str, Any]:
    """movePreview's body (927-937) on an already-loaded WO - the oracle loaded it a second time for its
    CONFIRM preview; the output is the same. `confirm` is the service's (OD-116)."""
    r = rules.moveRules(wo, to_iso, today)
    out = dict(r)
    out.update(
        {
            "woId": wo["id"],
            "sid": wo["sid"],
            "title": wo["title"],
            "status": wo["status"],
            "statusTitle": rules.STATUS_TITLES.get(wo["status"], wo["status"]),
            "prevStart": wo["start"],
            "prevEnd": wo["end"],
            "subtasks": len(wo["subtaskDates"]),
            "labourDates": [[d, n] for d, n in wo["labourDates"]],
        }
    )
    if r["ok"]:
        out["confirm"] = needs_confirm(r["reasons"])
        out["labourMoves"] = [
            {"from": d, "to": rules.iso(rules.parseIso(d) + timedelta(days=r["delta"])), "rows": n}
            for d, n in wo["labourDates"]
        ]
    return out


def _event(conn: Connection, wo_id: int, user_id: int, name: str, details: str) -> int:
    return repo.insert_event(conn, wo_id, user_id, name, _cap(details), SERVER_NAME, SOURCE_FORM)


def _write(
    conn: Connection,
    wo: dict[str, Any],
    r: dict[str, Any],
    plan: dict[str, Any],
    new_start: datetime,
    new_end: datetime | None,
    week: Any,
    user_id: int,
    event_name: str,
) -> None:
    """moveWO 992-1027, in the oracle's order: header, subtasks, planned labour, pin, audit."""
    wo_id = wo["id"]
    sid = wo["sid"]
    delta = plan["delta"]
    n = repo.move_header(conn, wo_id, new_start, new_end, week, wo["startDate"])
    if n == 0:
        raise _GuardMiss()
    if n != 1:
        raise _WriteFault(f"header update touched {n} rows")
    for d in _shift_order(wo["subtaskDates"], delta):
        old = rules.parseIso(d)
        repo.shift_subtasks(conn, wo_id, old, delta, weekno.week_no(old + timedelta(days=delta)))
    labour_rows = repo.shift_labour(conn, wo_id, delta)
    if r["willPin"]:
        note = f"Planner move {wo['start']} -> {plan['newStart']}"
        repo.upsert_pin(conn, wo_id, user_id, wo["startDate"], note, SERVER_NAME)
    elif r["willUnpin"]:
        repo.clear_pin(conn, wo_id)
    summary = f"{sid}: {wo['start']} -> {plan['newStart']} ({rules._fmtDelta(delta)}) via Planner"
    events = _event(conn, wo_id, user_id, event_name, summary)
    if r["willPin"]:
        text = f"{sid} pinned by the planner - engine re-dating suspended (engine date {wo['start']})"
        events += _event(conn, wo_id, user_id, "Pinned", text)
    elif r["willUnpin"]:
        text = f"{sid} back on the engine date {plan['newStart']} - pin cleared"
        events += _event(conn, wo_id, user_id, "Unpinned", text)
    start_diff = _field_diff_detail(
        "Request_Start_Date", _net_datetime(wo["startDate"]), _net_datetime(new_start)
    )
    events += _event(conn, wo_id, user_id, "Update", start_diff)
    if wo["end"]:
        end_diff = _field_diff_detail(
            "Request_End_Date", _net_datetime(wo["endDate"]), _net_datetime(new_end)
        )
        events += _event(conn, wo_id, user_id, "Update", end_diff)
    plan["events"] = events
    plan["labourRows"] = labour_rows


def _move(
    conn: Connection,
    wo_id: int,
    to_iso: str,
    user_id: int,
    expect_start_iso: str | None,
    confirm: bool,
    dry_run: bool,
    event_name: str,
    own: bool,
) -> dict[str, Any]:
    """moveWO's body (950-1052) on a connection. own=True: the transaction is ours, so a write failure
    raises _Rollback to undo everything; own=False: the caller's, so it gets the dict."""
    wo = repo.load_wo(conn, wo_id)
    if wo is None:
        return {"ok": False, "code": "NOT_FOUND", "message": f"WO {wo_id} not found"}
    sid = wo["sid"]
    if expect_start_iso and db.s_(expect_start_iso)[:10] != wo["start"]:
        return _stale(wo)
    today = today_iso()
    r = rules.moveRules(wo, to_iso, today)
    if not r["ok"]:
        return {"ok": False, "code": r["code"], "sid": sid, "message": r["message"]}
    if needs_confirm(r["reasons"]) and not confirm:
        preview = _preview(wo, to_iso, today)
        return {"ok": False, "code": "CONFIRM", "sid": sid, "message": "confirm required", "preview": preview}
    if user_id <= 0:
        return {"ok": False, "code": "NO_IDENTITY", "sid": sid, "message": NO_IDENTITY_MESSAGE}
    delta = int(r["delta"])
    new_start = _shifted(wo["startDate"], delta)
    new_end = _shifted(wo["endDate"], delta)
    week = weekno.week_no(new_start)
    plan: dict[str, Any] = {
        "ok": True,
        "dryRun": dry_run,
        "woId": wo_id,
        "sid": sid,
        "prevStart": wo["start"],
        "prevEnd": wo["end"],
        "newStart": rules.iso(new_start),
        "newEnd": rules.iso(new_end) if new_end is not None else "",
        "delta": delta,
        "weekNo": float(week),
        "prevWeekNo": wo["weekNo"],
        "subtasks": len(wo["subtaskDates"]),
        "labourRows": sum(n for _, n in wo["labourDates"]),
        "reasons": r["reasons"],
        "events": 0,
        "willPin": r["willPin"],
        "willUnpin": r["willUnpin"],
        "pinned": r["pinnedAfter"],
        "engineDate": wo["engineDate"] or (wo["start"] if r["willPin"] else ""),
        "undo": {"woId": wo_id, "toIso": wo["start"], "expectStartIso": rules.iso(new_start)},
    }
    if dry_run:
        return plan
    try:
        _write(conn, wo, r, plan, new_start, new_end, week, user_id, event_name)
    except _GuardMiss:
        result = _stale(repo.load_wo(conn, wo_id) or wo)
        if own:
            raise _Rollback(result) from None
        return result
    except (SQLAlchemyError, _WriteFault) as e:
        msg = db.db_error(e) if isinstance(e, SQLAlchemyError) else str(e)
        result = {"ok": False, "code": "WRITE_FAILED", "sid": sid, "message": msg}
        if own:
            raise _Rollback(result) from e
        return result
    return plan


# ---------------------------------------------------------------------------
# the move (DP3) - the three entry points
# ---------------------------------------------------------------------------


def move_preview(conn: Connection, wo_id: int, to_iso: str) -> dict[str, Any]:
    """movePreview (923-937): what a move would do - the rules, old and new, the labour moves. Nothing
    is written. NOT_FOUND when there is no header; a refused move comes back ok=False with its code."""
    wo = repo.load_wo(conn, wo_id)
    if wo is None:
        return {"ok": False, "code": "NOT_FOUND", "message": f"WO {wo_id} not found"}
    return _preview(wo, to_iso, today_iso())


def move_wo(
    wo_id: Any,
    to_iso: str,
    user_id: Any,
    expect_start_iso: str | None = None,
    confirm: bool = False,
    dry_run: bool = True,
    event_name: str = "Rescheduled",
    conn: Connection | None = None,
) -> dict[str, Any]:
    """moveWO (940-1052). Returns a dict; a database error never escapes (OD-110).
    dry_run=True (default)  the plan only - nothing written
    expect_start_iso        optimistic lock: STALE when the WO no longer starts on that day
    confirm=False           CONFIRM + preview instead of writing, when a CONFIRM_REASONS reason applies
    conn                    caller-owned transaction: nothing committed or rolled back here."""
    try:
        wo_id = int(wo_id)
    except (TypeError, ValueError):
        return {"ok": False, "code": "BAD_REQUEST", "message": "woId required"}
    args = (wo_id, to_iso, db.i_(user_id), expect_start_iso, bool(confirm), bool(dry_run), event_name)
    if conn is not None:
        return _move(conn, *args, own=False)
    try:
        if dry_run:
            with db.get_engine().connect() as c:  # reads only; leaving the block commits nothing
                return _move(c, *args, own=False)
        with db.get_engine().begin() as c:  # commits on a clean exit, rolls back on _Rollback
            return _move(c, *args, own=True)
    except _Rollback as rb:
        return rb.result


def undo_move(
    wo_id: Any,
    to_iso: str,
    user_id: Any,
    expect_start_iso: str | None = None,
    dry_run: bool = True,
    conn: Connection | None = None,
) -> dict[str, Any]:
    """undoMove (1055-1059): back to the start the move returned in `undo`. Confirm is implied - the
    planner just made the move."""
    return move_wo(
        wo_id,
        to_iso,
        user_id,
        expect_start_iso=expect_start_iso,
        confirm=True,
        dry_run=dry_run,
        event_name="Rescheduled (undo)",
        conn=conn,
    )
