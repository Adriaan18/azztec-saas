"""
Azztec_SaaS_app_workorders_rules_v1_0_0.py  ->  backend/app/workorders/rules.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_0.md §3.2 · OD-71
Oracle:   Workmate/Workorder/WOMaint v16.28.3 (docs/reference/WOMaint_2026-09-19_view.json) - the
          binding transforms and onStartup named on each function below.
Pair:     backend/tests/test_workorders_rules.py 1.0.0

PURE. No database, no FastAPI, no clock. The derivations the Ignition view did inside its binding
transforms, moved into the data layer (Perspective Rules v3.5 - data layers assemble, views never do).
Dates and status titles come from app.planner.rules, which already carries the DST-safe calendar
arithmetic (civilDays) and STATUS_TITLES - reused, not copied.

Changelog:
  1.0.0  Initial W1a.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.planner.rules import STATUS_TITLES, civilDays, iso

__version__ = "1.0.0"
VERSION = __version__

# CompleteWithinSeg v1.8.0's six segments, in the view's order (the schema's Literal reads this).
SEGMENTS = ("day", "week", "month", "3month", "nextshut", "range")

# WOStatus' nine cards. STATUS_TITLES is the wire title; the symbol's own labels (Ack'd) are W1b's.
STATUS_CODES = tuple(STATUS_TITLES)

_HIER_BLOCK = re.compile(r"\{([^{}]*)\}")
_HIER_SEG = re.compile(r"\(([^()]*)\)")


def _months_between(start: date, end: date) -> int:
    """The calendar-month twin of system.date.monthsBetween: whole months from start to end,
    one fewer when end's day-of-month is before start's."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def complete_within(start: date | datetime | None, end: date | datetime | None) -> str:
    """txtWorkOrderId.props.text transform - the reverse-derived Complete-within segment from the stored
    start/end span. `range` when either date is missing. Civil days, never (end - start).days on
    datetimes: daysBetween is asymmetric across a DST change; civilDays is the fix already in the tree."""
    if start is None or end is None:
        return "range"
    days = civilDays(iso(start), iso(end))
    if days is None:
        return "range"
    s = start.date() if isinstance(start, datetime) else start
    e = end.date() if isinstance(end, datetime) else end
    months = _months_between(s, e)
    if days == 1:
        return "day"
    if days == 7:
        return "week"
    if days == 14:
        return "nextshut"
    if months == 1 and days <= 31:
        return "month"
    if months == 3 and days <= 93:
        return "3month"
    return "range"


def hierarchy_titles(raw: Any) -> list[str]:
    """lblLocHierarchy.props.text transform - Parent_Location_Hierarchy is {(id)(short)(title)}...;
    the titles, in order. [] for empty; the whole raw string as one item when nothing parses (the
    oracle's `except: return str(raw)`)."""
    if raw is None:
        return []
    text = str(raw)
    if text.strip() == "" or text == "None":
        return []
    parts: list[str] = []
    for block in _HIER_BLOCK.findall(text):
        segs = _HIER_SEG.findall(block)
        if len(segs) >= 3:
            parts.append(segs[2])
    return parts if parts else [text]


def hierarchy(raw: Any) -> str:
    """The titles joined with ' > ' - what the label shows."""
    return " > ".join(hierarchy_titles(raw))


def badge(status: str, short_id: str, progress_id: int, has_po: bool) -> str:
    """WOListTable.props.data transform - the WONumBadge v1.3.0 composite status|shortId|prog|hasPO.
    The status and its pipe are dropped when the status is empty (the transform's `_base`)."""
    st = (status or "").strip()
    sid = (short_id or "").strip()
    base = f"{st}|{sid}" if st else sid
    return f"{base}|{int(progress_id or 0)}|{1 if has_po else 0}"


def money(n: float) -> str:
    """lblAllResourcesValue's _m(): $1,234.56, a leading minus for a negative amount."""
    neg = n < 0
    whole, frac = f"{abs(n):.2f}".split(".")
    groups = ""
    while len(whole) > 3:
        groups = "," + whole[-3:] + groups
        whole = whole[:-3]
    text = f"${whole}{groups}.{frac}"
    return f"-{text}" if neg else text


def resources_totals(rows: list[dict[str, Any]]) -> tuple[float, float, float]:
    """The card header's sums over the compare rows: (planned, actual, diff = actual - planned)."""
    planned = 0.0
    actual = 0.0
    for r in rows:
        planned += float(r.get("planCost") or 0)
        actual += float(r.get("actCost") or 0)
    return planned, actual, actual - planned


def resources_line(planned: float, actual: float, diff: float) -> str:
    """lblAllResourcesValue's text, byte for byte: two spaces either side of each bar, a plus sign only
    on a positive diff."""
    sign = "+" if diff > 0 else ""
    return f"Planned {money(planned)}  |  Actual {money(actual)}  |  Diff {sign}{money(diff)}"


def event_detail(raw: Any) -> str:
    """EVT_TimelineTable's clean(): the .NET braces removed, the text kept."""
    if raw is None:
        return ""
    return str(raw).replace("{", "").replace("}", "")


def query_type_label(code: Any) -> str:
    """QN_QueryTable's TypeLabel: Q -> Query, R -> Reply, anything else as stored (RST has N and A)."""
    qt = (str(code) if code is not None else "").strip()
    if qt == "Q":
        return "Query"
    if qt == "R":
        return "Reply"
    return qt


def rel_label(level: int, selected: bool) -> str:
    """LWO_FamilyTable's Rel: Parent / Child / Grandchild by level, ' (this WO)' on the selected row."""
    rel = {0: "Parent", 1: "Child", 2: "Grandchild"}.get(int(level), str(level))
    return rel + (" (this WO)" if selected else "")


def is_cp_location(short_location: str) -> bool:
    """Search v12's capital-project rule: the location's short id is CP or starts CP-."""
    loc = (short_location or "").strip()
    return loc == "CP" or loc.startswith("CP-")


def filters_for(status: str, type_flag: str, short_location: str) -> dict[str, Any]:
    """onStartup's handoff rule (v16.18.0, OD-71): the list filters that make this WO visible -
    includeClosed 1 for a closed/cancelled WO, woType M for a PM, CP for a capital-project location,
    else N. includeArchive stays 0 - an archived id never reaches this (OD-68)."""
    st = (status or "").strip()
    tf = (type_flag or "N").strip() or "N"
    if tf == "M":
        wo_type = "M"
    elif is_cp_location(short_location):
        wo_type = "CP"
    else:
        wo_type = "N"
    return {
        "includeClosed": 1 if st in ("C", "D") else 0,
        "includeArchive": 0,
        "woType": wo_type,
    }


def stamp(d: date | datetime | None) -> str:
    """'yyyy-MM-dd HH:mm:ss' - a display stamp, milliseconds dropped (the 3.33 ms landmine is a write
    problem; W3's optimistic lock reads the raw column). A plain date stamps at midnight. '' for None."""
    if d is None:
        return ""
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d %H:%M:%S")
    return d.strftime("%Y-%m-%d 00:00:00")


def status_title(code: str) -> str:
    """STATUS_TITLES, the code itself for an unknown one (the planner's convention)."""
    st = (code or "").strip()
    return STATUS_TITLES.get(st, st)
