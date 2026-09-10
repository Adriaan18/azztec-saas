# =============================================================================
# workmate_planner_code_v1_3_1.py
# Version:     1.3.1
# Target:      Project Library  workmate/planner
# Database:    TLSQL01_Workmate
# Author:      Adriaan
# Spec:        Workmate_P-PLN1_PlannerCalendar_Spec_v1_1_0.md  (slices S1-S4)
#
# Purpose:
#   Data + rules for the Planner Calendar. Everything the planner UI shows
#   is assembled HERE (D-8): the WebDev layer (workmate.planner_api) only
#   routes and serialises, the HTML only renders. Rules are PURE functions
#   over plain dicts so Test_workmate_planner runs them without a database:
#     category()        DONE > PM > REQ > WO           (HomeCalendar F1)
#     engineOwned()     PM WO the engine will re-date  (spec F3 / D-3)
#     hoursFor()        labour rows > Duration_In_Hours > 0 '?'   (D-5)
#     assignedFor()     labour users + User_ID_Responsibility     (D-5)
#     capacityByWeek()  planned / capacity per Mon-Sun week       (D-5)
#     workerLoad()      hours attributed per worker               (D-5)
#     classifyTeams()   internal teams vs contractors (modal supplier +
#                       Supplier.Internal_Dept - never a hard-coded 11)
#
# Facts this module relies on (probed on live 2026-09-04, spec s.2b):
#   - WO_N_Header.Request_Start_Date carries a time of day on ~half the rows;
#     the planner keys days on the DATE part only.
#   - Priority.Colour is #FF8000 on every row -> priority is a LETTER badge.
#   - Active domains: Users.Active 'Y'/'N', User_Skill.Active '1'/'0' - both
#     '0' and 'N' are excluded (KJ 5.0a).
#   - Assignable worker = active user with >= 1 active User_Skill row.
#
# WRITE SIDE (S2, D-2/D-4) - one transaction on TLSQL01_Workmate, DRY_RUN True
# by default; the API passes dryRun=False explicitly:
#     moveRules()   PURE. refuse: C/D, engine-owned PM (until S3), no change,
#                   bad date.  confirm: past target, status V, multi-day span,
#                   labour on more than one day.
#     moveWO()      header start/end shifted by the day delta (time of day
#                   kept, NULL end stays NULL), Week_No = pm_engine.weekNo,
#                   WO_N_Subtasks rows shifted per row, WO_N_Resource.Res_Date
#                   shifted, WO_Event_History 'Rescheduled' + per-field
#                   'Update' rows in the .NET clsSimpleComparer format,
#                   Source_Form 'Planner'. expectStartIso = optimistic lock.
#     undoMove()    moveWO back to the previous start, confirm implied.
#     setEstimate() WO_N_Details.Duration_In_Hours + audit row.
#   Every write returns a dict; nothing raises past the API boundary.
#
# PLANNER PIN (S3, D-3) - dbo.WO_N_Plan + pm_engine 2.5.0:
#   A PM work order the engine still owns (status not V/C/D) can be moved
#   once the pin table exists: the move UPSERTS WO_N_Plan (Pinned='Y',
#   Prev_Start = the engine's date before the first move) in the same
#   transaction and the engine treats the WO as FROZEN from its next run.
#   Moving it BACK onto Prev_Start clears the pin automatically (the engine
#   then SKIPs - same day). unpin() hands the date back explicitly; the
#   engine re-dates it home on its next run (<= 2 h). Without the table
#   (S3 DDL not run) engine-owned PMs stay locked exactly as in 1.1.0.
#
# LABOUR ALLOCATION (S4, legacy LRP parity):
#   addLabour()     one WO_N_Resource 'L' row: person, skill, hours, Res_Date
#                   (= the legacy 'User Planned Date', defaults to the WO
#                   start), Supplier_Id from the person's skill row, UOM =
#                   the LRStd unit (Unit_of_Measure.LRStd, resolved at
#                   runtime - never a hard-coded 9), Res_Id = MAX+1 in-tx as
#                   wo_resource does, status law via wo_resource.assertEditable,
#                   WO_Event_History 'Labour planned'.
#   removeLabour()  delete by Res_Id + WO_Id, returns the row for undo.
#   setCapacity()   User_Skill.Hrs_Per_Week on ONE skill row (Sys_User_Skill_Id),
#                   0..168 h - the greaser's 20 h/week lives here.
#   workerWeeks()   PURE. per worker per Mon-Sun week: planned (labour rows by
#                   Res_Date, else estimates by WO start to the responsible
#                   user) vs capacity -> flag over / ok / under / empty.
#
# Changelog:
#   v1.3.1  DST FIX. system.date.daysBetween proved asymmetric across the NZ
#           daylight-saving change (27 Sep 2026): 17 Sep -> 29 Sep gave 12,
#           29 Sep -> 17 Sep gave -11, so an undo landed a day short (caught
#           by the [F] trail: 'undo ... 2026-09-29 -> 2026-09-18 (-11 d)').
#           Every day delta now comes from civilDays() - calendar-date
#           arithmetic (datetime.date), no instants, no zones. addDays()
#           (wall-clock, DST-safe) is kept for shifting datetimes.
#   v1.3.0  S4: addLabour / removeLabour / setCapacity / workerWeeks; labour
#           rows carry resId/note/rate/skillTitle/uomId; worker skills carry
#           sysId; rangeData carries workerWeeks + uomHours.
#   v1.2.0  S3: pin-aware reads (pinned / engineOwned / pinTable), PM moves
#           pin, return-home unpins, unpin(); rangeData carries pinTable.
#   v1.1.0  S2 write side: moveRules / movePreview / moveWO / undoMove /
#           setEstimate; rangeData rows gain 'movable'.
#   v1.0.0  Initial (S1 read side).
# =============================================================================

_VERSION = '1.3.1'
DRY_RUN = True                 # module default for every write; the API passes dryRun=False
_LOCKED_STATUSES = ('C', 'D')  # never movable
_CONFIRM_STATUSES = ('V',)     # movable after a confirm (work in progress)
_EVENT_DETAILS_MAX = 990       # WO_Event_History.event_details is varchar(1000)
_MAX_ESTIMATE = 1000.0
_MAX_LABOUR_HOURS = 500.0
_MAX_HRS_PER_WEEK = 168.0
_hoursUom = None               # resolved once per JVM (LRStd unit)
_DB = 'TLSQL01_Workmate'
_SOURCE = 'workmate.planner'

# spec F3: statuses the PM engine never re-dates
_ENGINE_FROZEN = ('V', 'C', 'D')
# HomeCalendar F1 colours - shipped so the UI and the Home page agree
COLOURS = {'DONE': '#81C784', 'PM': '#4DD0E1', 'REQ': '#F48FB1', 'WO': '#FFC65C'}
STATUS_TITLES = {'R': 'Request', 'H': 'Planned', 'P': 'Pending', 'K': 'Acknowledged',
	'A': 'Approved', 'V': 'Active', 'C': 'Closed', 'D': 'Cancelled', 'F': 'Deferred'}


def version():
	return _VERSION


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _s(v):
	return '' if v is None else str(v).strip()


def _i(v, d=0):
	try:
		if v is None or str(v).strip() == '':
			return d
		return int(float(str(v).strip()))
	except:
		return d


def _f(v, d=0.0):
	try:
		if v is None or str(v).strip() == '':
			return d
		return float(str(v).strip())
	except:
		return d


def _err():
	import sys
	e = sys.exc_info()[1]
	parts = [str(e)]
	c = getattr(e, 'cause', None)
	n = 0
	while c is not None and n < 4:
		parts.append('CAUSED BY: ' + str(c))
		c = getattr(c, 'cause', None)
		n += 1
	return ' | '.join(parts)


def _log(message, level='info'):
	try:
		workmate.diag.log(_SOURCE, message, level)
	except:
		pass


def _query(sql, params=None):
	return system.db.runPrepQuery(sql, params or [], _DB)


