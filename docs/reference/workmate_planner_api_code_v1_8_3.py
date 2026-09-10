# =============================================================================
# workmate_planner_api_code_v1_8_3.py
# Version:     1.8.3
# Target:      Project Library  workmate/planner_api
# Database:    TLSQL01_Workmate  (via workmate.planner)
# Author:      Adriaan
# Spec:        Workmate_P-PLN1_PlannerCalendar_Spec_v1_1_0.md  (S1 D-1, S2 D-2/D-4, S3 D-3)
#
# Purpose:
#   HTTP layer for the Planner Calendar. Same shape as workmate.ferret_api:
#   route() is a pure function - request dict in, (status, body, kind) out -
#   so the whole API can be driven from the Script Console with a fake
#   request dict. The WebDev resource 'planner' is two one-line shims.
#
# ROUTING (WebDev python resource 'planner', dispatch on remainingPath):
#   GET  /health                    liveness + versions            (no sid)
#   GET  /ui[?v=Planner_v1_0_0.html] the single-file UI, served from
#                                   PLANNER_UI_DIR - newest version wins
#   GET  /range?from=&to=&sid=      one planner window (workmate.planner.rangeData)
#   GET  /_echo?sid=                request / gate / actor diagnostics
#   POST /open  {sid, pid, woId, shortId}
#                                   WOMaint handoff: sendMessage 'wm-plan-open'
#                                   into the caller's Perspective page
#   POST /move  {sid, woId, toIso, expectStartIso, confirm}     (S2)
#                                   workmate.planner.moveWO(dryRun=False)
#                                   200 ok | 200 ok:false code CONFIRM+preview
#                                   | 409 STALE | 422 rule refusal | 403 NO_IDENTITY
#   POST /undo  {sid, woId, toIso, expectStartIso}              (S2)
#   POST /estimate {sid, woId, hours}                            (S2)
#   POST /unpin {sid, woId}                                      (S3)
#                                   workmate.planner.unpin - hands a pinned PM
#                                   back to the release engine
#   POST /labour {sid, woId, userId, skillId, hours, resDate, note}   (S4)
#                                   workmate.planner.addLabour - one planned
#                                   labour row (WO_N_Resource 'L')
#   POST /labour/remove {sid, woId, resId}                       (S4)
#   POST /capacity {sid, userId, sysSkillId, hrsPerWeek}         (S4)
#                                   User_Skill.Hrs_Per_Week on one skill row
#   GET  /suggest?from=&weeks=&lookahead=&capacity=&woId=&sid=   (S5)
#                                   workmate.planner_ai.suggest - pull-forward
#                                   plan per week, needs-estimate list, people
#                                   over/under their hours, pairs, and (woId)
#                                   the history suggestion for that WO. READ ONLY.
#   GET  /history?woId=&sid=        workmate.planner_ai.historyFor (labour popup)
#   GET  /settings?sid=             the planner's own switches (autopilot, weeks,
#                                   guardrails) with their effective values
#   POST /settings {sid, key, value} set ONE whitelisted PLANNER_* switch
#                                   (System_Configuration upsert, actor required,
#                                   [F] line with old -> new). Turning autopilot
#                                   ON with no PLANNER_AUTOPILOT_USER_ID sets it
#                                   to the actor - the audit rows carry a name.
#   POST /chat {sid, uid, tok, text, woId}                       (S5c)
#                                   workmate.planner_chat.answer with the
#                                   selected-WO context - the in-planner
#                                   assistant panel. Writes confirm-gated
#                                   inside the chat ('yes'), same actor rules.
#   POST /nightly {sid, weeks, apply}   run workmate.planner_ai.nightly() now
#                                   (proposal file + optional autopilot) - actor
#                                   required; apply=true needs PLANNER_AUTOPILOT_USER_ID
#   GET  /preview?woId=&to=&sid=    movePreview (rules + old/new, no write)
#
# ACTOR (1.2.0): the host view injects uid = session.custom.wmUserId (the
#   proven startup identity) and tok = token(sid, uid) - an HMAC-SHA256 over
#   sid|uid with a gateway-only secret - into the iframe URL; the UI sends
#   both with every call. A valid token IS the actor (no client can forge it
#   without the secret). Fallback: the live session's userName through
#   workmate.identity.resolve (1.1.0 behaviour). Secret =
#   System_Configuration PLANNER_TOKEN_SECRET, else a random per-boot value
#   (tokens then expire on project save - the UI just reloads).
#
# WRITES need an actor: the session's user resolved through workmate.identity.
#   userId 0 (unmapped) -> 403 NO_IDENTITY. Dev only: System_Configuration
#   PLANNER_DEV_USER_ID = <User_Id> stands in when the gate is OFF, so moves
#   can be exercised from a browser without an AD login. /health shows both.
#
# GATE (spec D-1 / R2): every route except /health and /ui carries sid = the
#   caller's Perspective session id (session.props.id, injected into the
#   iframe URL by the host view). It must match a LIVE Perspective session on
#   this gateway (system.perspective.getSessionInfo). The actor is then
#   resolved with workmate.identity.resolve(userName) - the same identity
#   path as every Perspective write; 0 = unmapped login.
#   System_Configuration PLANNER_SID_GATE = '0' switches the gate off for
#   Designer-preview / Dev work. Never leave it off on live.
#
# CONFIG (System_Configuration, optional):
#   PLANNER_UI_DIR       folder holding Planner_v*.html   default C:\WorkmateData\Planner
#   PLANNER_SID_GATE     '0' = gate off                    default on
#   PLANNER_DEV_USER_ID  actor when the gate is off        default none (writes 403)
#   PLANNER_TOKEN_SECRET HMAC secret for the actor token   default per-boot random
#
# DIAGNOSTICS (1.3.0) - Forensic Diagnostics Standard v1.1.0, source 'Planner':
#   Every request outcome is wired to the caller's Workmate DebugConsole
#   (sendMessage 'debug-log' with sessionId = the caller's sid - WebDev has
#   no session of its own) AND persisted to dbo.Diag_Log through the same NQ
#   workmate.diag uses, attributed to the actor. Tags follow the standard:
#   [F] forensic = what happened (range, move, undo, estimate, pin, open)
#   [G] guard    = why it was blocked (gate, no identity, rule refusals, stale)
#   [E] error    = crashes and write failures (detail = message / traceback)
#   Async, never blocks a request, never raises. POST /_diag lets the browser
#   file its own [E]/[F] rows (window.onerror, debug mode) with the same
#   attribution. /_echo runs a diag self-test and reports which persist path
#   works on this gateway.
#
# Changelog:
#   v1.8.3  serveUI(prefix) so sibling apps (Work Board) serve their own
#           <Prefix>_vX_Y_Z.html from the same folder; GET /lib/<file> serves
#           the shared wm-ui.css / wm-ui.js kit (spec P-WB1 D-2).
#   v1.8.2  POST /chat {reset:true} forgets the session's chat context
#           (pending confirm, last plan, undo stack) - the 'new chat'.
#   v1.8.1  /chat carries 'next' (follow-up prompts) and 'commands' (the '/'
#           menu) from planner_chat 1.2.0.
#   v1.8.0  GET/POST /settings - autopilot on/off and guardrails from the UI.
#   v1.7.0  S5c: POST /chat (planner_chat 1.1.0 with selected-WO context).
#   v1.6.0  S5b: POST /nightly (proposal on demand); suggest carries the
#           latest proposal (planner_ai 1.1.0).
#   v1.5.0  S5: /suggest, /history (read-only, workmate.planner_ai 1.0.0).
#   v1.4.0  S4: /labour, /labour/remove, /capacity (+ diagnostics lines).
#   v1.3.0  DebugConsole + Diag_Log diagnostics (_diag), POST /_diag, echo
#           self-test. No behaviour change to any route's result.
#   v1.2.0  S3: actor token (host view uid+tok), /unpin, pinTable in /health,
#           NO_IDENTITY message names the login it could not resolve.
#   v1.1.0  S2: /move /undo /estimate /preview, actor rule, HTTP code map.
#   v1.0.0  Initial (S1).
# =============================================================================

