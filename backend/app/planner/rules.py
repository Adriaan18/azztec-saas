# ruff: noqa: UP031
# (printf-style %-formatting is kept 1:1 from the Ignition source - every
#  refusal/confirm message string must stay byte-identical for parity.)
"""
workmate_planner_rules_v1_0_0.py  ->  backend/app/planner/rules.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1a_Rules_Chunk_Spec_v1_0_0.md (whole file)
Parent:   Azztec_SaaS_Planner_Port_Spec_v1_0_0.md §2, §5
Ported from: workmate.planner 1.3.1 (docs/reference/workmate_planner_code_v1_3_1.py)
Pair:     backend/tests/test_planner_rules.py 1.0.0

The PURE rules of the Planner. Zero I/O: no database, no FastAPI, no config,
no imports beyond datetime. Plain dicts in, plain dicts/tuples out.

Function names and dict keys are the Ignition names EXACTLY (camelCase) -
they are the JSON contract and the parity-test surface. service.py will be
snake_case; this file is not. Do not "fix" the naming, the %-formatting,
the branch order in workerWeeks, or the string date comparisons in
moveRules - behaviour parity beats style (S1a spec §4).

Signed decisions in force:
  OD-1  engineOwned() unchanged. Without dbo.WO_N_Plan (RST today) every
        engine-owned PM comes back locked/immovable - that is the decision
        working, not a defect. The S3 migration makes them movable-with-pin.
  OD-6  All day math on civil dates (datetime.date) - no instants, no zones.
        civilDays() ported untouched; parseIso/iso/timeOf/weekStart are
        stdlib REWRITES of the system.date.* originals. weekStart uses
        Python weekday() 0=Monday in place of Ignition getDayOfWeek
        1=Sunday - a Sunday goes back 6 days under both conventions.
  OD-8  round() keeps Python 3 half-to-even semantics (Jython rounded half
        away from zero). Exposure is <=1 on pct values; documented in the
        pair's test_od8_rounding_documented, not patched.
  OD-9  labourRules returns resDate as a datetime.date (not JSON-safe);
        the S4 service formats it.
  OD-10 New version lineage from 1.0.0; PORTED_FROM carries the Ignition
        lineage for parity assertions. The /range contract's libVersion
        reports __version__.

Deliberate deviation (S1a spec §3.1): parseIso validates the calendar
strictly - '2026-02-31' is None here, where Java's lenient SimpleDateFormat
rolled it to March. civilDays() (_civil) was already strict in 1.3.1, so
this makes the module agree with itself; garbage in is BAD_DATE out.

Changelog:
  1.0.0  Initial port of the pure set from workmate.planner 1.3.1:
         category engineOwned hoursFor assignedFor classifyTeams
         buildWorkers initialsOf workerLoad capacityByWeek workerWeeks
         moveRules estimateRules labourRules civilDays weekStart parseIso
         iso timeOf + helpers (_s _i _f _civil _weekKeyOf _fmtDelta) and
         the rule constants. DRY_RUN, SQL, fetch*, loadWO and every write
         function stay behind for S1b/S2 (spec §2.3).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

__version__ = "1.0.0"
PORTED_FROM = "workmate.planner 1.3.1"

_LOCKED_STATUSES = ('C', 'D')  # never movable
_CONFIRM_STATUSES = ('V',)     # movable after a confirm (work in progress)
_MAX_ESTIMATE = 1000.0
_MAX_LABOUR_HOURS = 500.0
_MAX_HRS_PER_WEEK = 168.0      # setCapacity bound - the S4 service imports it

# spec F3: statuses the PM engine never re-dates
_ENGINE_FROZEN = ('V', 'C', 'D')
# HomeCalendar F1 colours - shipped so the UI and the Home page agree
COLOURS = {'DONE': '#81C784', 'PM': '#4DD0E1', 'REQ': '#F48FB1', 'WO': '#FFC65C'}
STATUS_TITLES = {'R': 'Request', 'H': 'Planned', 'P': 'Pending', 'K': 'Acknowledged',
    'A': 'Approved', 'V': 'Active', 'C': 'Closed', 'D': 'Cancelled', 'F': 'Deferred'}


# ---------------------------------------------------------------------------
# small helpers - the coercion twins
# ---------------------------------------------------------------------------

def _s(v):
    return '' if v is None else str(v).strip()


def _i(v, d=0):
    # int(float(...)) truncates toward zero - 1:1 with the source, keep it
    try:
        if v is None or str(v).strip() == '':
            return d
        return int(float(str(v).strip()))
    except Exception:
        return d


def _f(v, d=0.0):
    try:
        if v is None or str(v).strip() == '':
            return d
        return float(str(v).strip())
    except Exception:
        return d


def _fmtDelta(delta):
    """'+1 day' / '-12 days'. Lives here (not the service) because
    moveRules' LABOUR_MULTI reason text uses it - S1a spec §2.1."""
    delta = int(delta)
    return ('%+d day' % delta) if abs(delta) == 1 else ('%+d days' % delta)


