# =============================================================================
# workmate.identity  -  Session identity service
# Module:   workmate/identity/code.py
# Version:  1.1.1  (S4 security - resolveSecurity; 1.0.0 initial - resolve, self-healing AD map, no silent fallback)
# Author:   Adriaan
# Mirrors:  workmate.po_workflow / workmate.actions
# DB:       TLSQL01_Workmate
#
# INSTALL: Designer > Project Library > workmate > New Script "identity",
#          paste this file. Then paste Workmate_Session_Startup_v1_0_0.py
#          into Project Properties > Session Events > Startup, and define
#          session custom props wmUserId (0) and wmUserName ('') in Project
#          Properties so expression bindings subscribe reactively.
#
# Model (decision 2026-06-11):
#   One person = one gateway login (AD) + one Workmate user (authority lives
#   in User_Settings) + one Ignition_User_Map row joining them. Gateway roles
#   stay coarse (page access only); business authority is data.
#
# Resolution order:
#   1. Ignition_User_Map  (Ignition_Username match, Active='Y')
#   2. Users.AD_Login_ID  (Active='Y')  ->  auto-inserts the missing mapping
#      row so the next login takes path 1 (self-healing).
#   3. Unresolvable -> 0. NEVER a default user - a wrong audit identity is
#      worse than a blocked action (Forensic Audit incident, 2026-06-11).
#
# The auto-insert is best-effort: if Ignition_User_Map has columns this
# module doesn't know about (table is post-CSV-extract), the insert may fail
# - resolution still returns the AD-matched ID and logs the failure so the
# schema can be confirmed and the insert updated.
#
# 1.1.0 additions (2026-06-27, Security S4)
#   resolveSecurity(wmUserId) -> {'secGroupId', 'accessLevel'}
#     Legacy frmLogin model - lowest Sec_Group_Access_Level wins across
#     memberships (most privileged), same row supplies the group id.
#     Decision D5 - NO membership row -> {0, 0} = unassigned = NA everywhere.
#     Never the .NET fallback (auto-insert into group 1 ADMIN - a hole).
# =============================================================================

_VERSION = '1.1.1'
_DB = 'TLSQL01_Workmate'
_SOURCE = 'workmate.identity'


def _log(message, level='info'):
	"""Debug Console + dbo.Diag_Log persistence via workmate.diag (v1.1.1+).
	Never raises - logging must not break callers."""
	try:
		workmate.diag.log(_SOURCE, message, level)
	except:
		pass


def resolve(ignUsername):
	"""Ignition username -> Workmate User_Id. 0 when unresolvable.
	Self-heals: an AD_Login_ID match auto-creates the mapping row."""
	import sys
	name = str(ignUsername or '').strip()
	if not name:
		return 0

	# 1. explicit mapping
	try:
		ds = system.db.runPrepQuery(
			"SELECT Workmate_User_ID FROM Ignition_User_Map "
			"WHERE RTRIM(Ignition_Username) = ? AND Active = 'Y'",
			[name], _DB)
		if ds.getRowCount() > 0:
			wmId = int(ds.getValueAt(0, 'Workmate_User_ID') or 0)
			if wmId > 0:
				return wmId
	except:
		_log('resolve: mapping lookup failed for %r: %s'
		     % (name, sys.exc_info()[1]), level='error')

	# 2. AD_Login_ID on the Workmate user (case-insensitive trim match)
	try:
		ds = system.db.runPrepQuery(
			"SELECT User_Id, RTRIM(User_Name) AS UN FROM Users "
			"WHERE RTRIM(ISNULL(AD_Login_ID,'')) <> '' "
			"AND LOWER(RTRIM(AD_Login_ID)) = LOWER(?) AND Active = 'Y'",
			[name], _DB)
		if ds.getRowCount() > 0:
			wmId = int(ds.getValueAt(0, 'User_Id') or 0)
			if wmId > 0:
				_log('resolve: %r matched Users.AD_Login_ID -> %s (%s); auto-mapping'
				     % (name, wmId, str(ds.getValueAt(0, 'UN') or '').strip()))
				_autoMap(name, wmId)
				return wmId
	except:
		_log('resolve: AD_Login_ID lookup failed for %r: %s'
		     % (name, sys.exc_info()[1]), level='error')

	_log('resolve: NO Workmate identity for %r - returning 0 (writes must block)'
	     % name, level='warn')
	return 0


