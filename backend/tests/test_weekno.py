"""
Azztec_SaaS_test_weekno_v1_0_1.py  ->  backend/tests/test_weekno.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_S2a_Weekno_Chunk_Spec_v1_0_0.md §5 (OD-48, OD-49)
Pair of:  backend/app/core/weekno.py 1.0.0

ZERO DB, and actually zero DB - this file imports `datetime`, `decimal` and
the module under test, nothing else. Check the import graph, not just the
assertions (Ways of Working §4). No fixture, no connection, no skip: this
file must not change the suite's skip count, which is load-bearing at 2.

The three things the port is measured against (OD-49):

  1. the source, line for line - workmate.pm_engine 2.5.0 486-514.
  2. `dbWorkmate_KT.dbo.GetWeekNoAndYear` on thirteen branch dates. That
     function is an ISO-8601 REWRITE, not a transcription, and an orphan at
     KT (gateway references 0, dependencies 0), so it is an equivalence
     oracle rather than a second copy of the algorithm. Every value in
     KT_SQL_FUNCTION below was READ off the box on 2026-09-15 by calling the
     function itself - none is recomputed here.
  3. `date.isocalendar()` across 2000-2040, which reproduces pm_engine's own
     equivalence claim (its comment at 477) inside the suite instead of
     quoting it. Its expected value is built with an f-string, NOT with the
     module's own '%d.%02d' expression: a gate that formats the way the
     thing it is checking formats would agree with a module that padded
     wrongly in exactly the same way.

DELIBERATELY ABSENT - do not add it later:

  There is NO test that reads `WO_N_Header.Week_No` and asserts it equals
  week_no(Request_Start_Date). Week_No is COPIED from the subtask when the
  PM engine releases the WO and is never recomputed (pm_engine 476), so it
  is not a function of the start date at all. Measured 2026-09-15: KT's
  2026-09-17 carries 2026.35, 2026.36, 2026.37 AND 2026.38; RST's
  2026-01-01 carries both 2025.53 and 2026.01; RST's 2025-12-28 carries both
  2025.52 and 2025.53. Such a test goes red against perfectly good data on
  both databases - the same class of mistake as asserting one database's row
  order (Ways of Working §6).

Changelog:
  1.0.1  The ISO gate built its expected value with the module's own
         "%d.%02d" expression - UP031 flagged it, and it was partly circular
         besides: it would have agreed with a module that padded wrongly the
         same way. Now an f-string, independent of the implementation. No
         case added, removed or renamed - 25 either way - and no file-wide
         noqa is needed here, unlike the module, where the format string IS
         the artefact.
  1.0.0  Initial S2a.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.core import weekno as W

# Read off the box 2026-09-15:
#   sqlcmd ... SELECT dbWorkmate_KT.dbo.GetWeekNoAndYear(d) ...
# Thirteen dates chosen to hit every branch in the algorithm, not for variety.
KT_SQL_FUNCTION = [
    ("2019-12-30", "2020.01"),  # num6 > 52 and not flag -> week 1, year + 1
    ("2020-12-31", "2020.53"),  # flag True -> week 53 survives
    ("2021-01-01", "2020.53"),  # num6 == 0 -> recurse into 2020-12-31
    ("2025-12-26", "2025.52"),
    ("2025-12-28", "2025.52"),
    ("2025-12-29", "2026.01"),
    ("2025-12-31", "2026.01"),
    ("2026-01-01", "2026.01"),  # num2 == num3 == 4, flag True
    ("2026-01-03", "2026.01"),
    ("2026-01-04", "2026.01"),
    ("2026-09-07", "2026.37"),
    ("2026-09-14", "2026.38"),  # the Port Spec §8 figure, checked not recalled
    ("2026-12-21", "2026.52"),
]


@pytest.mark.parametrize(("iso_day", "expected"), KT_SQL_FUNCTION)
def test_matches_the_kt_sql_function(iso_day: str, expected: str) -> None:
    """Reference 2: the values the KT function itself returned."""
    assert W.week_no_and_year(date.fromisoformat(iso_day)) == expected


def test_iso_equivalent_2000_to_2040() -> None:
    """Reference 3. pm_engine 477 claims equivalence to ISO-8601 week-year +
    week over this range; run it rather than trust it. 14,976 dates (the
    range is inclusive at both ends - the source comment says 14,975)."""
    day, end, n, disagree = date(2000, 1, 1), date(2040, 12, 31), 0, []
    while day <= end:
        n += 1
        y, w, _dow = day.isocalendar()
        if W.week_no_and_year(day) != f"{y}.{w:02d}":
            disagree.append(day.isoformat())
        day += timedelta(days=1)
    assert n == 14976
    assert disagree == []


def test_num6_zero_recurses_into_the_previous_year() -> None:
    """2021 starts on a Friday: num2 = 5, num4 = 3, so 1 January gives
    ceil(-2/7) = 0 and the week belongs to 2020."""
    assert W.week_no_and_year(date(2021, 1, 1)) == "2020.53"


def test_over_52_resets_to_week_one() -> None:
    """2019 ends on a Tuesday with flag False, so 30 December is week 1 of
    2020 - the `num6 > 52 and not flag` branch."""
    assert W.week_no_and_year(date(2019, 12, 30)) == "2020.01"


def test_flag_keeps_week_53() -> None:
    """2020's 31 December is a Thursday (num3 == 4), so flag is True and week
    53 is NOT reset - the branch above must not fire here."""
    assert W.week_no_and_year(date(2020, 12, 31)) == "2020.53"


@pytest.mark.parametrize(
    ("iso_day", "expected"),
    [("2026-01-01", "2026.01"), ("2026-01-26", "2026.05"), ("2020-12-31", "2020.53")],
)
def test_week_is_zero_padded(iso_day: str, expected: str) -> None:
    """'%d.%02d' is contract, not cosmetics: week 5 is .05. An f-string
    f'{num}.{num6}' gives 2026.5, a different number in numeric(6,2)."""
    assert W.week_no_and_year(date.fromisoformat(iso_day)) == expected


def test_week_no_is_an_exact_decimal() -> None:
    """OD-48. Built from the string, so scale is 2 and the value is exact -
    unlike Decimal(2026.01), which is 2026.0100000000000477..."""
    got = W.week_no(date(2026, 1, 1))
    assert got == Decimal("2026.01")
    assert got.as_tuple().exponent == -2
    assert got != Decimal(2026.01)


def test_week_no_fits_numeric_6_2() -> None:
    """WO_N_Header.Week_No is numeric(6,2) NOT NULL - 4 digits before the
    point, 2 after (read from INFORMATION_SCHEMA on RST, 2026-09-15)."""
    for iso_day, _expected in KT_SQL_FUNCTION:
        got = W.week_no(date.fromisoformat(iso_day))
        whole, _dot, frac = str(got).partition(".")
        assert len(whole) <= 4
        assert len(frac) == 2


def test_accepts_date_and_datetime() -> None:
    """A datetime carries a time of day; the answer must not. `_as_date`
    checks datetime BEFORE date because datetime subclasses date."""
    plain = date(2026, 9, 14)
    stamped = datetime(2026, 9, 14, 23, 59, 59)
    assert W.week_no_and_year(stamped) == W.week_no_and_year(plain) == "2026.38"


def test_none_raises_value_error() -> None:
    """planner 1.3.1's `_weekNoFor` (765) raises when the port returns None,
    and the move then rolls back. A NULL into Week_No is a constraint
    violation, so failing loudly here is the whole point."""
    with pytest.raises(ValueError):
        W.week_no_and_year(None)
    with pytest.raises(ValueError):
        W.week_no_and_year("2026-09-14")


def test_ported_from_names_the_source() -> None:
    """OD-10's precedent: the lineage is a constant, not a comment."""
    assert W.PORTED_FROM.startswith("workmate.pm_engine")
    assert W.PORTED_FROM.endswith("2.5.0")