# ---------------------------------------------------------------------------
# dates - OD-6. parseIso and weekStart BOTH return datetime.date: the week
# walks below compare them with <=, and a date/datetime mix is a TypeError.
# ---------------------------------------------------------------------------

def _civil(isoDay):
    """yyyy-MM-dd -> datetime.date, or None. Ported untouched (1.3.1)."""
    t = _s(isoDay)[:10]
    try:
        return date(int(t[0:4]), int(t[5:7]), int(t[8:10]))
    except Exception:
        return None


def parseIso(s):
    """'yyyy-MM-dd' (first 10 chars) -> datetime.date, or None.
    Strict calendar validation - see the header deviation note."""
    s = _s(s)
    if len(s) < 10:
        return None
    return _civil(s)


def iso(d):
    """date or datetime -> 'yyyy-MM-dd'; '' for None."""
    return '' if d is None else d.strftime('%Y-%m-%d')


def timeOf(d):
    """'HH:mm' when the datetime carries a time of day, else ''.
    A plain date has no time -> ''. Midnight and 'no time' stay
    indistinguishable, exactly as in 1.3.1."""
    if d is None or not isinstance(d, datetime):
        return ''
    t = d.strftime('%H:%M')
    return '' if t == '00:00' else t


def civilDays(isoFrom, isoTo):
    """Whole calendar days from isoFrom to isoTo (yyyy-MM-dd), negative when
    isoTo is earlier. Pure calendar arithmetic - immune to DST (the 1.3.1
    fix, ported untouched)."""
    a = _civil(isoFrom)
    b = _civil(isoTo)
    if a is None or b is None:
        return None
    return int((b - a).days)


def weekStart(d):
    """Monday on or before d. Accepts date or datetime, returns date.
    OD-6 convention flip: Ignition getDayOfWeek was 1=Sunday with
    back = (dow - 2) % 7; Python weekday() is 0=Monday, so back = weekday().
    Both send a Sunday back 6 days - the pair tests all seven weekdays."""
    if isinstance(d, datetime):
        d = d.date()
    return d - timedelta(days=d.weekday())


def _weekKeyOf(isoDay):
    d = parseIso(isoDay)
    return '' if d is None else iso(weekStart(d))


# ---------------------------------------------------------------------------
# PURE rules
# ---------------------------------------------------------------------------

def category(status, typeFlag):
    """DONE > PM > REQ > WO - the HomeCalendar legend order (F1)."""
    st = _s(status).upper()
    if st == 'C':
        return 'DONE'
    if _s(typeFlag).upper() == 'M':
        return 'PM'
    if st == 'R':
        return 'REQ'
    return 'WO'


def engineOwned(status, typeFlag):
    """True when the PM engine would re-date this WO if the planner moved it
    (spec F3): a PM whose status is not in the engine's frozen set.
    OD-1: unchanged - no RST branch, no new code paths."""
    if _s(typeFlag).upper() != 'M':
        return False
    return _s(status).upper() not in _ENGINE_FROZEN


