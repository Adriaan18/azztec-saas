# =============================================================================
# workmate_planner_chat_code_v1_2_1.py
# Version:     1.2.1
# Target:      Project Library  workmate/planner_chat
# Database:    TLSQL01_Workmate  (via workmate.planner / planner_ai)
# Author:      Adriaan
# Spec:        Workmate_P-PLN1_PlannerCalendar_Spec_v1_1_0.md  (slice S5b)
#              Workmate_AI_Architecture_v1_2.md  - Layer 2 surface, Layer 3/4
#              stand-in until workmate-ai is live
#
# Purpose:
#   The planner brain behind the WM AI Assistant while there is no model:
#   a DETERMINISTIC intent router. parse() is PURE (text -> intent + params),
#   answer() executes through the same functions the /planner routes and the
#   future LLM tools use (workmate.planner, workmate.planner_ai) and renders
#   a Markdown reply the bubble already knows how to show. Writes always go
#   through a confirm turn ("yes") and every applied change is undoable
#   ("undo"). When workmate-ai arrives, parse() is what the model replaces;
#   nothing below it changes.
#
#   Intents:
#     help                        what it understands
#     plan [N weeks | next week]  pull-forward plan (planner_ai.planHorizon)
#     apply all | apply 1,3       apply moves from the last plan shown
#     move <WO> to <date expr>    date: 18 sep | 18/09 | thursday | tomorrow |
#                                 next week | 2026-09-18  -> confirm -> moveWO
#     estimate <WO> 4h            Duration_In_Hours -> confirm -> setEstimate
#     history / who does <WO>     history-based hours + usual crew
#     who is over/under [next week]   people over/under their weekly hours
#     pairs                       who usually works together
#     unpin <WO>                  hand a pinned PM back to the engine
#     proposal                    last night's proposal (planner_ai.nightly)
#     undo                        put the last chat-applied change back
#     yes / no                    confirm / cancel the pending action
#
#   Context per session (pending action, last plan, undo stack) lives in a
#   gateway-side dict keyed by session id with a 2 h TTL - no custom props
#   needed on the view.
#
# SELECTED-WO CONTEXT (1.1.0) - answer(text, session=None, ctx=None):
#   ctx = {'sid', 'userId', 'userName', 'woId'} from the planner's own
#   assistant panel (POST /chat). With a woId the words 'this' / 'it' /
#   'here' / 'this asset' / 'this location' resolve without naming anything:
#     last work on this asset        assetLast()    - last 5 WOs, hours logged
#     history of this asset          assetHistory() - counts, hours, usual crew
#     open work here / at this location   locationOpen()
#     parts used on this asset       assetParts()   - last 24 months, by count
#     who usually does this          historyFor(woId)
#     about this wo / summary        the card facts + history line
#     move this to thursday / estimate this 4h / unpin this  -> as before
#   Everything read-only except the same confirm-gated writes as 1.0.0.
#
# FOLLOW-UPS (1.2.0): answer() also returns 'next' - the 2-5 prompts that
#   make sense after this reply (pending confirm -> yes / no; a plan -> apply
#   all / apply 1; asset answers -> history / parts / open work here; a WO
#   without hours -> estimate this <median>h ...). The UI renders them as
#   chips under the bubble, so no permanent prompt row is needed. commands()
#   lists every intent with a one-line description for the '/' menu.
#
# Changelog:
#   v1.2.1  resetFor(sid): drop one session's pending / plan / undo context
#           (the planner's 'new chat' - a new WO selected, or the reset button).
#   v1.2.0  Follow-ups ('next') and commands() for the slash menu.
#   v1.1.0  Selected-WO context, asset / location / parts questions, /chat ctx.
#   v1.0.0  Initial.
# =============================================================================

import re

_VERSION = '1.2.1'
_DB = 'TLSQL01_Workmate'
_SOURCE = 'workmate.planner_chat'
_CTX = {}
_CTX_TTL_MS = 2 * 60 * 60 * 1000

_WO_RE = re.compile(r'\b((?:WO|K|KPP)-[A-Z0-9]+(?:-[A-Z0-9]+){1,3}(?:-S)?)\b', re.I)
_HOURS_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\b', re.I)
_DOW = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
_MON = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']


def version():
	return _VERSION


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


def _fmtH(h):
	h = _f(h)
	return (str(int(h)) if h == int(h) else ('%.1f' % h)) + ' h'


def _fmtDate(isoDay):
	d = workmate.planner.parseIso(isoDay)
	return isoDay if d is None else system.date.format(d, 'EEE d MMM')


# ---------------------------------------------------------------------------
# PURE: date expressions + intent parse
# ---------------------------------------------------------------------------

def parseDateExpr(expr, todayIso, weekdayHint=None):
	"""'18 sep' | '18/09' | 'thursday' | 'tomorrow' | 'today' | 'next week' |
	'2026-09-18' -> yyyy-MM-dd or ''. weekdayHint (0=Mon) keeps the WO's
	weekday for 'next week'. Never earlier than todayIso for names."""
	e = _s(expr).lower().strip()
	today = workmate.planner.parseIso(todayIso)
	if not e or today is None:
		return ''
	m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', e)
	if m:
		return '%04d-%02d-%02d' % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
	if e in ('today', 'now'):
		return todayIso
	if e == 'tomorrow':
		return workmate.planner.iso(system.date.addDays(today, 1))
	if e in ('next week', 'the week after', 'following week'):
		base = workmate.planner.weekStart(system.date.addDays(today, 7))
		off = weekdayHint if weekdayHint is not None else 0
		return workmate.planner.iso(system.date.addDays(base, int(off)))
	if e in ('this week',):
		base = workmate.planner.weekStart(today)
		off = weekdayHint if weekdayHint is not None else 0
		d = system.date.addDays(base, int(off))
		return workmate.planner.iso(d)
	isNext = e.startswith('next ')
	e2 = e[5:] if isNext else e
	for i, name in enumerate(_DOW):
		if e2 == name or e2 == name[:3]:
			if isNext:
				# 'next thursday' = the Thursday of next week
				base = workmate.planner.weekStart(system.date.addDays(today, 7))
				return workmate.planner.iso(system.date.addDays(base, i))
			dow = (system.date.getDayOfWeek(today) + 5) % 7      # 0 = Monday
			delta = (i - dow) % 7
			if delta == 0:
				delta = 7                                        # 'thursday' on a Thursday = next one
			return workmate.planner.iso(system.date.addDays(today, delta))
	m = re.match(r'^(\d{1,2})[ /\-]([a-z]{3,9}|\d{1,2})(?:[ /\-](\d{2,4}))?$', e)
	if m:
		day = int(m.group(1))
		mon = m.group(2)
		if mon.isdigit():
			month = int(mon)
		else:
			month = 0
			for i, mn in enumerate(_MON):
				if mon.startswith(mn):
					month = i + 1
		if month < 1 or month > 12 or day < 1 or day > 31:
			return ''
		year = int(system.date.getYear(today))
		if m.group(3):
			y = int(m.group(3))
			year = y + 2000 if y < 100 else y
		iso = '%04d-%02d-%02d' % (year, month, day)
		if not m.group(3) and iso < todayIso and workmate.planner.civilDays(iso, todayIso) > 120:
			iso = '%04d-%02d-%02d' % (year + 1, month, day)
		return iso if workmate.planner.parseIso(iso) is not None else ''
	return ''