_VERSION = '1.8.3'
_SOURCE = 'workmate.planner_api'
_DEFAULT_UI_DIR = 'C:\\WorkmateData\\Planner'
_MSG_OPEN = 'wm-plan-open'
_DIAG_SOURCE = 'Planner'
_DIAG_NQ = 'Workmate/Diag/Diag_LogInsert'
_DIAG_TIER = {'forensic': 'F', 'guard': 'G', 'error': 'E', 'info': 'S'}
_DIAG_MSGLEVEL = {'forensic': 'info', 'guard': 'warn', 'error': 'error', 'info': 'info'}
try:
	import uuid as _uuid
	_BOOT_SECRET = _uuid.uuid4().hex
except:
	_BOOT_SECRET = 'workmate-planner-%s' % system.date.now().getTime()


def version():
	return _VERSION


# ---------------------------------------------------------------------------
# helpers (defensive - WebDev hands us Java maps, not dicts)
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


def _diagPersist(sid, uid, level, message, detail=None):
	"""Diag_Log row through the standard NQ. Returns which call form worked
	('nq' | 'nq-project' | 'logger' | '') - WebDev scope varies by version."""
	params = {'sessionId': _s(sid), 'wmUserId': uid if uid > 0 else None, 'siteCode': None,
		'source': _DIAG_SOURCE, 'tier': _DIAG_TIER.get(level, 'S'),
		'msgLevel': _DIAG_MSGLEVEL.get(level, 'info'), 'message': str(message)[:1000],
		'detail': None if detail is None else str(detail)[:4000]}
	try:
		system.db.runNamedQuery(_DIAG_NQ, params)
		return 'nq'
	except:
		pass
	try:
		system.db.runNamedQuery(system.util.getProjectName(), _DIAG_NQ, params)
		return 'nq-project'
	except:
		pass
	try:
		system.util.getLogger(_DIAG_SOURCE).info('[%s] %s' % (_DIAG_TIER.get(level, 'S'), str(message)[:1000]))
		return 'logger'
	except:
		return ''


def _diagWire(sid, level, message):
	"""Live line in the caller's DebugConsole (same payload as workmate.diag)."""
	if not sid:
		return False
	try:
		system.perspective.sendMessage('debug-log', {'source': _DIAG_SOURCE, 'message': str(message)[:1000],
			'level': level}, scope='session', sessionId=sid)
		return True
	except:
		return False


def _diag(request, level, message, detail=None, actor=None):
	"""Fire-and-forget: wire + persist. level = forensic | guard | error | info.
	Attribution = the verified actor when known, else the uid the caller
	claims (diagnostics only - never a write decision)."""
	try:
		c = _creds(request) if request is not None else {}
		sid = c.get('sid', '')
		uid = _i(actor.get('userId')) if actor else _i(c.get('uid'))
		msg = str(message)[:1000]
		def _work(sid=sid, uid=uid, level=level, msg=msg, detail=detail):
			_diagWire(sid, level, msg)
			_diagPersist(sid, uid, level, msg, detail)
		system.util.invokeAsynchronous(_work)
	except:
		pass


def _get(request, key, default=None):
	try:
		v = request.get(key)
		return default if v is None else v
	except:
		return default


def _segments(request):
	rp = _get(request, 'remainingPath', '')
	try:
		rp = str(rp).strip('/')
	except:
		rp = ''
	if rp == '':
		return []
	return [s for s in rp.split('/') if s != '']


def _param(request, name, default=None):
	p = _get(request, 'params', None)
	if p is None:
		return default
	try:
		v = p.get(name)
	except:
		return default
	if v is None:
		return default
	try:
		if isinstance(v, (list, tuple)):
			return v[0] if len(v) else default
	except:
		pass
	return v