def _autoMap(ignUsername, wmUserId):
	"""Best-effort insert of the missing Ignition_User_Map row. Failure is
	logged, never raised - resolution does not depend on it."""
	import sys
	try:
		exists = system.db.runPrepQuery(
			"SELECT Workmate_User_ID FROM Ignition_User_Map "
			"WHERE RTRIM(Ignition_Username) = ?", [str(ignUsername)], _DB)
		if exists.getRowCount() > 0:
			# row exists but inactive / different ID - do not fight it silently
			_log('_autoMap: row already exists for %r (check Active flag / ID '
			     'in User Mapping)' % ignUsername, level='warn')
			return False
		system.db.runPrepUpdate(
			"INSERT INTO Ignition_User_Map (Ignition_Username, Workmate_User_ID, Active) "
			"VALUES (?, ?, 'Y')", [str(ignUsername), int(wmUserId)], _DB)
		_log('_autoMap: created mapping %r -> %s' % (ignUsername, wmUserId))
		return True
	except:
		_log('_autoMap: insert failed for %r -> %s: %s (confirm Ignition_User_Map '
		     'schema and update workmate.identity)' %
		     (ignUsername, wmUserId, sys.exc_info()[1]), level='error')
		return False


def displayName(wmUserId):
	"""'User Name (#id, SHORT)' for audit display, '' when unknown."""
	try:
		uid = int(wmUserId or 0)
		if uid <= 0:
			return ''
		ds = system.db.runPrepQuery(
			"SELECT RTRIM(ISNULL(User_Name,'')) AS N, "
			"RTRIM(ISNULL(Short_User_Id,'')) AS S "
			"FROM Users WHERE User_Id = ?", [uid], _DB)
		if ds.getRowCount() == 0:
			return ''
		return '%s (#%s, %s)' % (str(ds.getValueAt(0, 'N')).strip(), uid,
		                         str(ds.getValueAt(0, 'S')).strip())
	except:
		return ''


def mappingState(ignUsername):
	"""Diagnostic for the Forensic Audit tab: how does this login resolve?
	Returns {'ignUser', 'mapRow', 'mapActive', 'mappedId', 'adMatchId',
	         'resolvedId'} - read-only, no auto-map side effects."""
	name = str(ignUsername or '').strip()
	out = {'ignUser': name, 'mapRow': False, 'mapActive': False,
	       'mappedId': 0, 'adMatchId': 0, 'resolvedId': 0}
	if not name:
		return out
	try:
		ds = system.db.runPrepQuery(
			"SELECT Workmate_User_ID, RTRIM(ISNULL(Active,'N')) AS A "
			"FROM Ignition_User_Map WHERE RTRIM(Ignition_Username) = ?",
			[name], _DB)
		if ds.getRowCount() > 0:
			out['mapRow'] = True
			out['mapActive'] = (str(ds.getValueAt(0, 'A')).strip() == 'Y')
			out['mappedId'] = int(ds.getValueAt(0, 'Workmate_User_ID') or 0)
	except:
		pass
	try:
		ds = system.db.runPrepQuery(
			"SELECT User_Id FROM Users WHERE RTRIM(ISNULL(AD_Login_ID,'')) <> '' "
			"AND LOWER(RTRIM(AD_Login_ID)) = LOWER(?) AND Active = 'Y'",
			[name], _DB)
		if ds.getRowCount() > 0:
			out['adMatchId'] = int(ds.getValueAt(0, 'User_Id') or 0)
	except:
		pass
	if out['mapRow'] and out['mapActive'] and out['mappedId'] > 0:
		out['resolvedId'] = out['mappedId']
	elif out['adMatchId'] > 0:
		out['resolvedId'] = out['adMatchId']
	return out


def resolveSecurity(wmUserId):
	"""Workmate User_Id -> {'secGroupId': int, 'accessLevel': int}.
	Lowest access level wins (1 Admin .. 4 RO); ties break on lowest group id.
	D5 - unassigned or unresolvable returns {0, 0} (treated as NA)."""
	import sys
	out = {'secGroupId': 0, 'accessLevel': 0}
	try:
		uid = int(wmUserId or 0)
		if uid <= 0:
			return out
		ds = system.db.runPrepQuery(
			"SELECT sg.Sec_Group_ID, sg.Sec_Group_Access_Level "
			"FROM User_Security_Group usg "
			"JOIN Security_Group sg ON sg.Sec_Group_ID = usg.Sec_Group_ID "
			"WHERE usg.User_ID = ? "
			"ORDER BY sg.Sec_Group_Access_Level ASC, sg.Sec_Group_ID ASC "
			"OFFSET 0 ROWS FETCH FIRST 1 ROWS ONLY",
			[uid], _DB)
		if ds.getRowCount() > 0:
			out['secGroupId'] = int(ds.getValueAt(0, 'Sec_Group_ID') or 0)
			out['accessLevel'] = int(ds.getValueAt(0, 'Sec_Group_Access_Level') or 0)
		else:
			_log('resolveSecurity: user %s has NO security group - NA (D5, '
			     'no ADMIN fallback)' % uid, level='warn')
	except:
		_log('resolveSecurity failed for %s: %s'
		     % (wmUserId, sys.exc_info()[1]), level='error')
	return out


def version():
	return _VERSION