def parse(text):
	"""PURE. -> {'intent', ...params}. Unknown text -> intent 'unknown'."""
	t = _s(text)
	q = t.lower().strip()
	if not q:
		return {'intent': 'empty'}
	if q in ('yes', 'y', 'yep', 'yeah', 'confirm', 'do it', 'go', 'ok', 'okay', 'sure', 'apply'):
		return {'intent': 'confirm'}
	if q in ('no', 'n', 'nope', 'cancel', 'discard', 'stop', 'forget it'):
		return {'intent': 'cancel'}
	if q in ('undo', 'undo that', 'put it back', 'revert'):
		return {'intent': 'undo'}
	if q in ('help', '?', 'what can you do', 'what can you do?', 'commands'):
		return {'intent': 'help'}
	wos = [w.upper() for w in _WO_RE.findall(t)]
	sid = wos[0] if wos else ''
	ctxSid = _s(_CUR.get('woSid'))
	pron = bool(re.search(r"\b(this|it|here|that|current|selected)\b", q))
	if ctxSid and not sid and pron:
		if re.search(r'\b(last|previous|recent|when)\b.*\b(work|wo|job|done|maintenance)\b|\blast (wo|job|work)\b', q):
			return {'intent': 'asset_last'}
		if re.search(r'\b(history|happened|track record|how often|how many times)\b', q) and not re.search(r'\bwho\b', q):
			return {'intent': 'asset_history'}
		if re.search(r'\b(open|outstanding|scheduled|planned|else)\b', q) and re.search(r'\b(here|location|area|site|this location)\b', q):
			return {'intent': 'location_open'}
		if re.search(r'\b(parts?|spares?|consumables?|materials?)\b', q):
			return {'intent': 'asset_parts'}
		if re.search(r'\b(about|summary|summarise|summarize|tell me|details|what is)\b', q):
			return {'intent': 'this_wo'}
		sid = ctxSid
		q = re.sub(r'\b(this one|this wo|this job|this|it|that)\b', ctxSid.lower(), q, count=1)
	m = re.match(r'^apply\s+(all|everything|\d+(?:\s*[, ]\s*\d+)*)\s*$', q)
	if m:
		which = m.group(1)
		if which in ('all', 'everything'):
			return {'intent': 'apply', 'which': 'all'}
		return {'intent': 'apply', 'which': [int(x) for x in re.findall(r'\d+', which)]}
	if re.search(r'\b(move all|do all of them|apply the plan)\b', q):
		return {'intent': 'apply', 'which': 'all'}
	if re.search(r'\bunpin\b', q) and sid:
		return {'intent': 'unpin', 'sid': sid}
	if re.search(r'\b(estimate|takes|will take|set hours|hours for)\b', q) and sid:
		hm = _HOURS_RE.search(q)
		if not hm:
			hm = re.search(r'\b(\d+(?:\.\d+)?)\b(?!\d*-)', re.sub(re.escape(sid.lower()), '', q))
		if hm:
			return {'intent': 'estimate', 'sid': sid, 'hours': float(hm.group(1))}
		return {'intent': 'estimate', 'sid': sid, 'hours': None}
	m = re.search(r'\b(?:move|shift|push|bring|reschedule)\b\s+' + re.escape(sid.lower()) + r'\s+(?:to|onto|forward to|back to|into)\s+(.+?)\s*$', q) if sid else None
	if m:
		return {'intent': 'move', 'sid': sid, 'dateExpr': m.group(1).strip().rstrip('.?!')}
	if sid and re.search(r'\b(move|shift|push|bring|reschedule)\b', q):
		return {'intent': 'move', 'sid': sid, 'dateExpr': ''}
	if sid and re.search(r'\b(history|who (?:usually |normally )?(?:does|did|works on)|crew|how long|who should)\b', q):
		return {'intent': 'history', 'sid': sid}
	if re.search(r'\b(over|under|overloaded|overbooked|too much|too little|flag|flagged|spare)\b', q) and re.search(r'\b(who|anyone|people|workers|is )\b', q):
		return {'intent': 'flags'}
	if re.search(r'\b(pairs?|work together|worked together|together)\b', q):
		return {'intent': 'pairs'}
	if re.search(r'\b(proposal|last night|nightly|overnight)\b', q):
		return {'intent': 'proposal'}
	if re.search(r'\b(plan|suggest|fill|pull forward|what should we|schedule)\b', q):
		wm = re.search(r'(\d+)\s*(?:weeks?|wks?)', q)
		weeks = int(wm.group(1)) if wm else (2 if 'next week' in q else 4)
		return {'intent': 'plan', 'weeks': max(1, min(weeks, 8))}
	if sid:
		return {'intent': 'history', 'sid': sid}
	return {'intent': 'unknown'}


# ---------------------------------------------------------------------------
# context per session
# ---------------------------------------------------------------------------

_CUR = {}     # per-call context (set by answer): {'sid','userId','userName','woId'}


def _sid(session):
	if _CUR.get('sid'):
		return str(_CUR['sid'])
	try:
		return str(session.props.id)
	except:
		return 'console'


def _actor(session):
	if _CUR.get('userId'):
		return int(_CUR['userId'])
	try:
		return int(session.custom.wmUserId or 0)
	except:
		return 0