def _rows(ds, cols):
	out = []
	for i in range(ds.getRowCount()):
		r = {}
		for c in cols:
			r[c] = ds.getValueAt(i, c)
		out.append(r)
	return out


def parseIso(s):
	"""'yyyy-MM-dd' -> java Date at midnight, or None."""
	s = _s(s)
	if len(s) < 10:
		return None
	try:
		return system.date.midnight(system.date.parse(s[:10], 'yyyy-MM-dd'))
	except:
		return None


def iso(d):
	return '' if d is None else system.date.format(d, 'yyyy-MM-dd')


def timeOf(d):
	"""'HH:mm' when the datetime carries a time of day, else ''."""
	if d is None:
		return ''
	t = system.date.format(d, 'HH:mm')
	return '' if t == '00:00' else t


def _civil(isoDay):
	"""yyyy-MM-dd -> datetime.date, or None."""
	import datetime
	t = _s(isoDay)[:10]
	try:
		return datetime.date(int(t[0:4]), int(t[5:7]), int(t[8:10]))
	except:
		return None


def civilDays(isoFrom, isoTo):
	"""Whole calendar days from isoFrom to isoTo (yyyy-MM-dd), negative when
	isoTo is earlier. Pure calendar arithmetic - immune to DST (1.3.1)."""
	a = _civil(isoFrom)
	b = _civil(isoTo)
	if a is None or b is None:
		return None
	return int((b - a).days)


def weekStart(d):
	"""Monday on or before d (midnight)."""
	m = system.date.midnight(d)
	dow = system.date.getDayOfWeek(m)      # 1 = Sunday .. 7 = Saturday
	back = (dow - 2) % 7
	return system.date.addDays(m, -back)


def configValue(key, default=''):
	"""System_Configuration value for key, or default (char column - padded)."""
	try:
		ds = _query("SELECT RTRIM(ISNULL(System_ConfigVal, '')) AS V FROM dbo.System_Configuration "
			"WHERE RTRIM(System_ConfigCol) = ?", [key])
		if ds.getRowCount():
			v = _s(ds.getValueAt(0, 'V'))
			if v != '':
				return v
	except:
		_log('configValue(%s) failed: %s' % (key, _err()), 'warn')
	return default


def pinTableExists():
	"""dbo.WO_N_Plan present? Delegates to pm_engine 2.5.0 (True cached
	there); False on an engine without the S3 change."""
	try:
		return bool(workmate.pm_engine.pinTableExists())
	except:
		return False


def _pinSelect(alias='h'):
	"""Pinned / Prev_Start / Pinned_On columns for a SELECT on WO_N_Header
	<alias>, valid whether or not the pin table exists."""
	if pinTableExists():
		return ("ISNULL((SELECT TOP 1 CASE WHEN RTRIM(ISNULL(x.Pinned, 'N')) = 'Y' THEN 1 ELSE 0 END "
			"FROM dbo.WO_N_Plan x WHERE x.WO_ID = %s.WO_ID), 0) AS Pinned, "
			"(SELECT TOP 1 x.Prev_Start FROM dbo.WO_N_Plan x WHERE x.WO_ID = %s.WO_ID) AS Prev_Start, "
			"(SELECT TOP 1 x.Pinned_On FROM dbo.WO_N_Plan x WHERE x.WO_ID = %s.WO_ID) AS Pinned_On " % (alias, alias, alias))
	return "0 AS Pinned, NULL AS Prev_Start, NULL AS Pinned_On "


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
	(spec F3): a PM whose status is not in the engine's frozen set."""
	if _s(typeFlag).upper() != 'M':
		return False
	return _s(status).upper() not in _ENGINE_FROZEN


def hoursFor(wo, labourRows):
	"""(hours, source). Source 'labour' when WO_N_Resource 'L' rows carry
	hours, else 'estimate' from Duration_In_Hours, else ('', 0) = unknown."""
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
	internalDept. Returns {supplierId: {'id','short','name','internal'}}.
	Internal = the modal supplier among active skill rows (KJ 5.0a rule)
	OR Supplier.Internal_Dept in ('1','Y'). Never a hard-coded id."""
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
	summed weekly capacity and the team of the first skill row."""
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
	"""{userId: hours}. Labour rows attribute their own hours; a WO without
	labour rows attributes its estimate to the responsible user; anything
	else lands in key 0 (unassigned)."""
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
	  hours), capacity (sum Hrs_Per_Week of the capacity workers), pct.
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
	while not system.date.isAfter(ws, end):
		k = iso(ws)
		index[k] = len(weeks)
		weeks.append({'weekStart': k, 'planned': 0.0, 'unknown': 0, 'count': 0,
			'capacity': cap, 'pct': 0})
		ws = system.date.addDays(ws, 7)
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


def _weekKeyOf(isoDay):
	d = parseIso(isoDay)
	return '' if d is None else iso(weekStart(d))


def workerWeeks(wos, labourRows, workers, fromIso, toIso):
	"""PURE (S4). {str(userId): [{weekStart, planned, capacity, pct, flag}]}
	for every worker with capacity > 0 or any planned hours in the window.
	Attribution: a labour row lands in the week of its Res_Date (else its
	WO's start); a WO with no labour rows lands its estimate on the
	responsible user by start week. flag: over (>100%), ok (80-100),
	under (1-79, capacity > 0), empty (0)."""
	start = parseIso(fromIso)
	end = parseIso(toIso)
	if start is None or end is None:
		return {}
	weekKeys = []
	ws = weekStart(start)
	while not system.date.isAfter(ws, end):
		weekKeys.append(iso(ws))
		ws = system.date.addDays(ws, 7)
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


def hoursUomId():
	"""The labour-hours unit: Unit_of_Measure.LRStd (legacy 'LR standard'),
	else the modal UOM on existing labour rows, else 0 (NULL). Cached."""
	global _hoursUom
	if _hoursUom:
		return _hoursUom
	try:
		ds = _query("SELECT TOP 1 UOM_Id FROM dbo.Unit_of_Measure "
			"WHERE RTRIM(ISNULL(LRStd, '')) IN ('1', 'Y') AND RTRIM(ISNULL(Active, '')) NOT IN ('0', 'N') ORDER BY UOM_Id")
		if ds.getRowCount():
			_hoursUom = _i(ds.getValueAt(0, 'UOM_Id'))
	except:
		pass
	if not _hoursUom:
		try:
			ds = _query("SELECT TOP 1 UOM_Id FROM dbo.WO_N_Resource WHERE RTRIM(ISNULL(Resource_Type, '')) = 'L' "
				"AND UOM_Id IS NOT NULL GROUP BY UOM_Id ORDER BY COUNT(*) DESC")
			if ds.getRowCount():
				_hoursUom = _i(ds.getValueAt(0, 'UOM_Id'))
		except:
			pass
	return _hoursUom or 0


# ---------------------------------------------------------------------------
# data fetch (prepared SQL - the pm_engine_db convention, no NQs)
# ---------------------------------------------------------------------------

