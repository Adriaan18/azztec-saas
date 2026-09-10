# =============================================================================
# workmate_planner_test_code_v1_0_0.py
# Version:     1.0.0
# Target:      Project Library  workmate/planner_test
# Database:    TLSQL01_Workmate
# Author:      Adriaan
# Spec:        Workmate_Night_Shift_Standard_v1_0_0.md  +  P-PLN1 spec v1.1.0
#
# Purpose:
#   The Planner's Night Shift packs - Test_workmate_planner v1.6.0 rewritten
#   in the pack contract (fn(ctx) -> {'ok','detail','cleanupOk'}) so the
#   runner executes it unattended and the morning report reads it:
#     planner-pure      write:False   rules, dates, DST, token, chat parse,
#                                     planner_ai heuristics - no database
#     planner-read      write:False   rangeData shape, API routing, WebDev
#                                     HTTP smoke, planner_ai + chat on live data
#     planner-write-rb  write:True    move / pin / labour / capacity cycles
#                                     inside ONE rolled-back transaction each,
#                                     residue verified (cleanupOk) - skipped in
#                                     LIVE-SAFE like every write pack
#   Pairs with planner 1.3.1, planner_api 1.6.0, planner_ai 1.1.0,
#   planner_chat 1.0.0, pm_engine 2.5.0.
#
# Config: PLANNER_BASE_URL (System_Configuration) for the HTTP smoke -
#   default http://localhost:8088/system/webdev/MainSCADA_Timberlands/planner
#   (Dev: port 8089). PLANNER_TEST_USER_ID - the actor the rolled-back audit
#   rows carry (default 3).
#
# Changelog:
#   v1.0.0  Initial.
# =============================================================================

_VERSION = '1.0.0'
_DB = 'TLSQL01_Workmate'


def version():
	return _VERSION


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


def _cfg(key, default=''):
	return workmate.planner.configValue(key, default)


def _actor():
	try:
		return int(_cfg('PLANNER_TEST_USER_ID', '3'))
	except:
		return 3


def _chk(fails, name, cond, detail=''):
	if not cond:
		fails.append(name + ((' [' + str(detail)[:120] + ']') if detail != '' else ''))


def _res(fails, okDetail, cleanupOk=None):
	return {'ok': len(fails) == 0, 'detail': okDetail if not fails else '; '.join(fails)[:900], 'cleanupOk': cleanupOk}


def _skip(why):
	return {'ok': None, 'detail': 'SKIPPED - ' + why, 'cleanupOk': None}


# ---------------------------------------------------------------------------
# planner-pure
# ---------------------------------------------------------------------------

def t_versions(ctx):
	f = []
	P = workmate.planner
	_chk(f, 'planner', P.version() >= '1.3.1', P.version())
	_chk(f, 'planner_api', workmate.planner_api.version() >= '1.6.0', workmate.planner_api.version())
	_chk(f, 'planner_ai', workmate.planner_ai.version() >= '1.1.0', workmate.planner_ai.version())
	_chk(f, 'planner_chat', workmate.planner_chat.version() >= '1.0.0', workmate.planner_chat.version())
	_chk(f, 'pm_engine pin-aware', workmate.pm_engine.version() >= '2.5.0', workmate.pm_engine.version())
	_chk(f, 'DRY_RUN default True', P.DRY_RUN is True)
	return _res(f, 'planner %s api %s ai %s chat %s engine %s' % (P.version(), workmate.planner_api.version(),
		workmate.planner_ai.version(), workmate.planner_chat.version(), workmate.pm_engine.version()))


def t_rules(ctx):
	f = []
	P = workmate.planner
	_chk(f, 'category', P.category('C', 'M') == 'DONE' and P.category('H', 'M') == 'PM' and P.category('R', 'N') == 'REQ' and P.category('A', 'N') == 'WO')
	_chk(f, 'engineOwned', P.engineOwned('H', 'M') and not P.engineOwned('V', 'M') and not P.engineOwned('A', 'N'))
	wo = {'id': 1, 'estimate': 6, 'resp': 7}
	lab = [{'woId': 1, 'userId': 12, 'hours': 4}, {'woId': 1, 'userId': 13, 'hours': 2.5}, {'woId': 2, 'userId': 12, 'hours': 9}]
	_chk(f, 'hoursFor labour', P.hoursFor(wo, lab) == (6.5, 'labour'))
	_chk(f, 'hoursFor estimate', P.hoursFor({'id': 3, 'estimate': 6, 'resp': 0}, lab) == (6.0, 'estimate'))
	_chk(f, 'hoursFor unknown', P.hoursFor({'id': 3, 'estimate': 0}, []) == (0.0, ''))
	_chk(f, 'assignedFor', P.assignedFor(wo, lab) == [12, 13, 7])
	_chk(f, 'workerLoad', P.workerLoad([{'id': 1, 'hrs': 6.5, 'resp': 7}, {'id': 3, 'hrs': 5, 'resp': 7}, {'id': 4, 'hrs': 3, 'resp': 0}], lab) == {12: 13.0, 13: 2.5, 7: 5.0, 0: 3.0})
	return _res(f, 'category / engineOwned / hoursFor / assignedFor / workerLoad')