def _ctx(session):
	sid = _sid(session)
	now = system.date.now().getTime()
	for k in list(_CTX.keys()):
		if now - _CTX[k].get('t', 0) > _CTX_TTL_MS:
			del _CTX[k]
	c = _CTX.get(sid)
	if c is None:
		c = {'pending': None, 'plan': None, 'undo': [], 't': now}
		_CTX[sid] = c
	c['t'] = now
	return c


def resetFor(sid):
	"""Forget one session's pending action, plan and undo stack."""
	_CTX.pop(str(sid), None)


def resetContext(session=None):
	if session is None:
		_CTX.clear()
	else:
		_CTX.pop(_sid(session), None)


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------

def _woBySid(sid):
	ds = system.db.runPrepQuery(
		"SELECT TOP 1 WO_ID FROM dbo.WO_N_Header WHERE REPLACE(RTRIM(ISNULL(Short_WO_Id, '')), CHAR(160), '') = ?", [sid], _DB)
	if ds.getRowCount() == 0:
		return None
	return workmate.planner.loadWO(int(ds.getValueAt(0, 'WO_ID')))


def _help():
	return ('Here is what I can do from the planner:\n\n'
		'- **plan next week** / **plan 4 weeks** - pull work forward into spare hours\n'
		'- **apply all** / **apply 1,3** - do the moves from the last plan\n'
		'- **move WO-260902-012 to thursday** (or *18 sep*, *next week*, *2026-09-18*)\n'
		'- **estimate WO-260902-012 4h** - set the hours\n'
		'- **who usually does K-KPL-04-0007** - hours and crew from history\n'
		'- **who is over next week** - people over / under their hours\n'
		'- **pairs** - who works together, **proposal** - last night\'s plan\n'
		'- **unpin K-KGR-03-0002**, **undo**, **yes** / **no**\n'
		+ ('\nWith `%s` selected you can also ask: **last work on this asset**, **history of this asset**, '
		   '**open work here**, **parts used on this asset**, **who usually does this**, **about this WO**, '
		   '**move this to thursday**, **estimate this 4h**.\n' % _CUR['woSid'] if _CUR.get('woSid') else '')
		+ '\nEverything I change is audited and undoable.')


def _planReply(session, weeks):
	c = _ctx(session)
	todayIso = workmate.planner.iso(system.date.now())
	sug = workmate.planner_ai.suggest(todayIso, weeks, 2, None, 0)
	plan = sug['plan']
	c['plan'] = plan['moves']
	lines = ['**Plan from %s, %d week%s** (capacity %s/week)' % (_fmtDate(plan['from']), weeks, '' if weeks == 1 else 's', _fmtH(plan['capacity']))]
	for wk in plan['weeks']:
		lines.append('- week of %s: %s of %s (%d%%%s)%s' % (_fmtDate(wk['weekStart']), _fmtH(wk['planned']), _fmtH(wk['capacity']), wk['fillBefore'],
			(' -> %d%% after' % wk['fillAfter']) if wk['pulled'] else '', (' - %d without hours' % wk['unknown']) if wk['unknown'] else ''))
	if plan['moves']:
		lines.append('')
		lines.append('**Pull forward:**')
		for i, mv in enumerate(plan['moves']):
			lines.append('%d. `%s` %s -> %s (%s)%s - %s' % (i + 1, mv['sid'], _fmtDate(mv['from']), _fmtDate(mv['to']), _fmtH(mv['hrs']),
				' *pins*' if mv['pins'] else '', mv['title'][:40]))
		lines.append('')
		lines.append('Say **apply all** or **apply 1,3**.')
	else:
		lines.append('')
		lines.append('Nothing to pull forward - ' + ('every week is already at capacity.' if all([w['spare'] <= 0 for w in plan['weeks']]) else 'nothing in the next 2 weeks has hours that fit.'))
	if plan['needsEstimate']:
		lines.append('')
		lines.append('**%d job%s need%s an estimate** before I can plan them: %s%s' % (len(plan['needsEstimate']), '' if len(plan['needsEstimate']) == 1 else 's', 's' if len(plan['needsEstimate']) == 1 else '',
			', '.join(['`%s`' % n['sid'] for n in plan['needsEstimate'][:6]]), '...' if len(plan['needsEstimate']) > 6 else ''))
		lines.append('Say **estimate WO-xxx 4h** for any of them.')
	if sug.get('flags'):
		lines.append('')
		names = []
		for k, f in sug['flags'].items():
			over = len([w for w in f['weeks'] if w['flag'] == 'over'])
			under = len([w for w in f['weeks'] if w['flag'] == 'under'])
			names.append('%s (%s)' % (f['name'], ', '.join([x for x in ['%d over' % over if over else '', '%d under' % under if under else ''] if x])))
		lines.append('**People to look at:** ' + ', '.join(sorted(names)))
	return '\n'.join(lines)


def _applyReply(session, which):
	c = _ctx(session)
	moves = c.get('plan') or []
	if not moves:
		return 'I have no plan on the table - say **plan next week** first.'
	if which == 'all':
		picked = list(moves)
	else:
		picked = [moves[i - 1] for i in which if 1 <= i <= len(moves)]
		if not picked:
			return 'Those numbers are not in the plan (1-%d).' % len(moves)
	c['pending'] = {'kind': 'apply', 'moves': picked}
	return 'Move %d job%s: %s? Say **yes** to do it.' % (len(picked), '' if len(picked) == 1 else 's',
		', '.join(['`%s` -> %s' % (m['sid'], _fmtDate(m['to'])) for m in picked]))


def _doApply(session, moves):
	c = _ctx(session)
	actor = _actor(session)
	res = workmate.planner_ai.applyProposal({'moves': moves}, actor, None, autopilot=False, dryRun=False)
	for a in res['applied']:
		if a.get('undo'):
			c['undo'].append(dict(a['undo'], kind='move', sid=a['sid']))
	c['plan'] = [m for m in (c.get('plan') or []) if m['woId'] not in [a['woId'] for a in res['applied']]]
	lines = []
	if res['applied']:
		lines.append('Done - moved %s.' % ', '.join(['`%s` to %s%s' % (a['sid'], _fmtDate(a['to']), ' (pinned)' if a.get('pinned') else '') for a in res['applied']]))
	for f in res['failed']:
		lines.append('Could not move `%s`: %s' % (f.get('sid'), f.get('message') or f.get('code')))
	if res['applied']:
		lines.append('Say **undo** to put the last one back.')
	return '\n'.join(lines) or 'Nothing applied.'