def _woSql():
	return (
	"SELECT h.WO_ID, RTRIM(ISNULL(h.Short_WO_Id, '')) AS Short_WO_Id, "
	"RTRIM(ISNULL(h.WO_Title, '')) AS WO_Title, RTRIM(ISNULL(h.Status, '')) AS Status, "
	"RTRIM(ISNULL(h.WO_Type_Flag, 'N')) AS WO_Type_Flag, h.Request_Start_Date, "
	"h.Request_End_Date, ISNULL(h.Week_No, 0) AS Week_No, "
	"ISNULL(d.Progress_Id, 0) AS Progress_Id, ISNULL(d.Priority_Id, 0) AS Priority_Id, "
	"ISNULL(d.Duration_In_Hours, 0) AS Duration_In_Hours, "
	"ISNULL(d.User_ID_Responsibility, 0) AS Resp_User_Id, "
	"RTRIM(ISNULL(a.Short_asset_Id, '')) AS AssetId, RTRIM(ISNULL(a.Asset_Title, '')) AS AssetTitle, "
	"RTRIM(ISNULL(l.Short_Location_ID, '')) AS LocationId, "
	"RTRIM(ISNULL(l.Location_Title, '')) AS LocationTitle, "
	"RTRIM(ISNULL(p.Short_Priority_Id, '')) AS PriorityShort, "
	"CASE WHEN RTRIM(ISNULL(h.Purchase_Order_Flag, '')) = '1' "
	"  OR EXISTS (SELECT 1 FROM dbo.PO_Header ph WHERE ph.WO_Id = h.WO_ID) "
	"  OR EXISTS (SELECT 1 FROM dbo.PO_Details pd WHERE pd.WO_Id = h.WO_ID) "
	"  THEN 1 ELSE 0 END AS HasPO, "
	+ _pinSelect('h') +
	"FROM dbo.WO_N_Header h "
	"LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID "
	"LEFT JOIN dbo.Asset a ON a.Asset_ID = h.Asset_ID "
	"LEFT JOIN dbo.Location l ON l.Location_Id = h.Location_Id "
	"LEFT JOIN dbo.Priority p ON p.Priority_Id = d.Priority_Id "
	"WHERE RTRIM(ISNULL(h.Status, '')) <> 'D' "
	"  AND h.Request_Start_Date >= ? AND h.Request_Start_Date < ? "
	"ORDER BY h.Request_Start_Date, h.Short_WO_Id")

_WO_COLS = ['WO_ID', 'Short_WO_Id', 'WO_Title', 'Status', 'WO_Type_Flag',
	'Request_Start_Date', 'Request_End_Date', 'Week_No', 'Progress_Id', 'Priority_Id',
	'Duration_In_Hours', 'Resp_User_Id', 'AssetId', 'AssetTitle', 'LocationId',
	'LocationTitle', 'PriorityShort', 'HasPO', 'Pinned', 'Prev_Start', 'Pinned_On']

_LABOUR_COLS = "r.Res_Id, r.WO_Id, ISNULL(r.User_Id, 0) AS User_Id, ISNULL(r.Planned_Qty, 0) AS Planned_Qty, " \
	"ISNULL(r.Planned_Unit_Cost, 0) AS Rate, RTRIM(ISNULL(r.Resource_Note, '')) AS Note, r.Res_Date, " \
	"ISNULL(r.Skill_Id, 0) AS Skill_Id, RTRIM(ISNULL(k.Skill_Title, '')) AS Skill_Title, ISNULL(r.UOM_Id, 0) AS UOM_Id "
_LABOUR_NAMES = ['Res_Id', 'WO_Id', 'User_Id', 'Planned_Qty', 'Rate', 'Note', 'Res_Date', 'Skill_Id', 'Skill_Title', 'UOM_Id']

_LABOUR_SQL = (
	"SELECT " + _LABOUR_COLS +
	"FROM dbo.WO_N_Resource r JOIN dbo.WO_N_Header h ON h.WO_ID = r.WO_Id "
	"LEFT JOIN dbo.Skill k ON k.Skill_ID = r.Skill_Id "
	"WHERE RTRIM(ISNULL(r.Resource_Type, '')) = 'L' "
	"  AND RTRIM(ISNULL(h.Status, '')) <> 'D' "
	"  AND h.Request_Start_Date >= ? AND h.Request_Start_Date < ? "
	"ORDER BY r.WO_Id, r.Res_Date, r.Res_Id")

_LABOUR_ONE_SQL = (
	"SELECT " + _LABOUR_COLS +
	"FROM dbo.WO_N_Resource r LEFT JOIN dbo.Skill k ON k.Skill_ID = r.Skill_Id "
	"WHERE r.WO_Id = ? AND RTRIM(ISNULL(r.Resource_Type, '')) = 'L' ORDER BY r.Res_Date, r.Res_Id")

_WORKER_SQL = (
	"SELECT u.User_Id, RTRIM(ISNULL(u.Short_User_Id, '')) AS Short_User_Id, "
	"RTRIM(ISNULL(u.User_Name, '')) AS User_Name, ISNULL(s.Skill_ID, 0) AS Skill_ID, "
	"ISNULL(s.Sys_User_Skill_Id, 0) AS Sys_User_Skill_Id, ISNULL(s.UOM_ID, 0) AS UOM_ID, "
	"RTRIM(ISNULL(k.Skill_Title, '')) AS Skill_Title, ISNULL(s.Hrs_Per_Week, 0) AS Hrs_Per_Week, "
	"ISNULL(s.Supplier_ID, 0) AS Supplier_ID, RTRIM(ISNULL(sp.Short_Supplier_Id, '')) AS Supplier_Short, "
	"RTRIM(ISNULL(sp.Company_Name, '')) AS Supplier_Name, RTRIM(ISNULL(sp.Internal_Dept, '')) AS Internal_Dept "
	"FROM dbo.Users u "
	"JOIN dbo.User_Skill s ON s.User_ID = u.User_Id AND RTRIM(ISNULL(s.Active, '')) NOT IN ('0', 'N') "
	"LEFT JOIN dbo.Skill k ON k.Skill_ID = s.Skill_ID "
	"LEFT JOIN dbo.Supplier sp ON sp.Supplier_ID = s.Supplier_ID "
	"WHERE RTRIM(ISNULL(u.Active, '')) = 'Y' "
	"ORDER BY u.User_Name, s.Skill_ID")

_PRIORITY_SQL = (
	"SELECT Priority_Id, RTRIM(ISNULL(Short_Priority_Id, '')) AS Short_Priority_Id, "
	"RTRIM(ISNULL(Priority_Title, '')) AS Priority_Title, ISNULL(Sort_Sequence, 0) AS Sort_Sequence "
	"FROM dbo.Priority WHERE RTRIM(ISNULL(Active, '')) NOT IN ('0', 'N') "
	"ORDER BY Sort_Sequence, Priority_Id")


def fetchWOs(fromD, toD):
	"""WO dicts with start inside [fromD, toD] (toD inclusive - the SQL
	extends it by one day). Cancelled excluded; closed included (D-9 hides
	them by default in the UI)."""
	pinTable = pinTableExists()
	ds = _query(_woSql(), [fromD, system.date.addDays(toD, 1)])
	out = []
	for r in _rows(ds, _WO_COLS):
		st = _s(r['Status'])
		tf = _s(r['WO_Type_Flag']) or 'N'
		sd = r['Request_Start_Date']
		ed = r['Request_End_Date']
		eo = engineOwned(st, tf)
		pinned = _i(r['Pinned']) == 1
		locked = eo and not pinned and not pinTable
		days = 0
		if sd is not None and ed is not None:
			days = civilDays(iso(sd), iso(ed)) or 0
		out.append({
			'id': _i(r['WO_ID']), 'sid': _s(r['Short_WO_Id']), 'title': _s(r['WO_Title']),
			'status': st, 'statusTitle': STATUS_TITLES.get(st, st), 'type': tf,
			'cat': category(st, tf), 'start': iso(sd), 'startTime': timeOf(sd),
			'end': iso(ed) if ed is not None else '', 'days': days,
			'weekNo': _f(r['Week_No']), 'prog': _i(r['Progress_Id']),
			'priId': _i(r['Priority_Id']), 'pri': _s(r['PriorityShort']),
			'estimate': _f(r['Duration_In_Hours']), 'resp': _i(r['Resp_User_Id']),
			'asset': _s(r['AssetId']), 'assetTitle': _s(r['AssetTitle']),
			'loc': _s(r['LocationId']), 'locTitle': _s(r['LocationTitle']),
			'hasPO': _i(r['HasPO']) == 1, 'engineOwned': eo, 'pinned': pinned,
			'pinnedOn': iso(r['Pinned_On']) if r['Pinned_On'] is not None else '',
			'engineDate': iso(r['Prev_Start']) if r['Prev_Start'] is not None else '',
			'locked': locked, 'movable': (not locked) and st not in _LOCKED_STATUSES,
			'hrs': 0.0, 'hrsSrc': '', 'assigned': []})
	return out


