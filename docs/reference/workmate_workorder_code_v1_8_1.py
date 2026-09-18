# =============================================================================
# workmate.workorder  -  Work Order service layer
# Module:   workmate/workorder/code.py
# Version:  1.8.1  (Next WO_ID sourced from WO_Status - the sequence owner -
#           instead of WO_N_Header. WO_Status legitimately holds ids with no
#           surviving header row (archive/legacy purges), so MAX(header)+1
#           could collide: live PK dup on WO_Status(365) at KT 2026-07-22.
#           Transaction/rollback behaviour unchanged.)
# Prev:     1.8.0  (WO id prefix + diag tiers, Adriaan 2026-07-14:
#           D-WOID-1 Short_WO_Id prefix is always 'WO' - no longer derived
#           from the location's Short_Location_ID - so WOs are visually
#           distinct from POs (both derived 'K-...' at KT).
#           D-WOID-2 exception: a location-derived 'CP' prefix (capital
#           projects, CP-00) is preserved. Existing K-/CP- ids untouched;
#           per-prefix MAX(seq) scan means no collisions. .NET-created /
#           PM-released WOs keep deriving K- until those paths retire.
#           DIAG: _log(level='error') now routes to workmate.diag.error()
#           (tier E, auto-traceback into Detail) and write-path guard
#           rejections route via new _guard() -> workmate.diag.guard()
#           (tier G) - WO engine failures/blocks now surface in
#           vw_Diag_Problems instead of hiding as tier-S rows.)
# Prev:     1.7.2  (Delete guards hardened per cascade probe 2026-07-08:
#           NO_ACTION FKs surface as clean canDelete reasons instead of raw
#           SQL errors - linked child WOs (FK_Linked_WO_N_Header_WO_Status),
#           Part_Adjustment and Part_Holding references now block up front.)
# Prev:     1.7.0  (Delete: new canDelete(woId) + delete(woId, userId) -
#           .NET DeleteRecord parity: blocked for Closed/Active, blocked when
#           PO-linked (header flag / PO_Header / PO_Details), Meter_Reading
#           FROM_WO_ID detached, event-history DELETE row, then transactional
#           wmsp_WO_StatusDelete with an in-tx cascade verify (rollback + loud
#           error if the header row survives). Hard delete per decision D3;
#           admin-only gate lives in the WOMaint button per D5.)
# Prev:     1.6.0  (Clone: new clone(hostWoId, userId, sameAsset, assetId) -
#           copies title/notes/priority + full details set + Est_Cost, resets
#           audit fields, Status->P (audited), Progress->1, Linked_to_WO->0,
#           Start=today, End=today+host duration days, fresh Short_WO_Id.
#           Activities/labour/POs NOT cloned (PO-clone deferred, D1).
#           NOTE: no Cloned_to_WO column exists on WO_N_Header - the .NET
#           CLONED_WO var was an in-memory tracker for its PO-clone prompt.)
# Prev:     1.5.0  (Linked WOs: create() gains linkedToWo + shortWoIdOverride
#           kwargs (header param 24 Linked_to_WO + preset Short_WO_Id, seq-gen
#           skipped); createFromTemplate passes them through + optional
#           woGroupId merge; new canCreateLinked(hostWoId) ports the .NET
#           suffix rules (parent A-Z, child 1-9, depth cap). Legacy calls
#           byte-identical.)
# Prev:     1.4.0  (adds formatOpenForWeekReply() - builds the AI-assistant reply
#           payload {text, rows, summary} from getOpenForWeek() for the WM_AI overlay.
#           Presentation formatter; no DB writes. Builds on 1.3.0 getOpenForWeek.)
#           Mon-Mon week on Request_Start_Date, for the AI 'outstanding this week' query.
#           New NQ Workmate/Workorder/GetOpenForWeek. No change to existing fns.)
#           alongside Reference='Ref 2'. Adds Entered_By to text cols, UPDATE, _detailState.)
# Author:   Adriaan
# Mirrors:  workmate.actions (the gold-standard service module)
# Spec:     Workmate_WO_3_Spec_v1.2.md
#
# Stage 3C scope: write functions (create / updateStatus / updateProgress /
# update / addNote), audit writers (_logEvent / _logFieldDiffs), and the
# proven helpers ported from workmate.actions (_execProc, _weekNoAndYear,
# _currentState). create() is the canonical WO-creation path; Stage 3D
# refactors promoteToWO to call it.
#
# Audit goes to the EXISTING WO_Event_History table (the .NET app maintains
# it) via Workmate/Workorder/Event/Insert - so .NET and Perspective share
# one trail.
#
# Reads (Stage 3B) wrap the consolidated Workmate/Workorder/* NQs (WO-1 v2.0).
# =============================================================================

_VERSION = '1.8.1'
_DB = 'TLSQL01_Workmate'
_PROJECT = 'Main SCADA Timberlands'  # required for runNamedQuery(...) in transaction scope
_SOURCE = 'workmate.workorder'
_SITE_COMPANY_ID = 1

# WO status codes (R/H/P/K/A/V/C/D/F) - NOTE: F=Deferred, NOT G like actions.
_VALID_STATUS = ('R', 'H', 'P', 'K', 'A', 'V', 'C', 'D', 'F')
_STATUS_LABEL = {
	'R': 'Request', 'H': 'Planned', 'P': 'Pending', 'K': 'Acknowledged',
	'A': 'Approved', 'V': 'Active', 'C': 'Closed', 'D': 'Cancelled',
	'F': 'Deferred'
}
_VALID_PROGRESS = (1, 2, 3, 4, 5, 6)
_PROGRESS_LABEL = {1: 'None', 2: 'Wait', 3: '25%', 4: '50%', 5: '75%', 6: '100%'}


# ----------------------------------------------------------------------------
# logging / toast  (identical pattern to workmate.actions)
# ----------------------------------------------------------------------------

def _log(message, level='info'):
	"""Debug Console + dbo.Diag_Log persistence via workmate.diag (v1.1.1+).
	v1.8.0: level='error' routes to workmate.diag.error() so the row
	persists as tier E with the traceback auto-captured into Detail
	(call from inside the except block) and shows in vw_Diag_Problems.
	Never raises - logging must not break callers."""
	try:
		if str(level) == 'error':
			workmate.diag.error(None, _SOURCE, message)
		else:
			workmate.diag.log(_SOURCE, message, level)
	except:
		pass


def _guard(message):
	"""Tier-G guard rejection (Forensic Diagnostics Standard section 3):
	user-hittable blocked actions - the support-bot answer material.
	Persists tier G -> vw_Diag_Problems. Never raises."""
	try:
		workmate.diag.guard(None, _SOURCE, message)
	except:
		pass


def _toast(message, toastType='success'):
	"""Best-effort page-scope toast."""
	try:
		system.perspective.sendMessage(
			'show-toast',
			{'message': message, 'type': toastType},
			scope='page'
		)
	except:
		pass


# ----------------------------------------------------------------------------
# resolvers  (ports of the .NET clsWOeventHistory.GetShortID logic)
# ----------------------------------------------------------------------------

# Maps an ID column name -> (lookup table, short-code column, key column).
# Mirrors the .NET GetShortID switch exactly so audit diffs read the same.
_SHORTID_MAP = {
	'Asset_ID':                   ('Asset',           'Short_Asset_ID',     'Asset_ID'),
	'Location_Id':                ('Location',        'Short_Location_ID',  'Location_Id'),
	'WO_Group_Id':                ('WorkOrder_Group', 'Short_WO_Group_ID',  'WO_Group_Id'),
	'Priority_Id':                ('Priority',        'Short_Priority_Id',  'Priority_Id'),
	'Fault_Id':                   ('Fault',           'Short_Fault_Id',     'Fault_Id'),
	'Reason_Id':                  ('Reason',          'Short_reason_Id',    'Reason_Id'),
	'Cost_Center_Id':             ('Cost_Center',     'Short_Cost_Center_ID','Cost_Center_Id'),
	'Account_Id':                 ('Account',         'Short_Account_Id',   'Account_Id'),
	'Progress_Id':                ('Progress',        'Short_Progress_Id',  'Progress_Id'),
	'Condition_Id':               ('Condition',       'Short_Condition_id', 'Condition_Id'),
	'Meter_ID':                   ('Meter',           'Short_Meter_Id',     'Meter_ID'),
	'WOC1_ID':                    ('WOC1',            'Short_WOC1_ID',      'WOC1_ID'),
	'WOC2_ID':                    ('WOC2',            'Short_WOC2_ID',      'WOC2_ID'),
	'WOC3_ID':                    ('WOC3',            'Short_WOC3_ID',      'WOC3_ID'),
	# Supplier columns all resolve through Supplier.Short_Supplier_Id
	'Supplier_ID_Requested_By':   ('Supplier',        'Short_Supplier_Id',  'Supplier_Id'),
	'Supplier_ID_charge_To':      ('Supplier',        'Short_Supplier_Id',  'Supplier_Id'),
	'Supplier_ID_Responsibility': ('Supplier',        'Short_Supplier_Id',  'Supplier_Id'),
	# User columns all resolve through Users.Short_User_Id
	'User_ID_Responsibility':     ('Users',           'Short_User_Id',      'User_Id'),
	'User_Id_Ack_by':             ('Users',           'Short_User_Id',      'User_Id'),
	'User_Id_Approved_By':        ('Users',           'Short_User_Id',      'User_Id'),
	'User_ID_ClosedBy':           ('Users',           'Short_User_Id',      'User_Id'),
	'User_ID_CancelledBy':        ('Users',           'Short_User_Id',      'User_Id'),
	'User_ID_IntrusiveComplete':  ('Users',           'Short_User_Id',      'User_Id'),
	'User_id_Last_Save':          ('Users',           'Short_User_Id',      'User_Id'),
	'Progress_User':              ('Users',           'Short_User_Id',      'User_Id'),
}