def _moveReply(session, sid, dateExpr):
	c = _ctx(session)
	wo = _woBySid(sid)
	if wo is None:
		return 'I cannot find an open work order `%s`.' % sid
	todayIso = workmate.planner.iso(system.date.now())
	hint = None
	d0 = workmate.planner.parseIso(wo['start'])
	if d0 is not None:
		hint = (system.date.getDayOfWeek(d0) + 5) % 7
	toIso = parseDateExpr(dateExpr, todayIso, hint) if dateExpr else ''
	if not toIso:
		return 'Move `%s` (now %s) to when? Try *thursday*, *18 sep*, *next week* or *2026-09-18*.' % (sid, _fmtDate(wo['start']))
	rules = workmate.planner.moveRules(wo, toIso, todayIso)
	if not rules['ok']:
		return 'Cannot move `%s`: %s' % (sid, rules['message'])
	c['pending'] = {'kind': 'move', 'woId': wo['id'], 'sid': sid, 'toIso': toIso, 'expect': wo['start']}
	why = ''
	if rules['reasons']:
		why = ' Note: ' + '; '.join([r['text'] for r in rules['reasons']]) + '.'
	if rules.get('willPin'):
		why += ' It is a PM - the move pins it (the release engine leaves it alone).'
	return 'Move `%s` from %s to **%s** (%+d d)?%s Say **yes** to do it.' % (sid, _fmtDate(wo['start']), _fmtDate(toIso), rules['delta'], why)


def _doMove(session, p):
	c = _ctx(session)
	r = workmate.planner.moveWO(p['woId'], p['toIso'], _actor(session), expectStartIso=p['expect'], confirm=True, dryRun=False)
	if not r.get('ok'):
		return 'Could not move `%s`: %s' % (p['sid'], r.get('message') or r.get('code'))
	c['undo'].append(dict(r['undo'], kind='move', sid=p['sid']))
	return 'Done - `%s` is now on **%s**%s. Say **undo** to put it back.' % (p['sid'], _fmtDate(r['newStart']),
		' and pinned' if r.get('willPin') else (' - pin cleared' if r.get('willUnpin') else ''))


def _estimateReply(session, sid, hours):
	c = _ctx(session)
	wo = _woBySid(sid)
	if wo is None:
		return 'I cannot find an open work order `%s`.' % sid
	if hours is None:
		return 'How many hours for `%s`? Say **estimate %s 4h**.' % (sid, sid)
	rules = workmate.planner.estimateRules(wo, hours)
	if not rules['ok']:
		return 'Cannot set that: %s' % rules['message']
	c['pending'] = {'kind': 'estimate', 'woId': wo['id'], 'sid': sid, 'hours': rules['hours'], 'prev': wo['estimate']}
	return 'Set `%s` to **%s** (was %s)? Say **yes**.' % (sid, _fmtH(rules['hours']), _fmtH(wo['estimate']) if wo['estimate'] > 0 else 'no estimate')


def _doEstimate(session, p):
	c = _ctx(session)
	r = workmate.planner.setEstimate(p['woId'], p['hours'], _actor(session), dryRun=False)
	if not r.get('ok'):
		return 'Could not set the estimate: %s' % (r.get('message') or r.get('code'))
	c['undo'].append({'kind': 'estimate', 'woId': p['woId'], 'sid': p['sid'], 'hours': p['prev']})
	return 'Done - `%s` is %s. Say **undo** to revert.' % (p['sid'], _fmtH(r['hours']))


def _historyReply(session, sid):
	wo = _woBySid(sid)
	if wo is None:
		return 'I cannot find an open work order `%s`.' % sid
	h = workmate.planner_ai.historyFor(wo['id'])
	if not h.get('ok'):
		return 'No history answer for `%s`: %s' % (sid, h.get('message'))
	lines = ['`%s` - %s' % (sid, wo['title'][:60]), h['text']]
	if h.get('people'):
		lines.append('')
		for p in h['people']:
			lines.append('- **%s** on %d of %d jobs (%s logged)' % (p['name'], p['wos'], h['n'], _fmtH(p['hours'])))
	if h.get('medianHours', 0) > 0 and wo['estimate'] <= 0:
		lines.append('')
		lines.append('It has no estimate yet - say **estimate %s %sh** to use the median.' % (sid, workmate.planner_ai._fmt(h['medianHours'])))
	return '\n'.join(lines)


def _flagsReply(session):
	todayIso = workmate.planner.iso(system.date.now())
	sug = workmate.planner_ai.suggest(todayIso, 4, 2, None, 0)
	if not sug['flags']:
		return 'Nobody is over or under their hours in the next 4 weeks. (Hours only count once jobs have estimates or planned labour.)'
	lines = ['**Over / under their weekly hours, next 4 weeks:**']
	for k, f in sorted(sug['flags'].items(), key=lambda kv: kv[1]['name']):
		lines.append('- **%s**: ' % f['name'] + '; '.join(['wk %s %s/%s (%s)' % (_fmtDate(w['weekStart']), _fmtH(w['planned']).replace(' h', ''), _fmtH(w['capacity']), w['flag']) for w in f['weeks']]))
	return '\n'.join(lines)


def _pairsReply(session):
	rows = workmate.planner_ai.fetchHistory()
	pairs = workmate.planner_ai.pairsWhoWorkTogether(rows)
	if not pairs:
		return 'Not enough shared jobs in the history to call any pairs yet.'
	workers, teams = workmate.planner.workers()
	names = dict([(w['id'], w['name']) for w in workers])
	return '**Pairs who usually work together:**\n' + '\n'.join(['- %s + %s (%d jobs)' % (names.get(p['a'], '#%s' % p['a']), names.get(p['b'], '#%s' % p['b']), p['wos']) for p in pairs[:10]])