def _labourDict(r):
	return {'resId': _i(r['Res_Id']), 'woId': _i(r['WO_Id']), 'userId': _i(r['User_Id']),
		'hours': _f(r['Planned_Qty']), 'rate': _f(r['Rate']), 'note': _s(r['Note']),
		'date': iso(r['Res_Date']) if r['Res_Date'] is not None else '',
		'skillId': _i(r['Skill_Id']), 'skillTitle': _s(r['Skill_Title']), 'uomId': _i(r['UOM_Id'])}


def fetchLabour(fromD, toD):
	ds = _query(_LABOUR_SQL, [fromD, system.date.addDays(toD, 1)])
	return [_labourDict(r) for r in _rows(ds, _LABOUR_NAMES)]


def labourRows(woId, tx=None):
	ds = _queryTx(_LABOUR_ONE_SQL, [int(woId)], tx)
	return [_labourDict(r) for r in _rows(ds, _LABOUR_NAMES)]


def fetchSkillRows():
	ds = _query(_WORKER_SQL)
	out = []
	for r in _rows(ds, ['User_Id', 'Short_User_Id', 'User_Name', 'Skill_ID', 'Sys_User_Skill_Id', 'UOM_ID', 'Skill_Title',
			'Hrs_Per_Week', 'Supplier_ID', 'Supplier_Short', 'Supplier_Name', 'Internal_Dept']):
		out.append({'userId': _i(r['User_Id']), 'shortId': _s(r['Short_User_Id']),
			'name': _s(r['User_Name']), 'skillId': _i(r['Skill_ID']), 'sysId': _i(r['Sys_User_Skill_Id']),
			'uomId': _i(r['UOM_ID']),
			'skillTitle': _s(r['Skill_Title']), 'hrsPerWeek': _f(r['Hrs_Per_Week']),
			'supplierId': _i(r['Supplier_ID']), 'supplierShort': _s(r['Supplier_Short']),
			'supplierName': _s(r['Supplier_Name']), 'internalDept': _s(r['Internal_Dept'])})
	return out


def fetchPriorities():
	ds = _query(_PRIORITY_SQL)
	return [{'id': _i(r['Priority_Id']), 'short': _s(r['Short_Priority_Id']),
		'title': _s(r['Priority_Title'])} for r in
		_rows(ds, ['Priority_Id', 'Short_Priority_Id', 'Priority_Title', 'Sort_Sequence'])]


def workers():
	"""(workers, teams) from the live tables."""
	return buildWorkers(fetchSkillRows())


def rangeData(fromIso, toIso):
	"""Everything one planner window needs, as plain JSON-safe dicts.
	Raises on a bad window; the API turns that into a 400."""
	fromD = parseIso(fromIso)
	toD = parseIso(toIso)
	if fromD is None or toD is None or system.date.isAfter(fromD, toD):
		raise Exception('bad window %r..%r (expected yyyy-MM-dd, from <= to)' % (fromIso, toIso))
	if (civilDays(iso(fromD), iso(toD)) or 0) > 400:
		raise Exception('window too wide (max 400 days)')
	wos = fetchWOs(fromD, toD)
	labour = fetchLabour(fromD, toD)
	wlist, teams = workers()
	for wo in wos:
		h, src = hoursFor(wo, labour)
		wo['hrs'] = h
		wo['hrsSrc'] = src
		wo['assigned'] = assignedFor(wo, labour)
	openWO = len([w for w in wos if w['cat'] == 'WO' or w['cat'] == 'REQ'])
	openPM = len([w for w in wos if w['cat'] == 'PM'])
	done = len([w for w in wos if w['cat'] == 'DONE'])
	data = {
		'from': iso(fromD), 'to': iso(toD), 'today': iso(system.date.now()),
		'wos': wos, 'labour': labour, 'workers': wlist, 'teams': teams,
		'priorities': fetchPriorities(), 'colours': COLOURS,
		'weeks': capacityByWeek(wos, wlist, iso(fromD), iso(toD)),
		'load': dict([(str(k), v) for k, v in workerLoad(wos, labour).items()]),
		'counts': {'wo': openWO, 'pm': openPM, 'done': done, 'total': len(wos)},
		'pinTable': pinTableExists(),
		'workerWeeks': workerWeeks(wos, labour, wlist, iso(fromD), iso(toD)),
		'uomHours': hoursUomId(),
		'libVersion': _VERSION,
	}
	_log('rangeData %s..%s rows=%d labour=%d workers=%d' % (
		data['from'], data['to'], len(wos), len(labour), len(wlist)))
	return data


# ---------------------------------------------------------------------------
# WRITE SIDE (S2) - helpers
# ---------------------------------------------------------------------------

def _upd(sql, params, tx):
	return system.db.runPrepUpdate(sql, params or [], tx=tx)


def _queryTx(sql, params, tx):
	if tx is None:
		return system.db.runPrepQuery(sql, params or [], _DB)
	return system.db.runPrepQuery(sql, params or [], _DB, tx)


def _weekNoFor(d):
	"""Week_No exactly as .NET stores it (2026.36) via the tested port."""
	w = workmate.pm_engine.weekNo(d)
	if w is None:
		raise Exception('pm_engine.weekNo returned None for %s' % d)
	return w


def _shiftDays(d, delta):
	return None if d is None else system.date.addDays(d, int(delta))


def _fmtDate(d):
	return '' if d is None else system.date.format(d, 'yyyy-MM-dd')


def _fmtDelta(delta):
	delta = int(delta)
	return ('%+d day' % delta) if abs(delta) == 1 else ('%+d days' % delta)


def _eventRow(tx, woId, userId, eventName, details, sourceForm='Planner'):
	det = '' if details is None else str(details)
	if len(det) > _EVENT_DETAILS_MAX:
		det = det[:_EVENT_DETAILS_MAX - 3] + '...'
	return _upd(
		"INSERT INTO dbo.WO_Event_History "
		"(WO_ID, User_Id_Edited_By, Edited_Date, Event_Name, event_details, server_name, Source_Form) "
		"VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)",
		[int(woId), int(userId), str(eventName), det, 'Perspective', sourceForm], tx)


def _fieldDiffDetail(col, oldV, newV):
	"""'{Col} changed from {old} to {new}' - the .NET clsSimpleComparer shape
	WOMaint already writes, so the planner's rows read the same in history."""
	return '{%s} changed from {%s} to {%s}' % (col, oldV, newV)


def _loadSql():
	return (
	"SELECT h.WO_ID, RTRIM(ISNULL(h.Short_WO_Id, '')) AS Short_WO_Id, "
	"RTRIM(ISNULL(h.WO_Title, '')) AS WO_Title, RTRIM(ISNULL(h.Status, '')) AS Status, "
	"RTRIM(ISNULL(h.WO_Type_Flag, 'N')) AS WO_Type_Flag, h.Request_Start_Date, "
	"h.Request_End_Date, ISNULL(h.Week_No, 0) AS Week_No, "
	"ISNULL(d.Duration_In_Hours, 0) AS Duration_In_Hours, "
	"CASE WHEN d.WO_ID IS NULL THEN 0 ELSE 1 END AS HasDetails, "
	+ _pinSelect('h') +
	"FROM dbo.WO_N_Header h LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID "
	"WHERE h.WO_ID = ?")

_SUBTASK_SQL = ("SELECT Req_Start_Date FROM dbo.WO_N_Subtasks WHERE WO_ID = ? "
	"AND Req_Start_Date IS NOT NULL ORDER BY Req_Start_Date")

_LABOUR_DATES_SQL = ("SELECT Res_Date, COUNT(*) AS Cnt FROM dbo.WO_N_Resource "
	"WHERE WO_Id = ? AND RTRIM(ISNULL(Resource_Type, '')) = 'L' AND Res_Date IS NOT NULL "
	"GROUP BY Res_Date ORDER BY Res_Date")