def _resolveShortId(columnName, idValue):
	"""Resolve an ID-column value to its Short_ code, like the .NET GetShortID.
	Returns str(idValue) if the column isn't mapped or the lookup misses."""
	if idValue is None:
		return ''
	try:
		idInt = int(idValue)
	except:
		return str(idValue)
	mapping = _SHORTID_MAP.get(columnName)
	if mapping is None:
		return str(idInt)
	table, shortCol, keyCol = mapping
	try:
		ds = system.db.runPrepQuery(
			"SELECT RTRIM(%s) AS code FROM dbo.%s WHERE %s = ?"
			% (shortCol, table, keyCol), [idInt], _DB)
		if ds is not None and len(ds) > 0 and ds[0]['code'] is not None:
			return str(ds[0]['code'])
	except:
		import sys
		_log('_resolveShortId miss %s=%s: %s'
		     % (columnName, idValue, sys.exc_info()[1]), level='warn')
	return str(idInt)


def _resolveUser(userId):
	"""User_Id -> display name. User_Name first, then Short_User_Id, then the
	raw id, '' for None. This is the data-layer half of killing the 7.0 bug."""
	if userId is None:
		return ''
	try:
		uidInt = int(userId)
	except:
		return str(userId)
	try:
		ds = system.db.runPrepQuery(
			"SELECT RTRIM(User_Name) AS nm, RTRIM(Short_User_Id) AS su "
			"FROM dbo.Users WHERE User_Id = ?", [uidInt], _DB)
		if ds is not None and len(ds) > 0:
			nm = ds[0]['nm']
			su = ds[0]['su']
			if nm:
				return str(nm)
			if su:
				return str(su)
	except:
		import sys
		_log('_resolveUser miss %s: %s' % (userId, sys.exc_info()[1]), level='warn')
	return str(uidInt)


# ----------------------------------------------------------------------------
# read wrappers  (wrap the consolidated Workmate/Workorder/* NQs)
# ----------------------------------------------------------------------------

def getItem(woId):
	"""Full WO: header + WO_N_Details join. (Workorder/Item)"""
	_log('getItem woId=%s' % woId)
	try:
		return system.db.runNamedQuery('Workmate/Workorder/Item',
		                                {'woId': int(woId)})
	except:
		import sys
		_log('getItem exception: %s' % sys.exc_info()[1], level='error')
		return None


def getHeader(woId):
	"""Header-only, 25 cols. (Workorder/ItemHeader)"""
	_log('getHeader woId=%s' % woId)
	try:
		return system.db.runNamedQuery('Workmate/Workorder/ItemHeader',
		                                {'woId': int(woId)})
	except:
		import sys
		_log('getHeader exception: %s' % sys.exc_info()[1], level='error')
		return None


def getList(filters):
	"""Typed search. (Workorder/Search) filters is a dict; missing keys take
	their default here so a caller can pass {'shortWoId':'COS'} alone."""
	defaults = {
		'shortWoId': '', 'woTitle': '', 'shortAssetId': '',
		'shortLocationId': '', 'includeArchive': 0, 'includeClosed': 1
	}
	params = dict(defaults)
	if filters:
		params.update(filters)
	_log('getList shortWoId=%r includeClosed=%s includeArchive=%s'
	     % (params['shortWoId'], params['includeClosed'], params['includeArchive']))
	try:
		return system.db.runNamedQuery('Workmate/Workorder/Search', params)
	except:
		import sys
		_log('getList exception: %s' % sys.exc_info()[1], level='error')
		return None


def getOpen():
	"""All open WOs (NOT IN C,D), priority-sorted. (Workorder/GetOpen)"""
	_log('getOpen')
	try:
		return system.db.runNamedQuery('Workmate/Workorder/GetOpen', {})
	except:
		import sys
		_log('getOpen exception: %s' % sys.exc_info()[1], level='error')
		return None


def _thisWeekBounds():
	"""(weekStart, weekEnd) java.util.Date for the current week:
	   weekStart = Monday 00:00:00 this week; weekEnd = next Monday 00:00:00
	   (exclusive upper bound). Uses system.date -> gateway timezone."""
	now = system.date.now()
	midnight = system.date.setTime(now, 0, 0, 0)
	dow = system.date.getDayOfWeek(midnight)   # Sunday=1 .. Saturday=7
	daysFromMonday = (dow + 5) % 7             # Mon->0, Tue->1, ... Sun->6
	weekStart = system.date.addDays(midnight, -daysFromMonday)
	weekEnd = system.date.addDays(weekStart, 7)
	return weekStart, weekEnd


def getOpenForWeek(weekStart=None, weekEnd=None):
	"""Open WOs (NOT IN C,D) whose Request_Start_Date falls in a week window,
	   priority-sorted. Defaults to the current Mon-Mon week when called with no
	   args. (Workorder/GetOpenForWeek)"""
	if weekStart is None or weekEnd is None:
		weekStart, weekEnd = _thisWeekBounds()
	_log('getOpenForWeek weekStart=%s weekEnd=%s' % (weekStart, weekEnd))
	try:
		return system.db.runNamedQuery('Workmate/Workorder/GetOpenForWeek',
		                                {'weekStart': weekStart,
		                                 'weekEnd': weekEnd})
	except:
		import sys
		_log('getOpenForWeek exception: %s' % sys.exc_info()[1], level='error')
		return None


# ---------------------------------------------------------------------------
# AI-assistant presentation formatter (WM_AI overlay)
# ---------------------------------------------------------------------------
_PRIORITY_LABEL = {1: 'Critical', 2: 'High', 3: 'Medium', 4: 'Low', 5: 'Planned'}
_PRIORITY_COLOR = {1: '#C02026', 2: '#DC7323', 3: '#EBC452', 4: '#5CA6C4', 5: '#78A699'}


def _priInt(v):
	try:
		return int(round(float(v)))
	except:
		return 3


def formatOpenForWeekReply():
	"""Build the WM_AI reply for 'outstanding work orders this week'.
	   Returns a dict: {'text': <intro string>, 'rows': [<wo dicts>],
	   'summary': <one-line tally>}. rows carry display fields the bubble
	   renders as a rich card. Read-only; safe to call from the overlay."""
	ds = getOpenForWeek()
	weekStart, weekEnd = _thisWeekBounds()
	weekLabel = '%s to %s' % (
		system.date.format(weekStart, 'EEE d MMM'),
		system.date.format(system.date.addDays(weekEnd, -1), 'EEE d MMM'))
	if ds is None or ds.rowCount == 0:
		return {'text': "Nothing outstanding for this week (%s) - you're all clear." % weekLabel,
		        'rows': [], 'summary': '0 open work orders'}

	rows = []
	tally = {}
	for r in range(ds.rowCount):
		pri = _priInt(ds.getValueAt(r, 'Priority_Id'))
		status = ds.getValueAt(r, 'Status')
		tally[status] = tally.get(status, 0) + 1
		reqDt = ds.getValueAt(r, 'Request_Start_Date')
		due = system.date.format(reqDt, 'EEE d MMM') if hasattr(reqDt, 'getTime') else ''
		rows.append({
			'shortId': (ds.getValueAt(r, 'Short_WO_Id') or '').strip(),
			'title': (ds.getValueAt(r, 'WO_Title') or '').strip(),
			'asset': (ds.getValueAt(r, 'Asset_Title') or '').strip(),
			'status': status,
			'priLabel': _PRIORITY_LABEL.get(pri, 'Medium'),
			'priColor': _PRIORITY_COLOR.get(pri, '#EBC452'),
			'due': due,
			'pri': pri
		})

	# sort by priority asc (Critical first), then due date already ordered by NQ
	rows = sorted(rows, key=lambda x: x['pri'])

	n = ds.rowCount
	crit = tally.get('A', 0)  # Approved & ready
	intro = ("Here's what's outstanding for this week (%s). "
	         "%d open work order%s, sorted by priority:" %
	         (weekLabel, n, '' if n == 1 else 's'))
	summary = '%d open - %d approved & ready for the next shut' % (n, crit)
	return {'text': intro, 'rows': rows, 'summary': summary}


def getByAsset(assetId):
	"""Up to 100 most-recent WOs for an asset. (Workorder/GetByAsset)"""
	_log('getByAsset assetId=%s' % assetId)
	try:
		return system.db.runNamedQuery('Workmate/Workorder/GetByAsset',
		                                {'assetId': int(assetId)})
	except:
		import sys
		_log('getByAsset exception: %s' % sys.exc_info()[1], level='error')
		return None


def getByStatus(status):
	"""Up to 200 WOs at a status. (Workorder/GetByStatus)"""
	_log('getByStatus status=%r' % status)
	if status not in _VALID_STATUS:
		_log('getByStatus rejected: invalid code %r' % status, level='warn')
		return None
	try:
		return system.db.runNamedQuery('Workmate/Workorder/GetByStatus',
		                                {'status': status})
	except:
		import sys
		_log('getByStatus exception: %s' % sys.exc_info()[1], level='error')
		return None


def getByLocation(locationId):
	"""WOs at a location. (Workorder/GetByLocation)"""
	_log('getByLocation locationId=%s' % locationId)
	try:
		return system.db.runNamedQuery('Workmate/Workorder/GetByLocation',
		                                {'locationId': int(locationId)})
	except:
		import sys
		_log('getByLocation exception: %s' % sys.exc_info()[1], level='error')
		return None


def getPODetails(woId):
	"""PO lines linked to a WO. (Workorder/GetPODetails)"""
	_log('getPODetails woId=%s' % woId)
	try:
		return system.db.runNamedQuery('Workmate/Workorder/GetPODetails',
		                                {'woId': int(woId)})
	except:
		import sys
		_log('getPODetails exception: %s' % sys.exc_info()[1], level='error')
		return None


def getComments(woId):
	"""WO comments/notes. (Workorder/Get Comments)"""
	_log('getComments woId=%s' % woId)
	try:
		return system.db.runNamedQuery('Workmate/Workorder/Get Comments',
		                                {'woId': int(woId)})
	except:
		import sys
		_log('getComments exception: %s' % sys.exc_info()[1], level='error')
		return None


def getEvents(woId, offsetRows=0, pageSize=100):
	"""Real persisted audit timeline from WO_Event_History, newest first,
	editor name resolved. (Workorder/Event/Search)"""
	_log('getEvents woId=%s offset=%s page=%s' % (woId, offsetRows, pageSize))
	try:
		return system.db.runNamedQuery('Workmate/Workorder/Event/Search', {
			'woId': int(woId),
			'offsetRows': int(offsetRows),
			'pageSize': int(pageSize)
		})
	except:
		import sys
		_log('getEvents exception: %s' % sys.exc_info()[1], level='error')
		return None