def t_workers(ctx):
	f = []
	P = workmate.planner
	rows = [
		{'userId': 7, 'shortId': 'KF', 'name': 'Ken Fisher', 'skillId': 1, 'sysId': 1, 'uomId': 9, 'skillTitle': 'Fitter', 'hrsPerWeek': 0, 'supplierId': 11, 'supplierShort': 'TM-MAINT', 'supplierName': 'M', 'internalDept': ''},
		{'userId': 12, 'shortId': 'PM', 'name': 'Pam McDonald', 'skillId': 1, 'sysId': 2, 'uomId': 9, 'skillTitle': 'Fitter', 'hrsPerWeek': 60, 'supplierId': 11, 'supplierShort': 'TM-MAINT', 'supplierName': 'M', 'internalDept': ''},
		{'userId': 12, 'shortId': 'PM', 'name': 'Pam McDonald', 'skillId': 2, 'sysId': 3, 'uomId': 9, 'skillTitle': 'Welder', 'hrsPerWeek': 10, 'supplierId': 11, 'supplierShort': 'TM-MAINT', 'supplierName': 'M', 'internalDept': ''},
		{'userId': 50, 'shortId': 'LH', 'name': 'Liaanna Hay', 'skillId': 3, 'sysId': 4, 'uomId': 9, 'skillTitle': 'Elec', 'hrsPerWeek': 40, 'supplierId': 10, 'supplierShort': 'TM-ELEC', 'supplierName': 'E', 'internalDept': '1'},
		{'userId': 88, 'shortId': 'EXT-AMET', 'name': 'Aiden - MetalForm', 'skillId': 4, 'sysId': 5, 'uomId': 9, 'skillTitle': 'Welder', 'hrsPerWeek': 0, 'supplierId': 5565, 'supplierShort': 'METALFORM', 'supplierName': 'MF', 'internalDept': ''}]
	ws, teams = P.buildWorkers(rows)
	byid = dict([(w['id'], w) for w in ws])
	_chk(f, 'skills sum', byid[12]['hrsPerWeek'] == 70.0 and len(byid[12]['skills']) == 2 and byid[12]['skills'][0]['sysId'] == 2)
	_chk(f, 'modal supplier internal', byid[7]['internal'] and byid[12]['internal'])
	_chk(f, 'Internal_Dept internal', byid[50]['internal'])
	_chk(f, 'contractor', not byid[88]['internal'] and ws[-1]['id'] == 88)
	_chk(f, 'teams order', [t['short'] for t in teams] == ['TM-ELEC', 'TM-MAINT', 'METALFORM'])
	_chk(f, 'initials', byid[88]['initials'] == 'AMET' and byid[7]['initials'] == 'KF')
	wos = [{'id': 1, 'start': '2026-09-03', 'hrs': 6.0}, {'id': 2, 'start': '2026-09-17', 'hrs': 0.0}, {'id': 3, 'start': '2026-09-18', 'hrs': 4.0}]
	weeks = P.capacityByWeek(wos, ws, '2026-08-31', '2026-10-04')
	_chk(f, 'capacity weeks', [w['weekStart'] for w in weeks] == ['2026-08-31', '2026-09-07', '2026-09-14', '2026-09-21', '2026-09-28'])
	_chk(f, 'capacity numbers', weeks[0]['planned'] == 6.0 and weeks[0]['capacity'] == 110.0 and weeks[2]['unknown'] == 1 and weeks[0]['pct'] == 5)
	_chk(f, 'capacity workerIds', P.capacityByWeek(wos, ws, '2026-08-31', '2026-10-04', workerIds=[12])[0]['capacity'] == 70.0)
	ww = P.workerWeeks([{'id': 1, 'start': '2026-09-03', 'hrs': 6.0, 'resp': 7}, {'id': 2, 'start': '2026-09-17', 'hrs': 4.0, 'resp': 0}],
		[{'woId': 2, 'userId': 12, 'hours': 4.0, 'date': '2026-09-18'}], [{'id': 7, 'hrsPerWeek': 40.0}, {'id': 12, 'hrsPerWeek': 20.0}], '2026-08-31', '2026-09-20')
	w7 = dict([(r['weekStart'], r) for r in ww['7']])
	_chk(f, 'workerWeeks under/empty', w7['2026-08-31']['flag'] == 'under' and w7['2026-09-07']['flag'] == 'empty')
	return _res(f, 'buildWorkers / teams / capacityByWeek / workerWeeks')


