# ruff: noqa: UP031
# (printf-style %-formatting is kept 1:1 from the Ignition source: '%d.%02d'
#  is the expression that PRODUCES the contract value - week 5 is "2026.05",
#  not "2026.5" - so UP031's f-string rewrite is exactly what parity forbids.
#  Same pragma, same reason, as app/planner/rules.py 1.1.0.)
"""
Azztec_SaaS_app_core_weekno_v1_0_0.py  ->  backend/app/core/weekno.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_S2a_Weekno_Chunk_Spec_v1_0_0.md §3 (OD-48, OD-49)
Ported:   workmate.pm_engine 2.5.0 `_netWeekNoAndYear` (src 486-514), itself a
          line-for-line port of clsGeneralOperation.GetWeekNoANDYear (.NET 871-908)
Pair of:  backend/tests/test_weekno.py 1.0.0

The .NET week number, as `WO_N_Header.Week_No` and `WO_N_Subtasks.Week_No`
store it: 'YYYY.WW' -> numeric(6,2). S2b's move_wo writes one value on the
header (src planner 1.3.1 977) and one per distinct subtask date (1004), so a
wrong answer here is a silent defect on a NOT NULL column the release engine
also reads.

Pure: no I/O, no SQL, no database, no logging. `date`/`datetime` in, `str` or
`Decimal` out.

OD-48 - the two twins, and no float. The source's `weekNo()` returns
`float('%d.%02d')`. The exact artefact is the STRING; `Week_No` is
numeric(6,2) NOT NULL and 2026.01 is not exactly representable as a float, so
a float round-trips through the driver as a value nobody chose and pins badly
in a test. `week_no_and_year()` is byte-1:1 with the source and is the
primary; `week_no()` builds its Decimal FROM that string (never from a float -
Decimal(2026.01) is 2026.0100000000000477...). Nothing on the wire changes:
`wos[].weekNo` still comes from repo._wo_dict reading the column.

OD-49 - what this is measured against. (1) the source, line for line, names
kept. (2) `dbWorkmate_KT.dbo.GetWeekNoAndYear` - an ISO-8601 REWRITE, not a
transcription, and an orphan at KT (gateway refs 0, deps 0); its answers on
thirteen branch dates are pinned by the pair test. (3) `date.isocalendar()`
across 2000-2040 - 14,976 dates, 0 disagreements, measured 2026-09-15.
NOT a reference: `WO_N_Header.Week_No` itself. It is COPIED from the subtask
at release and never recomputed (pm_engine 476), so one start date carries up
to four different values (KT 2026-09-17 -> 2026.35/.36/.37/.38; RST
2026-01-01 -> 2025.53 and 2026.01). Asserting week_no(start) == Week_No goes
red against good data on both databases.

Changelog:
  1.0.0  Initial S2a.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal

__version__ = "1.0.0"
PORTED_FROM = "workmate.pm_engine 2.5.0"

# The source's own recursion guard (src 488). One level is all the algorithm
# can need - 31 December of the previous year never itself yields num6 == 0 -
# but the shape stays, so a divergence is a diff against source.
_MAX_DEPTH = 2


def _as_date(d: object) -> date | None:
    """datetime BEFORE date - datetime is a subclass of date, so the other
    order silently keeps the time of day and breaks `tm_yday` on nothing."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return None


def _net_day_of_week(d: date) -> int:
    """.NET DayOfWeek: Sunday = 0 .. Saturday = 6.

    The source reads `system.date.getDayOfWeek(d) - 1`, and Ignition's
    getDayOfWeek is 1 = Sunday .. 7 = Saturday. Python's `weekday()` is
    0 = Monday .. 6 = Sunday, so the twin is (weekday() + 1) % 7 - never a
    bare weekday() (Landmines §D)."""
    return (d.weekday() + 1) % 7


def _net_week_no_and_year(d: object, _depth: int = 0) -> str | None:
    """src 486-514, line for line, variable names kept.

    Ignition months are ZERO-BASED: the source's getDate(year, 0, 1) is
    1 January and getDate(year, 11, 31) is 31 December. Transcribing those
    literally into `date()` gives a crash and an 11 November respectively -
    the second of which would pass on most days of the year."""
    day = _as_date(d)
    if day is None or _depth > _MAX_DEPTH:
        return None
    year = day.year
    num = year
    dayOfYear = day.timetuple().tm_yday
    num2 = _net_day_of_week(date(year, 1, 1))
    num3 = _net_day_of_week(date(year, 12, 31))
    if num2 == 0:
        num2 = 7
    if num3 == 0:
        num3 = 7
    num4 = 8 - num2
    flag = num2 == 4 or num3 == 4
    # float() and 7.0 are deliberate: Jython's `/` on two ints floors, so the
    # source made the division explicit. int() around ceil keeps the
    # transcription readable on both Pythons (2's ceil returned a float).
    num6 = int(math.ceil(float(dayOfYear - num4) / 7.0))
    if num4 >= 4:
        num6 = num6 + 1
    if num6 > 52 and not flag:
        num6 = 1
        num = num + 1
    if num6 == 0:
        # ceil() of a small negative is -0.0 -> 0. Reachable: 2021-01-01 has
        # num4 = 3 and dayOfYear = 1. The week belongs to the previous year.
        num = num - 1
        prev = _net_week_no_and_year(date(year - 1, 12, 31), _depth + 1)
        if prev is None:
            return None
        num6 = int(prev.split(".")[1])
    return "%d.%02d" % (num, num6)


def week_no_and_year(d: date | datetime) -> str:
    """'YYYY.WW' - the byte-1:1 artefact. Raises ValueError where the source
    returned None; planner 1.3.1's `_weekNoFor` (765) raises there too, and a
    NULL into WO_N_Header.Week_No is a constraint violation either way."""
    s = _net_week_no_and_year(d)
    if s is None:
        raise ValueError("week_no_and_year: no week number for %r" % (d,))
    return s


def week_no(d: date | datetime) -> Decimal:
    """The value as numeric(6,2) holds it - exact, scale 2 (OD-48).

    Built from the string twin, never from a float."""
    return Decimal(week_no_and_year(d))
