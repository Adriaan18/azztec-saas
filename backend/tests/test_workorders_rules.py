"""
Azztec_SaaS_test_workorders_rules_v1_0_0.py  ->  backend/tests/test_workorders_rules.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_0.md §5
Pair of app/workorders/rules.py 1.0.0. No database. Twenty-two cases; the fixtures are RST rows read on
2026-09-19 (662704's start/end pair, its Parent_Location_Hierarchy) and the oracle's own ladders.

Changelog:
  1.0.0  Initial W1a.
"""

from __future__ import annotations

import os
from datetime import date, datetime

os.environ.setdefault("WORKMATE_ENV", "test")

from app.workorders import rules  # noqa: E402 - after env is set

__version__ = "1.0.0"

# WO 662704 on RST, 2026-09-19 - exactly seven days, same time of day.
START_662704 = datetime(2026, 8, 26, 19, 17, 9)
END_662704 = datetime(2026, 9, 2, 19, 17, 9)

HIER_662704 = (
    "{(1)(RST-00)(Red Stag Timber Waipa)}{(6586)(3-00)(3 Secondary Processing)}"
    "{(67)(3CL-00)(08 Coastal)}{(407)(3CL-090)(090 Viking Bins)}{(1963)(3CL-090.170)(170 Bin 16)}"
)


# ---------------------------------------------------------------------------
# complete_within - the oracle's ladder
# ---------------------------------------------------------------------------


def test_complete_within_week_from_the_real_pair():
    assert rules.complete_within(START_662704, END_662704) == "week"


def test_complete_within_day():
    assert rules.complete_within(date(2026, 9, 14), date(2026, 9, 15)) == "day"


def test_complete_within_nextshut_is_fourteen_days():
    assert rules.complete_within(date(2026, 9, 14), date(2026, 9, 28)) == "nextshut"


def test_complete_within_month():
    assert rules.complete_within(date(2026, 1, 15), date(2026, 2, 15)) == "month"
    # a calendar month that is 31 days long is still one month
    assert rules.complete_within(date(2026, 1, 31), date(2026, 3, 3)) == "month"


def test_complete_within_month_plus_two_days_is_range():
    # months == 1 but 33 days: the ladder's `days <= 31` guard
    assert rules.complete_within(date(2026, 1, 15), date(2026, 2, 17)) == "range"


def test_complete_within_three_months():
    assert rules.complete_within(date(2026, 4, 1), date(2026, 7, 1)) == "3month"


def test_complete_within_hundred_days_is_range():
    assert rules.complete_within(date(2026, 1, 1), date(2026, 4, 11)) == "range"


def test_complete_within_missing_date_is_range():
    assert rules.complete_within(None, END_662704) == "range"
    assert rules.complete_within(START_662704, None) == "range"
    assert rules.complete_within(None, None) == "range"


def test_complete_within_week_across_nz_dst():
    # NZDT starts 2026-09-27 02:00; a seven-civil-day span over it is still a week
    assert rules.complete_within(datetime(2026, 9, 24, 8, 0), datetime(2026, 10, 1, 8, 0)) == "week"


# ---------------------------------------------------------------------------
# the location hierarchy string
# ---------------------------------------------------------------------------


def test_hierarchy_titles_from_the_rst_sample():
    assert rules.hierarchy_titles(HIER_662704) == [
        "Red Stag Timber Waipa",
        "3 Secondary Processing",
        "08 Coastal",
        "090 Viking Bins",
        "170 Bin 16",
    ]
    assert rules.hierarchy(HIER_662704) == (
        "Red Stag Timber Waipa > 3 Secondary Processing > 08 Coastal > 090 Viking Bins > 170 Bin 16"
    )


def test_hierarchy_titles_empty():
    assert rules.hierarchy_titles(None) == []
    assert rules.hierarchy_titles("") == []
    assert rules.hierarchy_titles("   ") == []
    assert rules.hierarchy_titles("None") == []
    assert rules.hierarchy("") == ""


def test_hierarchy_titles_malformed_is_the_raw_string():
    assert rules.hierarchy_titles("Coastal / Bin 16") == ["Coastal / Bin 16"]
    assert rules.hierarchy_titles("{(1)(RST-00)}") == ["{(1)(RST-00)}"]


# ---------------------------------------------------------------------------
# the badge composite
# ---------------------------------------------------------------------------


