# =============================================================================
# workmate_planner_ai_code_v1_1_0.py
# Version:     1.1.0
# Target:      Project Library  workmate/planner_ai
# Database:    TLSQL01_Workmate  (read-only: labour history)
# Author:      Adriaan
# Spec:        Workmate_P-PLN1_PlannerCalendar_Spec_v1_1_0.md  (slice S5)
#              Andrew Willis 2026-09-03 - RST AI-assistant requirements
#
# Purpose:
#   The planning brain behind the "Suggest" button, as PURE functions over
#   the same dicts workmate.planner.rangeData serves. Nothing here writes;
#   every suggestion is applied by the planner through the existing
#   /move and /labour routes (rules, confirm, pin, audit all unchanged).
#   These are also the tool surface the workmate-ai agent calls later - the
#   heuristics are deterministic today, an LLM can rank the same candidates
#   tomorrow.
#
#   Andrew's list -> function:
#     "200 h/week, 180 h of PMs - bring jobs forward"   fillWeek() / planHorizon()
#     "look at past history, allocate resources"        historyStats() / suggestFor()
#     "new job with no history -> prompt an estimate"   planHorizon().needsEstimate
#     "pairs of workers that frequently work together"  pairsWhoWorkTogether()
#     "greaser 20 h/week - flag weeks over / under"     underOverWeeks()
#
#   History = labour activity rows (Trx_Type 'L') from WO_N_Activity and
#   WO_C_Activity joined to their headers, last HISTORY_DAYS days (census:
#   ~510 rows, 1 322 h, 24 people). Keys: PM master prefix (K-KPL-04) and
#   Asset_ID. Medians, not means - one 40 h outlier must not set the number.
#
# NIGHTLY PROPOSAL (1.1.0 - semi-automation without an LLM):
#   nightly(apply=False) runs planHorizon for the next PLANNER_NIGHTLY_WEEKS
#   weeks and saves the proposal as JSON in <PLANNER_UI_DIR>\proposals\
#   (latest.json + a dated copy). The Suggest panel and the chat assistant
#   read latestProposal(). With System_Configuration PLANNER_AUTOPILOT = '1'
#   the safe subset is applied automatically through workmate.planner.moveWO
#   (rules, audit, undo intact) - guardrails: no PMs (nothing pins), priority
#   A or B only, pulled at most PLANNER_AUTOPILOT_MAX_WEEKS weeks, at most
#   PLANNER_AUTOPILOT_MAX_MOVES per night, never into the past. Every applied
#   move is listed in the proposal with its undo; 'Source_Form' stays
#   'Planner' with 'autopilot' in the event text. Schedule it from a gateway
#   timer / Scheduled event: workmate.planner_ai.nightly().
#
# Changelog:
#   v1.1.0  masterPrefix ignores date-coded ids (K-260629-001 is a WO, not a
#           master); nightly() / latestProposal() / applyProposal() with
#           autopilot guardrails; suggest() carries the latest proposal.
#   v1.0.0  Initial (S5).
# =============================================================================

_VERSION = '1.1.0'
_AUTOPILOT_ACTOR = 0     # resolved at run time from System_Configuration PLANNER_AUTOPILOT_USER_ID
_DB = 'TLSQL01_Workmate'
_SOURCE = 'workmate.planner_ai'
HISTORY_DAYS = 730
_PRI_ORDER = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
_UNDER_PCT = 80
_MAX_SUGGEST_PER_WEEK = 12


def version():
	return _VERSION


# ---------------------------------------------------------------------------
# helpers
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