# ----------------------------------------------------------------------------
# audit writers  (write to the EXISTING WO_Event_History via Event/Insert)
# ----------------------------------------------------------------------------

_EVENT_DETAILS_MAX = 990   # WO_Event_History.event_details is varchar(1000)

def _logEvent(woId, eventName, eventDetails, userId, sourceForm='WOMaint'):
	"""Named-event audit row (Create / Update / Note / etc.). Best-effort:
	a failure logs a warning but does NOT raise, so it can't roll back the
	parent mutation (which has already committed). Mirrors actions._logEvent."""
	try:
		det = '' if eventDetails is None else str(eventDetails)
		if len(det) > _EVENT_DETAILS_MAX:
			det = det[:_EVENT_DETAILS_MAX - 3] + '...'
		system.db.runNamedQuery('Workmate/Workorder/Event/Insert', {
			'woId': int(woId),
			'userId': int(userId) if userId is not None else None,
			'eventName': str(eventName),
			'eventDetails': det,
			'serverName': 'Perspective',
			'sourceForm': sourceForm
		})
	except:
		import sys
		_log('AUDIT WRITE FAILED WO_ID=%s event=%s: %s'
		     % (woId, eventName, sys.exc_info()[1]), level='warn')


# Columns we diff for the field-edit audit. Header + Details fields that the
# .NET clsWOeventHistory also tracks (H_List + D_List), minus the always-
# changing Last_Save bookkeeping which would spam every save.
_DIFF_DATE_COLS = (
	'Request_Start_Date', 'Request_End_Date', 'Acknowledgement_date',
	'Approved_Date', 'Closed_Date', 'Cancelled_Date',
)

def _fmtDiffValue(colName, value):
	"""Format one side of a diff like the .NET UpdateWOEventHistory does:
	dates -> yyyy-MM-dd (blank for null/min), ID columns -> Short_ code,
	everything else -> str."""
	if value is None:
		return ''
	# date columns
	if colName in _DIFF_DATE_COLS or (hasattr(value, 'getTime')):
		try:
			return system.date.format(value, 'yyyy-MM-dd')
		except:
			return str(value)
	# ID columns -> resolve to Short_ code
	if colName in _SHORTID_MAP:
		return _resolveShortId(colName, value)
	s = str(value)
	return s.rstrip()


def _logFieldDiffs(woId, oldDict, newDict, userId, sourceForm='WOMaint'):
	"""Compare old vs new field dicts; write one WO_Event_History row per
	changed field, formatted '{Col} changed from {old} to {new}' exactly like
	the .NET clsSimpleComparer + UpdateWOEventHistory. Returns count written."""
	if not oldDict or not newDict:
		return 0
	written = 0
	for col in newDict:
		if col not in oldDict:
			continue
		oldV = oldDict[col]
		newV = newDict[col]
		if _sameValue(oldV, newV):
			continue
		detail = '{%s} changed from {%s} to {%s}' % (
			col, _fmtDiffValue(col, oldV), _fmtDiffValue(col, newV))
		_logEvent(woId, 'Update', detail, userId, sourceForm=sourceForm)
		written += 1
	return written


def _sameValue(a, b):
	"""True if two field values are equal for audit purposes. Normalises so
	that whitespace-only string differences, and None vs '' vs equivalent
	'empty' representations, do NOT register as a change (which is what caused
	the spurious '{Notes} changed from X to X' rows). Numeric-ish strings are
	compared by trimmed text; trailing-space differences are ignored."""
	# normalise each side to a comparable scalar
	def norm(v):
		if v is None:
			return None
		if isinstance(v, basestring):
			s = v.strip()
			return s if s != '' else None   # blank string == None for diffing
		return v
	na, nb = norm(a), norm(b)
	if na is None and nb is None:
		return True
	if na is None or nb is None:
		return False
	# string compare trimmed (handles trailing-space / CHAR padding)
	if isinstance(na, basestring) and isinstance(nb, basestring):
		return na == nb
	# fall back to value equality
	return na == nb


# ----------------------------------------------------------------------------
# helpers ported from workmate.actions (proven - copied, not reinvented)
# ----------------------------------------------------------------------------

def _execProc(procName, typedArgs, txId):
	"""Call a wmsp_ proc inside a transaction. These procs return no result
	set on success, a 'flagError' row on failure - so we exec via
	createSProcCall and inspect for the error row, raising if found (so the
	caller's transaction rolls back). typedArgs: list of (java.sql.Types, value).
	Copied verbatim from workmate.actions._execProc."""
	call = system.db.createSProcCall(procName, _DB, txId)
	for _i, (_typ, _val) in enumerate(typedArgs):
		call.registerInParam(_i + 1, _typ, _val)
	system.db.execSProcCall(call)
	try:
		rs = call.getResultSet()
	except:
		rs = None
	if rs is not None and rs.getRowCount() > 0:
		cols = [str(c).lower() for c in rs.getColumnNames()]
		if 'flagerror' in cols:
			fi = cols.index('flagerror')
			if str(rs.getValueAt(0, fi)) == 'SQLerror':
				msg = 'proc error'
				if 'error_message' in cols:
					msg = str(rs.getValueAt(0, cols.index('error_message')))
				raise Exception('Stored proc %s failed: %s' % (procName, msg))
	return call


def _weekNoAndYear(dt):
	"""WO Week_No as float YYYY.WW (ISO week). Copied verbatim from
	workmate.actions._weekNoAndYear."""
	from java.util import Calendar, GregorianCalendar
	cal = GregorianCalendar()
	cal.setTime(dt)
	cal.setFirstDayOfWeek(Calendar.MONDAY)
	cal.setMinimalDaysInFirstWeek(4)
	year = cal.get(Calendar.YEAR)
	wk = cal.get(Calendar.WEEK_OF_YEAR)
	month = cal.get(Calendar.MONTH)
	if month == 11 and wk == 1:
		year = year + 1
	elif month == 0 and wk >= 52:
		year = year - 1
	return float('%d.%02d' % (year, wk))


def _currentState(woId):
	"""Fetch header+detail fields for old-value capture before a mutation.
	Returns dict or None. Reads the columns updateStatus / update need."""
	try:
		ds = system.db.runPrepQuery(
			"SELECT h.Status, h.WO_Title, h.Location_Id, h.Asset_ID, h.Company_ID, "
			"       h.Request_Start_Date, h.Request_End_Date, "
			"       d.Progress_Id, d.Priority_Id, d.Fault_Id, d.Reason_Id, "
			"       d.Notes, d.User_ID_ClosedBy, d.Closed_Date "
			"FROM dbo.WO_N_Header h "
			"LEFT JOIN dbo.WO_N_Details d ON h.WO_ID = d.WO_ID "
			"WHERE h.WO_ID = ?", [int(woId)], _DB)
		if ds is None or len(ds) == 0:
			return None
		row = ds[0]
		return {
			'Status': row['Status'],
			'WO_Title': row['WO_Title'],
			'Location_Id': row['Location_Id'],
			'Asset_ID': row['Asset_ID'],
			'Company_ID': row['Company_ID'],
			'Request_Start_Date': row['Request_Start_Date'],
			'Request_End_Date': row['Request_End_Date'],
			'Progress_Id': row['Progress_Id'],
			'Priority_Id': row['Priority_Id'],
			'Fault_Id': row['Fault_Id'],
			'Reason_Id': row['Reason_Id'],
			'Notes': row['Notes'],
			'User_ID_ClosedBy': row['User_ID_ClosedBy'],
			'Closed_Date': row['Closed_Date'],
		}
	except:
		import sys
		_log('_currentState error WO_ID=%s: %s'
		     % (woId, sys.exc_info()[1]), level='warn')
		return None


# ----------------------------------------------------------------------------
# create  (canonical WO-creation path; promoteToWO delegates here in 3D)
# ----------------------------------------------------------------------------