def _body(request):
	"""Parsed JSON body as a dict; {} when absent or unparseable. WebDev
	parses application/json into 'data'; 'postData' holds the raw text."""
	d = _get(request, 'data', None)
	try:
		if isinstance(d, dict):
			return d
	except:
		pass
	if d is not None:
		try:
			return dict(d)
		except:
			pass
	pd = _get(request, 'postData', None)
	if pd is None:
		return {}
	try:
		if isinstance(pd, dict):
			return pd
	except:
		pass
	try:
		return system.util.jsonDecode(str(pd))
	except:
		return {}


def _errBody(code, message):
	return {'ok': False, 'error': {'code': code, 'message': message}}


def _attr(o, name):
	"""Attribute-or-key read (session info objects vary by version)."""
	try:
		v = getattr(o, name)
		if v is not None:
			return v
	except:
		pass
	try:
		v = o[name]
		if v is not None:
			return v
	except:
		pass
	try:
		return o.get(name)
	except:
		return None


# ---------------------------------------------------------------------------
# gate + actor
# ---------------------------------------------------------------------------

def gateEnabled():
	return workmate.planner.configValue('PLANNER_SID_GATE', '1') != '0'


def _secret():
	v = workmate.planner.configValue('PLANNER_TOKEN_SECRET', '')
	return (v, 'config') if v else (_BOOT_SECRET, 'boot')


def token(sid, uid):
	"""HMAC-SHA256(secret, sid|uid) hex. Called by the host view (gateway
	scope) when it builds the iframe URL, and by verifyToken()."""
	import hmac, hashlib
	sid = _s(sid)
	uid = _i(uid)
	if not sid or uid <= 0:
		return ''
	sec, src = _secret()
	return hmac.new(_b(sec), _b('%s|%d' % (sid, uid)), hashlib.sha256).hexdigest()


def _b(v):
	"""bytes for hmac: unicode -> utf-8, byte str unchanged."""
	try:
		return v.encode('utf-8')
	except:
		return v


def verifyToken(sid, uid, tok):
	want = token(sid, uid)
	got = _s(tok)
	if not want or not got or len(want) != len(got):
		return False
	diff = 0
	for i in range(len(want)):
		diff |= ord(want[i]) ^ ord(got[i])
	return diff == 0


def _creds(request):
	"""sid / pid / uid / tok from the query (GET) or the JSON body (POST)."""
	body = _body(request)
	out = {}
	for k in ('sid', 'pid', 'uid', 'tok'):
		v = _s(_param(request, k))
		if not v:
			v = _s(body.get(k))
		out[k] = v
	return out


def _sessions():
	try:
		return list(system.perspective.getSessionInfo())
	except:
		_log('getSessionInfo failed: ' + _err(), 'error')
		return []


def findSession(sid):
	sid = _s(sid)
	if not sid:
		return None
	for s in _sessions():
		if _s(_attr(s, 'id')) == sid:
			return s
	return None


def devUserId():
	return _i(workmate.planner.configValue('PLANNER_DEV_USER_ID', '0'))


def actorFor(sess, request=None):
	"""{'userId', 'userName', 'name', 'via'}. Order: (1) a valid uid+tok
	from the request (the host view's session identity), (2) the live
	session's userName through workmate.identity.resolve, (3) gate off ->
	PLANNER_DEV_USER_ID. userId 0 = no identity."""
	uid = 0
	uname = ''
	via = 'none'
	tokenState = 'absent'
	if request is not None:
		c = _creds(request)
		if c['uid'] and c['tok']:
			if verifyToken(c['sid'], c['uid'], c['tok']):
				uid = _i(c['uid'])
				via = 'token'
				tokenState = 'valid'
			else:
				tokenState = 'invalid'
	if sess is not None:
		uname = _s(_attr(sess, 'userName'))
	if uid <= 0 and uname:
		try:
			uid = int(workmate.identity.resolve(uname) or 0)
			if uid > 0:
				via = 'session'
		except:
			uid = 0
	if uid <= 0 and sess is None and not gateEnabled():
		uid = devUserId()
		if uid > 0:
			via = 'dev'
			uname = uname or ('dev-user-%d' % uid)
	name = ''
	if uid > 0:
		try:
			name = _s(workmate.identity.displayName(uid))
		except:
			name = ''
	return {'userId': uid, 'userName': uname, 'name': name or uname, 'via': via, 'token': tokenState}


def _sidOf(request):
	sid = _s(_param(request, 'sid'))
	if not sid:
		sid = _s(_body(request).get('sid'))
	return sid


def _gate(request):
	"""(ok, sessionObj, errorTuple). Gate off -> (True, None, None)."""
	if not gateEnabled():
		return (True, None, None)
	sess = findSession(_sidOf(request))
	if sess is None:
		_diag(request, 'guard', 'gate refused: sid %s... is not a live session (%s %s)' % (
			_sidOf(request)[:8], _s(_get(request, 'remainingPath', '')), _s(_get(request, 'remoteAddr', ''))))
		return (False, None, (401, _errBody('UNAUTHORIZED',
			'sid is not a live Perspective session on this gateway - reload the planner page')))
	return (True, sess, None)


# ---------------------------------------------------------------------------
# UI file serve
# ---------------------------------------------------------------------------

def uiDir():
	return workmate.planner.configValue('PLANNER_UI_DIR', _DEFAULT_UI_DIR)


def uiFiles(d=None, prefix='Planner'):
	"""<prefix>_vX_Y_Z.html files in the UI folder, oldest -> newest."""
	import os, re
	d = d or uiDir()
	out = []
	try:
		for fn in os.listdir(d):
			m = re.match(r'^' + re.escape(prefix) + r'_v(\d+)_(\d+)_(\d+)\.html$', str(fn))
			if m:
				out.append(((int(m.group(1)), int(m.group(2)), int(m.group(3))), str(fn)))
	except:
		_log('uiFiles(%s): %s' % (d, _err()), 'warn')
	out.sort()
	return [fn for v, fn in out]