def loadWO(woId, tx=None):
	"""Header + the dates a move must carry. None when the WO does not exist."""
	pinTable = pinTableExists()
	ds = _queryTx(_loadSql(), [int(woId)], tx)
	if ds.getRowCount() == 0:
		return None
	r = _rows(ds, ['WO_ID', 'Short_WO_Id', 'WO_Title', 'Status', 'WO_Type_Flag',
		'Request_Start_Date', 'Request_End_Date', 'Week_No', 'Duration_In_Hours', 'HasDetails',
		'Pinned', 'Prev_Start', 'Pinned_On'])[0]
	st = _s(r['Status'])
	tf = _s(r['WO_Type_Flag']) or 'N'
	subs = [x['Req_Start_Date'] for x in _rows(_queryTx(_SUBTASK_SQL, [int(woId)], tx), ['Req_Start_Date'])]
	labour = [(x['Res_Date'], _i(x['Cnt'])) for x in
		_rows(_queryTx(_LABOUR_DATES_SQL, [int(woId)], tx), ['Res_Date', 'Cnt'])]
	return {
		'id': _i(r['WO_ID']), 'sid': _s(r['Short_WO_Id']), 'title': _s(r['WO_Title']),
		'status': st, 'type': tf, 'cat': category(st, tf),
		'startDate': r['Request_Start_Date'], 'endDate': r['Request_End_Date'],
		'start': iso(r['Request_Start_Date']) if r['Request_Start_Date'] is not None else '',
		'end': iso(r['Request_End_Date']) if r['Request_End_Date'] is not None else '',
		'weekNo': _f(r['Week_No']), 'estimate': _f(r['Duration_In_Hours']),
		'hasDetails': _i(r['HasDetails']) == 1,
		'engineOwned': engineOwned(st, tf), 'pinned': _i(r['Pinned']) == 1,
		'pinTable': pinTable, 'hasPinRow': r['Prev_Start'] is not None or r['Pinned_On'] is not None,
		'engineDate': iso(r['Prev_Start']) if r['Prev_Start'] is not None else '',
		'engineDateValue': r['Prev_Start'],
		'locked': engineOwned(st, tf) and _i(r['Pinned']) != 1 and not pinTable,
		'subtaskDates': [iso(x) for x in subs],
		'labourDates': [(iso(d), n) for d, n in labour],
	}


# ---------------------------------------------------------------------------
# WRITE SIDE (S2) - PURE rules
# ---------------------------------------------------------------------------

def moveRules(wo, toIso, todayIso):
	"""PURE (spec D-2/D-4). wo needs status/type/start/end/pinned/subtaskDates/
	labourDates as loadWO builds them. Returns
	  {ok, code, message, confirm, reasons[], delta, newStart, newEnd}
	ok=False  -> refuse (code LOCKED_STATUS | ENGINE_OWNED | NO_START | BAD_DATE | NO_CHANGE)
	confirm   -> True when the move needs a planner confirm (reasons say why)."""
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
		newEnd = iso(system.date.addDays(parseIso(wo.get('end')), delta))
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


# ---------------------------------------------------------------------------
# WRITE SIDE (S2) - service functions
# ---------------------------------------------------------------------------

def movePreview(woId, toIso, tx=None):
	"""What a move would do - rules + old/new for the confirm modal."""
	wo = loadWO(woId, tx)
	if wo is None:
		return {'ok': False, 'code': 'NOT_FOUND', 'message': 'WO %s not found' % woId}
	rules = moveRules(wo, toIso, iso(system.date.now()))
	out = dict(rules)
	out.update({'woId': wo['id'], 'sid': wo['sid'], 'title': wo['title'], 'status': wo['status'],
		'statusTitle': STATUS_TITLES.get(wo['status'], wo['status']),
		'prevStart': wo['start'], 'prevEnd': wo['end'],
		'subtasks': len(wo['subtaskDates']), 'labourDates': wo['labourDates']})
	if rules['ok']:
		out['labourMoves'] = [{'from': d, 'to': iso(system.date.addDays(parseIso(d), rules['delta'])), 'rows': n}
			for d, n in wo['labourDates']]
	return out


def moveWO(woId, toIso, userId, expectStartIso=None, confirm=False, dryRun=DRY_RUN,
		eventName='Rescheduled', _tx=None):
	"""Move a work order to toIso (yyyy-MM-dd). Returns a dict, never raises.
	  dryRun=True (default)   plan only, nothing written
	  expectStartIso          optimistic lock: refuse with STALE when the WO
	                          no longer starts on that date
	  confirm=False           when the rules say confirm, return CONFIRM +
	                          preview instead of writing
	  _tx                     caller-owned transaction (tests): no commit,
	                          no close - the caller rolls it back."""
	try:
		woId = int(woId)
	except:
		return {'ok': False, 'code': 'BAD_REQUEST', 'message': 'woId required'}
	userId = _i(userId)
	tx = _tx
	own = _tx is None
	try:
		wo = loadWO(woId, tx)
		if wo is None:
			return {'ok': False, 'code': 'NOT_FOUND', 'message': 'WO %s not found' % woId}
		if expectStartIso and _s(expectStartIso)[:10] != wo['start']:
			return {'ok': False, 'code': 'STALE', 'sid': wo['sid'], 'currentStart': wo['start'],
				'message': '%s moved since you loaded the planner (now %s) - refreshing' % (wo['sid'], wo['start'])}
		rules = moveRules(wo, toIso, iso(system.date.now()))
		if not rules['ok']:
			return {'ok': False, 'code': rules['code'], 'sid': wo['sid'], 'message': rules['message']}
		if rules['confirm'] and not confirm:
			pv = movePreview(woId, toIso, tx)
			return {'ok': False, 'code': 'CONFIRM', 'sid': wo['sid'], 'message': 'confirm required',
				'preview': pv}
		if userId <= 0:
			return {'ok': False, 'code': 'NO_IDENTITY', 'sid': wo['sid'],
				'message': 'your login has no Workmate identity - see User Mapping'}
		delta = rules['delta']
		newStart = _shiftDays(wo['startDate'], delta)
		newEnd = _shiftDays(wo['endDate'], delta)
		weekNo = _weekNoFor(newStart)
		plan = {'ok': True, 'dryRun': bool(dryRun), 'woId': woId, 'sid': wo['sid'],
			'prevStart': wo['start'], 'prevEnd': wo['end'], 'newStart': iso(newStart),
			'newEnd': iso(newEnd) if newEnd is not None else '', 'delta': delta,
			'weekNo': weekNo, 'prevWeekNo': wo['weekNo'],
			'subtasks': len(wo['subtaskDates']), 'labourRows': sum([n for d, n in wo['labourDates']]),
			'reasons': rules['reasons'], 'events': 0,
			'willPin': rules['willPin'], 'willUnpin': rules['willUnpin'], 'pinned': rules['pinnedAfter'],
			'engineDate': wo['engineDate'] or (wo['start'] if rules['willPin'] else ''),
			'undo': {'woId': woId, 'toIso': wo['start'], 'expectStartIso': iso(newStart)}}
		if dryRun:
			_log('DRY RUN moveWO %s %s -> %s (%s) by %s' % (wo['sid'], wo['start'], plan['newStart'], _fmtDelta(delta), userId))
			return plan
		if own:
			tx = system.db.beginTransaction(_DB)
		try:
			n = _upd("UPDATE dbo.WO_N_Header SET Request_Start_Date = ?, Request_End_Date = ?, Week_No = ? WHERE WO_ID = ?",
				[newStart, newEnd, weekNo, woId], tx)
			if int(n or 0) != 1:
				raise Exception('header update touched %s rows' % n)
			# subtasks: per distinct old date, collision-safe order
			dates = sorted(set(wo['subtaskDates']), reverse=(delta > 0))
			for d in dates:
				old = parseIso(d)
				new = _shiftDays(old, delta)
				_upd("UPDATE dbo.WO_N_Subtasks SET Req_Start_Date = DATEADD(DAY, ?, Req_Start_Date), Week_No = ? "
					"WHERE WO_ID = ? AND Req_Start_Date >= ? AND Req_Start_Date < ?",
					[delta, _weekNoFor(new), woId, old, system.date.addDays(old, 1)], tx)
			# planned labour dates (legacy 'User Planned Date') move with the WO
			nl = _upd("UPDATE dbo.WO_N_Resource SET Res_Date = DATEADD(DAY, ?, Res_Date) "
				"WHERE WO_Id = ? AND RTRIM(ISNULL(Resource_Type, '')) = 'L' AND Res_Date IS NOT NULL",
				[delta, woId], tx)
			# planner pin (S3): first move of an engine-owned PM pins it; a move
			# back onto the engine's date hands it back
			if rules['willPin']:
				_upsertPin(tx, woId, userId, wo['startDate'], 'Planner move %s -> %s' % (wo['start'], plan['newStart']))
			elif rules['willUnpin']:
				_upd("UPDATE dbo.WO_N_Plan SET Pinned = 'N', Last_Save_Date = GETDATE() WHERE WO_ID = ?", [woId], tx)
			# audit: summary + per-field rows in the WOMaint/.NET format
			ev = 0
			ev += _eventRow(tx, woId, userId, eventName, '%s: %s -> %s (%s) via Planner' % (
				wo['sid'], wo['start'], plan['newStart'], _fmtDelta(delta)))
			if rules['willPin']:
				ev += _eventRow(tx, woId, userId, 'Pinned', '%s pinned by the planner - engine re-dating suspended (engine date %s)' % (wo['sid'], wo['start']))
			elif rules['willUnpin']:
				ev += _eventRow(tx, woId, userId, 'Unpinned', '%s back on the engine date %s - pin cleared' % (wo['sid'], plan['newStart']))
			ev += _eventRow(tx, woId, userId, 'Update', _fieldDiffDetail('Request_Start_Date', wo['start'], plan['newStart']))
			if wo['end']:
				ev += _eventRow(tx, woId, userId, 'Update', _fieldDiffDetail('Request_End_Date', wo['end'], plan['newEnd']))
			plan['events'] = int(ev)
			plan['labourRows'] = int(nl or 0)
			if own:
				system.db.commitTransaction(tx)
		except:
			msg = _err()
			if own:
				try:
					system.db.rollbackTransaction(tx)
				except:
					pass
			_log('moveWO %s FAILED (rolled back): %s' % (wo['sid'], msg), 'error')
			return {'ok': False, 'code': 'WRITE_FAILED', 'sid': wo['sid'], 'message': msg}
		finally:
			if own:
				try:
					system.db.closeTransaction(tx)
				except:
					pass
		_log('%s %s: %s -> %s (%s) by user %s, subtasks=%d labour=%d events=%d' % (
			eventName, wo['sid'], wo['start'], plan['newStart'], _fmtDelta(delta), userId,
			plan['subtasks'], plan['labourRows'], plan['events']))
		return plan
	except:
		msg = _err()
		_log('moveWO %s crashed: %s' % (woId, msg), 'error')
		return {'ok': False, 'code': 'INTERNAL', 'message': msg}