def create(title, locationId, userId,
           assetId=None, priorityId=None, description=None,
           sourceActionId=None, details=None,
           startDate=None, endDate=None,
           linkedToWo=None, shortWoIdOverride=None):
	"""Create a new WO_N work order. Transactional. Returns
	{'woId': int, 'shortWoId': str} on success, or None.

	The proven proc-chain from actions.promoteToWO, generalised:
	WO_Short_IDs insert -> wmsp_WO_StatusInsert -> wmsp_WO_N_HeaderInsert
	-> wmsp_WO_N_DetailsInsert -> optional Source_Action_ID back-link.
	priorityId is honoured (param 3 of DetailsInsert); sourceActionId optional.

	details (optional dict): override WO_N_Details defaults with template /
	caller-supplied values. When None (the default, and every legacy caller),
	behaviour is byte-IDENTICAL to before - all the fields below stay at their
	NULL/default values, so the differential vs promoteToWO is unchanged.
	Recognised keys (all optional; missing/None -> keep the default):
	  woGroupId, faultId, reasonId, costCenterId, accountId, intrusive,
	  durationInHours, downTime, supplierReqId, userReqId, supplierChargeId,
	  supplierRespId, userRespId, woc1Id, woc2Id, woc3Id, reference
	priorityId (the param) still wins for Priority_Id; description still wins
	for Notes (details['notes'] is NOT used - Notes comes from description).

	startDate / endDate (optional): persisted as Request_Start_Date /
	Request_End_Date. When None (every legacy caller), both default to now -
	byte-identical to before. createFromTemplate supplies these from the
	'complete within' choice (incl. Next shut). Entry_date is always now.

	linkedToWo / shortWoIdOverride (optional, v1.5.0): create a LINKED child
	WO - Linked_to_WO (header param 24) is set to the host WO_ID and the
	preset Short_WO_Id (host id + suffix from canCreateLinked) is used
	verbatim, skipping the {WO|CP}-{yyMMdd}-{NNN} generator (v1.8.0: prefix
	is 'WO', or 'CP' for capital-project locations). WO_Short_IDs
	still gets its row. When None (every legacy caller): byte-identical.
	"""
	import sys
	_log('create() title=%r loc=%s by=%s%s%s'
	     % (title, locationId, userId, ' (+details)' if details else '',
	        ' LINKED->%s as %s' % (linkedToWo, shortWoIdOverride) if linkedToWo else ''))

	# normalise details to a dict + small typed getters
	d = details if isinstance(details, dict) else {}
	# Asset dictates Dept/Class: when an asset is given and the caller did not
	# explicitly set costCenterId/accountId, default them from the Asset record
	# (Asset.Cost_Center_Id -> Dept, Asset.Account_ID -> Class). Universal across
	# companies (each asset carries its own codes); callers may still override.
	if assetId is not None:
		try:
			_aId = int(assetId)
			if _aId > 0 and (d.get('costCenterId') in (None, 0, '') or d.get('accountId') in (None, 0, '')):
				_aDs = system.db.runPrepQuery(
					"SELECT Cost_Center_Id, Account_ID FROM dbo.Asset WHERE Asset_ID = ?",
					[_aId], _DB)
				if _aDs is not None and len(_aDs) > 0:
					if d.get('costCenterId') in (None, 0, '') and _aDs[0]['Cost_Center_Id'] is not None:
						d['costCenterId'] = int(_aDs[0]['Cost_Center_Id'])
					if d.get('accountId') in (None, 0, '') and _aDs[0]['Account_ID'] is not None:
						d['accountId'] = int(_aDs[0]['Account_ID'])
					_log('create: Dept/Class defaulted from asset %s -> cc=%s acct=%s'
					     % (_aId, d.get('costCenterId'), d.get('accountId')))
		except:
			import sys as _sys
			_log('create: asset Dept/Class lookup failed: %s' % _sys.exc_info()[1], level='warn')
	def _dNum(key):
		v = d.get(key)
		try:
			return int(v) if v is not None else None
		except:
			return None
	def _dChr(key, default):
		v = d.get(key)
		return str(v) if v is not None and str(v).strip() != '' else default

	if not title or not str(title).strip():
		_guard('create rejected: empty title')
		_toast('Title is required', 'error')
		return None
	if not locationId or int(locationId) <= 0:
		_guard('create rejected: locationId required')
		_toast('Location is required', 'error')
		return None

	try:
		# --- resolve location prefix + hierarchy ---
		locPrefix = 'WO'
		parentHier = None
		locDs = system.db.runPrepQuery(
			"SELECT Short_Location_ID, Parent_Hierarchy "
			"FROM dbo.Location WHERE Location_Id = ?", [int(locationId)], _DB)
		if locDs is not None and len(locDs) > 0:
			slid = locDs[0]['Short_Location_ID']
			parentHier = locDs[0]['Parent_Hierarchy']
			if slid:
				slid = str(slid).strip()
				locPrefix = slid.split('-')[0] if '-' in slid else slid
		# v1.8.0 D-WOID-1/2: prefix is always 'WO' (visual distinction
		# from K-prefixed POs); only the CP- capital-project prefix
		# survives location derivation. Existing ids untouched - the
		# MAX(seq) scan below is per-prefix so sequences never collide.
		if locPrefix != 'CP':
			locPrefix = 'WO'

		# --- resolve Company_ID (location's group, else site default) ---
		companyId = _SITE_COMPANY_ID
		try:
			coDs = system.db.runPrepQuery(
				"SELECT TOP 1 Company_ID FROM dbo.WO_N_Header "
				"WHERE Location_Id = ? AND Company_ID IS NOT NULL "
				"ORDER BY WO_ID DESC", [int(locationId)], _DB)
			if coDs is not None and len(coDs) > 0 and coDs[0]['Company_ID'] is not None:
				companyId = int(coDs[0]['Company_ID'])
		except:
			companyId = _SITE_COMPANY_ID

		weekNo = _weekNoAndYear(system.date.now())

		# --- Short_WO_Id: preset (linked child, v1.5.0) or generated {WO|CP}-{yyMMdd}-{NNN} ---
		if shortWoIdOverride and str(shortWoIdOverride).strip():
			shortWoId = str(shortWoIdOverride).strip()
			_log('create: using preset Short_WO_Id %s (linked child)' % shortWoId)
		else:
			datePart = system.date.format(system.date.now(), 'yyMMdd')
			preWo = '%s-%s-' % (locPrefix, datePart)
			seqDs = system.db.runPrepQuery(
				"SELECT MAX(seq) AS MaxSeq FROM ("
				"  SELECT TRY_CAST(RIGHT(RTRIM(Short_WO_Id), 3) AS INT) AS seq "
				"  FROM dbo.WO_N_Header WHERE Short_WO_Id LIKE ? "
				"  UNION ALL "
				"  SELECT TRY_CAST(RIGHT(RTRIM(Short_WO_ID), 3) AS INT) AS seq "
				"  FROM dbo.WO_Short_IDs WHERE Short_WO_ID LIKE ? "
				") x", [preWo + '%', preWo + '%'], _DB)
			maxSeq = 0
			if seqDs is not None and len(seqDs) > 0 and seqDs[0]['MaxSeq'] is not None:
				maxSeq = int(seqDs[0]['MaxSeq'])
			shortWoId = '%s%03d' % (preWo, maxSeq + 1)

		# v1.8.1: WO_Status owns the WO_ID sequence (FK parent). It can hold
		# ids with no surviving WO_N_Header row (archive/legacy purges), so
		# MAX(header)+1 collides on those - live PK dup at KT (365). Always
		# take MAX from the sequence owner.
		woIdDs = system.db.runPrepQuery(
			"SELECT ISNULL(MAX(WO_ID), 0) + 1 AS NextWO FROM dbo.WO_Status",
			[], _DB)
		newWoId = int(woIdDs[0]['NextWO'])

		now = system.date.now()
		# Request_Start / Request_End: caller-supplied or default to now
		# (None -> now keeps legacy behaviour byte-identical). Entry_date is
		# always now.
		reqStart = startDate if startDate is not None else now
		reqEnd = endDate if endDate is not None else now
		_NUM, _CHR, _VCH, _TS = 2, 1, 12, 93   # java.sql.Types

		# detail notes from description
		detailNotes = '' if description is None else str(description)[:3000]
		priorityParam = int(priorityId) if priorityId else None

		# === TRANSACTION ===
		txId = system.db.beginTransaction(_DB)
		try:
			system.db.runPrepUpdate(
				"INSERT INTO dbo.WO_Short_IDs (Short_WO_ID, Date_Created) "
				"VALUES (?, ?)", [shortWoId, now], tx=txId)

			# WO_Status parent row first (FK requirement).
			# Status='N' on the WO_Status child row to match the legacy .NET
			# wizard exactly (capture-verified: .NET writes 'N' here while
			# WO_N_Header.Status holds the real lifecycle code). This is the
			# status-table marker, NOT the header status. v1.1.2 alignment fix.
			_execProc('wmsp_WO_StatusInsert', [
				(_NUM, newWoId), (_CHR, 'N'), (_CHR, None)
			], txId)

			# WO header (24 params, .NET order from promoteToWO)
			_execProc('wmsp_WO_N_HeaderInsert', [
				(_NUM, newWoId),    (_CHR, shortWoId),  (_CHR, str(title).strip()),
				(_NUM, int(assetId) if assetId else None), (_NUM, int(locationId)), (_CHR, '0'),
				(_VCH, parentHier), (_CHR, 'R'),        (_NUM, weekNo),
				(_TS,  reqStart),   (_TS,  reqEnd),     (_TS,  now),
				(_NUM, int(userId)),(_NUM, companyId),  (_CHR, 'N'),
				(_CHR, '0'),        (_CHR, '0'),        (_CHR, None),
				(_CHR, None),       (_CHR, None),       (_CHR, None),
				(_CHR, None),       (_CHR, None),
				(_NUM, int(linkedToWo) if linkedToWo else None)   # 24 Linked_to_WO (v1.5.0)
			], txId)

			# WO_N_Details (49 params; param 3 = Priority_Id honoured).
			# When details is empty, every field below equals the prior default
			# -> byte-identical to v1.1.2. When supplied (e.g. from a template),
			# the recognised keys override; missing keys keep the default.
			_execProc('wmsp_WO_N_DetailsInsert', [
				(_NUM, newWoId),               # 1  WO_ID
				(_NUM, _dNum('woGroupId')),    # 2  WO_Group_Id
				(_NUM, priorityParam),         # 3  Priority_Id (param wins)
				(_NUM, _dNum('faultId')),      # 4  Fault_Id
				(_NUM, _dNum('reasonId')),     # 5  Reason_Id
				(_NUM, _dNum('costCenterId')), # 6  Cost_Center_Id
				(_NUM, _dNum('accountId')),    # 7  Account_Id
				(_NUM, 1),                     # 8  Progress_Id = 1 (None)
				(_CHR, _dChr('intrusive', '0')),    # 9  Intrusive
				(_NUM, _dNum('durationInHours') or 0),  # 10 Duration_In_Hours
				(_CHR, 'R'),                   # 11 Generated_From
				(_NUM, _dNum('downTime') or 0),# 12 Down_Time
				(_CHR, None),                  # 13 Entered_By
				(_CHR, _dChr('reference', None) if d.get('reference') else None),  # 14 Reference
				(_VCH, detailNotes),           # 15 Notes (from description)
				(_NUM, _dNum('supplierReqId')),    # 16 Supplier_ID_Requested_By
				(_NUM, _dNum('userReqId')),        # 17 User_ID_Requested_By
				(_NUM, _dNum('supplierChargeId')), # 18 Supplier_ID_charge_To
				(_NUM, _dNum('supplierRespId')),   # 19 Supplier_ID_Responsibility
				(_NUM, _dNum('userRespId')),       # 20 User_ID_Responsibility
				(_NUM, None),       # 21 User_Id_Ack_by
				(_TS,  None),       # 22 Acknowledgement_date
				(_NUM, None),       # 23 User_Id_Approved_By
				(_TS,  None),       # 24 Approved_Date
				(_TS,  None),       # 25 first_activity_date
				(_TS,  None),       # 26 last_activity_date
				(_CHR, '0'),        # 27 Printed
				(_NUM, None),       # 28 Condition_Id
				(_NUM, None),       # 29 User_ID_ClosedBy
				(_TS,  None),       # 30 Closed_Date
				(_NUM, 0),          # 31 Meter_Reading
				(_NUM, None),       # 32 Meter_ID
				(_NUM, _dNum('woc1Id')),   # 33 WOC1_ID
				(_NUM, _dNum('woc2Id')),   # 34 WOC2_ID
				(_NUM, _dNum('woc3Id')),   # 35 WOC3_ID
				(_NUM, None),       # 36 User_ID_CancelledBy
				(_TS,  None),       # 37 Cancelled_Date
				(_VCH, None),       # 38 Server_Name
				(_CHR, ' '),        # 39 Intrusive_Complete
				(_NUM, None),       # 40 User_ID_IntrusiveComplete
				(_TS,  None),       # 41 IntrusiveComplete_Date
				(_TS,  None),       # 42 UnLock_Date
				(_VCH, None),       # 43 UnLock_Notes
				(_NUM, None),       # 44 User_ID_UnLock_By
				(_NUM, 0),          # 45 Est_Cost
				(_NUM, None),       # 46 Progress_User
				(_TS,  None),       # 47 Progress_Date
				(_NUM, int(userId)),# 48 User_id_Last_Save
				(_TS,  now)         # 49 Last_Save_Date
			], txId)

			# optional back-link to a source action
			if sourceActionId is not None:
				system.db.runPrepUpdate(
					"UPDATE dbo.WO_N_Header SET Source_Action_ID = ? "
					"WHERE WO_ID = ?", [int(sourceActionId), newWoId], tx=txId)

			system.db.commitTransaction(txId)
		except:
			system.db.rollbackTransaction(txId)
			raise
		finally:
			system.db.closeTransaction(txId)

		# post-commit audit (named-event, matches .NET 'Create')
		_logEvent(newWoId, 'Create', 'Work Order Created', userId)
		_log('create success WO_ID=%d Short=%s' % (newWoId, shortWoId))
		_toast('WO ' + shortWoId + ' created', 'success')
		return {'woId': newWoId, 'shortWoId': shortWoId}

	except:
		_log('create exception: %s' % sys.exc_info()[1], level='error')
		_toast('Create failed - check Debug Console', 'error')
		return None


