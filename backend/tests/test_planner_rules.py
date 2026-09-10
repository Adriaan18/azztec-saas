"""
workmate_test_planner_rules_v1_0_0.py  ->  backend/tests/test_planner_rules.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1a_Rules_Chunk_Spec_v1_0_0.md §5
Pair of:  backend/app/planner/rules.py 1.0.0

ZERO DB - plain dicts, exactly as Test_workmate_planner ran on the gateway.
Ports the four pure Night Shift cases from
docs/reference/workmate_planner_test_code_v1_0_0.py with their assertion
values UNCHANGED (they are the parity oracle):
  t_rules      -> TestRules
  t_workers    -> TestWorkers
  t_moverules  -> TestMoveRules
  t_dst        -> TestDst
plus the S1a port guards: weekStart across all seven weekdays, the
parseIso/weekStart date-type rule, iso() on datetimes, strict calendar
validation, _fmtDelta, and the OD-8 rounding divergence documented as a
test instead of a surprise.

Changelog:
  1.0.0  Initial - pair of rules.py 1.0.0.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.planner import rules as P

__version__ = "1.0.0"


# ---------------------------------------------------------------------------
# lineage and scope guards (OD-10 / S1a spec §1)
# ---------------------------------------------------------------------------

def test_version_and_lineage():
    assert P.__version__ == "1.0.0"
    assert P.PORTED_FROM == "workmate.planner 1.3.1"


def test_scope_write_side_stayed_behind():
    # DRY_RUN and the write/data side land in service.py (S2) / repo.py (S1b).
    # If any of these appear here, the chunk grew past its stop line.
    for name in ("DRY_RUN", "moveWO", "rangeData", "loadWO", "fetchWOs", "configValue"):
        assert not hasattr(P, name), name


# ---------------------------------------------------------------------------
# t_rules  (test source line 95)
# ---------------------------------------------------------------------------

class TestRules:
    wo = {"id": 1, "estimate": 6, "resp": 7}
    lab = [
        {"woId": 1, "userId": 12, "hours": 4},
        {"woId": 1, "userId": 13, "hours": 2.5},
        {"woId": 2, "userId": 12, "hours": 9},
    ]

    def test_category(self):
        assert P.category("C", "M") == "DONE"
        assert P.category("H", "M") == "PM"
        assert P.category("R", "N") == "REQ"
        assert P.category("A", "N") == "WO"

    def test_engine_owned(self):
        assert P.engineOwned("H", "M")
        assert not P.engineOwned("V", "M")
        assert not P.engineOwned("A", "N")

    def test_hours_for(self):
        assert P.hoursFor(self.wo, self.lab) == (6.5, "labour")
        assert P.hoursFor({"id": 3, "estimate": 6, "resp": 0}, self.lab) == (6.0, "estimate")
        assert P.hoursFor({"id": 3, "estimate": 0}, []) == (0.0, "")

    def test_assigned_for(self):
        assert P.assignedFor(self.wo, self.lab) == [12, 13, 7]

    def test_worker_load(self):
        wos = [
            {"id": 1, "hrs": 6.5, "resp": 7},
            {"id": 3, "hrs": 5, "resp": 7},
            {"id": 4, "hrs": 3, "resp": 0},
        ]
        # int keys incl. 0 = unassigned; str() is service.range_data's job
        assert P.workerLoad(wos, self.lab) == {12: 13.0, 13: 2.5, 7: 5.0, 0: 3.0}


# ---------------------------------------------------------------------------
# t_workers  (test source line 110)
# ---------------------------------------------------------------------------

SKILL_ROWS = [
    {"userId": 7, "shortId": "KF", "name": "Ken Fisher", "skillId": 1, "sysId": 1, "uomId": 9,
     "skillTitle": "Fitter", "hrsPerWeek": 0, "supplierId": 11, "supplierShort": "TM-MAINT",
     "supplierName": "M", "internalDept": ""},
    {"userId": 12, "shortId": "PM", "name": "Pam McDonald", "skillId": 1, "sysId": 2, "uomId": 9,
     "skillTitle": "Fitter", "hrsPerWeek": 60, "supplierId": 11, "supplierShort": "TM-MAINT",
     "supplierName": "M", "internalDept": ""},
    {"userId": 12, "shortId": "PM", "name": "Pam McDonald", "skillId": 2, "sysId": 3, "uomId": 9,
     "skillTitle": "Welder", "hrsPerWeek": 10, "supplierId": 11, "supplierShort": "TM-MAINT",
     "supplierName": "M", "internalDept": ""},
    {"userId": 50, "shortId": "LH", "name": "Liaanna Hay", "skillId": 3, "sysId": 4, "uomId": 9,
     "skillTitle": "Elec", "hrsPerWeek": 40, "supplierId": 10, "supplierShort": "TM-ELEC",
     "supplierName": "E", "internalDept": "1"},
    {"userId": 88, "shortId": "EXT-AMET", "name": "Aiden - MetalForm", "skillId": 4, "sysId": 5, "uomId": 9,
     "skillTitle": "Welder", "hrsPerWeek": 0, "supplierId": 5565, "supplierShort": "METALFORM",
     "supplierName": "MF", "internalDept": ""},
]


class TestWorkers:
    def _built(self):
        ws, teams = P.buildWorkers(SKILL_ROWS)
        return ws, teams, {w["id"]: w for w in ws}

    def test_skills_sum(self):
        ws, teams, byid = self._built()
        assert byid[12]["hrsPerWeek"] == 70.0
        assert len(byid[12]["skills"]) == 2
        assert byid[12]["skills"][0]["sysId"] == 2

    def test_modal_supplier_internal(self):
        ws, teams, byid = self._built()
        assert byid[7]["internal"] and byid[12]["internal"]

    def test_internal_dept_internal(self):
        ws, teams, byid = self._built()
        assert byid[50]["internal"]

    def test_contractor_sorts_last(self):
        ws, teams, byid = self._built()
        assert not byid[88]["internal"]
        assert ws[-1]["id"] == 88

    def test_teams_order(self):
        ws, teams, byid = self._built()
        assert [t["short"] for t in teams] == ["TM-ELEC", "TM-MAINT", "METALFORM"]

    def test_initials(self):
        ws, teams, byid = self._built()
        assert byid[88]["initials"] == "AMET"
        assert byid[7]["initials"] == "KF"

    def test_capacity_by_week(self):
        ws, teams, byid = self._built()
        wos = [
            {"id": 1, "start": "2026-09-03", "hrs": 6.0},
            {"id": 2, "start": "2026-09-17", "hrs": 0.0},
            {"id": 3, "start": "2026-09-18", "hrs": 4.0},
        ]
        weeks = P.capacityByWeek(wos, ws, "2026-08-31", "2026-10-04")
        assert [w["weekStart"] for w in weeks] == [
            "2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28"]
        assert weeks[0]["planned"] == 6.0
        assert weeks[0]["capacity"] == 110.0
        assert weeks[2]["unknown"] == 1
        assert weeks[0]["pct"] == 5
        assert P.capacityByWeek(wos, ws, "2026-08-31", "2026-10-04", workerIds=[12])[0]["capacity"] == 70.0

    def test_worker_weeks_under_empty(self):
        ww = P.workerWeeks(
            [{"id": 1, "start": "2026-09-03", "hrs": 6.0, "resp": 7},
             {"id": 2, "start": "2026-09-17", "hrs": 4.0, "resp": 0}],
            [{"woId": 2, "userId": 12, "hours": 4.0, "date": "2026-09-18"}],
            [{"id": 7, "hrsPerWeek": 40.0}, {"id": 12, "hrsPerWeek": 20.0}],
            "2026-08-31", "2026-09-20")
        w7 = {r["weekStart"]: r for r in ww["7"]}   # str keys ARE this function's job
        assert w7["2026-08-31"]["flag"] == "under"
        assert w7["2026-09-07"]["flag"] == "empty"


# ---------------------------------------------------------------------------
# t_moverules  (test source line 139)
# ---------------------------------------------------------------------------

WO_T = {"id": 1, "sid": "WO-T", "status": "A", "type": "N", "start": "2026-09-03",
        "end": "2026-09-05", "pinned": False, "pinTable": True, "engineDate": "",
        "subtaskDates": ["2026-09-03"], "labourDates": [("2026-09-03", 2), ("2026-09-04", 1)],
        "hasDetails": True}


class TestMoveRules:
    def test_delta_end_and_confirm_reasons(self):
        r = P.moveRules(WO_T, "2026-09-17", "2026-09-05")
        assert r["ok"] and r["delta"] == 14 and r["newEnd"] == "2026-09-19"
        assert r["confirm"]
        assert sorted(x["code"] for x in r["reasons"]) == ["LABOUR_MULTI", "SPAN"]

    def test_no_confirm(self):
        w1 = dict(WO_T, end="", labourDates=[])
        assert not P.moveRules(w1, "2026-09-17", "2026-09-05")["confirm"]

    def test_past(self):
        w1 = dict(WO_T, end="", labourDates=[])
        assert P.moveRules(w1, "2026-09-01", "2026-09-05")["reasons"][0]["code"] == "PAST"

    def test_active(self):
        w1 = dict(WO_T, end="", labourDates=[], status="V")
        assert P.moveRules(w1, "2026-09-17", "2026-09-05")["reasons"][0]["code"] == "ACTIVE"

    def test_locked(self):
        w1 = dict(WO_T, end="", labourDates=[], status="C")
        assert P.moveRules(w1, "2026-09-17", "2026-09-05")["code"] == "LOCKED_STATUS"

    def test_no_change_and_bad_date(self):
        w1 = dict(WO_T, end="", labourDates=[])
        assert P.moveRules(w1, "2026-09-03", "2026-09-05")["code"] == "NO_CHANGE"
        assert P.moveRules(w1, "nope", "2026-09-05")["code"] == "BAD_DATE"

    def test_pm_no_table_is_engine_owned(self):
        # OD-1: this is the RST reality until the S3 migration - 2,364 PMs
        pm = dict(WO_T, end="", labourDates=[], type="M", status="H", pinTable=False)
        assert P.moveRules(pm, "2026-09-14", "2026-09-05")["code"] == "ENGINE_OWNED"

    def test_pm_pins(self):
        pm = dict(WO_T, end="", labourDates=[], type="M", status="H", pinTable=True)
        r = P.moveRules(pm, "2026-09-14", "2026-09-05")
        assert r["ok"] and r["willPin"] and r["pinnedAfter"]

    def test_pm_return_home_unpins(self):
        pm = dict(WO_T, end="", labourDates=[], type="M", status="H", pinTable=True,
                  pinned=True, start="2026-09-14", engineDate="2026-09-03")
        r = P.moveRules(pm, "2026-09-03", "2026-09-05")
        assert r["ok"] and r["willUnpin"] and not r["pinnedAfter"]

    def test_estimate_rules(self):
        assert P.estimateRules(WO_T, "4.5")["hours"] == 4.5
        assert P.estimateRules(WO_T, -1)["code"] == "BAD_HOURS"
        assert P.estimateRules(dict(WO_T, status="C"), 2)["code"] == "LOCKED_STATUS"

    def test_labour_rules(self):
        sk = {"sysId": 1, "skillId": 1, "supplierId": 11, "uomId": 9, "rate": 0,
              "hrsPerWeek": 40, "skillTitle": "Fitter"}
        lw = {"sid": "WO-T", "status": "A", "start": "2026-09-17"}
        ok = P.labourRules(lw, "Pam", "Y", sk, 4, "")
        assert ok["ok"]
        assert ok["resDate"] == date(2026, 9, 17)   # OD-9: a datetime.date, from the WO start
        assert P.labourRules(dict(lw, status="C"), "Pam", "Y", sk, 4, "")["code"] == "LOCKED_STATUS"
        assert P.labourRules(lw, None, "", sk, 4, "")["code"] == "NO_USER"
        assert P.labourRules(lw, "X", "Y", None, 4, "")["code"] == "NO_SKILL"
        assert P.labourRules(lw, "X", "Y", sk, 0, "")["code"] == "BAD_HOURS"


# ---------------------------------------------------------------------------
# t_dst  (test source line 167) - the 1.3.1 fix, on stdlib now
# ---------------------------------------------------------------------------

class TestDst:
    def test_civil_days_symmetric_across_dst(self):
        # NZ daylight saving change 27 Sep 2026: the gateway's daysBetween
        # gave 12 / -11 here; civilDays must give 12 / -12.
        assert P.civilDays("2026-09-17", "2026-09-29") == 12
        assert P.civilDays("2026-09-29", "2026-09-17") == -12

    def test_civil_days_year_end(self):
        assert P.civilDays("2026-12-30", "2027-01-02") == 3

    def test_move_rules_across_dst(self):
        w = {"sid": "WO-DST", "status": "A", "type": "N", "start": "2026-09-29", "end": "",
             "pinned": False, "pinTable": False, "engineDate": "", "subtaskDates": [],
             "labourDates": []}
        r = P.moveRules(w, "2026-09-17", "2026-09-05")
        assert r["ok"] and r["delta"] == -12 and r["newStart"] == "2026-09-17"

    def test_week_start_sunday(self):
        # The OD-6 mandated case: 2026-09-06 is a Sunday
        assert P.iso(P.weekStart(date(2026, 9, 6))) == "2026-08-31"

    def test_time_of(self):
        assert P.timeOf(datetime(2026, 9, 6, 10, 0, 0)) == "10:00"
        assert P.timeOf(datetime(2026, 9, 7)) == ""    # midnight == 'no time', as in 1.3.1
        assert P.timeOf(date(2026, 9, 7)) == ""        # a plain date has no time
        assert P.timeOf(None) == ""


# ---------------------------------------------------------------------------
# S1a port guards (spec §5 - new cases)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("day", [
    "2026-08-31",  # Mon
    "2026-09-01",  # Tue
    "2026-09-02",  # Wed
    "2026-09-03",  # Thu
    "2026-09-04",  # Fri
    "2026-09-05",  # Sat
    "2026-09-06",  # Sun - the convention-flip case
])
def test_week_start_all_seven_weekdays(day):
    # Stops a (weekday()+1) % 7 ".NET convention" fix sneaking back in.
    assert P.iso(P.weekStart(P.parseIso(day))) == "2026-08-31"


def test_date_type_rule():
    # parseIso and weekStart both return datetime.date (NOT datetime) so the
    # week walks can compare them with <= without a TypeError.
    d = P.parseIso("2026-09-06")
    assert isinstance(d, date) and not isinstance(d, datetime)
    w = P.weekStart(datetime(2026, 9, 6, 10, 30))   # datetime in -> date out
    assert isinstance(w, date) and not isinstance(w, datetime)
    assert w <= d


def test_iso_accepts_date_and_datetime():
    assert P.iso(date(2026, 9, 6)) == "2026-09-06"
    assert P.iso(datetime(2026, 9, 6, 10, 30)) == "2026-09-06"
    assert P.iso(None) == ""


def test_parse_iso_strict_calendar():
    # Deliberate deviation from Java's lenient SimpleDateFormat (rules.py
    # header): invalid calendar dates are None -> BAD_DATE, not rolled over.
    assert P.parseIso("2026-02-31") is None
    assert P.parseIso("2026-13-01") is None
    assert P.parseIso("2026-9-1") is None            # < 10 chars
    assert P.parseIso("2026-09-17T10:00") == date(2026, 9, 17)  # first 10 chars, as before
    assert P.parseIso(None) is None


def test_civil_days_junk_is_none_and_move_rules_says_bad_date():
    assert P.civilDays("nope", "2026-09-01") is None
    w = {"sid": "WO-J", "status": "A", "type": "N", "start": "garbage-start", "end": "",
         "pinned": False, "pinTable": False, "engineDate": "", "subtaskDates": [],
         "labourDates": []}
    r = P.moveRules(w, "2026-09-17", "2026-09-05")
    assert r["code"] == "BAD_DATE" and "cannot diff" in r["message"]


def test_fmt_delta():
    assert P._fmtDelta(1) == "+1 day"
    assert P._fmtDelta(-1) == "-1 day"
    assert P._fmtDelta(14) == "+14 days"


def test_od8_rounding_documented():
    # OD-8 signed 2026-09-11: Python 3 round() is half-to-even; Jython 2.7
    # rounded half away from zero. 100 * 1 / 8 = 12.5 exactly:
    #   Ignition 1.3.1 pct -> 13, this port -> 12. Divergence accepted and
    #   pinned here; counts (the S1 parity oracle) are unaffected.
    weeks = P.capacityByWeek(
        [{"id": 1, "start": "2026-09-01", "hrs": 1.0}],
        [{"id": 7, "hrsPerWeek": 8.0, "internal": True}],
        "2026-08-31", "2026-09-06")
    assert len(weeks) == 1
    assert weeks[0]["pct"] == 12