def _uiErrorPage(d, files, msg):
	return ('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Planner</title></head>'
		'<body style="font-family:Segoe UI,Arial,sans-serif;background:#2a2e33;color:#e6e8ea;padding:24px">'
		'<h2 style="color:#FFC65C;margin:0 0 8px">Planner UI not available</h2>'
		'<p>%s</p><p>Folder: <code>%s</code></p><p>Files seen: %s</p>'
		'<p>Set System_Configuration <code>PLANNER_UI_DIR</code> to the folder holding '
		'<code>Planner_vX_Y_Z.html</code>, or copy the file there.</p></body></html>'
		% (msg, d, ', '.join(files) if files else '(none)'))


_LIB_TYPES = {'.css': 'text/css; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.svg': 'image/svg+xml', '.json': 'application/json'}


def serveLib(request, segs):
	"""GET /lib/<file>: a shared kit file (wm-ui.css, wm-ui.js ...) from the UI folder."""
	import os, codecs, re
	name = _s(segs[1]) if len(segs) > 1 else ''
	if not re.match(r'^[A-Za-z0-9_.-]+$', name) or '..' in name:
		return (404, _errBody('NOT_FOUND', 'bad lib name'), 'json')
	ext = os.path.splitext(name)[1].lower()
	if ext not in _LIB_TYPES:
		return (404, _errBody('NOT_FOUND', 'lib type not served'), 'json')
	path = os.path.join(uiDir(), name)
	if not os.path.isfile(path):
		return (404, _errBody('NOT_FOUND', '%s not in %s' % (name, uiDir())), 'json')
	f = codecs.open(path, 'r', 'utf-8')
	try:
		text = f.read()
	finally:
		f.close()
	return (200, text, 'raw:' + _LIB_TYPES[ext])


def serveUI(request, prefix='Planner'):
	import os, codecs
	d = uiDir()
	files = uiFiles(d, prefix)
	want = _s(_param(request, 'v'))
	fn = None
	if want and want in files:
		fn = want
	elif files:
		fn = files[-1]
	if fn is None:
		return (503, _uiErrorPage(d, files, 'No %s_vX_Y_Z.html found.' % prefix), 'html')
	try:
		f = codecs.open(os.path.join(d, fn), 'r', 'utf-8')
		try:
			text = f.read()
		finally:
			f.close()
		return (200, text, 'html')
	except:
		msg = _err()
		_log('serveUI %s: %s' % (fn, msg), 'error')
		return (500, _uiErrorPage(d, files, 'Could not read %s: %s' % (fn, msg)), 'html')


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------

def _chatVersion():
	try:
		return workmate.planner_chat.version()
	except:
		return ''


def _aiVersion():
	try:
		return workmate.planner_ai.version()
	except:
		return ''


def _health():
	return (200, {'ok': True, 'service': 'workmate-planner', 'api': _VERSION,
		'lib': workmate.planner.version(), 'ai': _aiVersion(), 'chat': _chatVersion(), 'gate': gateEnabled(), 'devUserId': devUserId(),
		'dryRunDefault': bool(workmate.planner.DRY_RUN),
		'pinTable': workmate.planner.pinTableExists(), 'tokenSecret': _secret()[1],
		'uiFiles': uiFiles(), 'now': system.date.format(system.date.now(), "yyyy-MM-dd'T'HH:mm:ss")}, 'json')


def _range(request, sess):
	fromIso = _s(_param(request, 'from'))
	toIso = _s(_param(request, 'to'))
	t0 = system.date.now().getTime()
	try:
		data = workmate.planner.rangeData(fromIso, toIso)
	except:
		msg = _err()
		if 'bad window' in msg or 'too wide' in msg:
			_diag(request, 'guard', 'range refused: %s' % msg)
			return (400, _errBody('BAD_WINDOW', msg), 'json')
		_log('range %s..%s FAILED: %s' % (fromIso, toIso, msg), 'error')
		_diag(request, 'error', 'range %s..%s FAILED' % (fromIso, toIso), detail=msg)
		return (500, _errBody('RANGE_FAILED', msg), 'json')
	actor = actorFor(sess, request)
	ms = int(system.date.now().getTime() - t0)
	data['ok'] = True
	data['apiVersion'] = _VERSION
	data['gate'] = gateEnabled()
	data['actor'] = actor
	data['ms'] = ms
	_diag(request, 'forensic', 'range %s..%s rows=%d labour=%d workers=%d pinTable=%s in %d ms' % (
		data.get('from'), data.get('to'), len(data.get('wos') or []), len(data.get('labour') or []),
		len(data.get('workers') or []), data.get('pinTable'), ms), actor=actor)
	return (200, data, 'json')


def _open(request, sess):
	body = _body(request)
	woId = _i(body.get('woId'))
	shortId = _s(body.get('shortId'))
	sid = _s(body.get('sid'))
	pid = _s(body.get('pid'))
	if woId <= 0:
		return (400, _errBody('BAD_REQUEST', 'woId required'), 'json')
	if not sid:
		return (400, _errBody('BAD_REQUEST', 'sid required for the page bridge'), 'json')
	payload = {'woId': woId, 'shortId': shortId}
	try:
		if pid:
			system.perspective.sendMessage(_MSG_OPEN, payload, scope='page', sessionId=sid, pageId=pid)
		else:
			system.perspective.sendMessage(_MSG_OPEN, payload, scope='session', sessionId=sid)
	except:
		msg = _err()
		_log('open WO %s bridge FAILED: %s' % (woId, msg), 'error')
		return (500, _errBody('BRIDGE_FAILED', msg), 'json')
	_log('open WO %s (%s) -> session %s page %s' % (woId, shortId, sid[:8], pid[:8]))
	_diag(request, 'forensic', 'open %s (WO_ID %s) in WOMaint' % (shortId, woId), actor=actorFor(sess, request))
	return (200, {'ok': True, 'woId': woId}, 'json')