def undoMove(woId, toIso, userId, expectStartIso=None, dryRun=DRY_RUN, _tx=None):
	"""Move the WO back to its previous start (the 'undo' dict moveWO
	returned). Confirm is implied - the planner just made the move."""
	return moveWO(woId, toIso, userId, expectStartIso=expectStartIso, confirm=True,
		dryRun=dryRun, eventName='Rescheduled (undo)', _tx=_tx)


def setEstimate(woId, hours, userId, dryRun=DRY_RUN, _tx=None):
	"""WO_N_Details.Duration_In_Hours + one 'Update' audit row."""
	try:
		woId = int(woId)
	except:
		return {'ok': False, 'code': 'BAD_REQUEST', 'message': 'woId required'}
	userId = _i(userId)
	tx = _tx
	own = _tx is None
	try:
		wo = loadWO(woId, tx)
		if wo is None:
			return {'ok': False, 'code': 'NOT_FOUND', 'message': 'WO %s not found' % woId}
		rules = estimateRules(wo, hours)
		if not rules['ok']:
			return {'ok': False, 'code': rules['code'], 'sid': wo['sid'], 'message': rules['message']}
		if userId <= 0:
			return {'ok': False, 'code': 'NO_IDENTITY', 'sid': wo['sid'],
				'message': 'your login has no Workmate identity - see User Mapping'}
		h = rules['hours']
		out = {'ok': True, 'dryRun': bool(dryRun), 'woId': woId, 'sid': wo['sid'],
			'prevHours': wo['estimate'], 'hours': h, 'events': 0}
		if dryRun:
			_log('DRY RUN setEstimate %s %s -> %s by %s' % (wo['sid'], wo['estimate'], h, userId))
			return out
		if own:
			tx = system.db.beginTransaction(_DB)
		try:
			n = _upd("UPDATE dbo.WO_N_Details SET Duration_In_Hours = ? WHERE WO_ID = ?", [h, woId], tx)
			if int(n or 0) < 1:
				raise Exception('details update touched %s rows' % n)
			out['events'] = int(_eventRow(tx, woId, userId, 'Update',
				_fieldDiffDetail('Duration_In_Hours', _fmtHours(wo['estimate']), _fmtHours(h))))
			if own:
				system.db.commitTransaction(tx)
		except:
			msg = _err()
			if own:
				try:
					system.db.rollbackTransaction(tx)
				except:
					pass
			_log('setEstimate %s FAILED (rolled back): %s' % (wo['sid'], msg), 'error')
			return {'ok': False, 'code': 'WRITE_FAILED', 'sid': wo['sid'], 'message': msg}
		finally:
			if own:
				try:
					system.db.closeTransaction(tx)
				except:
					pass
		_log('Estimate %s: %s -> %s h by user %s' % (wo['sid'], wo['estimate'], h, userId))
		return out
	except:
		msg = _err()
		_log('setEstimate %s crashed: %s' % (woId, msg), 'error')
		return {'ok': False, 'code': 'INTERNAL', 'message': msg}


def _upsertPin(tx, woId, userId, engineDate, note):
	"""WO_N_Plan row -> Pinned='Y'. Prev_Start is written on the FIRST pin
	only (the engine's own date) and never overwritten."""
	n = _upd("UPDATE dbo.WO_N_Plan SET Pinned = 'Y', Pinned_By = ?, Pinned_On = GETDATE(), "
		"Prev_Start = ISNULL(Prev_Start, ?), Note = ?, Last_Save_Date = GETDATE() WHERE WO_ID = ?",
		[int(userId), engineDate, note[:255], int(woId)], tx)
	if int(n or 0) == 0:
		n = _upd("INSERT INTO dbo.WO_N_Plan (WO_ID, Pinned, Pinned_By, Pinned_On, Prev_Start, Note, Server_Name) "
			"VALUES (?, 'Y', ?, GETDATE(), ?, ?, 'Perspective')",
			[int(woId), int(userId), engineDate, note[:255]], tx)
	return int(n or 0)