# ----------------------------------------------------------------------------
# createFromTemplate  (thin wrapper: template defaults + date logic -> create)
# ----------------------------------------------------------------------------

# "complete within" choices -> how to compute Request_End_Date from start
_COMPLETE_WITHIN = ('day', 'week', 'month', '3month', 'nextshut')

def _endDateFor(completeWithin, startDate, companyId):
	"""Compute Request_End_Date from a 'complete within' choice.
	day/week/month/3month add a fixed span to startDate. 'nextshut' looks up
	the next active shut for the site (Workmate/Shutdown/GetNextShut); if none
	scheduled, falls back to start + 14 days (the bi-weekly cadence)."""
	cw = str(completeWithin).lower().strip() if completeWithin else 'week'
	if cw == 'day':
		return system.date.addDays(startDate, 1)
	if cw == 'week':
		return system.date.addDays(startDate, 7)
	if cw == 'month':
		return system.date.addMonths(startDate, 1)
	if cw == '3month':
		return system.date.addMonths(startDate, 3)
	if cw == 'nextshut':
		try:
			ds = system.db.runNamedQuery('Workmate/Shutdown/GetNextShut',
			                             {'companyId': int(companyId) if companyId else 1})
			if ds is not None and hasattr(ds, 'getRowCount') and ds.getRowCount() > 0:
				cols = [str(ds.getColumnName(i)) for i in range(ds.getColumnCount())]
				if 'Shutdown_Date' in cols:
					return ds.getValueAt(0, cols.index('Shutdown_Date'))
		except:
			_log('nextshut lookup failed, using +14d: %s'
			     % sys.exc_info()[1], level='warn')
		return system.date.addDays(startDate, 14)   # bi-weekly fallback
	# unknown -> default to one week
	return system.date.addDays(startDate, 7)


def _templateDetails(templateId):
	"""Read a template's defaults via Workmate/Workorder/Template/Get and build
	the create() `details` dict, honouring the legacy Copy_* flags:
	  - always copy: WO_Group, Reason, Fault, Intrusive, Duration, Down_Time,
	    Supplier_Requested_By, Supplier_charge_To, WOC1-3
	  - copy Supplier_Responsibility only if Copy_Supplier_Resp == 'Y'
	  - copy Account/Cost_Center only if Copy_Account == 'Y' (usually 'N')
	Returns (detailsDict, copyTitleFlag, templateTitle) or (None, False, None)
	if the template can't be read. NULL template values are skipped (so they
	don't overwrite create()'s defaults with NULL)."""
	import sys
	try:
		ds = system.db.runNamedQuery('Workmate/Workorder/Template/Get',
		                             {'templateId': int(templateId)})
		if ds is None or not hasattr(ds, 'getRowCount') or ds.getRowCount() == 0:
			return None, False, None
		cols = [str(ds.getColumnName(i)) for i in range(ds.getColumnCount())]
		def g(name):
			return ds.getValueAt(0, cols.index(name)) if name in cols else None
		def flag(name):
			v = g(name)
			return str(v).strip().upper() == 'Y' if v is not None else False

		det = {}
		# always-copy numerics (skip if template value is NULL)
		_map = {
			'woGroupId': 'WO_Group_Id', 'reasonId': 'Reason_Id',
			'faultId': 'Fault_Id', 'durationInHours': 'Duration_In_Hours',
			'downTime': 'Down_Time', 'supplierReqId': 'Supplier_ID_Requested_By',
			'userReqId': 'User_ID_Requested_By',
			'supplierChargeId': 'Supplier_ID_charge_To',
			'woc1Id': 'WOC1_ID', 'woc2Id': 'WOC2_ID', 'woc3Id': 'WOC3_ID',
		}
		for k, col in _map.items():
			v = g(col)
			if v is not None:
				det[k] = v
		# Intrusive (char)
		if g('Intrusive') is not None:
			det['intrusive'] = str(g('Intrusive')).strip()

		# conditional: Responsibility supplier only if Copy_Supplier_Resp = 'Y'
		if flag('Copy_Supplier_Resp'):
			if g('Supplier_ID_Responsibility') is not None:
				det['supplierRespId'] = g('Supplier_ID_Responsibility')
			if g('User_ID_Responsibility') is not None:
				det['userRespId'] = g('User_ID_Responsibility')

		# conditional: Account/Cost_Center only if Copy_Account = 'Y'
		if flag('Copy_Account'):
			if g('Account_Id') is not None:
				det['accountId'] = g('Account_Id')
			if g('Cost_Center_Id') is not None:
				det['costCenterId'] = g('Cost_Center_Id')

		copyTitle = flag('Copy_Title')
		tTitle = g('Template_Title')
		return det, copyTitle, (str(tTitle).strip() if tTitle else None)
	except:
		_log('_templateDetails error: %s' % sys.exc_info()[1], level='warn')
		return None, False, None


def listTemplates(companyId=None):
	"""List WO templates for the Create-WO (WO-4) picker, shaped value/label.
	Wraps Workmate/Workorder/Template/List. companyId defaults to the site
	company (_SITE_COMPANY_ID) so callers stay site-agnostic; the NQ returns the
	site's templates PLUS global templates (Company_ID IS NULL). Returns a list
	of {'value': WO_ID, 'label': WO_Title} (ready for an ia.input.dropdown's
	props.options), or [] on error."""
	import sys
	cid = int(companyId) if companyId else _SITE_COMPANY_ID
	try:
		ds = system.db.runNamedQuery('Workmate/Workorder/Template/List',
		                             {'companyId': cid})
		opts = []
		if ds is not None and hasattr(ds, 'getRowCount'):
			cols = [str(ds.getColumnName(i)) for i in range(ds.getColumnCount())]
			vi = cols.index('WO_ID') if 'WO_ID' in cols else 0
			li = cols.index('WO_Title') if 'WO_Title' in cols else 1
			for r in range(ds.getRowCount()):
				opts.append({'value': ds.getValueAt(r, vi),
				             'label': ds.getValueAt(r, li)})
		return opts
	except:
		_log('listTemplates failed: %s' % sys.exc_info()[1], level='warn')
		return []


def getTemplate(templateId):
	"""Read one template's default field values + Copy_* flags as a dict
	(Workmate/Workorder/Template/Get). Used by the Create-WO UI to pre-fill a
	visible field (e.g. Priority) on template select; createFromTemplate() still
	applies the FULL legacy defaults server-side at create time. Returns a dict
	{column: value} for the single template row, or None if not found/on error."""
	import sys
	try:
		ds = system.db.runNamedQuery('Workmate/Workorder/Template/Get',
		                             {'templateId': int(templateId)})
		if ds is None or not hasattr(ds, 'getRowCount') or ds.getRowCount() == 0:
			return None
		cols = [str(ds.getColumnName(i)) for i in range(ds.getColumnCount())]
		return dict((c, ds.getValueAt(0, cols.index(c))) for c in cols)
	except:
		_log('getTemplate failed: %s' % sys.exc_info()[1], level='warn')
		return None


