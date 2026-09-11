"""
Azztec_SaaS_app_planner_service_v1_0_1.py  ->  backend/app/planner/service.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_S1c_Api_Chunk_Spec_v1_0_0.md §3 · Planner Port Spec §2/§3
Ported:   workmate.planner 1.3.1 rangeData (src 711-746)

S1c: range_data only. Read-only, plain def, takes the request Connection (D-2). Returns the Ignition
dict in src key order; the router validates it and adds the OD-14 envelope. Raises WindowError on a
bad window and nothing else on purpose - everything else is a 500 the middleware reports.

Deviation (spec §3.3): labour is indexed by woId once and the per-WO subset is passed to
rules.hoursFor / rules.assignedFor. Both filter on woId internally, so the output is identical and the
cost drops from O(wos x labour) to O(wos + labour). rules.py stays byte-1:1 with the port.
Pinned by tests/test_planner_api.py::test_range_by_wo_index_matches_full_scan.

The time zone (OD-6) lives here and only here: today = the civil date now in WORKMATE_TZ.

Changelog:
  1.0.1  Ruff UP031: WindowError messages to f-strings. Text unchanged. No behaviour change.
  1.0.0  Initial S1c.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.planner import repo, rules

__version__ = "1.0.1"

MAX_WINDOW_DAYS = 400


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