def t_moverules(ctx):
	f = []
	P = workmate.planner
	wo = {'id': 1, 'sid': 'WO-T', 'status': 'A', 'type': 'N', 'start': '2026-09-03', 'end': '2026-09-05', 'pinned': False, 'pinTable': True,
		'engineDate': '', 'subtaskDates': ['2026-09-03'], 'labourDates': [('2026-09-03', 2), ('2026-09-04', 1)], 'hasDetails': True}
	r = P.moveRules(wo, '2026-09-17', '2026-09-05')
	_chk(f, 'delta/end', r['ok'] and r['delta'] == 14 and r['newEnd'] == '2026-09-19')
	_chk(f, 'confirm SPAN+LABOUR', r['confirm'] and sorted([x['code'] for x in r['reasons']]) == ['LABOUR_MULTI', 'SPAN'])
	w1 = dict(wo, end='', labourDates=[])
	_chk(f, 'no confirm', not P.moveRules(w1, '2026-09-17', '2026-09-05')['confirm'])
	_chk(f, 'PAST', P.moveRules(w1, '2026-09-01', '2026-09-05')['reasons'][0]['code'] == 'PAST')
	_chk(f, 'ACTIVE', P.moveRules(dict(w1, status='V'), '2026-09-17', '2026-09-05')['reasons'][0]['code'] == 'ACTIVE')
	_chk(f, 'LOCKED', P.moveRules(dict(w1, status='C'), '2026-09-17', '2026-09-05')['code'] == 'LOCKED_STATUS')
	_chk(f, 'NO_CHANGE/BAD_DATE', P.moveRules(w1, '2026-09-03', '2026-09-05')['code'] == 'NO_CHANGE' and P.moveRules(w1, 'nope', '2026-09-05')['code'] == 'BAD_DATE')
	pm = dict(w1, type='M', status='H', pinTable=False)
	_chk(f, 'PM no table', P.moveRules(pm, '2026-09-14', '2026-09-05')['code'] == 'ENGINE_OWNED')
	r = P.moveRules(dict(pm, pinTable=True), '2026-09-14', '2026-09-05')
	_chk(f, 'PM pins', r['ok'] and r['willPin'] and r['pinnedAfter'])
	r = P.moveRules(dict(pm, pinTable=True, pinned=True, start='2026-09-14', engineDate='2026-09-03'), '2026-09-03', '2026-09-05')
	_chk(f, 'PM return home unpins', r['ok'] and r['willUnpin'] and not r['pinnedAfter'])
	_chk(f, 'estimateRules', P.estimateRules(wo, '4.5')['hours'] == 4.5 and P.estimateRules(wo, -1)['code'] == 'BAD_HOURS' and P.estimateRules(dict(wo, status='C'), 2)['code'] == 'LOCKED_STATUS')
	sk = {'sysId': 1, 'skillId': 1, 'supplierId': 11, 'uomId': 9, 'rate': 0, 'hrsPerWeek': 40, 'skillTitle': 'Fitter'}
	lw = {'sid': 'WO-T', 'status': 'A', 'start': '2026-09-17'}
	_chk(f, 'labourRules', P.labourRules(lw, 'Pam', 'Y', sk, 4, '')['ok'] and P.labourRules(dict(lw, status='C'), 'Pam', 'Y', sk, 4, '')['code'] == 'LOCKED_STATUS'
		and P.labourRules(lw, None, '', sk, 4, '')['code'] == 'NO_USER' and P.labourRules(lw, 'X', 'Y', None, 4, '')['code'] == 'NO_SKILL' and P.labourRules(lw, 'X', 'Y', sk, 0, '')['code'] == 'BAD_HOURS')
	return _res(f, 'moveRules incl. pin cases / estimateRules / labourRules')


def t_dst(ctx):
	f = []
	P = workmate.planner
	_chk(f, 'civilDays +12', P.civilDays('2026-09-17', '2026-09-29') == 12)
	_chk(f, 'civilDays -12', P.civilDays('2026-09-29', '2026-09-17') == -12)
	_chk(f, 'civilDays year end', P.civilDays('2026-12-30', '2027-01-02') == 3)
	w = {'sid': 'WO-DST', 'status': 'A', 'type': 'N', 'start': '2026-09-29', 'end': '', 'pinned': False, 'pinTable': False, 'engineDate': '', 'subtaskDates': [], 'labourDates': []}
	r = P.moveRules(w, '2026-09-17', '2026-09-05')
	_chk(f, 'moveRules across DST', r['ok'] and r['delta'] == -12 and r['newStart'] == '2026-09-17')
	_chk(f, 'weekStart Sunday', P.iso(P.weekStart(system.date.parse('2026-09-06', 'yyyy-MM-dd'))) == '2026-08-31')
	_chk(f, 'timeOf', P.timeOf(system.date.parse('2026-09-06 10:00:00', 'yyyy-MM-dd HH:mm:ss')) == '10:00' and P.timeOf(system.date.parse('2026-09-07', 'yyyy-MM-dd')) == '')
	a = system.date.parse('2026-09-17', 'yyyy-MM-dd')
	b = system.date.parse('2026-09-29', 'yyyy-MM-dd')
	return _res(f, 'civil days DST-immune (gateway daysBetween says 17->29=%s, 29->17=%s)' % (system.date.daysBetween(a, b), system.date.daysBetween(b, a)))


def t_token(ctx):
	f = []
	A = workmate.planner_api
	t = A.token('abc-session', 3)
	_chk(f, 'len', len(t) == 64)
	_chk(f, 'verify', A.verifyToken('abc-session', 3, t))
	_chk(f, 'other user', not A.verifyToken('abc-session', 4, t))
	_chk(f, 'other session', not A.verifyToken('xyz', 3, t))
	_chk(f, 'tamper', not A.verifyToken('abc-session', 3, t[:-1] + ('0' if t[-1] != '0' else '1')))
	_chk(f, 'empty', A.token('', 3) == '' and A.token('abc', 0) == '')
	act = A.actorFor(None, {'remainingPath': '/x', 'params': {}, 'data': {'sid': 'abc-session', 'uid': 3, 'tok': t}})
	_chk(f, 'actor via token', act['userId'] == 3 and act['via'] == 'token')
	c, b, k = A._writeResult({'ok': False, 'code': 'STALE', 'message': 'x'})
	_chk(f, 'STALE 409', c == 409)
	c, b, k = A._writeResult({'ok': False, 'code': 'CONFIRM', 'message': 'x', 'preview': {}})
	_chk(f, 'CONFIRM 200', c == 200 and b['ok'] is False)
	return _res(f, 'HMAC actor token + code map (secret: %s)' % A._secret()[1])