def _proposalReply(session):
	c = _ctx(session)
	p = workmate.planner_ai.latestProposal()
	if not p:
		return 'No nightly proposal yet - once workmate.planner_ai.nightly() is scheduled it lands here every morning.'
	c['plan'] = p.get('moves') or []
	lines = ['**Proposal from %s** (%d weeks from %s%s)' % (p.get('ranAt', '?').replace('T', ' ')[:16], _i(p.get('weeks')), _fmtDate(p.get('from', '')),
		', autopilot ON' if p.get('autopilot') else '')]
	if p.get('applied'):
		lines.append('Applied overnight: ' + ', '.join(['`%s` -> %s' % (a['sid'], _fmtDate(a['to'])) for a in p['applied']]))
	if c['plan']:
		lines.append('**Still proposed:**')
		for i, mv in enumerate(c['plan']):
			lines.append('%d. `%s` %s -> %s (%s)%s' % (i + 1, mv['sid'], _fmtDate(mv['from']), _fmtDate(mv['to']), _fmtH(mv['hrs']), ' *pins*' if mv.get('pins') else ''))
		lines.append('Say **apply all** or **apply 1,3**.')
	else:
		lines.append('No moves left to apply.')
	if p.get('needsEstimate'):
		lines.append('%d job%s still need an estimate.' % (len(p['needsEstimate']), '' if len(p['needsEstimate']) == 1 else 's'))
	return '\n'.join(lines)


def _unpinReply(session, sid):
	wo = _woBySid(sid)
	if wo is None:
		return 'I cannot find an open work order `%s`.' % sid
	if not wo['pinned']:
		return '`%s` is not pinned.' % sid
	r = workmate.planner.unpin(wo['id'], _actor(session), dryRun=False)
	if not r.get('ok'):
		return 'Could not unpin: %s' % (r.get('message') or r.get('code'))
	return 'Done - `%s` is back with the release engine; it re-dates it home on its next run (engine date %s).' % (sid, _fmtDate(r['engineDate']))


def _undoReply(session):
	c = _ctx(session)
	if not c['undo']:
		return 'Nothing to undo in this chat.'
	u = c['undo'].pop()
	actor = _actor(session)
	if u['kind'] == 'move':
		r = workmate.planner.undoMove(u['woId'], u['toIso'], actor, expectStartIso=u.get('expectStartIso'), dryRun=False)
		if not r.get('ok'):
			c['undo'].append(u)
			return 'Could not undo `%s`: %s' % (u.get('sid'), r.get('message') or r.get('code'))
		return 'Undone - `%s` is back on **%s**.' % (u.get('sid'), _fmtDate(r['newStart']))
	if u['kind'] == 'estimate':
		r = workmate.planner.setEstimate(u['woId'], u['hours'], actor, dryRun=False)
		if not r.get('ok'):
			c['undo'].append(u)
			return 'Could not revert the estimate: %s' % (r.get('message') or r.get('code'))
		return 'Undone - `%s` back to %s.' % (u.get('sid'), _fmtH(r['hours']) if r['hours'] > 0 else 'no estimate')
	return 'Nothing to undo.'


# ---------------------------------------------------------------------------
# selected-WO context (1.1.0) - read-only
# ---------------------------------------------------------------------------

def woContext(woId):
	ds = system.db.runPrepQuery(
		"SELECT h.WO_ID, RTRIM(ISNULL(h.Short_WO_Id, '')) AS Sid, RTRIM(ISNULL(h.WO_Title, '')) AS Title, "
		"ISNULL(h.Asset_ID, 0) AS AssetId, ISNULL(h.Location_Id, 0) AS LocId, RTRIM(ISNULL(h.Status, '')) AS Status, "
		"RTRIM(ISNULL(a.Short_asset_Id, '')) AS Asset, RTRIM(ISNULL(a.Asset_Title, '')) AS AssetTitle, "
		"RTRIM(ISNULL(l.Short_Location_ID, '')) AS Loc, RTRIM(ISNULL(l.Location_Title, '')) AS LocTitle "
		"FROM dbo.WO_N_Header h LEFT JOIN dbo.Asset a ON a.Asset_ID = h.Asset_ID "
		"LEFT JOIN dbo.Location l ON l.Location_Id = h.Location_Id WHERE h.WO_ID = ?", [int(woId)], _DB)
	if ds.getRowCount() == 0:
		return None
	g = lambda c: ds.getValueAt(0, c)
	return {'woId': _i(g('WO_ID')), 'sid': _s(g('Sid')), 'title': _s(g('Title')), 'status': _s(g('Status')),
		'assetId': _i(g('AssetId')), 'asset': _s(g('Asset')), 'assetTitle': _s(g('AssetTitle')),
		'locId': _i(g('LocId')), 'loc': _s(g('Loc')), 'locTitle': _s(g('LocTitle'))}


_ASSET_WOS_SQL = (
	"SELECT TOP %d * FROM ("
	"SELECT 'N' AS Src, h.WO_ID, RTRIM(ISNULL(h.Short_WO_Id, '')) AS Sid, RTRIM(ISNULL(h.WO_Title, '')) AS Title, "
	"RTRIM(ISNULL(h.Status, '')) AS Status, h.Request_Start_Date AS D, "
	"(SELECT SUM(ISNULL(a.Quantity, 0)) FROM dbo.WO_N_Activity a WHERE a.WO_ID = h.WO_ID AND RTRIM(ISNULL(a.Trx_Type, '')) = 'L') AS Hrs "
	"FROM dbo.WO_N_Header h WHERE h.Asset_ID = ? AND h.WO_ID <> ? AND RTRIM(ISNULL(h.Status, '')) <> 'D' "
	"UNION ALL "
	"SELECT 'C' AS Src, c.WO_ID, RTRIM(ISNULL(c.Short_WO_Id, '')) AS Sid, RTRIM(ISNULL(c.WO_Title, '')) AS Title, "
	"RTRIM(ISNULL(c.Status, '')) AS Status, c.Request_Start_Date AS D, "
	"(SELECT SUM(ISNULL(a.Quantity, 0)) FROM dbo.WO_C_Activity a WHERE a.WO_ID = c.WO_ID AND RTRIM(ISNULL(a.Trx_Type, '')) = 'L') AS Hrs "
	"FROM dbo.WO_C_header c WHERE c.Asset_ID = ? AND c.WO_ID <> ?) x ORDER BY x.D DESC")


def assetWOs(assetId, excludeWoId=0, top=5):
	ds = system.db.runPrepQuery(_ASSET_WOS_SQL % int(top), [int(assetId), int(excludeWoId), int(assetId), int(excludeWoId)], _DB)
	out = []
	for i in range(ds.getRowCount()):
		d = ds.getValueAt(i, 'D')
		out.append({'sid': _s(ds.getValueAt(i, 'Sid')), 'title': _s(ds.getValueAt(i, 'Title')), 'status': _s(ds.getValueAt(i, 'Status')),
			'date': workmate.planner.iso(d) if d is not None else '', 'hours': _f(ds.getValueAt(i, 'Hrs')), 'src': _s(ds.getValueAt(i, 'Src'))})
	return out