_CODE_HTTP = {'NOT_FOUND': 404, 'STALE': 409, 'NO_IDENTITY': 403, 'CONFIRM': 200,
	'LOCKED_STATUS': 422, 'ENGINE_OWNED': 422, 'NO_START': 422, 'BAD_DATE': 422,
	'NO_CHANGE': 422, 'BAD_HOURS': 422, 'NO_DETAILS': 422, 'NOT_PINNED': 422, 'BAD_REQUEST': 400,
	'NO_USER': 422, 'USER_INACTIVE': 422, 'NO_SKILL': 422,
	'WRITE_FAILED': 500, 'INTERNAL': 500}


def _diagWrite(request, what, res, actor=None):
	"""One diagnostics line per write outcome, tagged by the standard."""
	try:
		sid = _s(res.get('sid'))
		if res.get('ok'):
			extra = ''
			if 'newStart' in res:
				extra = ' %s -> %s (%s d)' % (res.get('prevStart'), res.get('newStart'), res.get('delta'))
				if res.get('willPin'):
					extra += ' PINNED'
				elif res.get('willUnpin'):
					extra += ' pin cleared'
				elif res.get('pinned'):
					extra += ' still pinned'
			elif 'hrsPerWeek' in res:
				extra = ' %s (%s) %s -> %s h/wk' % (res.get('userName'), res.get('skillTitle'), res.get('prevHrsPerWeek'), res.get('hrsPerWeek'))
			elif 'resId' in res and 'row' in res:
				extra = ' Res_Id %s (%s %s h)' % (res.get('resId'), res.get('userName'), (res.get('row') or {}).get('hours'))
			elif 'resId' in res:
				extra = ' %s %s h on %s (%s) Res_Id %s' % (res.get('userName'), res.get('hours'), res.get('resDate'), res.get('skillTitle'), res.get('resId'))
			elif 'hours' in res:
				extra = ' %s -> %s h' % (res.get('prevHours'), res.get('hours'))
			_diag(request, 'forensic', '%s %s%s events=%s' % (what, sid, extra, res.get('events')), actor=actor)
			return
		code = _s(res.get('code'))
		if code == 'CONFIRM':
			_diag(request, 'forensic', '%s %s needs confirm: %s' % (what, sid,
				', '.join([r.get('code', '') for r in (res.get('preview') or {}).get('reasons', [])])), actor=actor)
		elif code in ('WRITE_FAILED', 'INTERNAL'):
			_diag(request, 'error', '%s %s FAILED (%s)' % (what, sid, code), detail=res.get('message'), actor=actor)
		else:
			_diag(request, 'guard', '%s %s blocked: %s - %s' % (what, sid, code, _s(res.get('message'))[:300]), actor=actor)
	except:
		pass


def _writeResult(res):
	"""Library dict -> (status, body). ok -> 200; otherwise the code map."""
	if res.get('ok'):
		return (200, res, 'json')
	code = _s(res.get('code')) or 'INTERNAL'
	body = dict(res)
	body['ok'] = False
	body['error'] = {'code': code, 'message': _s(res.get('message'))}
	return (_CODE_HTTP.get(code, 500), body, 'json')


def _actorOrError(sess, request):
	actor = actorFor(sess, request)
	if _i(actor.get('userId')) <= 0:
		_diag(request, 'guard', 'write blocked: no Workmate identity for login "%s" (token %s) on %s' % (
			actor.get('userName') or '?', actor.get('token'), _s(_get(request, 'remainingPath', ''))))
		return (None, (403, _errBody('NO_IDENTITY',
			'no Workmate identity for login "%s" (token %s) - map it in User Mapping, then reload the planner'
			% (actor.get('userName') or '?', actor.get('token'))), 'json'))
	return (actor, None)


def _move(request, sess, undo=False):
	body = _body(request)
	woId = _i(body.get('woId'))
	toIso = _s(body.get('toIso'))[:10]
	expect = _s(body.get('expectStartIso'))[:10] or None
	if woId <= 0 or not toIso:
		return (400, _errBody('BAD_REQUEST', 'woId and toIso required'), 'json')
	actor, err = _actorOrError(sess, request)
	if err:
		return err
	uid = _i(actor['userId'])
	if undo:
		res = workmate.planner.undoMove(woId, toIso, uid, expectStartIso=expect, dryRun=False)
	else:
		confirm = str(body.get('confirm')).lower() in ('1', 'true', 'yes')
		res = workmate.planner.moveWO(woId, toIso, uid, expectStartIso=expect, confirm=confirm, dryRun=False)
	if isinstance(res, dict):
		res['actor'] = actor
		_diagWrite(request, 'undo' if undo else 'move', res, actor)
	return _writeResult(res)


def _estimate(request, sess):
	body = _body(request)
	woId = _i(body.get('woId'))
	if woId <= 0 or body.get('hours') is None:
		return (400, _errBody('BAD_REQUEST', 'woId and hours required'), 'json')
	actor, err = _actorOrError(sess, request)
	if err:
		return err
	res = workmate.planner.setEstimate(woId, body.get('hours'), _i(actor['userId']), dryRun=False)
	if isinstance(res, dict):
		res['actor'] = actor
		_diagWrite(request, 'estimate', res, actor)
	return _writeResult(res)


def _unpin(request, sess):
	body = _body(request)
	woId = _i(body.get('woId'))
	if woId <= 0:
		return (400, _errBody('BAD_REQUEST', 'woId required'), 'json')
	actor, err = _actorOrError(sess, request)
	if err:
		return err
	res = workmate.planner.unpin(woId, _i(actor['userId']), dryRun=False)
	if isinstance(res, dict):
		res['actor'] = actor
		_diagWrite(request, 'unpin', res, actor)
	return _writeResult(res)