def t_chat_parse(ctx):
	f = []
	C = workmate.planner_chat
	td = '2026-09-05'
	_chk(f, 'dates', C.parseDateExpr('2026-09-18', td) == '2026-09-18' and C.parseDateExpr('18 sep', td) == '2026-09-18' and C.parseDateExpr('18/09', td) == '2026-09-18' and C.parseDateExpr('tomorrow', td) == '2026-09-06' and C.parseDateExpr('junk', td) == '')
	_chk(f, 'weekday', C.parseDateExpr('thursday', td) == '2026-09-10' and C.parseDateExpr('next week', td, 3) == '2026-09-10')
	pr = C.parse
	_chk(f, 'plan', pr('plan next week') == {'intent': 'plan', 'weeks': 2} and pr('plan 6 weeks')['weeks'] == 6)
	_chk(f, 'apply', pr('apply all')['which'] == 'all' and pr('apply 1,3')['which'] == [1, 3])
	_chk(f, 'move', pr('move WO-260902-012 to thursday') == {'intent': 'move', 'sid': 'WO-260902-012', 'dateExpr': 'thursday'})
	_chk(f, 'estimate', pr('estimate WO-260902-012 4h') == {'intent': 'estimate', 'sid': 'WO-260902-012', 'hours': 4.0})
	_chk(f, 'others', pr('who usually does K-KPL-04-0007')['intent'] == 'history' and pr('who is over next week')['intent'] == 'flags' and pr('pairs')['intent'] == 'pairs'
		and pr('unpin K-KGR-03-0002')['intent'] == 'unpin' and pr('undo')['intent'] == 'undo' and pr('yes')['intent'] == 'confirm' and pr('no')['intent'] == 'cancel' and pr('blah')['intent'] == 'unknown')
	return _res(f, 'parse + date expressions')


def t_ai_pure(ctx):
	f = []
	AI = workmate.planner_ai
	_chk(f, 'masterPrefix', AI.masterPrefix('K-KPL-04-0007') == 'K-KPL-04' and AI.masterPrefix('K-KGR-03-0002-S') == 'K-KGR-03' and AI.masterPrefix('WO-260902-012') == '' and AI.masterPrefix('K-260629-001') == '')
	_chk(f, 'median', AI.median([1, 3, 2]) == 2 and AI.median([1, 2, 3, 4]) == 2.5 and AI.median([]) == 0.0)
	hist = []
	def h(wid, sid, aid, uid, hrs, d):
		hist.append({'woId': wid, 'sid': sid, 'master': AI.masterPrefix(sid), 'assetId': aid, 'userId': uid, 'hours': hrs, 'date': d})
	h(1, 'K-KPL-04-0001', 50, 12, 4, '2026-01-10'); h(1, 'K-KPL-04-0001', 50, 13, 4, '2026-01-10')
	h(2, 'K-KPL-04-0002', 50, 12, 3, '2026-03-10'); h(2, 'K-KPL-04-0002', 50, 13, 5, '2026-03-10')
	h(3, 'K-KPL-04-0003', 50, 12, 40, '2026-05-10')
	h(4, 'WO-260101-001', 77, 7, 2, '2026-02-01'); h(5, 'WO-260101-002', 77, 7, 6, '2026-02-11')
	st = AI.historyStats(hist)
	m = st['byMaster'].get('K-KPL-04') or {}
	_chk(f, 'historyStats', m.get('n') == 3 and m.get('medianHours') == 8.0 and m.get('medianCrew') == 2 and m['people'][0]['userId'] == 12)
	wk = [{'id': 12, 'name': 'Pam', 'initials': 'PM'}, {'id': 13, 'name': 'Dave', 'initials': 'DC'}, {'id': 7, 'name': 'Ken', 'initials': 'KF'}]
	sg = AI.suggestFor({'sid': 'K-KPL-04-0009', 'assetId': 50}, st, wk)
	_chk(f, 'suggestFor', sg['source'] == 'master' and sg['medianHours'] == 8.0 and [p['name'] for p in sg['people']] == ['Pam', 'Dave'] and sg['confidence'] == 'high')
	_chk(f, 'pairs', AI.pairsWhoWorkTogether(hist, minCount=2) == [{'a': 12, 'b': 13, 'wos': 2}])
	wos = [{'id': 10, 'sid': 'K-A-01-0001', 'start': '2026-09-08', 'hrs': 180, 'pri': 'B', 'cat': 'PM', 'status': 'H', 'movable': True, 'engineOwned': True, 'pinned': False, 'title': 'big'},
		{'id': 11, 'sid': 'WO-1', 'start': '2026-09-16', 'hrs': 12, 'pri': 'A', 'cat': 'WO', 'status': 'A', 'movable': True, 'engineOwned': False, 'pinned': False, 'title': 'a'},
		{'id': 12, 'sid': 'WO-2', 'start': '2026-09-15', 'hrs': 15, 'pri': 'B', 'cat': 'WO', 'status': 'A', 'movable': True, 'engineOwned': False, 'pinned': False, 'title': 'b'},
		{'id': 13, 'sid': 'WO-3', 'start': '2026-09-22', 'hrs': 8, 'pri': 'B', 'cat': 'WO', 'status': 'A', 'movable': True, 'engineOwned': False, 'pinned': False, 'title': 'c'},
		{'id': 16, 'sid': 'WO-noest', 'start': '2026-09-09', 'hrs': 0, 'pri': 'A', 'cat': 'WO', 'status': 'A', 'movable': True, 'engineOwned': False, 'pinned': False, 'title': 'n'}]
	r = AI.fillWeek('2026-09-07', wos, [{'internal': True, 'hrsPerWeek': 200}], todayIso='2026-09-05')
	_chk(f, 'fillWeek', r['planned'] == 180 and r['spare'] == 20 and [x['sid'] for x in r['suggestions']] == ['WO-1', 'WO-3'] and r['suggestions'][0]['to'] == '2026-09-09' and r['fillAfter'] == 100)
	ph = AI.planHorizon('2026-09-07', 2, wos, [{'internal': True, 'hrsPerWeek': 200}], todayIso='2026-09-05')
	_chk(f, 'planHorizon', [x['sid'] for x in ph['moves']] == ['WO-1', 'WO-3'] and [n['sid'] for n in ph['needsEstimate']] == ['WO-noest'])
	mv = {'pins': False, 'cat': 'WO', 'pri': 'A', 'deltaDays': -7}
	_chk(f, 'autopilotGuard', AI.autopilotGuard(mv, 2) and not AI.autopilotGuard(dict(mv, pins=True), 2) and not AI.autopilotGuard(dict(mv, cat='PM'), 2) and not AI.autopilotGuard(dict(mv, pri='C'), 2) and not AI.autopilotGuard(dict(mv, deltaDays=-21), 2))
	ww = {'12': [{'weekStart': '2026-08-31', 'flag': 'over'}, {'weekStart': '2026-09-07', 'flag': 'under'}, {'weekStart': '2026-11-09', 'flag': 'over'}]}
	_chk(f, 'underOverWeeks', [x['weekStart'] for x in AI.underOverWeeks(ww, 12, '2026-09-05', 8)] == ['2026-08-31', '2026-09-07'])
	return _res(f, 'masterPrefix / stats / suggestFor / pairs / fillWeek / planHorizon / guard')