def unpin(woId, userId, dryRun=DRY_RUN, _tx=None):
	"""Hand a pinned work order back to the release engine: Pinned='N' +
	audit row. The engine re-dates it home on its next run (<= 2 h)."""
	try:
		woId = int(woId)
	except:
		return {'ok': False, 'code': 'BAD_REQUEST', 'message': 'woId required'}
	userId = _i(userId)
	tx = _tx
	own = _tx is None
	try:
		wo = loadWO(woId, tx)
		if wo is None:
			return {'ok': False, 'code': 'NOT_FOUND', 'message': 'WO %s not found' % woId}
		if not wo['pinned']:
			return {'ok': False, 'code': 'NOT_PINNED', 'sid': wo['sid'], 'message': '%s is not pinned' % wo['sid']}
		if userId <= 0:
			return {'ok': False, 'code': 'NO_IDENTITY', 'sid': wo['sid'],
				'message': 'your login has no Workmate identity - see User Mapping'}
		out = {'ok': True, 'dryRun': bool(dryRun), 'woId': woId, 'sid': wo['sid'],
			'engineDate': wo['engineDate'], 'start': wo['start'], 'events': 0,
			'message': '%s unpinned - the engine re-dates it on its next run' % wo['sid']}
		if dryRun:
			_log('DRY RUN unpin %s by %s' % (wo['sid'], userId))
			return out
		if own:
			tx = system.db.beginTransaction(_DB)
		try:
			n = _upd("UPDATE dbo.WO_N_Plan SET Pinned = 'N', Last_Save_Date = GETDATE() WHERE WO_ID = ?", [woId], tx)
			if int(n or 0) < 1:
				raise Exception('pin row update touched %s rows' % n)
			out['events'] = int(_eventRow(tx, woId, userId, 'Unpinned',
				'%s unpinned by the planner - engine re-dating resumes (engine date %s)' % (wo['sid'], wo['engineDate'])))
			if own:
				system.db.commitTransaction(tx)
		except:
			msg = _err()
			if own:
				try:
					system.db.rollbackTransaction(tx)
				except:
					pass
			_log('unpin %s FAILED (rolled back): %s' % (wo['sid'], msg), 'error')
			return {'ok': False, 'code': 'WRITE_FAILED', 'sid': wo['sid'], 'message': msg}
		finally:
			if own:
				try:
					system.db.closeTransaction(tx)
				except:
					pass
		_log('Unpinned %s by user %s (engine date %s)' % (wo['sid'], userId, wo['engineDate']))
		return out
	except:
		msg = _err()
		_log('unpin %s crashed: %s' % (woId, msg), 'error')
		return {'ok': False, 'code': 'INTERNAL', 'message': msg}


# ---------------------------------------------------------------------------
# WRITE SIDE (S4) - labour allocation + capacity
# ---------------------------------------------------------------------------

def _skillRowFor(userId, skillId, tx=None):
	"""The person's active User_Skill row for skillId (or the first active
	row when skillId is 0). None when the person has no active skill."""
	sql = ("SELECT TOP 1 s.Sys_User_Skill_Id, ISNULL(s.Skill_ID, 0) AS Skill_ID, ISNULL(s.Supplier_ID, 0) AS Supplier_ID, "
		"ISNULL(s.UOM_ID, 0) AS UOM_ID, ISNULL(s.Rate, 0) AS Rate, ISNULL(s.Hrs_Per_Week, 0) AS Hrs_Per_Week, "
		"RTRIM(ISNULL(k.Skill_Title, '')) AS Skill_Title "
		"FROM dbo.User_Skill s LEFT JOIN dbo.Skill k ON k.Skill_ID = s.Skill_ID "
		"WHERE s.User_ID = ? AND RTRIM(ISNULL(s.Active, '')) NOT IN ('0', 'N') ")
	params = [int(userId)]
	if _i(skillId) > 0:
		sql += "AND s.Skill_ID = ? "
		params.append(_i(skillId))
	sql += "ORDER BY s.Sys_User_Skill_Id"
	ds = _queryTx(sql, params, tx)
	if ds.getRowCount() == 0:
		return None
	r = _rows(ds, ['Sys_User_Skill_Id', 'Skill_ID', 'Supplier_ID', 'UOM_ID', 'Rate', 'Hrs_Per_Week', 'Skill_Title'])[0]
	return {'sysId': _i(r['Sys_User_Skill_Id']), 'skillId': _i(r['Skill_ID']), 'supplierId': _i(r['Supplier_ID']),
		'uomId': _i(r['UOM_ID']), 'rate': _f(r['Rate']), 'hrsPerWeek': _f(r['Hrs_Per_Week']), 'skillTitle': _s(r['Skill_Title'])}


def _userName(userId, tx=None):
	ds = _queryTx("SELECT RTRIM(ISNULL(User_Name, '')) AS N, RTRIM(ISNULL(Active, '')) AS A FROM dbo.Users WHERE User_Id = ?", [int(userId)], tx)
	if ds.getRowCount() == 0:
		return None, ''
	return _s(ds.getValueAt(0, 'N')), _s(ds.getValueAt(0, 'A'))


def labourRules(wo, userName, userActive, skillRow, hours, resDateIso):
	"""PURE-ish (inputs pre-fetched). Refuse codes: LOCKED_STATUS, NO_USER,
	USER_INACTIVE, NO_SKILL, BAD_HOURS, BAD_DATE."""
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


def addLabour(woId, userId, skillId, hours, resDateIso, note, actorId, dryRun=DRY_RUN, _tx=None):
	"""One planned-labour row on a work order. Returns a dict, never raises."""
	try:
		woId = int(woId)
		userId = int(userId)
	except:
		return {'ok': False, 'code': 'BAD_REQUEST', 'message': 'woId and userId required'}
	actorId = _i(actorId)
	tx = _tx
	own = _tx is None
	try:
		wo = loadWO(woId, tx)
		if wo is None:
			return {'ok': False, 'code': 'NOT_FOUND', 'message': 'WO %s not found' % woId}
		uname, uactive = _userName(userId, tx)
		skill = _skillRowFor(userId, skillId, tx) if uname is not None else None
		rules = labourRules(wo, uname, uactive, skill, hours, resDateIso)
		if not rules['ok']:
			return {'ok': False, 'code': rules['code'], 'sid': wo['sid'], 'message': rules['message']}
		if actorId <= 0:
			return {'ok': False, 'code': 'NO_IDENTITY', 'sid': wo['sid'],
				'message': 'your login has no Workmate identity - see User Mapping'}
		note = _s(note)[:100]
		uom = hoursUomId() or skill['uomId'] or 0
		out = {'ok': True, 'dryRun': bool(dryRun), 'woId': woId, 'sid': wo['sid'], 'userId': userId,
			'userName': uname, 'skillId': skill['skillId'], 'skillTitle': skill['skillTitle'],
			'supplierId': skill['supplierId'], 'hours': rules['hours'], 'rate': skill['rate'],
			'resDate': iso(rules['resDate']), 'note': note, 'uomId': uom, 'resId': 0, 'events': 0}
		if dryRun:
			_log('DRY RUN addLabour %s %s %sh on %s by %s' % (wo['sid'], uname, rules['hours'], out['resDate'], actorId))
			return out
		if own:
			tx = system.db.beginTransaction(_DB, system.db.READ_COMMITTED, 10000)
		try:
			workmate.wo_resource.assertEditable(woId, tx)
			resId = _i(system.db.runScalarPrepQuery("SELECT ISNULL(MAX(Res_Id), 0) + 1 FROM dbo.WO_N_Resource", [], tx=tx))
			n = _upd("INSERT INTO dbo.WO_N_Resource (Res_Id, WO_Id, Resource_Type, Part_Id, User_Id, Skill_Id, Supplier_Id, "
				"Planned_Qty, Planned_Unit_Cost, Resource_Note, Res_Date, UOM_Id, Server_Name) "
				"VALUES (?, ?, 'L', NULL, ?, ?, ?, ?, ?, ?, ?, ?, 'Perspective')",
				[resId, woId, userId, skill['skillId'] or None, skill['supplierId'] or None, rules['hours'],
				 skill['rate'], note, rules['resDate'], uom or None], tx)
			if int(n or 0) != 1:
				raise Exception('labour insert touched %s rows' % n)
			out['resId'] = resId
			out['events'] = int(_eventRow(tx, woId, actorId, 'Labour planned', '%s: %s %s h on %s (%s) via Planner' % (
				wo['sid'], uname, _fmtHours(rules['hours']), out['resDate'], skill['skillTitle'] or 'no skill')))
			if own:
				system.db.commitTransaction(tx)
		except:
			msg = _err()
			if own:
				try:
					system.db.rollbackTransaction(tx)
				except:
					pass
			_log('addLabour %s FAILED (rolled back): %s' % (wo['sid'], msg), 'error')
			return {'ok': False, 'code': 'WRITE_FAILED', 'sid': wo['sid'], 'message': msg}
		finally:
			if own:
				try:
					system.db.closeTransaction(tx)
				except:
					pass
		out['undo'] = {'kind': 'labourRemove', 'woId': woId, 'resId': out['resId']}
		_log('Labour planned %s: %s %sh on %s Res_Id %s by user %s' % (wo['sid'], uname, rules['hours'], out['resDate'], out['resId'], actorId))
		return out
	except:
		msg = _err()
		_log('addLabour %s crashed: %s' % (woId, msg), 'error')
		return {'ok': False, 'code': 'INTERNAL', 'message': msg}