def assetCounts(assetId, months=12):
	ds = system.db.runPrepQuery(
		"SELECT COUNT(*) AS N, SUM(ISNULL(x.Hrs, 0)) AS H FROM ("
		"SELECT h.WO_ID, (SELECT SUM(ISNULL(a.Quantity, 0)) FROM dbo.WO_N_Activity a WHERE a.WO_ID = h.WO_ID AND RTRIM(ISNULL(a.Trx_Type, '')) = 'L') AS Hrs "
		"FROM dbo.WO_N_Header h WHERE h.Asset_ID = ? AND h.Request_Start_Date >= DATEADD(MONTH, -%d, GETDATE()) AND RTRIM(ISNULL(h.Status, '')) <> 'D' "
		"UNION ALL SELECT c.WO_ID, (SELECT SUM(ISNULL(a.Quantity, 0)) FROM dbo.WO_C_Activity a WHERE a.WO_ID = c.WO_ID AND RTRIM(ISNULL(a.Trx_Type, '')) = 'L') "
		"FROM dbo.WO_C_header c WHERE c.Asset_ID = ? AND c.Request_Start_Date >= DATEADD(MONTH, -%d, GETDATE())) x" % (int(months), int(months)),
		[int(assetId), int(assetId)], _DB)
	return _i(ds.getValueAt(0, 'N')), _f(ds.getValueAt(0, 'H'))


def locationOpen(locId, excludeWoId=0, top=10):
	ds = system.db.runPrepQuery(
		"SELECT TOP %d RTRIM(ISNULL(h.Short_WO_Id, '')) AS Sid, RTRIM(ISNULL(h.WO_Title, '')) AS Title, RTRIM(ISNULL(h.Status, '')) AS Status, "
		"h.Request_Start_Date AS D, RTRIM(ISNULL(a.Short_asset_Id, '')) AS Asset FROM dbo.WO_N_Header h LEFT JOIN dbo.Asset a ON a.Asset_ID = h.Asset_ID "
		"WHERE h.Location_Id = ? AND h.WO_ID <> ? AND RTRIM(ISNULL(h.Status, '')) NOT IN ('C', 'D') ORDER BY h.Request_Start_Date" % int(top),
		[int(locId), int(excludeWoId)], _DB)
	out = []
	for i in range(ds.getRowCount()):
		d = ds.getValueAt(i, 'D')
		out.append({'sid': _s(ds.getValueAt(i, 'Sid')), 'title': _s(ds.getValueAt(i, 'Title')), 'status': _s(ds.getValueAt(i, 'Status')),
			'date': workmate.planner.iso(d) if d is not None else '', 'asset': _s(ds.getValueAt(i, 'Asset'))})
	return out


def assetParts(assetId, months=24, top=10):
	ds = system.db.runPrepQuery(
		"SELECT TOP %d RTRIM(ISNULL(p.Short_Part_ID, '')) AS PartNo, RTRIM(ISNULL(p.Part_Title, '')) AS Title, COUNT(*) AS Times, "
		"SUM(ISNULL(x.Qty, 0)) AS Qty, MAX(x.D) AS LastD FROM ("
		"SELECT a.Part_Id, a.Quantity AS Qty, a.Activity_Date AS D FROM dbo.WO_N_Activity a JOIN dbo.WO_N_Header h ON h.WO_ID = a.WO_ID "
		"WHERE RTRIM(ISNULL(a.Trx_Type, '')) = 'P' AND h.Asset_ID = ? AND a.Activity_Date >= DATEADD(MONTH, -%d, GETDATE()) "
		"UNION ALL SELECT a.Part_Id, a.Quantity, a.Activity_Date FROM dbo.WO_C_Activity a JOIN dbo.WO_C_header c ON c.WO_ID = a.WO_ID "
		"WHERE RTRIM(ISNULL(a.Trx_Type, '')) = 'P' AND c.Asset_ID = ? AND a.Activity_Date >= DATEADD(MONTH, -%d, GETDATE())) x "
		"JOIN dbo.Parts p ON p.Part_ID = x.Part_Id GROUP BY RTRIM(ISNULL(p.Short_Part_ID, '')), RTRIM(ISNULL(p.Part_Title, '')) "
		"ORDER BY COUNT(*) DESC, SUM(ISNULL(x.Qty, 0)) DESC" % (int(top), int(months), int(months)), [int(assetId), int(assetId)], _DB)
	out = []
	for i in range(ds.getRowCount()):
		d = ds.getValueAt(i, 'LastD')
		out.append({'partNo': _s(ds.getValueAt(i, 'PartNo')), 'title': _s(ds.getValueAt(i, 'Title')), 'times': _i(ds.getValueAt(i, 'Times')),
			'qty': _f(ds.getValueAt(i, 'Qty')), 'last': workmate.planner.iso(d) if d is not None else ''})
	return out


def _woLine(w):
	st = workmate.planner.STATUS_TITLES.get(w['status'], w['status'])
	return '- **%s** %s - %s (%s%s)' % (_fmtDate(w['date']) if w['date'] else '?', '`%s`' % w['sid'], w['title'][:50], st,
		(', %s logged' % _fmtH(w['hours'])) if w.get('hours', 0) > 0 else '')


def _ctxOrNone():
	c = _CUR.get('wo')
	if not c:
		return None, 'Select a work order first (or name one).'
	return c, ''


def _assetLastReply():
	c, err = _ctxOrNone()
	if err:
		return err
	if c['assetId'] <= 0:
		return '`%s` has no asset on it, so there is nothing to look back on.' % c['sid']
	rows = assetWOs(c['assetId'], c['woId'], 5)
	if not rows:
		return 'No other work orders on **%s** (%s) in the records.' % (c['asset'], c['assetTitle'])
	last = rows[0]
	lines = ['Last work on **%s** (%s): %s ago - `%s` %s (%s%s).' % (c['asset'], c['assetTitle'], _ago(last['date']), last['sid'], last['title'][:50],
		workmate.planner.STATUS_TITLES.get(last['status'], last['status']), (', %s logged' % _fmtH(last['hours'])) if last['hours'] > 0 else '')]
	if len(rows) > 1:
		lines.append('Before that:')
		lines += [_woLine(w) for w in rows[1:]]
	return '\n'.join(lines)