# ---------------------------------------------------------------------------
# planner-read
# ---------------------------------------------------------------------------

def t_range(ctx):
	f = []
	P = workmate.planner
	today = system.date.now()
	ws = P.weekStart(today)
	fromIso = P.iso(ws)
	toIso = P.iso(system.date.addDays(ws, 6))
	t0 = system.date.now().getTime()
	d = P.rangeData(fromIso, toIso)
	ms = system.date.now().getTime() - t0
	ctx['fromIso'] = fromIso
	ctx['toIso'] = toIso
	_chk(f, 'inside window', not [w['sid'] for w in d['wos'] if not (fromIso <= w['start'] <= toIso)])
	_chk(f, 'cats', set([w['cat'] for w in d['wos']]) <= set(['WO', 'PM', 'REQ', 'DONE']))
	_chk(f, 'no cancelled', not [w for w in d['wos'] if w['status'] == 'D'])
	_chk(f, 'hours sane', not [w for w in d['wos'] if w['hrs'] < 0 or (w['hrs'] == 0 and w['hrsSrc'] != '')])
	_chk(f, 'locked only engine-owned w/o table', not [w for w in d['wos'] if w['locked'] and not w['engineOwned']])
	_chk(f, 'workers', len(d['workers']) > 0 and not [w for w in d['workers'] if not w['skills'] or not w['initials']])
	_chk(f, 'internal team', [t for t in d['teams'] if t['internal']])
	_chk(f, 'one week', len(d['weeks']) == 1)
	_chk(f, 'load keys str', not [k for k in d['load'].keys() if not isinstance(k, basestring)])
	_chk(f, 'counts', d['counts']['total'] == len(d['wos']))
	_chk(f, 'workerWeeks + uom', isinstance(d.get('workerWeeks'), dict) and d.get('uomHours') is not None)
	try:
		P.rangeData('2026-09-10', '2026-09-01')
		_chk(f, 'bad window raises', False)
	except:
		pass
	return _res(f, '%s..%s rows=%d labour=%d workers=%d pinTable=%s in %d ms' % (fromIso, toIso, len(d['wos']), len(d['labour']), len(d['workers']), d['pinTable'], ms))


def t_api_routes(ctx):
	f = []
	A = workmate.planner_api
	c, b, k = A.route({'remainingPath': '/health', 'params': {}}, 'GET')
	_chk(f, '/health', c == 200 and b.get('ok') and b.get('api') == A.version())
	c, b, k = A.route({'remainingPath': '/range', 'params': {'from': '2026-09-10', 'to': '2026-09-01', 'sid': 'bogus-sid'}}, 'GET')
	if A.gateEnabled():
		_chk(f, 'bogus sid 401', c == 401)
	else:
		_chk(f, 'bad window 400 (gate off)', c == 400)
	c, b, k = A._range({'remainingPath': '/range', 'params': {'from': ctx.get('fromIso', '2026-08-31'), 'to': ctx.get('toIso', '2026-09-06')}}, None)
	_chk(f, '_range payload', c == 200 and b.get('ok') and 'ms' in b)
	c, b, k = A._move({'remainingPath': '/move', 'params': {}, 'data': {'woId': 0}}, None)
	_chk(f, '_move 400', c == 400)
	c, b, k = A._estimate({'remainingPath': '/estimate', 'params': {}, 'data': {'woId': 1}}, None)
	_chk(f, '_estimate 400', c == 400)
	c, b, k = A._clientDiag({'remainingPath': '/_diag', 'params': {}, 'data': {'sid': ''}}, None)
	_chk(f, '_diag 400', c == 400)
	c, b, k = A.route({'remainingPath': '/ui', 'params': {}}, 'GET')
	_chk(f, '/ui html', k == 'html' and c in (200, 503), (c, A.uiFiles()))
	ctx['uiFiles'] = A.uiFiles()
	return _res(f, 'routing ok; gate %s; ui files %s' % ('on' if A.gateEnabled() else 'OFF', ', '.join(A.uiFiles()[-2:]) or 'none'))


def t_http(ctx):
	f = []
	base = _cfg('PLANNER_BASE_URL', 'http://localhost:8088/system/webdev/MainSCADA_Timberlands/planner')
	try:
		client = system.net.httpClient(timeout=8000)
		r = client.get(base + '/health')
	except:
		return _skip('WebDev not reachable at %s (%s)' % (base, _err()[:80]))
	_chk(f, 'GET /health 200', r.statusCode == 200, r.statusCode)
	if r.statusCode == 402:
		return _res(f, '')
	try:
		j = r.json
		_chk(f, '/health json', j.get('ok') and j.get('api') == workmate.planner_api.version())
	except:
		_chk(f, '/health json', False, _err())
	r2 = client.get(base + '/range?from=2026-08-31&to=2026-09-06&sid=bogus')
	_chk(f, 'bogus sid 401', r2.statusCode == (401 if workmate.planner_api.gateEnabled() else 200), r2.statusCode)
	r3 = client.post(base + '/move', data=system.util.jsonEncode({'sid': 'bogus', 'woId': 1, 'toIso': '2026-09-17'}), headers={'Content-Type': 'application/json'})
	_chk(f, 'POST /move bogus', r3.statusCode in (401, 403, 404, 422), r3.statusCode)
	r4 = client.get(base + '/ui')
	_chk(f, 'GET /ui', r4.statusCode in (200, 503), r4.statusCode)
	return _res(f, '%s health/range/move/ui answered as expected' % base)