def removeLabour(woId, resId, actorId, dryRun=DRY_RUN, _tx=None):
	"""Delete one planned-labour row. Returns the row (for undo = re-add)."""
	try:
		woId = int(woId)
		resId = int(resId)
	except:
		return {'ok': False, 'code': 'BAD_REQUEST', 'message': 'woId and resId required'}
	actorId = _i(actorId)
	tx = _tx
	own = _tx is None
	try:
		wo = loadWO(woId, tx)
		if wo is None:
			return {'ok': False, 'code': 'NOT_FOUND', 'message': 'WO %s not found' % woId}
		if _s(wo['status']).upper() in _LOCKED_STATUSES:
			return {'ok': False, 'code': 'LOCKED_STATUS', 'sid': wo['sid'],
				'message': '%s is %s - planning is locked' % (wo['sid'], STATUS_TITLES.get(wo['status'], wo['status']))}
		rows = [r for r in labourRows(woId, tx) if r['resId'] == resId]
		if not rows:
			return {'ok': False, 'code': 'NOT_FOUND', 'sid': wo['sid'], 'message': 'planned row %s not on %s' % (resId, wo['sid'])}
		row = rows[0]
		if actorId <= 0:
			return {'ok': False, 'code': 'NO_IDENTITY', 'sid': wo['sid'],
				'message': 'your login has no Workmate identity - see User Mapping'}
		uname = _userName(row['userId'], tx)[0] or ('#%s' % row['userId'])
		out = {'ok': True, 'dryRun': bool(dryRun), 'woId': woId, 'sid': wo['sid'], 'resId': resId, 'row': row,
			'userName': uname, 'events': 0,
			'undo': {'kind': 'labourAdd', 'woId': woId, 'userId': row['userId'], 'skillId': row['skillId'],
				'hours': row['hours'], 'resDate': row['date'], 'note': row['note']}}
		if dryRun:
			_log('DRY RUN removeLabour %s Res_Id %s (%s %sh) by %s' % (wo['sid'], resId, uname, row['hours'], actorId))
			return out
		if own:
			tx = system.db.beginTransaction(_DB, system.db.READ_COMMITTED, 10000)
		try:
			workmate.wo_resource.assertEditable(woId, tx)
			n = _upd("DELETE FROM dbo.WO_N_Resource WHERE Res_Id = ? AND WO_Id = ? AND RTRIM(ISNULL(Resource_Type, '')) = 'L'",
				[resId, woId], tx)
			if int(n or 0) != 1:
				raise Exception('labour delete touched %s rows' % n)
			out['events'] = int(_eventRow(tx, woId, actorId, 'Labour removed', '%s: %s %s h on %s removed via Planner' % (
				wo['sid'], uname, _fmtHours(row['hours']), row['date'] or '?')))
			if own:
				system.db.commitTransaction(tx)
		except:
			msg = _err()
			if own:
				try:
					system.db.rollbackTransaction(tx)
				except:
					pass
			_log('removeLabour %s FAILED (rolled back): %s' % (wo['sid'], msg), 'error')
			return {'ok': False, 'code': 'WRITE_FAILED', 'sid': wo['sid'], 'message': msg}
		finally:
			if own:
				try:
					system.db.closeTransaction(tx)
				except:
					pass
		_log('Labour removed %s Res_Id %s (%s %sh) by user %s' % (wo['sid'], resId, uname, row['hours'], actorId))
		return out
	except:
		msg = _err()
		_log('removeLabour %s crashed: %s' % (woId, msg), 'error')
		return {'ok': False, 'code': 'INTERNAL', 'message': msg}


def setCapacity(userId, sysSkillId, hrsPerWeek, actorId, dryRun=DRY_RUN, _tx=None):
	"""User_Skill.Hrs_Per_Week on ONE skill row (Sys_User_Skill_Id), 0..168."""
	try:
		userId = int(userId)
		sysSkillId = int(sysSkillId)
	except:
		return {'ok': False, 'code': 'BAD_REQUEST', 'message': 'userId and sysSkillId required'}
	h = _f(hrsPerWeek, -1.0)
	if h < 0 or h > _MAX_HRS_PER_WEEK:
		return {'ok': False, 'code': 'BAD_HOURS', 'message': 'hours per week must be between 0 and %d' % int(_MAX_HRS_PER_WEEK)}
	actorId = _i(actorId)
	tx = _tx
	own = _tx is None
	try:
		ds = _queryTx("SELECT ISNULL(s.Hrs_Per_Week, 0) AS H, RTRIM(ISNULL(k.Skill_Title, '')) AS T, RTRIM(ISNULL(u.User_Name, '')) AS N "
			"FROM dbo.User_Skill s LEFT JOIN dbo.Skill k ON k.Skill_ID = s.Skill_ID LEFT JOIN dbo.Users u ON u.User_Id = s.User_ID "
			"WHERE s.Sys_User_Skill_Id = ? AND s.User_ID = ?", [sysSkillId, userId], tx)
		if ds.getRowCount() == 0:
			return {'ok': False, 'code': 'NOT_FOUND', 'message': 'skill row %s for user %s not found' % (sysSkillId, userId)}
		prev = _f(ds.getValueAt(0, 'H'))
		title = _s(ds.getValueAt(0, 'T'))
		uname = _s(ds.getValueAt(0, 'N'))
		if actorId <= 0:
			return {'ok': False, 'code': 'NO_IDENTITY', 'message': 'your login has no Workmate identity - see User Mapping'}
		out = {'ok': True, 'dryRun': bool(dryRun), 'userId': userId, 'sysSkillId': sysSkillId, 'userName': uname,
			'skillTitle': title, 'prevHrsPerWeek': prev, 'hrsPerWeek': round(h, 2)}
		if dryRun:
			_log('DRY RUN setCapacity %s (%s) %s -> %s h/wk by %s' % (uname, title, prev, h, actorId))
			return out
		if own:
			tx = system.db.beginTransaction(_DB)
		try:
			n = _upd("UPDATE dbo.User_Skill SET Hrs_Per_Week = ? WHERE Sys_User_Skill_Id = ? AND User_ID = ?", [round(h, 2), sysSkillId, userId], tx)
			if int(n or 0) != 1:
				raise Exception('capacity update touched %s rows' % n)
			if own:
				system.db.commitTransaction(tx)
		except:
			msg = _err()
			if own:
				try:
					system.db.rollbackTransaction(tx)
				except:
					pass
			_log('setCapacity %s FAILED (rolled back): %s' % (uname, msg), 'error')
			return {'ok': False, 'code': 'WRITE_FAILED', 'message': msg}
		finally:
			if own:
				try:
					system.db.closeTransaction(tx)
				except:
					pass
		_log('Capacity %s (%s): %s -> %s h/wk by user %s' % (uname, title, prev, h, actorId))
		return out
	except:
		msg = _err()
		_log('setCapacity %s crashed: %s' % (userId, msg), 'error')
		return {'ok': False, 'code': 'INTERNAL', 'message': msg}


def _fmtHours(h):
	h = _f(h)
	if h == int(h):
		return str(int(h))
	return ('%.2f' % h).rstrip('0').rstrip('.')