def _labour(request, sess, remove=False):
	body = _body(request)
	woId = _i(body.get('woId'))
	if woId <= 0:
		return (400, _errBody('BAD_REQUEST', 'woId required'), 'json')
	actor, err = _actorOrError(sess, request)
	if err:
		return err
	uid = _i(actor['userId'])
	if remove:
		resId = _i(body.get('resId'))
		if resId <= 0:
			return (400, _errBody('BAD_REQUEST', 'resId required'), 'json')
		res = workmate.planner.removeLabour(woId, resId, uid, dryRun=False)
	else:
		userId = _i(body.get('userId'))
		if userId <= 0 or body.get('hours') is None:
			return (400, _errBody('BAD_REQUEST', 'userId and hours required'), 'json')
		res = workmate.planner.addLabour(woId, userId, _i(body.get('skillId')), body.get('hours'),
			_s(body.get('resDate'))[:10], _s(body.get('note')), uid, dryRun=False)
	if isinstance(res, dict):
		res['actor'] = actor
		_diagWrite(request, 'labour-' if remove else 'labour+', res, actor)
	return _writeResult(res)


def _capacity(request, sess):
	body = _body(request)
	userId = _i(body.get('userId'))
	sysId = _i(body.get('sysSkillId'))
	if userId <= 0 or sysId <= 0 or body.get('hrsPerWeek') is None:
		return (400, _errBody('BAD_REQUEST', 'userId, sysSkillId and hrsPerWeek required'), 'json')
	actor, err = _actorOrError(sess, request)
	if err:
		return err
	res = workmate.planner.setCapacity(userId, sysId, body.get('hrsPerWeek'), _i(actor['userId']), dryRun=False)
	if isinstance(res, dict):
		res['actor'] = actor
		_diagWrite(request, 'capacity', res, actor)
	return _writeResult(res)


def _suggest(request, sess):
	fromIso = _s(_param(request, 'from'))[:10]
	if not fromIso:
		return (400, _errBody('BAD_REQUEST', 'from required (yyyy-MM-dd)'), 'json')
	weeks = _i(_param(request, 'weeks'), 4)
	look = _i(_param(request, 'lookahead'), 2)
	capRaw = _s(_param(request, 'capacity'))
	cap = None
	if capRaw:
		try:
			cap = float(capRaw)
		except:
			return (400, _errBody('BAD_REQUEST', 'capacity must be a number'), 'json')
	woId = _i(_param(request, 'woId'))
	t0 = system.date.now().getTime()
	try:
		out = workmate.planner_ai.suggest(fromIso, weeks, max(1, min(look, 6)), cap, woId)
	except:
		msg = _err()
		if 'bad window' in msg or 'too wide' in msg:
			return (400, _errBody('BAD_WINDOW', msg), 'json')
		_log('suggest %s FAILED: %s' % (fromIso, msg), 'error')
		_diag(request, 'error', 'suggest %s FAILED' % fromIso, detail=msg)
		return (500, _errBody('SUGGEST_FAILED', msg), 'json')
	actor = actorFor(sess, request)
	out['ok'] = True
	out['apiVersion'] = _VERSION
	out['actor'] = actor
	out['ms'] = int(system.date.now().getTime() - t0)
	_diag(request, 'forensic', 'suggest %s +%dw: %d moves, %d need estimate, %d flagged, in %d ms' % (
		out.get('from'), weeks, len((out.get('plan') or {}).get('moves') or []),
		len((out.get('plan') or {}).get('needsEstimate') or []), len(out.get('flags') or {}), out['ms']), actor=actor)
	return (200, out, 'json')


def _history(request, sess):
	woId = _i(_param(request, 'woId'))
	if woId <= 0:
		return (400, _errBody('BAD_REQUEST', 'woId required'), 'json')
	try:
		out = workmate.planner_ai.historyFor(woId)
	except:
		msg = _err()
		_log('history %s FAILED: %s' % (woId, msg), 'error')
		return (500, _errBody('HISTORY_FAILED', msg), 'json')
	if not out.get('ok'):
		return _writeResult(out)
	out['apiVersion'] = _VERSION
	return (200, out, 'json')


def _nightly(request, sess):
	body = _body(request)
	actor, err = _actorOrError(sess, request)
	if err:
		return err
	weeks = _i(body.get('weeks'), 0)
	apply = str(body.get('apply')).lower() in ('1', 'true', 'yes')
	t0 = system.date.now().getTime()
	try:
		prop = workmate.planner_ai.nightly(weeks or None, apply, dryRun=False)
	except:
		msg = _err()
		_log('nightly FAILED: %s' % msg, 'error')
		_diag(request, 'error', 'nightly FAILED', detail=msg, actor=actor)
		return (500, _errBody('NIGHTLY_FAILED', msg), 'json')
	out = {'ok': True, 'ranAt': prop.get('ranAt'), 'from': prop.get('from'), 'weeks': prop.get('weeks'),
		'moves': len(prop.get('moves') or []), 'applied': len(prop.get('applied') or []), 'skipped': len(prop.get('skipped') or []),
		'failed': prop.get('failed') or [], 'needsEstimate': len(prop.get('needsEstimate') or []), 'saved': prop.get('saved'),
		'saveError': prop.get('saveError'), 'autopilot': prop.get('autopilot'), 'ms': int(system.date.now().getTime() - t0), 'actor': actor}
	_diag(request, 'forensic', 'nightly run by %s: %d moves proposed, %d applied, saved=%s in %d ms' % (
		actor.get('name'), out['moves'], out['applied'], bool(out['saved']), out['ms']), actor=actor)
	return (200, out, 'json')


_SETTINGS = [
	('PLANNER_AUTOPILOT', '0', 'Apply the guarded subset of the nightly proposal automatically (1 = on)'),
	('PLANNER_AUTOPILOT_USER_ID', '', 'Users.User_Id the autopilot writes as (audit rows)'),
	('PLANNER_AUTOPILOT_MAX_WEEKS', '2', 'Pull forward at most N weeks'),
	('PLANNER_AUTOPILOT_MAX_MOVES', '10', 'At most N moves per night'),
	('PLANNER_NIGHTLY_WEEKS', '4', 'Weeks the nightly proposal plans'),
]
_SETTING_KEYS = [k for k, d, t in _SETTINGS]


def _settingsList():
	out = []
	for k, d, t in _SETTINGS:
		v = workmate.planner.configValue(k, '')
		out.append({'key': k, 'value': v, 'effective': v if v != '' else d, 'default': d, 'set': v != '', 'text': t})
	return out