def createFromTemplate(templateId, title, locationId, userId,
                       assetId=None, completeWithin='week',
                       priorityId=None, description=None,
                       companyId=None, sourceActionId=None,
                       startDate=None, endDate=None,
                       linkedToWo=None, shortWoIdOverride=None, woGroupId=None):
	"""Create a WO from a template (the WO-4 Create-WO flow's main entry).
	Thin policy wrapper over the proven create():
	  1. read the template's defaults (Copy_* flags applied) -> details dict
	  2. compute Request_End_Date from the 'completeWithin' choice (incl. Next
	     shut) - NOTE: create() currently sets its own start/end; see below
	  3. call create(...) with the details dict
	If templateId is None/0, behaves as a plain create (no template defaults).
	priorityId param overrides the template's Priority. completeWithin is one
	of: 'day','week','month','3month','nextshut'.

	Returns create()'s result: {'woId':..., 'shortWoId':...} or None,
	with 'endDate' and 'completeWithin' added for the caller/UI.

	linkedToWo / shortWoIdOverride / woGroupId (optional, v1.5.0): passthrough
	for the Linked-WO flow - woGroupId (the host's group) is merged into the
	details dict; the other two go straight to create(). Defaults keep every
	legacy call byte-identical.
	"""
	import sys
	_log('createFromTemplate tmpl=%s title=%r loc=%s within=%s'
	     % (templateId, title, locationId, completeWithin))

	details = None
	tmplPriority = None
	if templateId:
		details, copyTitle, tTitle = _templateDetails(templateId)
		# template may carry a Priority we should use if caller didn't specify
		if details is not None and priorityId is None:
			try:
				ds = system.db.runNamedQuery('Workmate/Workorder/Template/Get',
				                             {'templateId': int(templateId)})
				if ds is not None and ds.getRowCount() > 0:
					cols = [str(ds.getColumnName(i)) for i in range(ds.getColumnCount())]
					if 'Priority_Id' in cols:
						tmplPriority = ds.getValueAt(0, cols.index('Priority_Id'))
			except:
				tmplPriority = None
		# honour Copy_Title: if 'Y' and no title given, use the template title
		if copyTitle and (not title or not str(title).strip()) and tTitle:
			title = tTitle

	# v1.5.0: linked-child extras - host WO Group wins when supplied
	if woGroupId:
		if details is None:
			details = {}
		details['woGroupId'] = int(woGroupId)

	effPriority = priorityId if priorityId is not None else tmplPriority

	# explicit Range (both dates supplied) wins; else compute from the window
	if startDate is not None and endDate is not None:
		sDate = startDate
		eDate = endDate
		completeWithin = 'range'
	else:
		sDate = system.date.now()
		eDate = _endDateFor(completeWithin, sDate, companyId)

	result = create(title, locationId, userId,
	                assetId=assetId, priorityId=effPriority,
	                description=description, sourceActionId=sourceActionId,
	                details=details, startDate=sDate, endDate=eDate,
	                linkedToWo=linkedToWo, shortWoIdOverride=shortWoIdOverride)
	if result:
		result['startDate'] = sDate
		result['endDate'] = eDate
		result['completeWithin'] = completeWithin
	return result


# ----------------------------------------------------------------------------
# updateStatus  (header touch + .NET-exact Closed stamp + audit)
# ----------------------------------------------------------------------------

def updateStatus(woId, newStatus, userId):
	"""Change WO status. Stamps/clears Closed_Date+User_ID_ClosedBy per the
	exact .NET rule (only on C, only if not already set; cleared on reopen).
	Approved/Ack dates are user-picker driven (set via update()), NOT here.
	Audits a 'Update' row. Returns bool."""
	import sys
	_log('updateStatus woId=%s newStatus=%r by=%s' % (woId, newStatus, userId))

	if newStatus not in _VALID_STATUS:
		_guard('updateStatus rejected: invalid code %r' % newStatus)
		return False

	current = _currentState(woId)
	if current is None:
		_guard('updateStatus rejected: WO %s not found' % woId)
		return False
	oldStatus = current['Status']
	if oldStatus == newStatus:
		_log('updateStatus no-op (already %s)' % newStatus)
		return True

	now = system.date.now()
	txId = system.db.beginTransaction(_DB)
	try:
		# 1. header status touch
		# Direct parameterised UPDATE (not an NQ): the WO_N_Header.Status write
		# is the same proven pattern create() uses (runPrepUpdate on WO_N_Header
		# inside the tx). Removes all dependency on the UpdateStatus NQ's
		# connection/definition, which was committing 0 rows (status never moved).
		system.db.runPrepUpdate(
			"UPDATE dbo.WO_N_Header SET Status = ? WHERE WO_ID = ?",
			[str(newStatus), int(woId)], tx=txId)

		# 2. Closed stamp (matches frmWOMaintenance lines 5395-5410)
		if newStatus == 'C':
			# only if not already closed
			alreadyClosedBy = current['User_ID_ClosedBy']
			if alreadyClosedBy in (None, 0):
				system.db.runPrepUpdate(
					"UPDATE dbo.WO_N_Details SET User_ID_ClosedBy = ?, Closed_Date = ? "
					"WHERE WO_ID = ?",
					[int(userId), system.date.midnight(now), int(woId)], tx=txId)
		elif oldStatus == 'C':
			# moving away from C -> clear the close stamp
			system.db.runPrepUpdate(
				"UPDATE dbo.WO_N_Details SET User_ID_ClosedBy = ?, Closed_Date = ? "
				"WHERE WO_ID = ?",
				[None, None, int(woId)], tx=txId)

		system.db.commitTransaction(txId)
	except:
		system.db.rollbackTransaction(txId)
		_log('updateStatus exception: %s' % sys.exc_info()[1], level='error')
		try: system.db.closeTransaction(txId)
		except: pass
		return False
	system.db.closeTransaction(txId)

	# post-commit audit
	_logEvent(int(woId), 'Update',
	          'Status changed from {%s} to {%s}' % (oldStatus, newStatus), userId)
	_log('updateStatus success WO %s %s -> %s' % (woId, oldStatus, newStatus))
	return True


# ----------------------------------------------------------------------------
# updateProgress  (Progress on WO_N_Details + audit)
# ----------------------------------------------------------------------------

def updateProgress(woId, newProgress, userId):
	"""Set Progress_Id (+Progress_User/Progress_Date) on WO_N_Details. bool."""
	import sys
	_log('updateProgress woId=%s newProgress=%s by=%s' % (woId, newProgress, userId))

	try:
		newProgInt = int(newProgress)
	except:
		_guard('updateProgress rejected: non-int %r' % newProgress)
		return False
	if newProgInt not in _VALID_PROGRESS:
		_guard('updateProgress rejected: out of range %s' % newProgInt)
		return False

	current = _currentState(woId)
	if current is None:
		_guard('updateProgress rejected: WO %s not found' % woId)
		return False
	oldProg = current['Progress_Id']
	if oldProg is not None and int(oldProg) == newProgInt:
		return True

	try:
		system.db.runNamedQuery('Workmate/Workorder/UpdateProgress', {
			'id': int(woId), 'progressId': newProgInt, 'userId': int(userId)
		})
		_logEvent(int(woId), 'Update',
		          'Progress_Id changed from {%s} to {%s}'
		          % (_resolveShortId('Progress_Id', oldProg),
		             _resolveShortId('Progress_Id', newProgInt)), userId)
		_log('updateProgress success WO %s %s -> %s' % (woId, oldProg, newProgInt))
		return True
	except:
		_log('updateProgress exception: %s' % sys.exc_info()[1], level='error')
		return False


# ----------------------------------------------------------------------------
# update  (header fields via NQ + field-diff audit)
# ----------------------------------------------------------------------------

def update(woId, payload, userId):
	"""Edit header fields (title/location/asset/dates). Detail-field edits
	(priority/fault/reason/notes) continue via the existing
	Workorder Detail/InsertUpdate proc path - update() handles the header.
	Writes one WO_Event_History row per changed field. Returns bool.

	payload keys: title, locationId, assetId, companyId, requestStart, requestEnd.
	"""
	import sys
	_log('update woId=%s by=%s keys=%s'
	     % (woId, userId, list(payload.keys()) if payload else []))

	current = _currentState(woId)
	if current is None:
		_guard('update rejected: WO %s not found' % woId)
		return False

	try:
		# FK-safe coercion: Asset_ID/Location_Id/Company_ID must be a valid FK or NULL,
		# never 0. Promoted/asset-less WOs carry Asset_ID=0/None -> pass NULL.
		def _fk(v):
			try:
				iv = int(float(v))
				return iv if iv > 0 else None
			except:
				return None
		_assetId = _fk(payload.get('assetId', current['Asset_ID']))
		_locId   = _fk(payload.get('locationId', current['Location_Id']))
		_compId  = _fk(payload.get('companyId', current.get('Company_ID')))
		system.db.runNamedQuery('Workmate/Workorder/Update', {
			'id':           int(woId),
			'title':        payload.get('title', current['WO_Title']),
			'locationId':   _locId,
			'assetId':      _assetId,
			'companyId':    _compId,
			'requestStart': payload.get('requestStart', current['Request_Start_Date']),
			'requestEnd':   payload.get('requestEnd', current['Request_End_Date']),
		})

		# field-diff audit: compare old vs new header values
		newState = {
			'WO_Title':           payload.get('title', current['WO_Title']),
			'Location_Id':        _locId,
			'Asset_ID':           _assetId,
			'Request_Start_Date': payload.get('requestStart', current['Request_Start_Date']),
			'Request_End_Date':   payload.get('requestEnd', current['Request_End_Date']),
		}
		oldState = {
			'WO_Title':           current['WO_Title'],
			'Location_Id':        current['Location_Id'],
			'Asset_ID':           current['Asset_ID'],
			'Request_Start_Date': current['Request_Start_Date'],
			'Request_End_Date':   current['Request_End_Date'],
		}
		n = _logFieldDiffs(int(woId), oldState, newState, userId)
		_log('update success WO %s (%d field change(s) audited)' % (woId, n))
		return True
	except:
		_log('update exception: %s' % sys.exc_info()[1], level='error')
		return False