def t_ai_live(ctx):
	f = []
	AI = workmate.planner_ai
	rows = AI.fetchHistory()
	st = AI.historyStats(rows)
	fromIso = ctx.get('fromIso') or workmate.planner.iso(system.date.now())
	t0 = system.date.now().getTime()
	sug = AI.suggest(fromIso, 4, 2, None, 0)
	ms = system.date.now().getTime() - t0
	_chk(f, 'plan weeks', len(sug['plan']['weeks']) == 4)
	_chk(f, 'plan shape', 'moves' in sug['plan'] and 'needsEstimate' in sug['plan'] and 'flags' in sug and 'pairs' in sug)
	ctx['aiSummary'] = 'history %d rows/%d jobs; plan: %d moves, %d need estimate, %d flagged, %d pairs, %d ms' % (
		st['rows'], st['wos'], len(sug['plan']['moves']), len(sug['plan']['needsEstimate']), len(sug['flags']), len(sug['pairs']), ms)
	pmc = system.db.runPrepQuery("SELECT TOP 1 WO_ID FROM dbo.WO_N_Header WHERE RTRIM(ISNULL(WO_Type_Flag, 'N')) = 'M' AND RTRIM(ISNULL(Status, '')) NOT IN ('C', 'D') ORDER BY Request_Start_Date", [], _DB)
	if pmc.getRowCount():
		hf = AI.historyFor(int(pmc.getValueAt(0, 'WO_ID')))
		_chk(f, 'historyFor', hf.get('ok') and 'text' in hf)
	return _res(f, ctx['aiSummary'])


def t_chat_live(ctx):
	f = []
	C = workmate.planner_chat
	r = C.answer('help')
	_chk(f, 'help', r['ok'] and 'plan next week' in r['reply'])
	r = C.answer('plan next week')
	_chk(f, 'plan', r['ok'] and r['intent'] == 'plan' and 'Plan from' in r['reply'])
	r = C.answer('who is over next week')
	_chk(f, 'flags', r['ok'] and r['intent'] == 'flags')
	r = C.answer('yes')
	_chk(f, 'stray yes harmless', 'Nothing pending' in r['reply'])
	C.resetContext()
	return _res(f, 'help / plan / flags answered read-only')


# ---------------------------------------------------------------------------
# planner-write-rb  (rolled back)
# ---------------------------------------------------------------------------

def t_rb_move(ctx):
	f = []
	P = workmate.planner
	actor = _actor()
	cand = system.db.runPrepQuery(
		"SELECT TOP 1 h.WO_ID, RTRIM(h.Short_WO_Id) AS Sid, h.Request_Start_Date, h.Request_End_Date, ISNULL(h.Week_No, 0) AS Week_No "
		"FROM dbo.WO_N_Header h JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID "
		"WHERE RTRIM(ISNULL(h.Status, '')) NOT IN ('C', 'D', 'V') AND RTRIM(ISNULL(h.WO_Type_Flag, 'N')) <> 'M' "
		"AND h.Request_Start_Date IS NOT NULL ORDER BY h.Request_Start_Date DESC", [], _DB)
	if cand.getRowCount() == 0:
		return _skip('no movable non-PM WO')
	woId = int(cand.getValueAt(0, 'WO_ID'))
	sid = str(cand.getValueAt(0, 'Sid'))
	origStart = cand.getValueAt(0, 'Request_Start_Date')
	origIso = system.date.format(origStart, 'yyyy-MM-dd')
	toIso = system.date.format(system.date.addDays(origStart, 7), 'yyyy-MM-dd')
	evBefore = int(system.db.runScalarPrepQuery("SELECT COUNT(*) FROM dbo.WO_Event_History WHERE WO_ID = ?", [woId], _DB) or 0)
	estBefore = float(str(system.db.runScalarPrepQuery("SELECT ISNULL(Duration_In_Hours, 0) FROM dbo.WO_N_Details WHERE WO_ID = ?", [woId], _DB) or 0))
	plan = P.moveWO(woId, toIso, actor, expectStartIso=origIso, confirm=True)
	_chk(f, 'dry run plan', plan.get('ok') and plan.get('dryRun') and plan['newStart'] == toIso and plan['delta'] == 7)
	_chk(f, 'stale', P.moveWO(woId, toIso, actor, expectStartIso='1999-01-01', confirm=True).get('code') == 'STALE')
	tx = system.db.beginTransaction(_DB)
	try:
		res = P.moveWO(woId, toIso, actor, expectStartIso=origIso, confirm=True, dryRun=False, _tx=tx)
		_chk(f, 'real move', res.get('ok') and not res.get('dryRun'), res.get('message') or res.get('code'))
		inTx = system.db.runPrepQuery("SELECT Request_Start_Date, Week_No FROM dbo.WO_N_Header WHERE WO_ID = ?", [woId], _DB, tx)
		ns = inTx.getValueAt(0, 'Request_Start_Date')
		_chk(f, 'start +7 time kept', system.date.format(ns, 'yyyy-MM-dd') == toIso and system.date.format(ns, 'HH:mm') == system.date.format(origStart, 'HH:mm'))
		_chk(f, 'Week_No engine port', float(str(inTx.getValueAt(0, 'Week_No'))) == float(workmate.pm_engine.weekNo(ns)))
		evIn = int(system.db.runScalarPrepQuery("SELECT COUNT(*) FROM dbo.WO_Event_History WHERE WO_ID = ?", [woId], _DB, tx) or 0)
		_chk(f, 'audit rows', evIn == evBefore + int(res.get('events') or 0) and int(res.get('events') or 0) >= 2)
		est = P.setEstimate(woId, 4.5, actor, dryRun=False, _tx=tx)
		_chk(f, 'estimate', est.get('ok') and est.get('hours') == 4.5)
		und = P.undoMove(woId, origIso, actor, expectStartIso=toIso, dryRun=False, _tx=tx)
		_chk(f, 'undo', und.get('ok') and und['newStart'] == origIso)
	finally:
		system.db.rollbackTransaction(tx)
		system.db.closeTransaction(tx)
	after = system.db.runPrepQuery("SELECT Request_Start_Date FROM dbo.WO_N_Header WHERE WO_ID = ?", [woId], _DB)
	evAfter = int(system.db.runScalarPrepQuery("SELECT COUNT(*) FROM dbo.WO_Event_History WHERE WO_ID = ?", [woId], _DB) or 0)
	estAfter = float(str(system.db.runScalarPrepQuery("SELECT ISNULL(Duration_In_Hours, 0) FROM dbo.WO_N_Details WHERE WO_ID = ?", [woId], _DB) or 0))
	clean = (system.date.format(after.getValueAt(0, 'Request_Start_Date'), 'yyyy-MM-dd HH:mm') == system.date.format(origStart, 'yyyy-MM-dd HH:mm')
		and evAfter == evBefore and estAfter == estBefore)
	_chk(f, 'residue 0', clean, (evBefore, evAfter, estBefore, estAfter))
	return _res(f, '%s moved +7, estimated, undone inside a rolled-back tx; audit %d->%d' % (sid, evBefore, evAfter), clean)