def _settingsGet(request, sess):
	actor = actorFor(sess, request)
	uid = _i(workmate.planner.configValue('PLANNER_AUTOPILOT_USER_ID', '0'))
	name = ''
	if uid > 0:
		try:
			name = _s(workmate.identity.displayName(uid))
		except:
			name = ''
	return (200, {'ok': True, 'settings': _settingsList(), 'autopilot': workmate.planner.configValue('PLANNER_AUTOPILOT', '0') == '1',
		'autopilotUser': {'userId': uid, 'name': name}, 'actor': actor, 'apiVersion': _VERSION}, 'json')


def _settingsSet(request, sess):
	body = _body(request)
	key = _s(body.get('key')).upper()
	val = _s(body.get('value'))
	if key not in _SETTING_KEYS:
		return (400, _errBody('BAD_REQUEST', 'key must be one of %s' % ', '.join(_SETTING_KEYS)), 'json')
	actor, err = _actorOrError(sess, request)
	if err:
		return err
	if key == 'PLANNER_AUTOPILOT':
		val = '1' if val in ('1', 'true', 'on', 'yes') else '0'
	elif key in ('PLANNER_AUTOPILOT_MAX_WEEKS', 'PLANNER_AUTOPILOT_MAX_MOVES', 'PLANNER_NIGHTLY_WEEKS', 'PLANNER_AUTOPILOT_USER_ID'):
		n = _i(val, -1)
		if n < 0 or n > 500:
			return (422, _errBody('BAD_VALUE', '%s must be a whole number' % key), 'json')
		val = str(n)
	prev = workmate.planner.configValue(key, '')
	try:
		_upsertConfig(key, val, 'Planner (set from the planner by %s)' % actor.get('name'))
		extra = ''
		if key == 'PLANNER_AUTOPILOT' and val == '1' and _i(workmate.planner.configValue('PLANNER_AUTOPILOT_USER_ID', '0')) <= 0:
			_upsertConfig('PLANNER_AUTOPILOT_USER_ID', str(_i(actor['userId'])), 'Planner autopilot actor (set with autopilot ON)')
			extra = ' (autopilot user set to %s)' % actor.get('name')
	except:
		msg = _err()
		_diag(request, 'error', 'settings %s FAILED' % key, detail=msg, actor=actor)
		return (500, _errBody('WRITE_FAILED', msg), 'json')
	_diag(request, 'forensic', 'setting %s: %s -> %s%s' % (key, prev or '(unset)', val, extra), actor=actor)
	return _settingsGet(request, sess)


def _upsertConfig(key, val, desc):
	n = system.db.runPrepUpdate("UPDATE dbo.System_Configuration SET System_ConfigVal = ? WHERE RTRIM(System_ConfigCol) = ?", [val, key], _DB())
	if int(n or 0) == 0:
		system.db.runPrepUpdate("INSERT INTO dbo.System_Configuration (System_ConfigCol, System_ConfigDesc, System_ConfigVal) VALUES (?, ?, ?)", [key, desc[:100], val], _DB())


def _DB():
	return 'TLSQL01_Workmate'


def _chat(request, sess):
	body = _body(request)
	text = _s(body.get('text'))[:500]
	actor = actorFor(sess, request)
	c = _creds(request)
	if str(body.get('reset')).lower() in ('1', 'true', 'yes'):
		try:
			workmate.planner_chat.resetFor(c.get('sid', ''))
		except:
			pass
		if not text:
			return (200, {'ok': True, 'reset': True, 'apiVersion': _VERSION}, 'json')
	if not text:
		return (400, _errBody('BAD_REQUEST', 'text required'), 'json')
	ctx = {'sid': c.get('sid', ''), 'userId': _i(actor.get('userId')), 'userName': actor.get('name'), 'woId': _i(body.get('woId'))}
	t0 = system.date.now().getTime()
	try:
		r = workmate.planner_chat.answer(text, None, ctx)
	except:
		msg = _err()
		_diag(request, 'error', 'chat crashed', detail=msg, actor=actor)
		return (500, _errBody('CHAT_FAILED', msg), 'json')
	out = {'ok': True, 'reply': r.get('reply'), 'intent': r.get('intent'), 'answered': bool(r.get('ok')),
		'next': r.get('next') or [], 'hasWo': bool(r.get('hasWo')),
		'commands': workmate.planner_chat.commands(bool(r.get('hasWo'))) if hasattr(workmate.planner_chat, 'commands') else [],
		'woId': ctx['woId'], 'ms': int(system.date.now().getTime() - t0), 'apiVersion': _VERSION}
	_diag(request, 'forensic', 'chat %s%s: "%s" in %d ms' % (r.get('intent'), (' (WO %s)' % ctx['woId']) if ctx['woId'] else '', text[:80], out['ms']), actor=actor)
	return (200, out, 'json')


def _preview(request, sess):
	woId = _i(_param(request, 'woId'))
	toIso = _s(_param(request, 'to'))[:10]
	if woId <= 0 or not toIso:
		return (400, _errBody('BAD_REQUEST', 'woId and to required'), 'json')
	return _writeResult(workmate.planner.movePreview(woId, toIso))


def _clientDiag(request, sess):
	"""POST /_diag {level, message, detail}: the browser files its own row
	(window.onerror -> [E], debug mode -> [F]). Gate + token apply."""
	body = _body(request)
	level = _s(body.get('level')).lower()
	if level not in ('forensic', 'guard', 'error', 'info'):
		level = 'forensic'
	message = _s(body.get('message'))[:500]
	if not message:
		return (400, _errBody('BAD_REQUEST', 'message required'), 'json')
	actor = actorFor(sess, request)
	_diag(request, level, 'ui: ' + message, detail=_s(body.get('detail'))[:4000] or None, actor=actor)
	return (200, {'ok': True}, 'json')