def updateDetail(woId, payload, userId):
	"""Edit WO_N_Details fields from the WOMaint edit-mode Save. Companion to
	update() (which handles WO_N_Header). Writes one WO_Event_History row per
	changed field (via _logFieldDiffs) and stamps User_id_Last_Save / Last_Save_Date.
	Returns bool.

	payload keys (all optional; omitted keys are left unchanged):
	  Priority_Id, Duration_In_Hours, Est_Cost, Down_Time,
	  User_ID_Responsibility, Supplier_ID_charge_To, Supplier_ID_Responsibility,
	  WO_Group_Id, Reason_Id, Fault_Id, Cost_Center_Id, Account_Id,
	  WOC1_ID, WOC2_ID, WOC3_ID, Reference, Notes, Entered_By
	"""
	import sys
	_log('updateDetail woId=%s by=%s keys=%s'
	     % (woId, userId, list(payload.keys()) if payload else []))

	# capture current detail values for omitted-key fallback + field-diff audit
	cur = _detailState(woId)
	if cur is None:
		_guard('updateDetail rejected: WO %s detail row not found' % woId)
		return False

	# numeric columns -> None when <=0 (FK safety); text columns kept as-is
	_numCols = ('Priority_Id', 'User_ID_Responsibility', 'Supplier_ID_charge_To',
	            'Supplier_ID_Responsibility', 'WO_Group_Id', 'Reason_Id', 'Fault_Id',
	            'Cost_Center_Id', 'Account_Id', 'WOC1_ID', 'WOC2_ID', 'WOC3_ID')
	_floatCols = ('Duration_In_Hours', 'Est_Cost', 'Down_Time')
	_textCols = ('Reference', 'Notes', 'Entered_By')
	_cols = _numCols + _floatCols + _textCols

	def _coerce(col, v):
		if col in _numCols:
			try:
				iv = int(float(v))
				return iv if iv > 0 else None
			except:
				return None
		if col in _floatCols:
			try:
				return float(str(v).strip())
			except:
				return 0.0
		# text
		return '' if v is None else unicode(v)

	# build effective new values (payload override else current)
	newVals = {}
	for col in _cols:
		if payload is not None and col in payload:
			newVals[col] = _coerce(col, payload[col])
		else:
			newVals[col] = cur.get(col)

	try:
		uid = int(userId) if userId is not None else None
	except:
		uid = None

	sql = ("UPDATE dbo.WO_N_Details SET "
	       "Priority_Id=?, Duration_In_Hours=?, Est_Cost=?, Down_Time=?, "
	       "User_ID_Responsibility=?, Supplier_ID_charge_To=?, Supplier_ID_Responsibility=?, "
	       "WO_Group_Id=?, Reason_Id=?, Fault_Id=?, Cost_Center_Id=?, Account_Id=?, "
	       "WOC1_ID=?, WOC2_ID=?, WOC3_ID=?, Reference=?, Notes=?, Entered_By=?, "
	       "User_id_Last_Save=?, Last_Save_Date=? WHERE WO_ID=?")
	args = [newVals['Priority_Id'], newVals['Duration_In_Hours'], newVals['Est_Cost'],
	        newVals['Down_Time'], newVals['User_ID_Responsibility'],
	        newVals['Supplier_ID_charge_To'], newVals['Supplier_ID_Responsibility'],
	        newVals['WO_Group_Id'], newVals['Reason_Id'], newVals['Fault_Id'],
	        newVals['Cost_Center_Id'], newVals['Account_Id'], newVals['WOC1_ID'],
	        newVals['WOC2_ID'], newVals['WOC3_ID'], newVals['Reference'], newVals['Notes'],
	        newVals['Entered_By'],
	        uid, system.date.now(), int(woId)]

	try:
		system.db.runPrepUpdate(sql, args, _DB)
		# field-diff audit: only the columns the caller actually supplied
		auditCols = [c for c in _cols if (payload is not None and c in payload)]
		oldState = dict((c, cur.get(c)) for c in auditCols)
		newState = dict((c, newVals[c]) for c in auditCols)
		n = _logFieldDiffs(int(woId), oldState, newState, userId)
		_log('updateDetail success WO %s (%d field change(s) audited)' % (woId, n))
		return True
	except:
		_log('updateDetail exception: %s' % sys.exc_info()[1], level='error')
		return False


def _detailState(woId):
	"""Fetch the WO_N_Details columns updateDetail edits, for fallback + audit.
	Returns dict or None."""
	try:
		ds = system.db.runPrepQuery(
			"SELECT Priority_Id, Duration_In_Hours, Est_Cost, Down_Time, "
			"       User_ID_Responsibility, Supplier_ID_charge_To, Supplier_ID_Responsibility, "
			"       WO_Group_Id, Reason_Id, Fault_Id, Cost_Center_Id, Account_Id, "
			"       WOC1_ID, WOC2_ID, WOC3_ID, Reference, Notes, Entered_By "
			"FROM dbo.WO_N_Details WHERE WO_ID = ?", [int(woId)], _DB)
		if ds is None or len(ds) == 0:
			return None
		row = ds[0]
		out = {}
		for c in ('Priority_Id', 'Duration_In_Hours', 'Est_Cost', 'Down_Time',
		          'User_ID_Responsibility', 'Supplier_ID_charge_To', 'Supplier_ID_Responsibility',
		          'WO_Group_Id', 'Reason_Id', 'Fault_Id', 'Cost_Center_Id', 'Account_Id',
		          'WOC1_ID', 'WOC2_ID', 'WOC3_ID', 'Reference', 'Notes', 'Entered_By'):
			out[c] = row[c]
		return out
	except:
		import sys
		_log('_detailState error WO_ID=%s: %s' % (woId, sys.exc_info()[1]), level='warn')
		return None


# ----------------------------------------------------------------------------
# addNote  (free-text audit row, does not modify the WO)
# ----------------------------------------------------------------------------

def addNote(woId, comment, userId, actingForUserId=None):
	"""Append a free-text note as a WO_Event_History row. bool."""
	_log('addNote woId=%s by=%s' % (woId, userId))
	if not comment or not str(comment).strip():
		_guard('addNote rejected: empty comment')
		return False
	detail = str(comment).strip()
	if actingForUserId is not None:
		detail = '[for %s] %s' % (_resolveUser(actingForUserId), detail)
	_logEvent(int(woId), 'Note', detail, userId)
	return True


# ----------------------------------------------------------------------------
# version probe (handy for the test harness)
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# clone  (v1.6.0 - .NET frmWOMaintenance Clone rules; PO-clone deferred D1)
# ----------------------------------------------------------------------------

def clone(hostWoId, userId, sameAsset=True, assetId=None):
	"""Clone a WO per the .NET rules: copies title, notes, priority and the
	full details set (group/fault/reason/dept/class/intrusive/duration/
	down-time/suppliers/users/WOC1-3/reference + Est_Cost); resets audit
	fields, Status -> P (Pending, audited transition), Progress -> 1,
	Linked_to_WO -> 0 (never inherited); Start = today, End = today + host
	duration in days; brand-new standard Short_WO_Id. Activities / labour /
	POs are NOT cloned. Returns {'woId','shortWoId'} or None."""
	import sys
	_log('clone hostWoId=%s by=%s sameAsset=%s assetId=%s'
	     % (hostWoId, userId, sameAsset, assetId))
	try:
		hd = system.db.runPrepQuery(
			"SELECT h.WO_Title, h.Asset_ID, h.Location_Id, h.Request_Start_Date, h.Request_End_Date, "
			"       d.WO_Group_Id, d.Priority_Id, d.Fault_Id, d.Reason_Id, d.Cost_Center_Id, d.Account_Id, "
			"       d.Intrusive, d.Duration_In_Hours, d.Down_Time, d.Supplier_ID_Requested_By, "
			"       d.User_ID_Requested_By, d.Supplier_ID_charge_To, d.Supplier_ID_Responsibility, "
			"       d.User_ID_Responsibility, d.WOC1_ID, d.WOC2_ID, d.WOC3_ID, d.Reference, d.Notes, d.Est_Cost "
			"FROM dbo.WO_N_Header h "
			"LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID "
			"WHERE h.WO_ID = ?", [int(hostWoId)], _DB)
		if hd is None or len(hd) == 0:
			_guard('clone rejected: host %s not found' % hostWoId)
			return None
		row = hd[0]
		def _n(col):
			v = row[col]
			try:
				return int(v) if v is not None else None
			except:
				return None
		locId = _n('Location_Id')
		aId = _n('Asset_ID') if sameAsset else (int(assetId) if assetId else None)
		now = system.date.now()
		days = 0
		try:
			if row['Request_Start_Date'] is not None and row['Request_End_Date'] is not None:
				days = system.date.daysBetween(row['Request_Start_Date'], row['Request_End_Date'])
				if days < 0:
					days = 0
		except:
			days = 0
		details = {
			'woGroupId': _n('WO_Group_Id'), 'faultId': _n('Fault_Id'),
			'reasonId': _n('Reason_Id'), 'costCenterId': _n('Cost_Center_Id'),
			'accountId': _n('Account_Id'),
			'intrusive': str(row['Intrusive']) if row['Intrusive'] is not None else None,
			'durationInHours': row['Duration_In_Hours'],
			'downTime': row['Down_Time'],
			'supplierReqId': _n('Supplier_ID_Requested_By'),
			'userReqId': _n('User_ID_Requested_By'),
			'supplierChargeId': _n('Supplier_ID_charge_To'),
			'supplierRespId': _n('Supplier_ID_Responsibility'),
			'userRespId': _n('User_ID_Responsibility'),
			'woc1Id': _n('WOC1_ID'), 'woc2Id': _n('WOC2_ID'), 'woc3Id': _n('WOC3_ID'),
			'reference': str(row['Reference']).strip() if row['Reference'] else None,
		}
		notes = str(row['Notes']) if row['Notes'] else None
		res = create(str(row['WO_Title'] or '').strip() or 'Clone', locId, userId,
		             assetId=aId, priorityId=_n('Priority_Id'),
		             description=notes, details=details,
		             startDate=now, endDate=system.date.addDays(now, days))
		if not res or not res.get('woId'):
			return None
		newId = int(res['woId'])
		# .NET parity: clone lands as Pending (audited transition R->P)
		try:
			updateStatus(newId, 'P', userId)
		except:
			_log('clone: status->P failed for %s: %s' % (newId, sys.exc_info()[1]), level='warn')
		# Est_Cost copied (not a create() details key)
		try:
			if row['Est_Cost'] is not None:
				system.db.runPrepUpdate(
					"UPDATE dbo.WO_N_Details SET Est_Cost = ? WHERE WO_ID = ?",
					[row['Est_Cost'], newId], _DB)
		except:
			_log('clone: Est_Cost copy failed for %s: %s' % (newId, sys.exc_info()[1]), level='warn')
		_log('clone success: %s -> %s (%s)' % (hostWoId, newId, res.get('shortWoId')))
		return res
	except:
		_log('clone error host=%s: %s' % (hostWoId, sys.exc_info()[1]), level='error')
		return None


# ----------------------------------------------------------------------------
# delete  (v1.7.0 - .NET frmWOMaintenance DeleteRecord parity; hard delete D3)
# ----------------------------------------------------------------------------