def t_rb_pin(ctx):
	f = []
	P = workmate.planner
	actor = _actor()
	if not P.pinTableExists():
		return _skip('dbo.WO_N_Plan absent')
	cand = system.db.runPrepQuery(
		"SELECT TOP 1 h.WO_ID, RTRIM(h.Short_WO_Id) AS Sid, h.Request_Start_Date FROM dbo.WO_N_Header h "
		"WHERE RTRIM(ISNULL(h.WO_Type_Flag, 'N')) = 'M' AND RTRIM(ISNULL(h.Status, '')) NOT IN ('C', 'D', 'V') "
		"AND h.Request_Start_Date IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dbo.WO_N_Plan p WHERE p.WO_ID = h.WO_ID) "
		"ORDER BY h.Request_Start_Date DESC", [], _DB)
	if cand.getRowCount() == 0:
		return _skip('no engine-owned unpinned PM WO')
	woId = int(cand.getValueAt(0, 'WO_ID'))
	sid = str(cand.getValueAt(0, 'Sid'))
	origStart = cand.getValueAt(0, 'Request_Start_Date')
	origIso = system.date.format(origStart, 'yyyy-MM-dd')
	toIso = system.date.format(system.date.addDays(origStart, 7), 'yyyy-MM-dd')
	evBefore = int(system.db.runScalarPrepQuery("SELECT COUNT(*) FROM dbo.WO_Event_History WHERE WO_ID = ?", [woId], _DB) or 0)
	tx = system.db.beginTransaction(_DB)
	try:
		res = P.moveWO(woId, toIso, actor, expectStartIso=origIso, dryRun=False, _tx=tx)
		_chk(f, 'move pins', res.get('ok') and res.get('willPin') and res.get('pinned'), res.get('message') or res.get('code'))
		pin = system.db.runPrepQuery("SELECT RTRIM(ISNULL(Pinned,'N')) AS Pinned, Prev_Start FROM dbo.WO_N_Plan WHERE WO_ID = ?", [woId], _DB, tx)
		_chk(f, 'pin row', pin.getRowCount() == 1 and str(pin.getValueAt(0, 'Pinned')) == 'Y' and system.date.format(pin.getValueAt(0, 'Prev_Start'), 'yyyy-MM-dd') == origIso)
		dec = workmate.pm_engine.releaseDecision({'subId': sid, 'strippedId': workmate.pm_engine.stripS(sid), 'dayKey': origIso},
			[{'src': 'N', 'woId': woId, 'dayKey': toIso, 'status': 'H', 'poLinked': False, 'pinned': True}])
		_chk(f, 'engine FROZEN', dec[0] == 'FROZEN' and 'planner-pinned' in dec[1], dec)
		und = P.undoMove(woId, origIso, actor, expectStartIso=toIso, dryRun=False, _tx=tx)
		_chk(f, 'undo unpins', und.get('ok') and und.get('willUnpin') and not und.get('pinned'))
		res2 = P.moveWO(woId, toIso, actor, expectStartIso=origIso, dryRun=False, _tx=tx)
		un = P.unpin(woId, actor, dryRun=False, _tx=tx)
		_chk(f, 're-pin + unpin', res2.get('ok') and res2.get('pinned') and un.get('ok') and un.get('events') == 1)
		_chk(f, 'NOT_PINNED', P.unpin(woId, actor, dryRun=False, _tx=tx).get('code') == 'NOT_PINNED')
	finally:
		system.db.rollbackTransaction(tx)
		system.db.closeTransaction(tx)
	rows = int(system.db.runScalarPrepQuery("SELECT COUNT(*) FROM dbo.WO_N_Plan WHERE WO_ID = ?", [woId], _DB) or 0)
	after = system.db.runPrepQuery("SELECT Request_Start_Date FROM dbo.WO_N_Header WHERE WO_ID = ?", [woId], _DB)
	evAfter = int(system.db.runScalarPrepQuery("SELECT COUNT(*) FROM dbo.WO_Event_History WHERE WO_ID = ?", [woId], _DB) or 0)
	clean = rows == 0 and system.date.format(after.getValueAt(0, 'Request_Start_Date'), 'yyyy-MM-dd HH:mm') == system.date.format(origStart, 'yyyy-MM-dd HH:mm') and evAfter == evBefore
	_chk(f, 'residue 0', clean, (rows, evBefore, evAfter))
	return _res(f, '%s pinned, engine FROZEN, unpinned inside a rolled-back tx' % sid, clean)