def _diagSelfTest(request, sess):
	"""Synchronous wire + persist so /_echo can report what works here."""
	c = _creds(request)
	actor = actorFor(sess, request)
	wired = _diagWire(c.get('sid', ''), 'forensic', 'echo self-test (api %s)' % _VERSION)
	via = _diagPersist(c.get('sid', ''), _i(actor.get('userId')), 'forensic', 'echo self-test (api %s)' % _VERSION)
	return {'wired': wired, 'persistVia': via}


def _echo(request, sess):
	params = {}
	try:
		p = _get(request, 'params', None)
		if p is not None:
			for k in p.keys():
				params[str(k)] = str(p[k]) if str(k) not in ('sid', 'tok') else '***'
	except:
		pass
	return (200, {'ok': True, 'api': _VERSION, 'lib': workmate.planner.version(),
		'diagSelfTest': _diagSelfTest(request, sess),
		'gate': gateEnabled(), 'session': None if sess is None else
			{'id': _s(_attr(sess, 'id'))[:8] + '...', 'userName': _s(_attr(sess, 'userName'))},
		'actor': actorFor(sess, request), 'devUserId': devUserId(), 'pinTable': workmate.planner.pinTableExists(),
		'remainingPath': _s(_get(request, 'remainingPath', '')),
		'params': params, 'remoteAddr': _s(_get(request, 'remoteAddr', '')),
		'uiDir': uiDir(), 'uiFiles': uiFiles()}, 'json')


def route(request, method):
	"""Pure dispatch: (status, body, kind) with kind 'json' | 'html'."""
	method = _s(method).upper() or 'GET'
	segs = _segments(request)
	if not segs:
		return (200, {'ok': True, 'service': 'workmate-planner', 'api': _VERSION,
			'hint': 'GET /health, /ui, /range?from=&to=&sid=, /suggest?from=&weeks=&sid=, /history?woId=&sid=, /preview?woId=&to=&sid=, /settings?sid=, /_echo?sid= ; POST /open /move /undo /estimate /unpin /labour /labour/remove /capacity /nightly /chat /settings /_diag'}, 'json')
	head = segs[0].lower()
	if head == 'health':
		return _health()
	if head == 'ui':
		if method != 'GET':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/ui is GET only'), 'json')
		return serveUI(request)
	if head == 'lib':
		return serveLib(request, segs)
	ok, sess, err = _gate(request)
	if not ok:
		return (err[0], err[1], 'json')
	if head == 'range':
		if method != 'GET':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/range is GET only'), 'json')
		return _range(request, sess)
	if head == '_echo':
		return _echo(request, sess)
	if head == '_diag':
		if method != 'POST':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/_diag is POST only'), 'json')
		return _clientDiag(request, sess)
	if head == 'open':
		if method != 'POST':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/open is POST only'), 'json')
		return _open(request, sess)
	if head == 'preview':
		if method != 'GET':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/preview is GET only'), 'json')
		return _preview(request, sess)
	if head == 'suggest':
		if method != 'GET':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/suggest is GET only'), 'json')
		return _suggest(request, sess)
	if head == 'history':
		if method != 'GET':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/history is GET only'), 'json')
		return _history(request, sess)
	if head == 'labour':
		if method != 'POST':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/labour is POST only'), 'json')
		sub = segs[1].lower() if len(segs) > 1 else ''
		if sub == 'remove':
			return _labour(request, sess, remove=True)
		if sub:
			return (404, _errBody('NOT_FOUND', "Unknown path 'labour/%s'" % sub), 'json')
		return _labour(request, sess)
	if head == 'capacity':
		if method != 'POST':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/capacity is POST only'), 'json')
		return _capacity(request, sess)
	if head == 'settings':
		if method == 'GET':
			return _settingsGet(request, sess)
		if method == 'POST':
			return _settingsSet(request, sess)
		return (405, _errBody('METHOD_NOT_ALLOWED', '/settings is GET or POST'), 'json')
	if head == 'chat':
		if method != 'POST':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/chat is POST only'), 'json')
		return _chat(request, sess)
	if head == 'nightly':
		if method != 'POST':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/nightly is POST only'), 'json')
		return _nightly(request, sess)
	if head in ('move', 'undo', 'estimate', 'unpin'):
		if method != 'POST':
			return (405, _errBody('METHOD_NOT_ALLOWED', '/%s is POST only' % head), 'json')
		if head == 'estimate':
			return _estimate(request, sess)
		if head == 'unpin':
			return _unpin(request, sess)
		return _move(request, sess, undo=(head == 'undo'))
	return (404, _errBody('NOT_FOUND', "Unknown path '%s'" % head), 'json')


# ---------------------------------------------------------------------------
# WebDev entry points
# ---------------------------------------------------------------------------

def _finish(request, code):
	"""Status + no-store on the servlet response. No-op in the Script Console."""
	try:
		resp = request.get('servletResponse')
		if resp is not None:
			if code != 200:
				resp.setStatus(int(code))
			resp.setHeader('Cache-Control', 'no-store')
	except:
		pass


def _respond(request, result):
	code, body, kind = result
	_finish(request, code)
	if kind == 'html':
		return {'html': body, 'contentType': 'text/html; charset=utf-8'}
	if str(kind).startswith('raw:'):
		return {'response': body, 'contentType': str(kind)[4:]}
	return {'json': body}


def _crash(request, method):
	msg = _err()
	tb = ''
	try:
		import traceback
		tb = traceback.format_exc()
	except:
		tb = ''
	_log('handle%s crashed: %s' % (method, msg), 'error')
	_diag(request, 'error', '%s %s crashed: %s' % (method, _s(_get(request, 'remainingPath', '')), msg[:300]), detail=tb or msg)
	return _respond(request, (500, _errBody('INTERNAL', msg), 'json'))


def handleGet(request, session=None):
	try:
		return _respond(request, route(request, 'GET'))
	except:
		return _crash(request, 'GET')


def handlePost(request, session=None):
	try:
		return _respond(request, route(request, 'POST'))
	except:
		return _crash(request, 'POST')