def canDelete(woId):
	"""Pre-flight for the delete flow. Returns {'ok', 'reason', 'shortWoId',
	'title', 'status', 'meterCount'}. Never raises."""
	import sys
	out = {'ok': False, 'reason': '', 'shortWoId': '', 'title': '',
	       'status': '', 'meterCount': 0}
	try:
		ds = system.db.runPrepQuery(
			"SELECT RTRIM(h.Short_WO_Id) AS S, RTRIM(ISNULL(h.WO_Title,'')) AS T, "
			"       RTRIM(ISNULL(h.Status,'')) AS St, ISNULL(h.Purchase_Order_Flag,'0') AS PF "
			"FROM dbo.WO_N_Header h WHERE h.WO_ID = ?", [int(woId)], _DB)
		if ds is None or len(ds) == 0:
			out['reason'] = 'Work Order not found'
			return out
		out['shortWoId'] = str(ds[0]['S'] or '')
		out['title'] = str(ds[0]['T'] or '')
		st = str(ds[0]['St'] or '').strip()
		out['status'] = st
		if st == 'C':
			out['reason'] = 'Closed Work Orders cannot be deleted'
			return out
		if st == 'V':
			out['reason'] = 'Active Work Orders cannot be deleted'
			return out
		if str(ds[0]['PF'] or '0').strip() == '1':
			out['reason'] = 'This Work Order has Purchase Orders attached - it cannot be deleted'
			return out
		poDs = system.db.runPrepQuery(
			"SELECT (SELECT COUNT(*) FROM dbo.PO_Header WHERE WO_Id = ?) "
			"     + (SELECT COUNT(*) FROM dbo.PO_Details WHERE WO_Id = ?) AS N",
			[int(woId), int(woId)], _DB)
		if poDs is not None and len(poDs) > 0 and int(poDs[0]['N'] or 0) > 0:
			out['reason'] = 'This Work Order is referenced by Purchase Orders - it cannot be deleted'
			return out
		# v1.7.1: NO_ACTION FKs from the cascade probe - guard with clean reasons
		lcDs = system.db.runPrepQuery(
			"SELECT COUNT(*) AS N FROM dbo.WO_N_Header WHERE ISNULL(Linked_to_WO, 0) = ?",
			[int(woId)], _DB)
		if lcDs is not None and len(lcDs) > 0 and int(lcDs[0]['N'] or 0) > 0:
			out['reason'] = 'This Work Order has %s linked child WO(s) - delete the children first' % int(lcDs[0]['N'])
			return out
		ptDs = system.db.runPrepQuery(
			"SELECT (SELECT COUNT(*) FROM dbo.Part_Adjustment WHERE WO_ID = ?) "
			"     + (SELECT COUNT(*) FROM dbo.Part_Holding WHERE WO_ID = ?) AS N",
			[int(woId), int(woId)], _DB)
		if ptDs is not None and len(ptDs) > 0 and int(ptDs[0]['N'] or 0) > 0:
			out['reason'] = 'This Work Order has part issue/adjustment history - it cannot be deleted'
			return out
		mDs = system.db.runPrepQuery(
			"SELECT COUNT(*) AS N FROM dbo.Meter_Reading WHERE FROM_WO_ID = ?",
			[int(woId)], _DB)
		if mDs is not None and len(mDs) > 0:
			out['meterCount'] = int(mDs[0]['N'] or 0)
		out['ok'] = True
		return out
	except:
		out['reason'] = 'Validation error: %s' % sys.exc_info()[1]
		_log('canDelete error wo=%s: %s' % (woId, sys.exc_info()[1]), level='error')
		return out


def delete(woId, userId):
	"""Hard-delete a WO (.NET DeleteRecord parity, decision D3). Re-verifies
	canDelete server-side, detaches Meter_Reading.FROM_WO_ID, writes the
	event-history DELETE row (.NET order), then wmsp_WO_StatusDelete inside a
	transaction with a cascade verify - if the WO_N_Header row survives the
	status delete (no FK cascade), the transaction is ROLLED BACK and an error
	is logged. Returns {'ok', 'reason', 'shortWoId', 'metersDetached'}."""
	import sys
	_log('delete woId=%s by=%s' % (woId, userId))
	chk = canDelete(woId)
	res = {'ok': False, 'reason': chk.get('reason', ''),
	       'shortWoId': chk.get('shortWoId', ''), 'metersDetached': 0}
	if not chk.get('ok'):
		_guard('delete blocked wo=%s: %s' % (woId, chk.get('reason')))
		return res
	# .NET order: event history row first (best-effort; cascade may remove it,
	# which matches the legacy behaviour exactly)
	_logEvent(woId, 'DELETE', 'WO is Deleted from Database', userId)
	txId = None
	try:
		_NUM = 2
		txId = system.db.beginTransaction(_DB)
		if chk.get('meterCount', 0) > 0:
			n = system.db.runPrepUpdate(
				"UPDATE dbo.Meter_Reading SET FROM_WO_ID = NULL WHERE FROM_WO_ID = ?",
				[int(woId)], tx=txId)
			res['metersDetached'] = n
			_log('delete: detached %s meter reading(s) from WO %s' % (n, woId))
		_execProc('wmsp_WO_StatusDelete', [(_NUM, int(woId))], txId)
		left = system.db.runPrepQuery(
			"SELECT COUNT(*) AS N FROM dbo.WO_N_Header WHERE WO_ID = ?",
			[int(woId)], _DB, tx=txId)
		if left is not None and len(left) > 0 and int(left[0]['N'] or 0) > 0:
			system.db.rollbackTransaction(txId)
			system.db.closeTransaction(txId)
			txId = None
			res['reason'] = 'Delete aborted: no FK cascade from WO_Status (header row survived). Run the cascade probe.'
			_log(res['reason'], level='error')
			return res
		system.db.commitTransaction(txId)
		system.db.closeTransaction(txId)
		txId = None
		res['ok'] = True
		res['reason'] = ''
		_log('delete success: WO %s (%s) removed by %s'
		     % (woId, res['shortWoId'], userId))
		return res
	except:
		if txId is not None:
			try:
				system.db.rollbackTransaction(txId)
				system.db.closeTransaction(txId)
			except:
				pass
		res['reason'] = 'Delete error: %s' % sys.exc_info()[1]
		_log('delete error wo=%s: %s' % (woId, sys.exc_info()[1]), level='error')
		return res


# ----------------------------------------------------------------------------
# linked WOs  (v1.5.0 - .NET frmWOMaintenance ValidateLinkedWOCreation +
# GetNextLinkedWOSequence rules, ported verbatim)
# ----------------------------------------------------------------------------

def canCreateLinked(hostWoId):
	"""Validate + compute the next linked Short_WO_Id for a host WO.
	.NET rules: a PARENT's children take letter suffixes A-Z appended to the
	host Short_WO_Id; a linked CHILD's children take digit suffixes 1-9; a
	child whose own id already ends in a digit cannot link further (depth
	cap). Returns {'ok', 'reason', 'nextShortId', 'hostShortWoId',
	'hostTitle', 'hostAssetId', 'hostLocationId', 'hostWoGroupId',
	'hostIsChild'}. Never raises."""
	import sys
	out = {'ok': False, 'reason': '', 'nextShortId': '',
	       'hostShortWoId': '', 'hostTitle': '', 'hostAssetId': None,
	       'hostLocationId': None, 'hostWoGroupId': None, 'hostIsChild': False}
	try:
		ds = system.db.runPrepQuery(
			"SELECT h.Short_WO_Id, h.WO_Title, h.Asset_ID, h.Location_Id, "
			"       ISNULL(h.Linked_to_WO, 0) AS Linked_to_WO, d.WO_Group_Id "
			"FROM dbo.WO_N_Header h "
			"LEFT JOIN dbo.WO_N_Details d ON d.WO_ID = h.WO_ID "
			"WHERE h.WO_ID = ?", [int(hostWoId)], _DB)
		if ds is None or len(ds) == 0:
			out['reason'] = 'Work Order not found'
			return out
		row = ds[0]
		hostShort = str(row['Short_WO_Id'] or '').strip()
		out['hostShortWoId'] = hostShort
		out['hostTitle'] = str(row['WO_Title'] or '').strip()
		out['hostAssetId'] = int(row['Asset_ID']) if row['Asset_ID'] else None
		out['hostLocationId'] = int(row['Location_Id']) if row['Location_Id'] else None
		out['hostWoGroupId'] = int(row['WO_Group_Id']) if row['WO_Group_Id'] else None
		hostIsChild = int(row['Linked_to_WO'] or 0) > 0
		out['hostIsChild'] = hostIsChild
		if not hostShort:
			out['reason'] = 'Host WO has no Short WO Id'
			return out
		if hostIsChild and hostShort[-1:].isdigit():
			out['reason'] = 'Linked depth limit reached (%s cannot link further)' % hostShort
			return out
		# highest existing child suffix: LIKE host + single-char wildcard (.NET-exact)
		mx = system.db.runPrepQuery(
			"SELECT MAX(RTRIM(Short_WO_Id)) AS MaxId FROM dbo.WO_N_Header "
			"WHERE Short_WO_Id LIKE ?", [hostShort + '_'], _DB)
		maxId = None
		if mx is not None and len(mx) > 0 and mx[0]['MaxId']:
			maxId = str(mx[0]['MaxId']).strip()
		if not hostIsChild:
			# parent -> letter suffix A..Z
			if maxId is None:
				nxt = 'A'
			else:
				c = maxId[-1:]
				if c.isdigit():
					nxt = 'A'
				elif c.upper() >= 'Z':
					out['reason'] = 'Linked suffix pool exhausted (%sZ exists)' % hostShort
					return out
				else:
					nxt = chr(ord(c.upper()) + 1)
		else:
			# child -> digit suffix 1..9
			if maxId is None:
				nxt = '1'
			else:
				c = maxId[-1:]
				if not c.isdigit():
					nxt = '1'
				elif c >= '9':
					out['reason'] = 'Linked suffix pool exhausted (%s9 exists)' % hostShort
					return out
				else:
					nxt = str(int(c) + 1)
		out['ok'] = True
		out['nextShortId'] = hostShort + nxt
		_log('canCreateLinked host=%s (%s) -> next=%s'
		     % (hostWoId, 'child' if hostIsChild else 'parent', out['nextShortId']))
		return out
	except:
		out['reason'] = 'Validation error: %s' % sys.exc_info()[1]
		_log('canCreateLinked error host=%s: %s' % (hostWoId, sys.exc_info()[1]), level='error')
		return out


def version():
	return _VERSION