def median(values):
	v = sorted([_f(x) for x in values if x is not None])
	if not v:
		return 0.0
	n = len(v)
	if n % 2:
		return round(v[n // 2], 2)
	return round((v[n // 2 - 1] + v[n // 2]) / 2.0, 2)


def masterPrefix(sid):
	"""PM occurrence id -> its master prefix: 'K-KPL-04-0007' -> 'K-KPL-04',
	'K-KGR-03-0002-S' -> 'K-KGR-03'. '' when the id has no trailing
	occurrence number (a normal WO like 'WO-260902-012' returns '')."""
	s = _s(sid).upper()
	if s.endswith('-S'):
		s = s[:-2]
	parts = s.split('-')
	if len(parts) < 3:
		return ''
	last = parts[-1]
	if not last.isdigit() or len(last) < 3:
		return ''
	base = '-'.join(parts[:-1])
	if base.startswith('WO-'):
		return ''
	for seg in parts[:-1]:
		if seg.isdigit() and len(seg) == 6:      # YYMMDD-coded work orders (K-260629-001)
			return ''
	return base


def civilDays(isoFrom, isoTo):
	return workmate.planner.civilDays(isoFrom, isoTo)


def addDaysIso(isoDay, n):
	d = workmate.planner.parseIso(isoDay)
	if d is None:
		return ''
	return workmate.planner.iso(system.date.addDays(d, int(n)))


def weekStartIso(isoDay):
	d = workmate.planner.parseIso(isoDay)
	if d is None:
		return ''
	return workmate.planner.iso(workmate.planner.weekStart(d))


# ---------------------------------------------------------------------------
# history (one read, then PURE)
# ---------------------------------------------------------------------------

_HIST_SQL = (
	"SELECT 'N' AS Src, a.WO_ID, RTRIM(ISNULL(h.Short_WO_Id, '')) AS Sid, RTRIM(ISNULL(h.WO_Type_Flag, 'N')) AS TypeFlag, "
	"ISNULL(h.Asset_ID, 0) AS AssetId, RTRIM(ISNULL(h.WO_Title, '')) AS Title, ISNULL(a.User_ID, 0) AS UserId, "
	"ISNULL(a.Quantity, 0) AS Qty, a.Activity_Date, ISNULL(a.Skill_Id, 0) AS SkillId "
	"FROM dbo.WO_N_Activity a JOIN dbo.WO_N_Header h ON h.WO_ID = a.WO_ID "
	"WHERE RTRIM(ISNULL(a.Trx_Type, '')) = 'L' AND a.Activity_Date >= ? "
	"UNION ALL "
	"SELECT 'C' AS Src, a.WO_ID, RTRIM(ISNULL(c.Short_WO_Id, '')) AS Sid, RTRIM(ISNULL(c.WO_Type_Flag, 'N')) AS TypeFlag, "
	"ISNULL(c.Asset_ID, 0) AS AssetId, RTRIM(ISNULL(c.WO_Title, '')) AS Title, ISNULL(a.User_ID, 0) AS UserId, "
	"ISNULL(a.Quantity, 0) AS Qty, a.Activity_Date, ISNULL(a.Skill_Id, 0) AS SkillId "
	"FROM dbo.WO_C_Activity a JOIN dbo.WO_C_header c ON c.WO_ID = a.WO_ID "
	"WHERE RTRIM(ISNULL(a.Trx_Type, '')) = 'L' AND a.Activity_Date >= ? "
	"ORDER BY Activity_Date")


def fetchHistory(days=HISTORY_DAYS):
	"""Labour activity rows for the last `days` days, live + archive."""
	since = system.date.addDays(system.date.midnight(system.date.now()), -int(days))
	ds = system.db.runPrepQuery(_HIST_SQL, [since, since], _DB)
	out = []
	for i in range(ds.getRowCount()):
		sid = _s(ds.getValueAt(i, 'Sid'))
		out.append({'src': _s(ds.getValueAt(i, 'Src')), 'woId': _i(ds.getValueAt(i, 'WO_ID')), 'sid': sid,
			'type': _s(ds.getValueAt(i, 'TypeFlag')) or 'N', 'master': masterPrefix(sid),
			'assetId': _i(ds.getValueAt(i, 'AssetId')), 'title': _s(ds.getValueAt(i, 'Title')),
			'userId': _i(ds.getValueAt(i, 'UserId')), 'hours': _f(ds.getValueAt(i, 'Qty')),
			'date': workmate.planner.iso(ds.getValueAt(i, 'Activity_Date')) if ds.getValueAt(i, 'Activity_Date') is not None else '',
			'skillId': _i(ds.getValueAt(i, 'SkillId'))})
	return out


def _statsFromGroups(groups):
	"""groups: {key: {woId: {'hours': h, 'users': set, 'last': iso}}} ->
	{key: {n, medianHours, meanHours, medianCrew, people:[{userId, wos, hours}], last}}"""
	out = {}
	for key, wosMap in groups.items():
		hoursPerWo = []
		crewPerWo = []
		people = {}
		last = ''
		for wid, g in wosMap.items():
			hoursPerWo.append(g['hours'])
			crewPerWo.append(len(g['users']))
			if g['last'] > last:
				last = g['last']
			for uid in g['users']:
				p = people.setdefault(uid, {'userId': uid, 'wos': 0, 'hours': 0.0})
				p['wos'] += 1
				p['hours'] = round(p['hours'] + g['perUser'].get(uid, 0.0), 2)
		n = len(hoursPerWo)
		if n == 0:
			continue
		ranked = sorted(people.values(), key=lambda p: (-p['wos'], -p['hours'], p['userId']))
		out[key] = {'n': n, 'medianHours': median(hoursPerWo),
			'meanHours': round(sum(hoursPerWo) / float(n), 2), 'medianCrew': int(round(median(crewPerWo))) or 1,
			'people': ranked, 'last': last}
	return out


def historyStats(rows):
	"""PURE. rows from fetchHistory() -> {'byMaster', 'byAsset', 'byWo', 'rows'}"""
	byWo = {}
	for r in rows or []:
		wid = _i(r.get('woId'))
		uid = _i(r.get('userId'))
		h = _f(r.get('hours'))
		if wid <= 0 or h <= 0:
			continue
		g = byWo.setdefault(wid, {'hours': 0.0, 'users': set(), 'perUser': {}, 'last': '', 'master': _s(r.get('master')),
			'assetId': _i(r.get('assetId')), 'sid': _s(r.get('sid'))})
		g['hours'] = round(g['hours'] + h, 2)
		if uid > 0:
			g['users'].add(uid)
			g['perUser'][uid] = round(g['perUser'].get(uid, 0.0) + h, 2)
		if _s(r.get('date')) > g['last']:
			g['last'] = _s(r.get('date'))
	byMaster = {}
	byAsset = {}
	for wid, g in byWo.items():
		if g['master']:
			byMaster.setdefault(g['master'], {})[wid] = g
		if g['assetId'] > 0:
			byAsset.setdefault(g['assetId'], {})[wid] = g
	return {'byMaster': _statsFromGroups(byMaster), 'byAsset': _statsFromGroups(byAsset),
		'wos': len(byWo), 'rows': len(rows or [])}


def suggestFor(wo, stats, workers=None, maxPeople=3):
	"""PURE. History-based estimate + crew for one WO dict (sid, asset id in
	'assetId' or 'asset' resolved by the caller). Master history first, then
	the asset's. People are filtered to the active worker list when given."""
	active = {}
	for w in workers or []:
		active[_i(w.get('id'))] = w
	src = None
	st = None
	key = masterPrefix(wo.get('sid'))
	if key and key in (stats.get('byMaster') or {}):
		src = 'master'
		st = stats['byMaster'][key]
	elif _i(wo.get('assetId')) > 0 and _i(wo.get('assetId')) in (stats.get('byAsset') or {}):
		src = 'asset'
		key = _i(wo.get('assetId'))
		st = stats['byAsset'][key]
	if st is None:
		return {'source': None, 'key': '', 'n': 0, 'medianHours': 0.0, 'crew': 0, 'people': [], 'confidence': 'none',
			'text': 'no labour history for this master or asset - ask the planner for an estimate'}
	people = []
	for p in st['people']:
		if workers is not None and p['userId'] not in active:
			continue
		w = active.get(p['userId'], {})
		people.append({'userId': p['userId'], 'name': _s(w.get('name')) or ('#%s' % p['userId']),
			'initials': _s(w.get('initials')), 'wos': p['wos'], 'hours': p['hours'],
			'share': round(float(p['wos']) / st['n'], 2)})
		if len(people) >= maxPeople:
			break
	conf = 'high' if st['n'] >= 3 else 'low'
	names = ', '.join([p['name'] for p in people]) or 'nobody in particular'
	return {'source': src, 'key': str(key), 'n': st['n'], 'medianHours': st['medianHours'], 'meanHours': st['meanHours'],
		'crew': st['medianCrew'], 'people': people, 'last': st['last'], 'confidence': conf,
		'text': '%s: %d job%s, median %s h, usually %d %s - %s' % (
			'master ' + str(key) if src == 'master' else 'asset', st['n'], '' if st['n'] == 1 else 's',
			_fmt(st['medianHours']), st['medianCrew'], 'person' if st['medianCrew'] == 1 else 'people', names)}


def pairsWhoWorkTogether(rows, minCount=2, top=15):
	"""PURE. Pairs of people who logged labour on the same work orders."""
	users = {}
	for r in rows or []:
		wid = _i(r.get('woId'))
		uid = _i(r.get('userId'))
		if wid <= 0 or uid <= 0 or _f(r.get('hours')) <= 0:
			continue
		users.setdefault(wid, set()).add(uid)
	counts = {}
	for wid, s in users.items():
		ids = sorted(s)
		for i in range(len(ids)):
			for j in range(i + 1, len(ids)):
				k = (ids[i], ids[j])
				counts[k] = counts.get(k, 0) + 1
	out = [{'a': k[0], 'b': k[1], 'wos': n} for k, n in counts.items() if n >= minCount]
	out.sort(key=lambda p: (-p['wos'], p['a'], p['b']))
	return out[:top]


# ---------------------------------------------------------------------------
# capacity fill (Andrew's 200 h week)
# ---------------------------------------------------------------------------

def _fmt(h):
	h = _f(h)
	return str(int(h)) if h == int(h) else ('%.1f' % h)


def _priRank(p):
	return _PRI_ORDER.get(_s(p).upper(), 9)


def _weekPlanned(weekStart, wos):
	we = addDaysIso(weekStart, 6)
	planned = 0.0
	unknown = []
	count = 0
	for w in wos:
		st = _s(w.get('start'))
		if st < weekStart or st > we:
			continue
		if _s(w.get('cat')) == 'DONE':
			continue
		count += 1
		if _f(w.get('hrs')) > 0:
			planned += _f(w.get('hrs'))
		else:
			unknown.append(w)
	return round(planned, 2), unknown, count


def fillWeek(weekIso, wos, workers, capacityHours=None, lookAheadWeeks=2, todayIso=None, exclude=None):
	"""PURE. Pull-forward candidates for one Mon-Sun week.
	  capacityHours  the week's labour budget (default: sum Hrs_Per_Week of
	                 internal workers - Andrew's 200 h)
	  candidates     open work starting in the following `lookAheadWeeks`
	                 weeks, with hours, movable, not already pulled (exclude)
	  order          priority A>B>C>D, then earliest start, then largest job
	                 that still fits the spare hours (greedy)
	  target day     same weekday in the target week, never before today
	Returns {weekStart, capacity, planned, spare, count, unknown[], fillBefore,
	         fillAfter, suggestions[]}."""
	ws = weekStartIso(weekIso)
	we = addDaysIso(ws, 6)
	exclude = set(exclude or [])
	if capacityHours is None:
		capacityHours = sum([_f(w.get('hrsPerWeek')) for w in workers or [] if w.get('internal')])
	capacityHours = round(_f(capacityHours), 2)
	planned, unknown, count = _weekPlanned(ws, wos)
	spare = round(capacityHours - planned, 2)
	todayIso = _s(todayIso)[:10] or workmate.planner.iso(system.date.now())
	horizonEnd = addDaysIso(ws, 6 + 7 * int(lookAheadWeeks))
	cands = []
	for w in wos:
		st = _s(w.get('start'))
		if st <= we or st > horizonEnd:
			continue
		if _s(w.get('cat')) == 'DONE' or _s(w.get('status')).upper() in ('C', 'D'):
			continue
		if not w.get('movable', True):
			continue
		if _i(w.get('id')) in exclude:
			continue
		h = _f(w.get('hrs'))
		if h <= 0:
			continue
		cands.append(w)
	cands.sort(key=lambda w: (_priRank(w.get('pri')), _s(w.get('start')), -_f(w.get('hrs')), _s(w.get('sid'))))
	suggestions = []
	remaining = spare
	for w in cands:
		if len(suggestions) >= _MAX_SUGGEST_PER_WEEK:
			break
		h = _f(w.get('hrs'))
		if h > remaining:
			continue
		st = _s(w.get('start'))
		weeksAhead = int(civilDays(ws, weekStartIso(st)) // 7)
		to = addDaysIso(st, -7 * weeksAhead)
		if to < todayIso:
			to = todayIso if todayIso <= we else we
		if to < ws or to > we:
			continue
		suggestions.append({'woId': _i(w.get('id')), 'sid': _s(w.get('sid')), 'title': _s(w.get('title')),
			'hrs': h, 'pri': _s(w.get('pri')), 'cat': _s(w.get('cat')), 'from': st, 'to': to,
			'deltaDays': civilDays(st, to), 'pins': bool(w.get('engineOwned')) and not w.get('pinned'),
			'reason': 'priority %s, %d week%s ahead, %s h fits the %s h spare' % (
				_s(w.get('pri')) or '-', weeksAhead, '' if weeksAhead == 1 else 's', _fmt(h), _fmt(remaining))})
		remaining = round(remaining - h, 2)
	pulled = round(sum([s['hrs'] for s in suggestions]), 2)
	return {'weekStart': ws, 'weekEnd': we, 'capacity': capacityHours, 'planned': planned, 'spare': spare,
		'count': count, 'unknown': [{'woId': _i(u.get('id')), 'sid': _s(u.get('sid')), 'title': _s(u.get('title'))} for u in unknown],
		'fillBefore': int(round(100.0 * planned / capacityHours)) if capacityHours > 0 else 0,
		'fillAfter': int(round(100.0 * (planned + pulled) / capacityHours)) if capacityHours > 0 else 0,
		'pulled': pulled, 'suggestions': suggestions}


def planHorizon(fromIso, weeks, wos, workers, capacityHours=None, lookAheadWeeks=2, todayIso=None):
	"""PURE. fillWeek() chained over `weeks` Mon-Sun weeks: a job pulled into
	week k is planned there for week k+1's arithmetic and is no longer a
	candidate. Also lists open work without hours (needsEstimate)."""
	ws = weekStartIso(fromIso)
	pulled = set()
	simWos = [dict(w) for w in wos]
	out = {'from': ws, 'weeks': [], 'moves': [], 'needsEstimate': [], 'capacity': None}
	for k in range(int(weeks)):
		wk = addDaysIso(ws, 7 * k)
		r = fillWeek(wk, simWos, workers, capacityHours, lookAheadWeeks, todayIso, exclude=pulled)
		out['capacity'] = r['capacity']
		for sg in r['suggestions']:
			pulled.add(sg['woId'])
			for w in simWos:
				if _i(w.get('id')) == sg['woId']:
					w['start'] = sg['to']
			out['moves'].append(dict(sg, weekStart=wk))
		out['weeks'].append({'weekStart': wk, 'capacity': r['capacity'], 'planned': r['planned'], 'spare': r['spare'],
			'count': r['count'], 'fillBefore': r['fillBefore'], 'fillAfter': r['fillAfter'], 'pulled': r['pulled'],
			'unknown': len(r['unknown']), 'suggestions': r['suggestions']})
	seen = set()
	for w in wos:
		if _s(w.get('cat')) == 'DONE' or _s(w.get('status')).upper() in ('C', 'D'):
			continue
		if _f(w.get('hrs')) > 0 or _i(w.get('id')) in seen:
			continue
		seen.add(_i(w.get('id')))
		out['needsEstimate'].append({'woId': _i(w.get('id')), 'sid': _s(w.get('sid')), 'title': _s(w.get('title')),
			'start': _s(w.get('start')), 'cat': _s(w.get('cat'))})
	out['needsEstimate'].sort(key=lambda x: x['start'])
	return out


def underOverWeeks(workerWeeks, userId, todayIso=None, weeksAhead=8):
	"""PURE. The greaser rule: weeks from this Monday forward where the person
	is over (>100%) or under (<80%) their Hrs_Per_Week."""
	todayIso = _s(todayIso)[:10] or workmate.planner.iso(system.date.now())
	fromWk = weekStartIso(todayIso)
	toWk = addDaysIso(fromWk, 7 * int(weeksAhead))
	rows = (workerWeeks or {}).get(str(_i(userId))) or []
	out = []
	for r in rows:
		wk = _s(r.get('weekStart'))
		if wk < fromWk or wk >= toWk:
			continue
		if r.get('flag') in ('over', 'under'):
			out.append(dict(r))
	return out


# ---------------------------------------------------------------------------
# service: everything the Suggest panel needs in one call
# ---------------------------------------------------------------------------

def suggest(fromIso, weeks=4, lookAheadWeeks=2, capacityHours=None, selectedWoId=0):
	"""rangeData over the horizon + look-ahead, history stats, planHorizon,
	pairs, and (when selectedWoId) the history suggestion for that WO."""
	weeks = max(1, min(int(weeks), 12))
	ws = weekStartIso(fromIso)
	toIso = addDaysIso(ws, 7 * (weeks + int(lookAheadWeeks)) - 1)
	data = workmate.planner.rangeData(ws, toIso)
	wos = data['wos']
	workers = data['workers']
	rows = fetchHistory()
	stats = historyStats(rows)
	todayIso = data.get('today')
	plan = planHorizon(ws, weeks, wos, workers, capacityHours, lookAheadWeeks, todayIso)
	out = {'from': ws, 'to': addDaysIso(ws, 7 * weeks - 1), 'weeks': weeks, 'lookAheadWeeks': lookAheadWeeks,
		'plan': plan, 'pairs': pairsWhoWorkTogether(rows), 'history': {'rows': stats['rows'], 'wos': stats['wos'],
		'masters': len(stats['byMaster']), 'assets': len(stats['byAsset'])},
		'flags': {}, 'libVersion': _VERSION, 'proposal': latestProposal(summary=True)}
	for w in workers:
		f = underOverWeeks(data.get('workerWeeks'), w['id'], todayIso, weeks)
		if f:
			out['flags'][str(w['id'])] = {'name': w['name'], 'initials': w['initials'], 'weeks': f}
	if _i(selectedWoId) > 0:
		wo = None
		for w in wos:
			if _i(w.get('id')) == _i(selectedWoId):
				wo = w
				break
		if wo is None:
			wo = workmate.planner.loadWO(_i(selectedWoId))
		if wo is not None:
			out['selected'] = suggestFor(_withAssetId(wo), stats, workers)
	_log('suggest %s +%dw: %d moves, %d need estimate, %d flagged people, history %d rows' % (
		ws, weeks, len(plan['moves']), len(plan['needsEstimate']), len(out['flags']), stats['rows']))
	return out


def _withAssetId(wo):
	"""rangeData rows carry the asset SHORT id; history keys on Asset_ID."""
	w = dict(wo)
	if _i(w.get('assetId')) <= 0 and _s(w.get('asset')):
		try:
			aid = system.db.runScalarPrepQuery("SELECT TOP 1 Asset_ID FROM dbo.Asset WHERE RTRIM(Short_asset_Id) = ?",
				[_s(w.get('asset'))], _DB)
			w['assetId'] = _i(aid)
		except:
			w['assetId'] = 0
	return w


def historyFor(woId):
	"""History suggestion for one WO (labour popup / selected card)."""
	wo = workmate.planner.loadWO(int(woId))
	if wo is None:
		return {'ok': False, 'code': 'NOT_FOUND', 'message': 'WO %s not found' % woId}
	rows = fetchHistory()
	stats = historyStats(rows)
	workers, teams = workmate.planner.workers()
	aid = _i(system.db.runScalarPrepQuery("SELECT ISNULL(Asset_ID, 0) FROM dbo.WO_N_Header WHERE WO_ID = ?", [int(woId)], _DB))
	sg = suggestFor({'sid': wo['sid'], 'assetId': aid}, stats, workers)
	sg['ok'] = True
	sg['woId'] = int(woId)
	sg['sid'] = wo['sid']
	return sg


# ---------------------------------------------------------------------------
# nightly proposal + autopilot (1.1.0)
# ---------------------------------------------------------------------------

def _cfg(key, default=''):
	return workmate.planner.configValue(key, default)


def proposalDir():
	import os
	base = _cfg('PLANNER_UI_DIR', 'C:\\WorkmateData\\Planner')
	return os.path.join(base, 'proposals')


def _ensureDir(d):
	"""Create the folder and prove it is writable (Marker Law: probe first)."""
	import os
	if not os.path.isdir(d):
		os.makedirs(d)
	probe = os.path.join(d, '_probe.tmp')
	f = open(probe, 'w')
	try:
		f.write('probe')
	finally:
		f.close()
	os.remove(probe)
	return d


def _writeJson(path, obj):
	import codecs
	f = codecs.open(path, 'w', 'utf-8')
	try:
		f.write(system.util.jsonEncode(obj))
	finally:
		f.close()


def _readJson(path):
	import codecs, os
	if not os.path.isfile(path):
		return None
	f = codecs.open(path, 'r', 'utf-8')
	try:
		txt = f.read()
	finally:
		f.close()
	return system.util.jsonDecode(txt)


def latestProposal(summary=False):
	"""The last nightly proposal (or None). summary=True trims the moves to
	what the Suggest panel shows."""
	import os
	try:
		p = _readJson(os.path.join(proposalDir(), 'latest.json'))
	except:
		return None
	if not p:
		return None
	if summary:
		return {'ranAt': p.get('ranAt'), 'from': p.get('from'), 'weeks': p.get('weeks'),
			'moves': p.get('moves') or [], 'applied': p.get('applied') or [], 'autopilot': bool(p.get('autopilot')),
			'needsEstimate': len(p.get('needsEstimate') or []), 'flagged': len(p.get('flags') or {}),
			'capacity': p.get('capacity')}
	return p


def autopilotGuard(move, maxWeeks):
	"""PURE. True when a proposed move is safe to apply unattended."""
	if move.get('pins'):
		return False
	if _s(move.get('cat')) == 'PM':
		return False
	if _s(move.get('pri')).upper() not in ('A', 'B'):
		return False
	if (-_i(move.get('deltaDays'))) > 7 * int(maxWeeks):
		return False
	return True


def applyProposal(proposal, actorId, moveIds=None, autopilot=False, dryRun=True):
	"""Apply moves from a proposal through workmate.planner.moveWO (confirm
	implied). moveIds limits it; autopilot=True applies only the guarded
	subset. Returns {applied[], skipped[], failed[]}."""
	maxWeeks = _i(_cfg('PLANNER_AUTOPILOT_MAX_WEEKS', '2'), 2)
	maxMoves = _i(_cfg('PLANNER_AUTOPILOT_MAX_MOVES', '10'), 10)
	want = None if moveIds is None else set([_i(x) for x in moveIds])
	out = {'applied': [], 'skipped': [], 'failed': [], 'dryRun': bool(dryRun)}
	for mv in (proposal or {}).get('moves') or []:
		wid = _i(mv.get('woId'))
		if want is not None and wid not in want:
			continue
		if autopilot and not autopilotGuard(mv, maxWeeks):
			out['skipped'].append(dict(mv, why='autopilot guard'))
			continue
		if autopilot and len(out['applied']) >= maxMoves:
			out['skipped'].append(dict(mv, why='autopilot max moves'))
			continue
		r = workmate.planner.moveWO(wid, mv.get('to'), actorId, expectStartIso=mv.get('from'), confirm=True,
			dryRun=dryRun, eventName='Rescheduled (autopilot)' if autopilot else 'Rescheduled')
		if r.get('ok'):
			out['applied'].append({'woId': wid, 'sid': mv.get('sid'), 'from': mv.get('from'), 'to': r.get('newStart'),
				'hrs': mv.get('hrs'), 'undo': r.get('undo'), 'pinned': r.get('pinned')})
		else:
			out['failed'].append(dict(mv, code=r.get('code'), message=r.get('message')))
	return out


def nightly(weeks=None, apply=None, dryRun=False):
	"""Run the plan for the coming weeks, save it, optionally apply the
	guarded subset (autopilot). Returns the proposal dict. Safe to run any
	time; the file is the record. apply=None -> System_Configuration
	PLANNER_AUTOPILOT ('1' = on)."""
	import os
	weeks = _i(weeks, 0) or _i(_cfg('PLANNER_NIGHTLY_WEEKS', '4'), 4)
	if apply is None:
		apply = _cfg('PLANNER_AUTOPILOT', '0') == '1'
	actor = _i(_cfg('PLANNER_AUTOPILOT_USER_ID', '0'))
	todayIso = workmate.planner.iso(system.date.now())
	sug = suggest(todayIso, weeks, 2, None, 0)
	plan = sug['plan']
	prop = {'ranAt': system.date.format(system.date.now(), "yyyy-MM-dd'T'HH:mm:ss"), 'from': plan['from'], 'weeks': weeks,
		'capacity': plan['capacity'], 'weekly': plan['weeks'], 'moves': plan['moves'],
		'needsEstimate': plan['needsEstimate'], 'flags': sug['flags'], 'pairs': sug['pairs'],
		'autopilot': bool(apply), 'applied': [], 'skipped': [], 'failed': [], 'libVersion': _VERSION}
	if apply:
		if actor <= 0:
			prop['failed'].append({'why': 'PLANNER_AUTOPILOT_USER_ID not set - nothing applied'})
		else:
			res = applyProposal(prop, actor, None, autopilot=True, dryRun=dryRun)
			prop['applied'] = res['applied']
			prop['skipped'] = res['skipped']
			prop['failed'] = res['failed']
	try:
		d = _ensureDir(proposalDir())
		_writeJson(os.path.join(d, 'latest.json'), prop)
		_writeJson(os.path.join(d, 'proposal_%s.json' % system.date.format(system.date.now(), 'yyyyMMdd_HHmm')), prop)
		prop['saved'] = d
	except:
		prop['saved'] = ''
		prop['saveError'] = _err()
		_log('nightly: proposal not saved: ' + prop['saveError'], 'warn')
	_log('nightly %s +%dw: %d moves proposed, %d applied (autopilot=%s dryRun=%s), %d need estimate, %d flagged' % (
		prop['from'], weeks, len(prop['moves']), len(prop['applied']), apply, dryRun, len(prop['needsEstimate']), len(prop['flags'])))
	try:
		workmate.diag.log('Planner', 'nightly proposal %s: %d moves, %d applied, %d need estimate' % (
			prop['from'], len(prop['moves']), len(prop['applied']), len(prop['needsEstimate'])), 'info')
	except:
		pass
	return prop