"""
Azztec_SaaS_app_planner_repo_v1_2_0.py  ->  backend/app/planner/repo.py
Version:  1.2.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §5.2 (OD-110, OD-114);
          earlier: Azztec_SaaS_S1h_Priority_Initials_Chunk_Spec_v1_0_0.md §3.2
Parent:   Azztec_SaaS_Planner_Port_Spec_v1_0_0.md §2, §3
Ported from: workmate.planner 1.3.1 lines 532-706 (hoursUomId, fetchWOs,
             fetchLabour, fetchSkillRows, fetchPriorities, _labourDict); DP3
             adds 820-853 (loadWO), the writes of moveWO (993-1014), _upsertPin
             (1120-1130) and _eventRow (783-791)
Pair:     backend/tests/test_planner_repo.py 1.0.3 (reads, the SQL gates) +
          backend/tests/test_planner_move.py 1.0.0 (load_wo, dry moves)

Row fetch and row mapping. Takes a SQLAlchemy Connection, returns PLAIN
DICTS - the exact shapes rules.py already consumes and the JSON contract
already publishes. No Pydantic, no FastAPI, no transactions: this layer
reads and writes on the connection it is given, service.py composes and owns
the transaction, router.py serialises. Every writer returns its rowcount and
never commits.

FUNCTION names are snake_case (port spec §2). DICT KEYS stay camelCase -
they are the contract and rules.py's input shape. A snake_case key here
breaks hoursFor(), buildWorkers() and the UI in one move.

The _i/_f/_s mappers stay on every field even though db.rows() already
strips strings and converts Decimal. db._clean() returns an INT for an
integral numeric, and weekNo (numeric 2026.38) must be a float in the
contract - belt and braces, as Landmines §B prescribes for char(n).

OD-1 in force: without dbo.WO_N_Plan every engine-owned PM comes back
locked=True, movable=False. On RST that was ~2,364 PMs (raw log §1) until
0001 landed the table (S1j, OD-44); since then they read movable, and DP3's
first move of one pins it (OD-114).

Changelog:
  1.2.0  DP3a. load_wo (the oracle's loadWO dict, same keys, plus the raw
         startDate / endDate / engineDateValue the writer shifts); the six
         writers move_header, shift_subtasks, shift_labour, upsert_pin,
         clear_pin, insert_event, named in WRITERS so the API tests' tripwire
         reaches every one (OD-111); _day_bounds, the half-open day every DP3
         date predicate uses. No read path changed.
  1.1.0  S1h. fetch_priorities gains the colour key (open item 29). Ships
         with schemas.py 1.1.0 or not at all - Priority is extra='forbid',
         so a key here that the model does not declare is a 500 on every
         /range, and a field there without this key is a validation error.
  1.0.0  Initial. hours_uom_id caches per ENGINE OBJECT, not per URL string:
         the MSSQL odbc_connect URL carries the password in its query string
         and SQLAlchemy's hide_password does not mask it, so a URL-keyed
         cache would put a secret in a module global.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy.engine import Connection, Engine

from app.core import db
from app.core.db import f_, i_, s_
from app.planner import sql as psql
from app.planner.rules import (
    _LOCKED_STATUSES,
    STATUS_TITLES,
    category,
    civilDays,
    engineOwned,
    iso,
    timeOf,
)

__version__ = "1.2.0"

PIN_TABLE = "WO_N_Plan"

# Every function below that writes. The API tests patch each name to raise, so
# a test that sends a real move fails instead of writing (OD-111) - add a new
# writer here or the tripwire cannot see it.
WRITERS = ("move_header", "shift_subtasks", "shift_labour", "upsert_pin", "clear_pin", "insert_event")

# UOM id per engine. Engine objects are hashable and get_engine() caches one
# per tenant (D-12), so this is bounded by tenant count and holds no secret.
_uom_by_engine: dict[Engine, int] = {}


def _bound(d: date | datetime) -> datetime:
    """Day bound as an explicit midnight datetime. The legacy columns are
    MSSQL `datetime`; sending a bare `date` makes the driver decide the
    comparison type. Be explicit on both dialects."""
    return d if isinstance(d, datetime) else datetime.combine(d, time.min)


def _exclusive_end(to_d: date | datetime) -> datetime:
    """to_d is INCLUSIVE in the API and EXCLUSIVE in the SQL - the +1 day
    lives here, exactly as fetchWOs did it (source 637). Not in sql.py, not
    in the router."""
    base = to_d.date() if isinstance(to_d, datetime) else to_d
    return datetime.combine(base + timedelta(days=1), time.min)


def pin_table_exists(conn: Connection) -> bool:
    """The pinTableExists() twin (source 238). No pm_engine to delegate to
    any more - ask the database."""
    return db.table_exists(conn, PIN_TABLE)


# ---------------------------------------------------------------------------
# work orders
# ---------------------------------------------------------------------------


def _wo_dict(r: dict[str, Any], pin_table: bool) -> dict[str, Any]:
    st = s_(r["Status"])
    tf = s_(r["WO_Type_Flag"]) or "N"
    sd = r["Request_Start_Date"]
    ed = r["Request_End_Date"]
    eo = engineOwned(st, tf)
    pinned = i_(r["Pinned"]) == 1
    locked = eo and not pinned and not pin_table
    days = 0
    if sd is not None and ed is not None:
        days = civilDays(iso(sd), iso(ed)) or 0
    return {
        "id": i_(r["WO_ID"]),
        "sid": s_(r["Short_WO_Id"]),
        "title": s_(r["WO_Title"]),
        "status": st,
        "statusTitle": STATUS_TITLES.get(st, st),
        "type": tf,
        "cat": category(st, tf),
        "start": iso(sd),
        "startTime": timeOf(sd),
        "end": iso(ed) if ed is not None else "",
        "days": days,
        "weekNo": f_(r["Week_No"]),
        "prog": i_(r["Progress_Id"]),
        "priId": i_(r["Priority_Id"]),
        "pri": s_(r["PriorityShort"]),
        "estimate": f_(r["Duration_In_Hours"]),
        "resp": i_(r["Resp_User_Id"]),
        "asset": s_(r["AssetId"]),
        "assetTitle": s_(r["AssetTitle"]),
        "loc": s_(r["LocationId"]),
        "locTitle": s_(r["LocationTitle"]),
        "hasPO": i_(r["HasPO"]) == 1,
        "engineOwned": eo,
        "pinned": pinned,
        "pinnedOn": iso(r["Pinned_On"]) if r["Pinned_On"] is not None else "",
        "engineDate": iso(r["Prev_Start"]) if r["Prev_Start"] is not None else "",
        "locked": locked,
        "movable": (not locked) and st not in _LOCKED_STATUSES,
        "hrs": 0.0,
        "hrsSrc": "",
        "assigned": [],
    }


def fetch_wos(conn: Connection, from_d: date, to_d: date) -> list[dict[str, Any]]:
    """WO dicts with start inside [from_d, to_d] - to_d INCLUSIVE. Cancelled
    excluded; closed included (the UI hides them by default, D-9).
    hrs / hrsSrc / assigned are left at their zero values here - service.py
    fills them from rules.hoursFor() and rules.assignedFor()."""
    pin_table = pin_table_exists(conn)
    statement = psql.WO_RANGE_PINNED if pin_table else psql.WO_RANGE_NOPIN
    rows = db.rows(conn, statement, from_d=_bound(from_d), to_d=_exclusive_end(to_d))
    return [_wo_dict(r, pin_table) for r in rows]


# ---------------------------------------------------------------------------
# labour
# ---------------------------------------------------------------------------


def _labour_dict(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "resId": i_(r["Res_Id"]),
        "woId": i_(r["WO_Id"]),
        "userId": i_(r["User_Id"]),
        "hours": f_(r["Planned_Qty"]),
        "rate": f_(r["Rate"]),
        "note": s_(r["Note"]),
        "date": iso(r["Res_Date"]) if r["Res_Date"] is not None else "",
        "skillId": i_(r["Skill_Id"]),
        "skillTitle": s_(r["Skill_Title"]),
        "uomId": i_(r["UOM_Id"]),
    }


def fetch_labour(conn: Connection, from_d: date, to_d: date) -> list[dict[str, Any]]:
    """Planned-labour rows for the WOs in the window. Scoped by the WO's
    start date, not by Res_Date - see the sql.py note."""
    rows = db.rows(conn, psql.LABOUR_RANGE, from_d=_bound(from_d), to_d=_exclusive_end(to_d))
    return [_labour_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# workers, priorities, uom
# ---------------------------------------------------------------------------


def fetch_skill_rows(conn: Connection) -> list[dict[str, Any]]:
    """One row per active user x active skill. Feeds rules.buildWorkers()."""
    return [
        {
            "userId": i_(r["User_Id"]),
            "shortId": s_(r["Short_User_Id"]),
            "name": s_(r["User_Name"]),
            "skillId": i_(r["Skill_ID"]),
            "sysId": i_(r["Sys_User_Skill_Id"]),
            "uomId": i_(r["UOM_ID"]),
            "skillTitle": s_(r["Skill_Title"]),
            "hrsPerWeek": f_(r["Hrs_Per_Week"]),
            "supplierId": i_(r["Supplier_ID"]),
            "supplierShort": s_(r["Supplier_Short"]),
            "supplierName": s_(r["Supplier_Name"]),
            "internalDept": s_(r["Internal_Dept"]),
        }
        for r in db.rows(conn, psql.WORKER_SKILLS)
    ]


def fetch_priorities(conn: Connection) -> list[dict[str, Any]]:
    """Active priorities in contract order. The order is the point - see the
    Sort_Sequence, Priority_Id note in sql.py."""
    return [
        {
            "id": i_(r["Priority_Id"]),
            "short": s_(r["Short_Priority_Id"]),
            "title": s_(r["Priority_Title"]),
            # varchar(255) NULL, free text, '' when NULL - shipped as stored,
            # validated nowhere in the backend (OD-36). s_ is belt and braces
            # over the SQL COALESCE, as every other field here has it.
            "colour": s_(r["Colour"]),
        }
        for r in db.rows(conn, psql.PRIORITIES)
    ]


def hours_uom_id(conn: Connection) -> int:
    """The labour-hours unit id, resolved at runtime and cached per engine.
    Both probes swallow their errors and fall through to 0, exactly as the
    source does (537-553) - a missing UOM table must not take the whole
    range request down. Every other query in this module raises on purpose."""
    engine = conn.engine
    cached = _uom_by_engine.get(engine)
    if cached:
        return cached
    uom = 0
    for statement in (psql.UOM_LR_STD, psql.UOM_MODAL):
        try:
            uom = i_(db.scalar(conn, statement))
        except Exception:  # noqa: BLE001 - probe, falls through to 0 by design
            uom = 0
        if uom:
            break
    if uom:
        _uom_by_engine[engine] = uom
    return uom or 0


def clear_caches() -> None:
    """Test seam - drops the per-engine UOM cache."""
    _uom_by_engine.clear()


# ---------------------------------------------------------------------------
# DP3 - one work order for the writer
# ---------------------------------------------------------------------------


def _day_bounds(d: date | datetime) -> tuple[datetime, datetime]:
    """[midnight of d's day, midnight of the next) - the half-open day every DP3
    predicate uses. No datetime is compared by equality (sql.py header)."""
    base = d.date() if isinstance(d, datetime) else d
    start = datetime.combine(base, time.min)
    return start, start + timedelta(days=1)


def load_wo(conn: Connection, wo_id: int) -> dict[str, Any] | None:
    """The oracle's loadWO (820-853): the header and every date a move must
    carry, or None when there is no header. Same keys as the source;
    startDate / endDate / engineDateValue are the RAW datetimes the writer
    shifts, so the time of day survives (DP3-E P3)."""
    pin_table = pin_table_exists(conn)
    statement = psql.LOAD_WO_PINNED if pin_table else psql.LOAD_WO_NOPIN
    found = db.rows(conn, statement, wo_id=int(wo_id))
    if not found:
        return None
    r = found[0]
    st = s_(r["Status"])
    tf = s_(r["WO_Type_Flag"]) or "N"
    sd = r["Request_Start_Date"]
    ed = r["Request_End_Date"]
    eo = engineOwned(st, tf)
    pinned = i_(r["Pinned"]) == 1
    subs = [x["Req_Start_Date"] for x in db.rows(conn, psql.SUBTASK_DATES, wo_id=int(wo_id))]
    labour = [(x["Res_Date"], i_(x["Cnt"])) for x in db.rows(conn, psql.LABOUR_DATES, wo_id=int(wo_id))]
    return {
        "id": i_(r["WO_ID"]),
        "sid": s_(r["Short_WO_Id"]),
        "title": s_(r["WO_Title"]),
        "status": st,
        "type": tf,
        "cat": category(st, tf),
        "startDate": sd,
        "endDate": ed,
        "start": iso(sd) if sd is not None else "",
        "end": iso(ed) if ed is not None else "",
        "weekNo": f_(r["Week_No"]),
        "estimate": f_(r["Duration_In_Hours"]),
        "hasDetails": i_(r["HasDetails"]) == 1,
        "engineOwned": eo,
        "pinned": pinned,
        "pinTable": pin_table,
        "hasPinRow": r["Prev_Start"] is not None or r["Pinned_On"] is not None,
        "engineDate": iso(r["Prev_Start"]) if r["Prev_Start"] is not None else "",
        "engineDateValue": r["Prev_Start"],
        "locked": eo and not pinned and not pin_table,
        "subtaskDates": [iso(x) for x in subs],
        "labourDates": [(iso(d), n) for d, n in labour],
    }


# ---------------------------------------------------------------------------
# DP3 - the writes. Each returns its rowcount; none commits (the service owns
# the transaction, OD-110). Named in WRITERS above.
# ---------------------------------------------------------------------------


def move_header(
    conn: Connection,
    wo_id: int,
    new_start: datetime,
    new_end: datetime | None,
    week_no: Any,
    old_start: datetime,
) -> int:
    """moveWO 993, guarded by the loaded start's day: 0 rows means another move
    got there first (STALE), never an overwrite."""
    day_from, day_to = _day_bounds(old_start)
    return db.execute(
        conn,
        psql.MOVE_HEADER,
        wo_id=int(wo_id),
        new_start=new_start,
        new_end=new_end,
        week_no=week_no,
        day_from=day_from,
        day_to=day_to,
    )


def shift_subtasks(conn: Connection, wo_id: int, old_day: date, delta: int, week_no: Any) -> int:
    """moveWO 1002: every subtask on old_day moves by delta, Week_No to the new
    day's. The service calls it once per distinct day, in collision-safe order."""
    day_from, day_to = _day_bounds(old_day)
    return db.execute(
        conn,
        psql.SHIFT_SUBTASKS,
        wo_id=int(wo_id),
        delta=int(delta),
        week_no=week_no,
        day_from=day_from,
        day_to=day_to,
    )


def shift_labour(conn: Connection, wo_id: int, delta: int) -> int:
    """moveWO 1006: every dated planned-labour row moves by delta."""
    return db.execute(conn, psql.SHIFT_LABOUR, wo_id=int(wo_id), delta=int(delta))


def upsert_pin(
    conn: Connection, wo_id: int, user_id: int, engine_date: datetime, note: str, server_name: str
) -> int:
    """_upsertPin (1120-1130): the update first, the insert when it touched
    nothing. Prev_Start is kept from the first pin (COALESCE in the SQL)."""
    note = (note or "")[:255]
    n = db.execute(
        conn, psql.PIN_UPDATE, wo_id=int(wo_id), user_id=int(user_id), engine_date=engine_date, note=note
    )
    if n == 0:
        n = db.execute(
            conn,
            psql.PIN_INSERT,
            wo_id=int(wo_id),
            user_id=int(user_id),
            engine_date=engine_date,
            note=note,
            server_name=server_name,
        )
    return n


def clear_pin(conn: Connection, wo_id: int) -> int:
    """moveWO 1014: a move back onto the engine's date hands the WO back. The
    row stays, Pinned goes to 'N' (OD-114)."""
    return db.execute(conn, psql.PIN_CLEAR, wo_id=int(wo_id))


def insert_event(
    conn: Connection,
    wo_id: int,
    user_id: int,
    event_name: str,
    details: str,
    server_name: str,
    source_form: str,
) -> int:
    """_eventRow (783-791): one WO_Event_History row. The caller caps details."""
    return db.execute(
        conn,
        psql.EVENT_INSERT,
        wo_id=int(wo_id),
        user_id=int(user_id),
        event_name=event_name,
        details=details,
        server_name=server_name,
        source_form=source_form,
    )