def hoursFor(wo, labourRows):
    """(hours, source). Source 'labour' when WO_N_Resource 'L' rows carry
    hours, else 'estimate' from Duration_In_Hours, else (0.0, '') = unknown."""
    total = 0.0
    for r in labourRows or []:
        if _i(r.get('woId')) == _i(wo.get('id')):
            total += _f(r.get('hours'))
    if total > 0:
        return (round(total, 2), 'labour')
    est = _f(wo.get('estimate'))
    if est > 0:
        return (round(est, 2), 'estimate')
    return (0.0, '')


def assignedFor(wo, labourRows):
    """Ordered unique user ids: labour-row users first, then the responsible
    user when set (D-5)."""
    out = []
    for r in labourRows or []:
        if _i(r.get('woId')) == _i(wo.get('id')):
            u = _i(r.get('userId'))
            if u > 0 and u not in out:
                out.append(u)
    resp = _i(wo.get('resp'))
    if resp > 0 and resp not in out:
        out.append(resp)
    return out


def classifyTeams(skillRows):
    """skillRows: dicts with supplierId, supplierShort, supplierName,
    internalDept. Returns {supplierId: {'id','short','name','internal','users'}}.
    Internal = the modal supplier among active skill rows (KJ 5.0a rule)
    OR Supplier.Internal_Dept in ('1','Y'). Never a hard-coded id.
    'users' starts 0 here; buildWorkers counts it."""
    counts = {}
    teams = {}
    for r in skillRows or []:
        sid = _i(r.get('supplierId'))
        if sid <= 0:
            continue
        counts[sid] = counts.get(sid, 0) + 1
        if sid not in teams:
            teams[sid] = {'id': sid, 'short': _s(r.get('supplierShort')),
                'name': _s(r.get('supplierName')), 'internal': False, 'users': 0}
        if _s(r.get('internalDept')).upper() in ('1', 'Y'):
            teams[sid]['internal'] = True
    if counts:
        modal = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        teams[modal]['internal'] = True
    return teams


def buildWorkers(skillRows):
    """Collapse skill rows (one per user x skill) into worker dicts with the
    summed weekly capacity and the team of the first skill row.
    Returns (workers, teamList) - internal first, then by name / short."""
    teams = classifyTeams(skillRows)
    byUser = {}
    order = []
    for r in skillRows or []:
        uid = _i(r.get('userId'))
        if uid <= 0:
            continue
        w = byUser.get(uid)
        if w is None:
            name = _s(r.get('name'))
            w = {'id': uid, 'sid': _s(r.get('shortId')), 'name': name,
                'initials': initialsOf(_s(r.get('shortId')), name),
                'skills': [], 'hrsPerWeek': 0.0, 'teamId': 0, 'team': '',
                'internal': False}
            byUser[uid] = w
            order.append(uid)
        sid = _i(r.get('supplierId'))
        t = teams.get(sid)
        w['skills'].append({'id': _i(r.get('skillId')), 'title': _s(r.get('skillTitle')),
            'sysId': _i(r.get('sysId')), 'hrsPerWeek': _f(r.get('hrsPerWeek')), 'supplierId': sid})
        w['hrsPerWeek'] = round(w['hrsPerWeek'] + _f(r.get('hrsPerWeek')), 2)
        if w['teamId'] == 0 and sid > 0:
            w['teamId'] = sid
            w['team'] = t['short'] if t else ''
        if t and t['internal']:
            w['internal'] = True
    for uid in order:
        w = byUser[uid]
        t = teams.get(w['teamId'])
        if t:
            t['users'] += 1
    workers = [byUser[u] for u in order]
    workers.sort(key=lambda w: (0 if w['internal'] else 1, w['name'].lower()))
    teamList = sorted(teams.values(), key=lambda t: (0 if t['internal'] else 1, t['short']))
    return workers, teamList