def test_badge_with_status():
    assert rules.badge("V", "3CL-260826-010", 6, True) == "V|3CL-260826-010|6|1"
    assert rules.badge("A ", " K-260630-002 ", 0, False) == "A|K-260630-002|0|0"


def test_badge_without_status_drops_the_first_pipe():
    assert rules.badge("", "3CL-260826-010", 3, False) == "3CL-260826-010|3|0"
    assert rules.badge(None, "X", None, False) == "X|0|0"


# ---------------------------------------------------------------------------
# resources - the card header
# ---------------------------------------------------------------------------


def test_money():
    assert rules.money(1234.5) == "$1,234.50"
    assert rules.money(0) == "$0.00"
    assert rules.money(-0.5) == "-$0.50"
    assert rules.money(1234567.891) == "$1,234,567.89"
    assert rules.money(999.999) == "$1,000.00"


def test_resources_totals():
    rows = [
        {"planCost": 100.0, "actCost": 80.0},
        {"planCost": None, "actCost": 25.5},
        {"planCost": 40.0, "actCost": None},
    ]
    assert rules.resources_totals(rows) == (140.0, 105.5, -34.5)
    assert rules.resources_totals([]) == (0.0, 0.0, 0.0)


def test_resources_line_signs():
    assert rules.resources_line(100.0, 150.0, 50.0) == "Planned $100.00  |  Actual $150.00  |  Diff +$50.00"
    assert rules.resources_line(100.0, 80.0, -20.0) == "Planned $100.00  |  Actual $80.00  |  Diff -$20.00"
    assert rules.resources_line(0.0, 0.0, 0.0) == "Planned $0.00  |  Actual $0.00  |  Diff $0.00"


# ---------------------------------------------------------------------------
# the tabs' small labels
# ---------------------------------------------------------------------------


def test_event_detail_strips_the_braces():
    raw = "{WO_Title} changed from {Illegag bearer placement alarms} to {Illegal bearer placement alarms}"
    assert rules.event_detail(raw) == (
        "WO_Title changed from Illegag bearer placement alarms to Illegal bearer placement alarms"
    )
    assert rules.event_detail(None) == ""


def test_query_type_label():
    assert rules.query_type_label("Q") == "Query"
    assert rules.query_type_label("R") == "Reply"
    assert rules.query_type_label("N") == "N"
    assert rules.query_type_label("A ") == "A"
    assert rules.query_type_label(None) == ""


def test_rel_label():
    assert rules.rel_label(0, False) == "Parent"
    assert rules.rel_label(1, True) == "Child (this WO)"
    assert rules.rel_label(2, False) == "Grandchild"
    assert rules.rel_label(9, False) == "9"


# ---------------------------------------------------------------------------
# the handoff rule
# ---------------------------------------------------------------------------


def test_filters_for():
    assert rules.filters_for("V", "N", "3CL-090") == {"includeClosed": 0, "includeArchive": 0, "woType": "N"}
    assert rules.filters_for("C", "N", "3CL-090")["includeClosed"] == 1
    assert rules.filters_for("D", "N", "")["includeClosed"] == 1
    assert rules.filters_for("A", "M", "CP-01")["woType"] == "M"  # the flag wins over the location
    assert rules.filters_for("A", "N", "CP-01")["woType"] == "CP"
    assert rules.filters_for("A", "N", "CP")["woType"] == "CP"
    assert rules.filters_for("A", "N", "CPX")["woType"] == "N"
    assert rules.filters_for("", "", "")["woType"] == "N"


# ---------------------------------------------------------------------------
# stamps and titles
# ---------------------------------------------------------------------------


def test_stamp_and_status_title():
    assert rules.stamp(datetime(2026, 8, 26, 19, 19, 4, 57000)) == "2026-08-26 19:19:04"
    assert rules.stamp(date(2026, 8, 26)) == "2026-08-26 00:00:00"
    assert rules.stamp(None) == ""
    assert rules.status_title("V") == "Active"
    assert rules.status_title("C ") == "Closed"
    assert rules.status_title("Z") == "Z"
    assert rules.status_title("") == ""
    assert rules.SEGMENTS == ("day", "week", "month", "3month", "nextshut", "range")
    assert set(rules.STATUS_CODES) == {"R", "H", "P", "K", "A", "V", "C", "D", "F"}