def _assetHistoryReply():
	c, err = _ctxOrNone()
	if err:
		return err
	if c['assetId'] <= 0:
		return '`%s` has no asset on it.' % c['sid']
	n12, h12 = assetCounts(c['assetId'], 12)
	n24, h24 = assetCounts(c['assetId'], 24)
	rows = assetWOs(c['assetId'], c['woId'], 5)
	lines = ['**%s** (%s): %d work order%s in the last 12 months (%s logged), %d in 24 months (%s).' % (
		c['asset'], c['assetTitle'], n12, '' if n12 == 1 else 's', _fmtH(h12), n24, _fmtH(h24))]
	if rows:
		lines.append('Most recent:')
		lines += [_woLine(w) for w in rows]
	try:
		h = workmate.planner_ai.historyFor(c['woId'])
		if h.get('ok') and h.get('source'):
			lines.append('')
			lines.append('For jobs like `%s`: %s' % (c['sid'], h['text']))
	except:
		pass
	return '\n'.join(lines)


def _locationOpenReply():
	c, err = _ctxOrNone()
	if err:
		return err
	if c['locId'] <= 0:
		return '`%s` has no location on it.' % c['sid']
	rows = locationOpen(c['locId'], c['woId'], 10)
	if not rows:
		return 'Nothing else open at **%s** (%s).' % (c['loc'], c['locTitle'])
	lines = ['Open work at **%s** (%s) besides `%s`:' % (c['loc'], c['locTitle'], c['sid'])]
	for w in rows:
		lines.append('- %s `%s` %s%s (%s)' % (_fmtDate(w['date']) if w['date'] else '?', w['sid'], w['title'][:45],
			(' on %s' % w['asset']) if w['asset'] else '', workmate.planner.STATUS_TITLES.get(w['status'], w['status'])))
	return '\n'.join(lines)


def _assetPartsReply():
	c, err = _ctxOrNone()
	if err:
		return err
	if c['assetId'] <= 0:
		return '`%s` has no asset on it.' % c['sid']
	rows = assetParts(c['assetId'], 24, 10)
	if not rows:
		return 'No parts booked against **%s** in the last 24 months.' % c['asset']
	lines = ['Parts used on **%s** (last 24 months):' % c['asset']]
	for p in rows:
		lines.append('- `%s` %s - %d time%s, qty %s, last %s' % (p['partNo'], p['title'][:40], p['times'], '' if p['times'] == 1 else 's',
			workmate.planner_ai._fmt(p['qty']), _fmtDate(p['last']) if p['last'] else '?'))
	return '\n'.join(lines)


def _thisWoReply():
	c, err = _ctxOrNone()
	if err:
		return err
	wo = workmate.planner.loadWO(c['woId'])
	lines = ['`%s` - %s' % (c['sid'], c['title'])]
	lines.append('%s, starts %s%s%s.' % (workmate.planner.STATUS_TITLES.get(wo['status'], wo['status']), _fmtDate(wo['start']),
		(', ends %s' % _fmtDate(wo['end'])) if wo['end'] and wo['end'] != wo['start'] else '',
		' - PINNED by the planner' if wo.get('pinned') else (' - PM the engine owns' if wo.get('engineOwned') else '')))
	if c['asset']:
		lines.append('Asset **%s** %s%s.' % (c['asset'], c['assetTitle'], (' at %s %s' % (c['loc'], c['locTitle'])) if c['loc'] else ''))
	lines.append('Hours: %s.%s' % (_fmtH(wo['estimate']) if wo['estimate'] > 0 else 'no estimate yet',
		(' Planned labour on %d date%s.' % (len(wo['labourDates']), '' if len(wo['labourDates']) == 1 else 's')) if wo['labourDates'] else ''))
	try:
		h = workmate.planner_ai.historyFor(c['woId'])
		if h.get('ok'):
			lines.append(h['text'])
	except:
		pass
	lines.append('Ask: **last work on this asset**, **open work here**, **parts used**, **move this to thursday**.')
	return '\n'.join(lines)