def initialsOf(shortId, name):
    s = _s(shortId)
    if s.upper().startswith('EXT-'):
        s = s[4:]
    if 1 < len(s) <= 4:
        return s.upper()
    parts = [p for p in _s(name).replace('-', ' ').split(' ') if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return s[:3].upper() if s else '?'


def workerLoad(wos, labourRows):
    """{userId: hours} with INT keys, incl. 0 = unassigned. Labour rows
    attribute their own hours; a WO without labour rows attributes its
    estimate to the responsible user. The str(key) conversion for the JSON
    contract is service.range_data's job (source 738), not this function's."""
    load = {}
    hasLabour = {}
    for r in labourRows or []:
        wid = _i(r.get('woId'))
        uid = _i(r.get('userId'))
        h = _f(r.get('hours'))
        if h <= 0:
            continue
        hasLabour[wid] = True
        load[uid] = round(load.get(uid, 0.0) + h, 2)
    for wo in wos or []:
        wid = _i(wo.get('id'))
        if hasLabour.get(wid):
            continue
        h = _f(wo.get('hrs'))
        if h <= 0:
            continue
        uid = _i(wo.get('resp'))
        load[uid] = round(load.get(uid, 0.0) + h, 2)
    return load


def capacityByWeek(wos, workers, fromIso, toIso, workerIds=None):
    """One dict per Mon-Sun week touching [fromIso, toIso]:
      weekStart, planned (h, WOs starting that week), unknown (WOs with no
      hours), count, capacity (sum Hrs_Per_Week of the capacity workers), pct.
    Capacity workers = workerIds when given, else every internal worker."""
    start = parseIso(fromIso)
    end = parseIso(toIso)
    if start is None or end is None:
        return []
    if workerIds:
        want = set([_i(x) for x in workerIds])
        cap = sum([_f(w.get('hrsPerWeek')) for w in workers or [] if _i(w.get('id')) in want])
    else:
        cap = sum([_f(w.get('hrsPerWeek')) for w in workers or [] if w.get('internal')])
    cap = round(cap, 2)
    weeks = []
    index = {}
    ws = weekStart(start)
    while ws <= end:
        k = iso(ws)
        index[k] = len(weeks)
        weeks.append({'weekStart': k, 'planned': 0.0, 'unknown': 0, 'count': 0,
            'capacity': cap, 'pct': 0})
        ws = ws + timedelta(days=7)
    for wo in wos or []:
        d = parseIso(wo.get('start'))
        if d is None:
            continue
        k = iso(weekStart(d))
        i = index.get(k)
        if i is None:
            continue
        w = weeks[i]
        w['count'] += 1
        h = _f(wo.get('hrs'))
        if h > 0:
            w['planned'] = round(w['planned'] + h, 2)
        else:
            w['unknown'] += 1
    for w in weeks:
        w['pct'] = int(round(100.0 * w['planned'] / w['capacity'])) if w['capacity'] > 0 else 0
    return weeks


def workerWeeks(wos, labourRows, workers, fromIso, toIso):
    """PURE (S4). {str(userId): [{weekStart, planned, capacity, pct, flag}]}
    for every worker with capacity > 0 or any planned hours in the window.
    Attribution: a labour row lands in the week of its Res_Date (else its
    WO's start); a WO with no labour rows lands its estimate on the
    responsible user by start week. flag: over (>100%), ok (80-100),
    under (1-79, capacity > 0), empty (0). Branch order is behaviour -
    do not let a lint autofix reorder it (S1a spec §4)."""
    start = parseIso(fromIso)
    end = parseIso(toIso)
    if start is None or end is None:
        return {}
    weekKeys = []
    ws = weekStart(start)
    while ws <= end:
        weekKeys.append(iso(ws))
        ws = ws + timedelta(days=7)
    byWo = dict([(_i(w.get('id')), w) for w in wos or []])
    planned = {}
    hasLabour = {}
    for r in labourRows or []:
        wid = _i(r.get('woId'))
        uid = _i(r.get('userId'))
        h = _f(r.get('hours'))
        if h <= 0 or uid <= 0:
            continue
        hasLabour[wid] = True
        wk = _weekKeyOf(r.get('date')) or _weekKeyOf((byWo.get(wid) or {}).get('start'))
        if not wk:
            continue
        planned.setdefault(uid, {})
        planned[uid][wk] = round(planned[uid].get(wk, 0.0) + h, 2)
    for wo in wos or []:
        wid = _i(wo.get('id'))
        if hasLabour.get(wid):
            continue
        h = _f(wo.get('hrs'))
        uid = _i(wo.get('resp'))
        if h <= 0 or uid <= 0:
            continue
        wk = _weekKeyOf(wo.get('start'))
        if not wk:
            continue
        planned.setdefault(uid, {})
        planned[uid][wk] = round(planned[uid].get(wk, 0.0) + h, 2)
    out = {}
    for w in workers or []:
        uid = _i(w.get('id'))
        cap = _f(w.get('hrsPerWeek'))
        mine = planned.get(uid, {})
        if cap <= 0 and not mine:
            continue
        rows = []
        for wk in weekKeys:
            p = mine.get(wk, 0.0)
            pct = int(round(100.0 * p / cap)) if cap > 0 else 0
            if p <= 0:
                flag = 'empty'
            elif cap <= 0:
                flag = 'ok'
            elif pct > 100:
                flag = 'over'
            elif pct >= 80:
                flag = 'ok'
            else:
                flag = 'under'
            rows.append({'weekStart': wk, 'planned': p, 'capacity': cap, 'pct': pct, 'flag': flag})
        out[str(uid)] = rows
    return out


def moveRules(wo, toIso, todayIso):
    """PURE (spec D-2/D-4). wo needs status/type/start/end/pinned/pinTable/
    engineDate/subtaskDates/labourDates as loadWO builds them. Returns
      {ok, code, message, confirm, reasons[], delta, newStart, newEnd,
       willPin, willUnpin, pinnedAfter}
    ok=False  -> refuse (LOCKED_STATUS | ENGINE_OWNED | NO_START | BAD_DATE | NO_CHANGE)
    confirm   -> True when the move needs a planner confirm (reasons say why).
    newStart/todayIso and end/start comparisons are STRING comparisons of
    yyyy-MM-dd - deliberate, leave them (S1a spec §4)."""
    st = _s(wo.get('status')).upper()
    if st in _LOCKED_STATUSES:
        return {'ok': False, 'code': 'LOCKED_STATUS', 'confirm': False, 'reasons': [],
            'message': '%s is %s - closed and cancelled work orders do not move' % (wo.get('sid'), STATUS_TITLES.get(st, st))}
    eo = engineOwned(st, wo.get('type'))
    if eo and not wo.get('pinned') and not wo.get('pinTable'):
        return {'ok': False, 'code': 'ENGINE_OWNED', 'confirm': False, 'reasons': [],
            'message': '%s is a PM the release engine owns - run the S3 DDL (WO_N_Plan) to allow planner pins' % wo.get('sid')}
    if not wo.get('start'):
        return {'ok': False, 'code': 'NO_START', 'confirm': False, 'reasons': [],
            'message': '%s has no start date' % wo.get('sid')}
    target = parseIso(toIso)
    if target is None:
        return {'ok': False, 'code': 'BAD_DATE', 'confirm': False, 'reasons': [],
            'message': 'target date %r is not yyyy-MM-dd' % toIso}
    delta = civilDays(wo.get('start'), iso(target))
    if delta is None:
        return {'ok': False, 'code': 'BAD_DATE', 'confirm': False, 'reasons': [],
            'message': 'cannot diff %r and %r' % (wo.get('start'), toIso)}
    if delta == 0:
        return {'ok': False, 'code': 'NO_CHANGE', 'confirm': False, 'reasons': [],
            'message': '%s already starts on %s' % (wo.get('sid'), wo.get('start'))}
    newStart = iso(target)
    newEnd = ''
    if wo.get('end'):
        newEnd = iso(parseIso(wo.get('end')) + timedelta(days=delta))
    reasons = []
    if newStart < _s(todayIso):
        reasons.append({'code': 'PAST', 'text': 'The target date is in the past'})
    if st in _CONFIRM_STATUSES:
        reasons.append({'code': 'ACTIVE', 'text': '%s is Active (work in progress)' % wo.get('sid')})
    if wo.get('end') and wo.get('end') > wo.get('start'):
        reasons.append({'code': 'SPAN', 'text': 'Multi-day span: the end date moves %s -> %s' % (wo.get('end'), newEnd)})
    ld = wo.get('labourDates') or []
    if len(ld) > 1:
        reasons.append({'code': 'LABOUR_MULTI', 'text': 'Planned labour sits on %d dates - every row moves %s' % (len(ld), _fmtDelta(delta))})
    willPin = bool(eo and not wo.get('pinned') and wo.get('pinTable'))
    willUnpin = bool(wo.get('pinned') and wo.get('engineDate') and newStart == _s(wo.get('engineDate'))[:10])
    return {'ok': True, 'code': 'OK', 'confirm': len(reasons) > 0, 'reasons': reasons,
        'message': '', 'delta': int(delta), 'newStart': newStart, 'newEnd': newEnd,
        'willPin': willPin, 'willUnpin': willUnpin,
        'pinnedAfter': bool((wo.get('pinned') or willPin) and not willUnpin)}


def estimateRules(wo, hours):
    """0 <= h <= 1000, needs a WO_N_Details row, not on a locked status."""
    st = _s(wo.get('status')).upper()
    if st in _LOCKED_STATUSES:
        return {'ok': False, 'code': 'LOCKED_STATUS',
            'message': '%s is %s - estimates are read-only' % (wo.get('sid'), STATUS_TITLES.get(st, st))}
    h = _f(hours, -1.0)
    if h < 0 or h > _MAX_ESTIMATE:
        return {'ok': False, 'code': 'BAD_HOURS', 'message': 'hours must be between 0 and %d' % int(_MAX_ESTIMATE)}
    if not wo.get('hasDetails'):
        return {'ok': False, 'code': 'NO_DETAILS', 'message': '%s has no WO_N_Details row' % wo.get('sid')}
    return {'ok': True, 'code': 'OK', 'message': '', 'hours': round(h, 2)}


def labourRules(wo, userName, userActive, skillRow, hours, resDateIso):
    """PURE-ish (inputs pre-fetched). Refuse codes: LOCKED_STATUS, NO_USER,
    USER_INACTIVE, NO_SKILL, BAD_HOURS, BAD_DATE. OD-9: resDate in the OK
    dict is a datetime.date - the S4 service formats it, this stays 1:1."""
    st = _s(wo.get('status')).upper()
    if st in _LOCKED_STATUSES:
        return {'ok': False, 'code': 'LOCKED_STATUS', 'message': '%s is %s - planning is locked' % (wo.get('sid'), STATUS_TITLES.get(st, st))}
    if userName is None:
        return {'ok': False, 'code': 'NO_USER', 'message': 'user not found'}
    if userActive != 'Y':
        return {'ok': False, 'code': 'USER_INACTIVE', 'message': '%s is not an active user' % userName}
    if skillRow is None:
        return {'ok': False, 'code': 'NO_SKILL', 'message': '%s has no active skill row - add one on the Labour page first' % userName}
    h = _f(hours, -1.0)
    if h <= 0 or h > _MAX_LABOUR_HOURS:
        return {'ok': False, 'code': 'BAD_HOURS', 'message': 'hours must be between 0 and %d' % int(_MAX_LABOUR_HOURS)}
    d = parseIso(resDateIso) if _s(resDateIso) else parseIso(wo.get('start'))
    if d is None:
        return {'ok': False, 'code': 'BAD_DATE', 'message': 'planned date must be yyyy-MM-dd'}
    return {'ok': True, 'code': 'OK', 'message': '', 'hours': round(h, 2), 'resDate': d}