def t_rb_labour(ctx):
	f = []
	P = workmate.planner
	actor = _actor()
	cand = system.db.runPrepQuery(
		"SELECT TOP 1 h.WO_ID, RTRIM(h.Short_WO_Id) AS Sid FROM dbo.WO_N_Header h "
		"WHERE RTRIM(ISNULL(h.Status, '')) NOT IN ('C', 'D') AND h.Request_Start_Date IS NOT NULL ORDER BY h.Request_Start_Date DESC", [], _DB)
	who = system.db.runPrepQuery(
		"SELECT TOP 1 u.User_Id, RTRIM(u.User_Name) AS N, s.Sys_User_Skill_Id, ISNULL(s.Hrs_Per_Week, 0) AS H FROM dbo.Users u "
		"JOIN dbo.User_Skill s ON s.User_ID = u.User_Id AND RTRIM(ISNULL(s.Active, '')) NOT IN ('0', 'N') "
		"WHERE RTRIM(ISNULL(u.Active, '')) = 'Y' AND u.User_Id = ?", [actor], _DB)
	if cand.getRowCount() == 0 or who.getRowCount() == 0:
		return _skip('no open WO or no active skill row for user %s' % actor)
	woId = int(cand.getValueAt(0, 'WO_ID'))
	sid = str(cand.getValueAt(0, 'Sid'))
	userId = int(who.getValueAt(0, 'User_Id'))
	sysId = int(float(str(who.getValueAt(0, 'Sys_User_Skill_Id'))))
	hBefore = float(str(who.getValueAt(0, 'H')))
	labBefore = len(P.labourRows(woId))
	evBefore = int(system.db.runScalarPrepQuery("SELECT COUNT(*) FROM dbo.WO_Event_History WHERE WO_ID = ?", [woId], _DB) or 0)
	tx = system.db.beginTransaction(_DB, system.db.READ_COMMITTED, 10000)
	try:
		a = P.addLabour(woId, userId, 0, 3.5, '', 'NIGHT SHIFT TEST - safe to delete', actor, dryRun=False, _tx=tx)
		_chk(f, 'addLabour', a.get('ok') and a.get('resId') > 0 and a.get('events') == 1, a.get('message') or a.get('code'))
		rows = P.labourRows(woId, tx)
		_chk(f, 'row present', len(rows) == labBefore + 1 and [r for r in rows if r['resId'] == a.get('resId') and r['hours'] == 3.5])
		rm = P.removeLabour(woId, a.get('resId'), actor, dryRun=False, _tx=tx)
		_chk(f, 'removeLabour', rm.get('ok') and (rm.get('undo') or {}).get('kind') == 'labourAdd' and len(P.labourRows(woId, tx)) == labBefore)
		cp = P.setCapacity(userId, sysId, 20, actor, dryRun=False, _tx=tx)
		_chk(f, 'setCapacity', cp.get('ok') and cp.get('prevHrsPerWeek') == hBefore and cp.get('hrsPerWeek') == 20.0)
	finally:
		system.db.rollbackTransaction(tx)
		system.db.closeTransaction(tx)
	evAfter = int(system.db.runScalarPrepQuery("SELECT COUNT(*) FROM dbo.WO_Event_History WHERE WO_ID = ?", [woId], _DB) or 0)
	hAfter = float(str(system.db.runScalarPrepQuery("SELECT ISNULL(Hrs_Per_Week, 0) FROM dbo.User_Skill WHERE Sys_User_Skill_Id = ?", [sysId], _DB) or 0))
	clean = len(P.labourRows(woId)) == labBefore and evAfter == evBefore and hAfter == hBefore
	_chk(f, 'residue 0', clean, (evBefore, evAfter, hBefore, hAfter))
	return _res(f, '%s labour add/remove + capacity %s->20 inside a rolled-back tx' % (sid, hBefore), clean)


# ---------------------------------------------------------------------------
# pack registry
# ---------------------------------------------------------------------------

PACKS = [
	{'name': 'planner-pure', 'write': False,
	 'libVersion': lambda: workmate.planner.version(),
	 'tests': [('versions', t_versions), ('rules', t_rules), ('workers + capacity', t_workers),
	           ('move / estimate / labour rules', t_moverules), ('DST civil days', t_dst),
	           ('actor token + code map', t_token), ('chat parse', t_chat_parse), ('planner_ai heuristics', t_ai_pure)]},
	{'name': 'planner-read', 'write': False,
	 'libVersion': lambda: workmate.planner.version(),
	 'tests': [('rangeData this week', t_range), ('api routing', t_api_routes), ('webdev http smoke', t_http),
	           ('planner_ai on live data', t_ai_live), ('chat read-only', t_chat_live)]},
	{'name': 'planner-write-rb', 'write': True,
	 'libVersion': lambda: workmate.planner.version(),
	 'tests': [('move + estimate + undo (rolled back)', t_rb_move), ('PM pin cycle (rolled back)', t_rb_pin),
	           ('labour + capacity (rolled back)', t_rb_labour)]},
]