def _ago(isoDay):
	d = workmate.planner.civilDays(isoDay, workmate.planner.iso(system.date.now()))
	if d is None:
		return '?'
	if d < 0:
		return 'in %d days' % (-d)
	if d == 0:
		return 'today'
	if d < 14:
		return '%d day%s' % (d, '' if d == 1 else 's')
	if d < 90:
		return '%d weeks' % (d // 7)
	if d < 730:
		return '%d months' % (d // 30)
	return '%d years' % (d // 365)


def commands(hasWo=False):
	"""PURE. The '/' menu: [{'cmd', 'text', 'needsWo'}]."""
	out = [
		{'cmd': 'plan next week', 'text': 'pull work forward into next week\'s spare hours', 'needsWo': False},
		{'cmd': 'plan 4 weeks', 'text': 'the four-week fill plan', 'needsWo': False},
		{'cmd': 'who is over next week', 'text': 'people over / under their weekly hours', 'needsWo': False},
		{'cmd': 'proposal', 'text': 'last night\'s proposal (and what autopilot applied)', 'needsWo': False},
		{'cmd': 'pairs', 'text': 'who usually works together', 'needsWo': False},
		{'cmd': 'last work on this asset', 'text': 'most recent work orders on the selected asset', 'needsWo': True},
		{'cmd': 'history of this asset', 'text': 'counts, hours and usual crew for the asset', 'needsWo': True},
		{'cmd': 'open work here', 'text': 'everything else open at this location', 'needsWo': True},
		{'cmd': 'parts used on this asset', 'text': 'parts booked against the asset, last 24 months', 'needsWo': True},
		{'cmd': 'who usually does this', 'text': 'median hours + usual people for jobs like this', 'needsWo': True},
		{'cmd': 'about this WO', 'text': 'status, dates, asset, hours, people', 'needsWo': True},
		{'cmd': 'move this to ', 'text': 'thursday / 18 sep / next week / 2026-09-18', 'needsWo': True},
		{'cmd': 'estimate this ', 'text': 'e.g. estimate this 4h', 'needsWo': True},
		{'cmd': 'unpin this', 'text': 'hand a pinned PM back to the release engine', 'needsWo': True},
		{'cmd': 'undo', 'text': 'put back the last thing I changed', 'needsWo': False},
		{'cmd': 'help', 'text': 'everything I understand', 'needsWo': False},
	]
	return [c for c in out if hasWo or not c['needsWo']]


def followUps(intent, pending=None, hadPlan=False, wo=None, estimateHint=None):
	"""PURE. 2-5 next prompts for the reply just given."""
	if pending:
		return ['yes', 'no']
	hasWo = bool(wo)
	sidTxt = 'this'
	if intent == 'plan':
		return (['apply all', 'apply 1'] if hadPlan else []) + ['who is over next week', 'proposal']
	if intent == 'apply':
		return ['undo', 'plan next week', 'proposal']
	if intent == 'proposal':
		return (['apply all'] if hadPlan else []) + ['plan next week', 'who is over next week']
	if intent in ('move', 'estimate', 'unpin', 'undo'):
		return ['undo', 'about this WO', 'who usually does this'] if hasWo else ['undo', 'plan next week']
	if intent == 'asset_last':
		return ['history of this asset', 'parts used on this asset', 'open work here', 'who usually does this']
	if intent == 'asset_history':
		return ['last work on this asset', 'parts used on this asset', 'who usually does this']
	if intent == 'location_open':
		return ['last work on this asset', 'about this WO', 'plan next week']
	if intent == 'asset_parts':
		return ['history of this asset', 'last work on this asset', 'about this WO']
	if intent in ('this_wo', 'history'):
		out = []
		if estimateHint:
			out.append('estimate this %sh' % estimateHint)
		out += ['last work on this asset', 'open work here', 'move this to next week']
		return out[:4]
	if intent == 'flags':
		return ['plan next week', 'pairs', 'proposal']
	if intent == 'pairs':
		return ['who is over next week', 'plan next week']
	if hasWo:
		return ['about this WO', 'last work on this asset', 'who usually does this', 'move this to thursday']
	return ['plan next week', 'who is over next week', 'proposal', 'help']


def answer(text, session=None, ctx=None):
	"""-> {'reply': markdown, 'intent': str, 'ok': bool}. Never raises.
	ctx (1.1.0): {'sid','userId','userName','woId'} from the planner panel."""
	_CUR.clear()
	try:
		if ctx:
			for k in ('sid', 'userId', 'userName'):
				if ctx.get(k):
					_CUR[k] = ctx[k]
			if _i(ctx.get('woId')) > 0:
				try:
					c = woContext(_i(ctx.get('woId')))
					if c:
						_CUR['wo'] = c
						_CUR['woSid'] = c['sid']
				except:
					pass
	except:
		pass
	r = _answer(text, session)
	try:
		c = _ctx(session)
		hint = None
		if _CUR.get('wo') and r.get('intent') in ('this_wo', 'history'):
			try:
				h = workmate.planner_ai.historyFor(_CUR['wo']['woId'])
				if h.get('ok') and h.get('medianHours', 0) > 0:
					w = workmate.planner.loadWO(_CUR['wo']['woId'])
					if w and w['estimate'] <= 0:
						hint = workmate.planner_ai._fmt(h['medianHours'])
			except:
				hint = None
		r['next'] = followUps(r.get('intent'), c.get('pending'), bool(c.get('plan')), _CUR.get('wo'), hint)
		r['hasWo'] = bool(_CUR.get('wo'))
	except:
		r['next'] = []
	return r


def _answer(text, session=None):
	try:
		p = parse(text)
		intent = p['intent']
		c = _ctx(session)
		if intent == 'empty':
			return {'reply': _help(), 'intent': 'help', 'ok': True}
		if intent == 'confirm':
			pend = c.get('pending')
			c['pending'] = None
			if not pend:
				return {'reply': 'Nothing pending to confirm. Say **help** for what I can do.', 'intent': 'confirm', 'ok': True}
			if _actor(session) <= 0:
				return {'reply': 'Your login has no Workmate identity, so I cannot write anything - see User Mapping.', 'intent': 'confirm', 'ok': False}
			if pend['kind'] == 'move':
				reply = _doMove(session, pend)
			elif pend['kind'] == 'estimate':
				reply = _doEstimate(session, pend)
			elif pend['kind'] == 'apply':
				reply = _doApply(session, pend['moves'])
			else:
				reply = 'Nothing pending.'
			_log('confirm %s by %s: %s' % (pend['kind'], _actor(session), reply[:120]))
			return {'reply': reply, 'intent': pend['kind'], 'ok': True}
		if intent == 'cancel':
			had = c.get('pending') is not None
			c['pending'] = None
			return {'reply': 'No worries - nothing changed.' if had else 'Nothing was pending.', 'intent': 'cancel', 'ok': True}
		c['pending'] = None
		if intent == 'help' or intent == 'unknown':
			reply = _help() if intent == 'help' else ('Not sure what you mean. ' + _help())
		elif intent == 'plan':
			reply = _planReply(session, p['weeks'])
		elif intent == 'apply':
			reply = _applyReply(session, p['which'])
		elif intent == 'move':
			reply = _moveReply(session, p['sid'], p['dateExpr'])
		elif intent == 'estimate':
			reply = _estimateReply(session, p['sid'], p['hours'])
		elif intent == 'history':
			reply = _historyReply(session, p['sid'])
		elif intent == 'flags':
			reply = _flagsReply(session)
		elif intent == 'pairs':
			reply = _pairsReply(session)
		elif intent == 'proposal':
			reply = _proposalReply(session)
		elif intent == 'unpin':
			reply = _unpinReply(session, p['sid'])
		elif intent == 'undo':
			reply = _undoReply(session)
		elif intent == 'asset_last':
			reply = _assetLastReply()
		elif intent == 'asset_history':
			reply = _assetHistoryReply()
		elif intent == 'location_open':
			reply = _locationOpenReply()
		elif intent == 'asset_parts':
			reply = _assetPartsReply()
		elif intent == 'this_wo':
			reply = _thisWoReply()
		else:
			reply = _help()
		_log('%s: %s' % (intent, _s(text)[:80]))
		return {'reply': reply, 'intent': intent, 'ok': True}
	except:
		msg = _err()
		_log('answer crashed: ' + msg, 'error')
		return {'reply': 'Sorry - the planner assistant hit a snag: %s' % msg[:200], 'intent': 'error', 'ok': False}