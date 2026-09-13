# ==============================================================================
# workmate.pm_engine  -  PM release engine (correctness-first) - DRY RUN
# File:     ignition/script-python/workmate/pm_engine/code.py
# Version:  2.5.0
# Author:   Claude (for Adriaan)
# ==============================================================================
# Notation: 'S<n>' = section <n> of Workmate_P-PM5a_Engine_Extraction v1.1.0.
# Design:   Workmate_P-PM5_Engine_Design v1.0.0 (signed off 2026-07-25).
#           P-PM5d Repeat12/Rebase Spec v1.0.0 (signed off 2026-07-26).
#           P-PM5d-3 BlockScope+X Spec v1.0.1 (Q1-Q3 signed 2026-07-27).
# ==============================================================================
# Changelog (newest first):
#   2.5.0  P-PLN1 slice S3 - the PLANNER PIN (Planner Calendar spec v1.1.0,
#          D-3). A work order whose row in dbo.WO_N_Plan carries Pinned='Y'
#          is FROZEN for releaseDecision: never re-dated, never re-released
#          (F-1 identity still holds - no duplicate). The planner sets the
#          pin when it moves a PM work order; unpinning hands the date back
#          to the engine on the next run. matchedWOs() reads the pin with a
#          correlated subquery ONLY when the table exists (pinTableExists(),
#          INFORMATION_SCHEMA, True cached) - a gateway without the S3 DDL
#          runs byte-identical to 2.4.0. Still zero DML.
#   2.4.0  P-PM5d slice 5d-4a - mastersFor(woIds): ANY-status display
#          read for the Block console (the console must render non-'A'
#          selections as "not Active", which activeMasters rightly
#          filters). Parameterised IN, ordered by Short_WO_Id, zero DML.
#          Nothing else changed.
#   2.3.0  P-PM5d slice 5d-3a - Block scope + X-awareness (spec 3, Q1-Q3).
#          Still zero DML. Omitting the new arguments is 2.2.0 exactly.
#
#          plan(upTo=, woIds=): upTo is .NET's RELEASE_UPTO_DATE slot - the
#          horizon becomes dayKey <= dayKey(upTo) instead of asOf+WO_WINDOW,
#          nothing else changes (rails included: a far upTo can and should
#          trip perRun/perMaster, that is the guard working). woIds is the
#          Block console's master scope, parameterised IN only (BX-5) -
#          non-Active selections are reported, not planned. Named plan-level
#          errors, no work attempted: 'scope-ambiguous' (woId AND woIds),
#          'scope-empty' ([] never means everything), 'scope-bad-id',
#          'upto-unparseable', 'upto-before-asof'.
#
#          Q2 EXTENSION x X: new read xDatesFor() - (Task_Id CHAR(160)-
#          normalised, dayKey) pairs from WO_X_Subtasks. An extension
#          occurrence landing on an X-held date is withheld: no id burned,
#          the cadence step consumed (X = cadence ghost, matching .NET's
#          release re-anchor UNION). Per task 'xHeld' dayKeys + counters
#          skipX; per event a warn log 'skip-x'. X unreadable -> extension
#          behaves as 2.2.0 (no silent skipping on a guess) and the plan
#          carries a stub saying so. Repeat12 tasks unchanged here (their
#          own X refusal is lifted on the WRITE side in 1.4.0, per Q1(b)).
#          Rail: window rows whose id ends '-X' are reported as
#          'windowXDrift' (legacy drift surfacing; behaviour unchanged).
#
#          Q3 SKIP-IDLEN: masters whose base id exceeds 15 chars are a
#          named whole-master skip (masterSkip='SKIP-IDLEN...'), zero
#          occurrences considered - uniform across timer/console/Block,
#          deliberately wider than .NET's message-only warning (BX-3).
#          Q3's RoC naming is already satisfied by 2.2.0's SKIP-CM-RATE
#          (spec 3 v1.0.1 errata) - no new name.
#
#          Counters gained skipX and skipIdlen; report() untouched (new
#          fields visible in the raw plan dict).
#   2.2.0  P-PM5d slice 5d-1 - Repeat12 lifecycle PLANNED, rebase decisions.
#          Still zero DML; the write side is pm_engine_db 1.3.0 (5d-2).
#
#          REPEAT12 ADOPTED (D-PM5-6a). 'Y' tasks are window-driven: no
#          frequency extends; each RELEASE/UPDATE of a window occurrence
#          plans a LIFECYCLE pair - consume the WO_M_Subtasks row, append a
#          replacement at occurrence date + 'PM WM Horizon' months - into
#          plan['masters'][i]['repeat12']. db 1.2.1 reads only release/
#          update, so applying a 2.2.0 plan with the old writer releases
#          NOTHING for Repeat12 tasks: the interim is safe by construction,
#          never half-applied. FROZEN Repeat12 occurrences are reported and
#          their window rows left alone (per spec - conservative; the
#          window does not roll until a human resolves the freeze).
#          Named .NET divergences: N-A append ids are always a fresh
#          sequence, never '-S' sibling-share (extraction 14.3.6); N-B
#          Entry_date is never rewritten (D13); N-C no TEMP_PMR_Repeat12 -
#          the plan is in memory and that table stays .NET's scratchpad
#          (D11); N-D consume+append will ride the release's own F-3
#          transaction (5d-2), replacing .NET's two-pass + global staging.
#
#          THE 2.1.0 LATENT FINDING (spec S0) FIXED: the candidate loop ran
#          over ALL materialised subtasks, so a Repeat12 (or otherwise
#          skipped) task's occurrences would release while the engine
#          refused to maintain the task - shrinking a Repeat12 window every
#          run until the task silently died. Now a skipped task's subtasks
#          are excluded from candidates entirely: a task the engine refuses
#          to maintain is a task it refuses to act on. Refusals are named:
#          SKIP-REPEAT12-CM (Repeat12 on a CM task - unspecified in source),
#          SKIP-REPEAT12-X (WO_X_Subtasks present or unreadable - X
#          interplay unread), SKIP-REPEAT12-HORIZON ('PM WM Horizon'
#          unparseable), SKIP-REPEAT12-SEQ (no fresh id in the walk).
#
#          REBASE DECISIONS (D-PM5-7): rebaseAnchor() - restartOn, or one
#          full frequency past the newest spared work order, using the
#          CD_Freq+CM_Freq sum with .NET rounding (S1; fixes .NET's own
#          Block-rebuild inconsistency, extraction D10). The op itself is
#          pm_engine_db.rebase() in 5d-2.
#
#          Rails extended: lifecycle pairs count as releases (1:1 with a
#          write) in perRun/perMaster/duplicate/same-date; new
#          'repeat12Append' ABORT rail - duplicate append ids, an append id
#          colliding with a planned occurrence, or an append not strictly
#          after its occurrence. freshSubtaskId() walks the master-wide
#          sequence for appends. plan()/report() gained repeat12 counts.
#   2.1.0  medianMultiple rail given a minimum sample size, and its input
#          narrowed to runs that actually released something.
#          With a 5-minute timer the great majority of ticks release nothing.
#          A median taken over all runs therefore sits at 0, and the rail only
#          fires when med > 0 - so it would have been permanently dead exactly
#          when it matters. Callers now pass only non-zero release counts
#          (pm_engine_db.history() does this), and fewer than
#          _MEDIAN_MIN_SAMPLES of them reports SKIPPED rather than acting: a
#          median of one run is not a median, and aborting on it would be
#          worse than not checking.
#          No other behaviour changed.
#   2.0.0  MAJOR - parity is no longer the specification. Andrew reported .NET
#          occasionally releasing ~400 work orders for one work order; the
#          source read found the mechanism, so we now diverge on purpose where
#          .NET is wrong, and each divergence is named and tested.
#
#          F-1 RELEASE IDENTITY IS NO LONGER DATE-SENSITIVE (the 400 fix).
#          .NET asks "does a WO exist with this id AND this exact date?" so the
#          moment an occurrence's date moves - a CD_Freq edit, a Start_Date
#          change, a Block Update, a meter rate drifting - every previously
#          released occurrence of that master stops matching and is released
#          again. With PM WM Horizon = 12 months a weekly task is ~52
#          occurrences, so one master reaches the hundreds in a single pass.
#          Now: an occurrence is released if ANY work order carries its subtask
#          id (raw or -S-stripped) in WO_N_Header or WO_C_header, with NO date
#          condition. A date change becomes an UPDATE of the existing work
#          order, never a second one. WO_N_Subtasks already records
#          Short_SubTask_ID per released WO, so the ledger is already in schema.
#
#          F-4 RUNAWAY RAILS, checked on the PLAN before any write exists:
#          per-run cap, per-master cap, per-task occurrence cap, zero tolerance
#          for a duplicate stripped id or two releases on the same master+date,
#          and a rolling-median multiple (history store lands in 5c-3; until
#          then that rail reports SKIPPED rather than pretending to pass).
#
#          D-PM5-1 ONE WORK ORDER PER TASK. .NET merges tasks sharing a
#          Week_No into a single WO (Syncronise_All_PM_Task, S9a). We do not.
#          Simpler, matches the PMx model, and drops a large slice of .NET
#          complexity. Syncronise_All_PM_Task is deliberately NOT read.
#
#          F-5 correctness fixes from the source read:
#            D2  CM meter-due trigger implemented - a subtask whose
#                Meter_Reading is below the meter's Last_Reading_Value is due
#                regardless of date (S2.3). 1.x missed this entirely and would
#                under-release every meter PM.
#            D4  Task_Id comparisons strip CHAR(160). Task ids carry
#                non-breaking spaces; RTRIM does not remove them and the join
#                silently misses. .NET does this in 16 places.
#            D5  frequency is CAST(CD_Freq)+CAST(CM_Freq) coerced with .NET
#                rounding (half-to-EVEN), not CD_Freq truncated. 3.5 -> 4,
#                where Python int() gives 3.
#            D6  PO linkage is the UNION of PO_Header.WO_Id and
#                PO_Details.WO_Id - stricter than either engine alone.
#
#          STRUCTURE: the decision surface is now pure functions taking dicts
#          (occurrencesFor / releaseDecision / checkRails). They touch no
#          database, so the Night Shift pack can drive every rule without one.
#          DB access is confined to the adapters in the reads section.
#
#          Still DRY RUN. There is no INSERT/UPDATE/DELETE in this module.
#   1.3.0  Week_No corrected from source (verbatim GetWeekNoANDYear port,
#          stored as the double YYYY.WW); diagnostics attribution via
#          session=/actor=; stopped double-printing.
#   1.2.0  Week_No rule pinned (superseded by 1.3.0).
#   1.1.0  Settings correctness: 'PM WM Horizon' (WM, not WO) and the
#          space-separated PM_WO_Settings key convention. NOTE: 1.1.0 also
#          captured 'WRoC %' and four 'Insp. ...' settings as S9.1 operands.
#          That was WRONG - those six strings appear ZERO times in
#          frmReleasePMWO and belong to frmSystemConfig. The real projection is
#          one division (S2.2). meterConfig() is kept for reference only and is
#          explicitly NOT engine input.
#   1.0.0  P-PM5b slice 1, parity port per extraction pack v1.0.0.
# ==============================================================================
# Usage (Script Console):
#   print workmate.pm_engine.version()            # 2.0.0
#   print workmate.pm_engine.config()
#   p = workmate.pm_engine.plan(actor='console')
#   print workmate.pm_engine.report(p)
# Tests: workmate.pm_engine_test.run()
# ==============================================================================

import math

_VERSION = '2.5.0'
_SOURCE = 'workmate.pm_engine'
_DB = 'TLSQL01_Workmate'
_MODULE_CODE = 'PMENGINE'

# --- config keys ------------------------------------------------------------
# System_Configuration keys are UPPER_SNAKE; PM_WO_Settings keys are
# space-separated prose. Both verified against a live dump 2026-07-25 - do not
# re-guess either spelling.
_KEY_WO_WINDOW = 'WO_WINDOW'
_MAX_BASE_ID_LEN = 15   # Q3/BX-3: .NET's rebuild boundary, now enforced by name
_KEY_REBUILD_DEL = 'PM_REBUILD_DELETE_RELEASED'
_KEY_METER_TASK_DELETE = 'ENABLE_METER_PMTASK_DELETE'
_KEY_PM_HORIZON = 'PM WM Horizon'
_KEY_UPDATE_INTERVAL = 'Update PM Sch. Interval'
_KEY_PLANNED_RELEASE = 'Planned WO Release'

_HORIZON_FALLBACK_DAYS = 30
_SEQ_WIDTH_DEFAULT = 4
_FRESH_SEQ_WALK = 500

# --- F-4 rails --------------------------------------------------------------
# Breaching a hard rail aborts and writes nothing; it is never a silent
# truncation. Defaults are D-PM5-3 and deliberately conservative for KT.
# Below this many usable history points the median rail reports SKIPPED
# instead of judging - see 2.1.0.
_MEDIAN_MIN_SAMPLES = 3

_RAILS = {
	'perRun': 50,
	'perMaster': 8,
	'perTask': 200,
	'medianMultiple': 5.0,
}

# --- F-1 / releaseDecision --------------------------------------------------
# A work order in one of these states is never re-dated and never re-released:
# work has started, finished, or been cancelled. This is .NET's set (S6).
# 'F' (Deferred) is a CANDIDATE for this list - deferring is a human decision
# about a date and re-dating it would undo them - but adding it is a divergence
# beyond what was signed off, so it is called out rather than assumed.
_FROZEN_STATUSES = ('V', 'C', 'D')

# --- P-PLN1 S3 planner pin --------------------------------------------------
# dbo.WO_N_Plan (WO_ID PK, Pinned char(1), Pinned_By, Pinned_On, Prev_Start,
# Note ...) is created by Workmate_DDL_WO_N_Plan_v1_0_0.py. Pinned='Y' =
# the planner owns this work order's date; the engine treats it as FROZEN.
_PIN_TABLE = 'WO_N_Plan'
_pinTableKnown = False      # cache True only - a later CREATE is picked up


def version():
	return _VERSION


# ---------------------------------------------------------------------------
# plumbing (bare except + cause chain: Jython's 'except Exception' does not
# catch java.lang.Exception)
# ---------------------------------------------------------------------------

def _err():
	import sys
	e = sys.exc_info()[1]
	parts = [str(e)]
	c = getattr(e, 'cause', None)
	n = 0
	while c is not None and n < 3:
		parts.append('CAUSED BY: ' + str(c))
		c = getattr(c, 'cause', None)
		n += 1
	return ' | '.join(parts)


def _log(sink, message, level='info', session=None):
	"""Run-scoped log list plus the forensic channels. session is the ONLY way
	the Diagnostics Viewer fills its User column (diag reads
	session.custom.wmUserId); a gateway timer has none by nature - use actor=.
	diag._send already falls back to print with no Perspective session, so we
	print only if the diag call itself was unavailable."""
	if sink is not None:
		sink.append('%-5s %s' % (level.upper(), message))
	sent = False
	try:
		workmate.diag.log(_SOURCE, message, level, session)
		sent = True
	except:
		pass
	if not sent:
		try:
			print '[%s] %s %s' % (_SOURCE, level.upper(), message)
		except:
			pass


def _i(v):
	try:
		if v is None or str(v).strip() == '':
			return None
		return int(float(str(v).strip()))
	except:
		return None


def _f(v):
	try:
		if v is None or str(v).strip() == '':
			return None
		return float(str(v).strip())
	except:
		return None


def _s(v):
	return '' if v is None else str(v).strip()


def _tid(v):
	"""D4: normalise a Task_Id. Task ids carry CHAR(160) non-breaking spaces
	which RTRIM does not touch; .NET strips them in 16 places.

	Filters by ORDINAL rather than replacing with a pattern: JDBC returns Java
	strings (Jython unicode), and mixing a u'\\u00a0' pattern into a
	byte-string replace raises UnicodeDecodeError on precisely the input this
	function exists to handle. keep[0][:0] yields an empty string of the same
	type as the input, so the join never coerces either way."""
	if v is None:
		return ''
	try:
		seq = list(v)
	except:
		seq = list(str(v))
	keep = []
	for ch in seq:
		try:
			o = ord(ch)
		except:
			continue
		if o in (160, 65279):		# NBSP, BOM
			continue
		keep.append(ch)
	if not keep:
		return ''
	return keep[0][:0].join(keep).strip()


def _netRound(x):
	"""D5: Convert.ToInt32(double) - round half to EVEN, .NET's rule.
	Python 2 round() goes half-away-from-zero, so 3.5 would give 4 but 2.5
	would give 3 where .NET gives 2."""
	if x is None:
		return None
	f = math.floor(x)
	diff = x - f
	if diff > 0.5:
		return int(f + 1)
	if diff < 0.5:
		return int(f)
	# exactly .5 -> pick the even neighbour
	fi = int(f)
	return fi if fi % 2 == 0 else fi + 1


def _toDate(v):
	if v is None:
		return None
	if hasattr(v, 'getTime'):
		return v
	s = str(v).strip()
	if ' GMT' in s:
		s = s.split(' GMT')[0].strip()
	for fmt in ['EEE MMM dd yyyy HH:mm:ss', 'yyyy-MM-dd HH:mm:ss',
	            'yyyy-MM-dd', 'dd/MM/yyyy']:
		try:
			return system.date.parse(s, fmt)
		except:
			pass
	return None


def _mid(d):
	return None if d is None else system.date.midnight(d)


def _dayKey(d):
	return '' if d is None else system.date.format(d, 'yyyy-MM-dd')


def _scalar(sql, params=None):
	return system.db.runScalarPrepQuery(sql, params or [], _DB)


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


# ---------------------------------------------------------------------------
# settings (S3)
# ---------------------------------------------------------------------------

def systemConfig(key):
	try:
		v = _scalar(
			"SELECT RTRIM(ISNULL(System_ConfigVal, '')) "
			"FROM dbo.System_Configuration "
			"WHERE RTRIM(System_ConfigCol) = ?", [str(key)])
		s = _s(v)
		return s if s != '' else None
	except:
		return None


def pmWoSetting(key):
	try:
		v = _scalar(
			"SELECT RTRIM(ISNULL(PM_WO_SettingVal, '')) "
			"FROM dbo.PM_WO_Settings "
			"WHERE RTRIM(PM_WO_SettingCol) = ?", [str(key)])
		s = _s(v)
		return s if s != '' else None
	except:
		return None


def gateEnabled():
	"""Module_Settings PMENGINE gate. Missing table/row => disabled.
	2.0.0 has no write path, so this is reported, not obeyed."""
	try:
		v = _scalar("SELECT Is_Enabled FROM dbo.Module_Settings "
			"WHERE Module_Code = ?", [_MODULE_CODE])
		return _s(v).upper() == 'Y'
	except:
		return False


def meterConfig():
	"""REFERENCE ONLY - NOT engine input. Engine 1.1.0 wrongly recorded these
	as S9.1 operands; they appear nowhere in frmReleasePMWO (see 1.1.0 note in
	the changelog). Kept because they are still the plant's meter-inspection
	tuning and someone will ask."""
	return {
		'wrocPct': _f(pmWoSetting('WRoC %')),
		'inspMeterRatio': _f(pmWoSetting('Insp. Meter Ratio')),
		'inspPreHighDays': _i(pmWoSetting('Insp. Pre High Ratio Days')),
		'inspPostHighDays': _i(pmWoSetting('Insp. Post High Ratio Days')),
		'inspPreLowDays': _i(pmWoSetting('Insp. Pre Low Ratio Days')),
		'meterTaskDelete': systemConfig(_KEY_METER_TASK_DELETE),
		'NOTE': 'reference only - not used by the engine',
	}


def config():
	raw = systemConfig(_KEY_WO_WINDOW)
	days = _i(raw)
	return {
		'woWindowRaw': raw,
		'woWindowDays': days if days is not None else _HORIZON_FALLBACK_DAYS,
		'horizonSource': 'System_Configuration.WO_WINDOW'
			if days is not None else 'FALLBACK (WO_WINDOW unreadable)',
		'rebuildDeleteReleased': systemConfig(_KEY_REBUILD_DEL),
		'pmHorizonMonths': _i(pmWoSetting(_KEY_PM_HORIZON)),
		'pmHorizonRaw': pmWoSetting(_KEY_PM_HORIZON),
		'netUpdateIntervalDays': _i(pmWoSetting(_KEY_UPDATE_INTERVAL)),
		'plannedWoRelease': pmWoSetting(_KEY_PLANNED_RELEASE),
		'gate': gateEnabled(),
		'rails': dict(_RAILS),
		'frozenStatuses': list(_FROZEN_STATUSES),
		'weekNoSample': weekNoAndYear(system.date.now()),
		'db': _DB,
		'version': _VERSION,
	}


# ---------------------------------------------------------------------------
# GetWeekNoANDYear - VERBATIM PORT (S9.2)
# ---------------------------------------------------------------------------
# clsGeneralOperation.GetWeekNoANDYear (source 871-908) transcribed
# line-for-line. Returns 'YYYY.WW'; frmReleasePMWO 983 stores
# Convert.ToDouble() of it, so Week_No holds e.g. 2026.53. WO_N_Header.Week_No
# is COPIED from the subtask (source 261/376), never recomputed.
# Verified: 306/306 against .NET-written values on dev, and equivalent to
# ISO-8601 week-year+week on all 14,975 dates 2000-2040. Kept verbatim anyway
# so any divergence is a diff against source, not an argument about calendars.
# .NET DayOfWeek is Sunday=0..Saturday=6; the source maps 0 -> 7.

def _netDayOfWeek(d):
	return int(system.date.getDayOfWeek(d)) - 1


def _netWeekNoAndYear(date, _depth=0):
	d = _toDate(date)
	if d is None or _depth > 2:
		return None
	year = int(system.date.getYear(d))
	num = year
	dayOfYear = int(system.date.getDayOfYear(d))
	num2 = _netDayOfWeek(system.date.getDate(year, 0, 1))
	num3 = _netDayOfWeek(system.date.getDate(year, 11, 31))
	if num2 == 0:
		num2 = 7
	if num3 == 0:
		num3 = 7
	num4 = 8 - num2
	flag = (num2 == 4 or num3 == 4)
	num6 = int(math.ceil(float(dayOfYear - num4) / 7.0))
	if num4 >= 4:
		num6 = num6 + 1
	if num6 > 52 and not flag:
		num6 = 1
		num = num + 1
	if num6 == 0:
		num = num - 1
		prev = _netWeekNoAndYear(system.date.getDate(year - 1, 11, 31),
			_depth + 1)
		if prev is None:
			return None
		num6 = int(prev.split('.')[1])
	return '%d.%02d' % (num, num6)


def weekNoAndYear(date):
	return _netWeekNoAndYear(date)


def weekNo(date):
	"""Week_No as stored: Convert.ToDouble('YYYY.WW') -> 2026.53."""
	s = _netWeekNoAndYear(date)
	if s is None:
		return None
	try:
		return float(s)
	except:
		return None


# ---------------------------------------------------------------------------
# identity (S5)
# ---------------------------------------------------------------------------

def stripS(shortId):
	s = _s(shortId)
	if len(s) > 2 and s[-2:] == '-S':
		return s[:-2]
	return s


def _seqWidth(existingIds):
	for sid in existingIds:
		s = stripS(sid)
		if '-' in s:
			tail = s.rsplit('-', 1)[1]
			if tail.isdigit():
				return len(tail)
	return _SEQ_WIDTH_DEFAULT


def nextSubtaskId(shortWoId, seq, width, taken):
	base = '%s-%0*d' % (_s(shortWoId), width, int(seq))
	if base in taken:
		return base + '-S', True
	return base, False


def freshSubtaskId(shortWoId, state, maxWalk=None):
	"""Next '-NNNN' id that is NOT already taken - NEVER returns an -S form.
	Spec N-A / D-PM5-6a: appended (and rebased) occurrences always get their
	own sequence number; '-S' sibling-share is retired with the sync merge.
	Advances state['seq'] and registers the id in state['taken'].
	Returns the id, or None if maxWalk numbers were all taken (caller
	refuses with SKIP-REPEAT12-SEQ - never guesses)."""
	walk = int(maxWalk or _FRESH_SEQ_WALK)
	for _n in range(walk):
		state['seq'] += 1
		sid, suffixed = nextSubtaskId(shortWoId, state['seq'],
			state['width'], state['taken'])
		if not suffixed:
			state['taken'].add(sid)
			return sid
	return None


# ===========================================================================
# PURE DECISIONS - no database, fully testable from dicts
# ===========================================================================

def advance(date, n, unit):
	"""S1: 'D' AddDays(n) | 'W' AddDays(n*7) | 'M' AddMonths(n).
	Unit defaults to 'W' per WO_M_details.Freq_Unit ISNULL(...,'W')."""
	d = _toDate(date)
	if d is None:
		return None
	u = (_s(unit) or 'W').upper()[:1]
	try:
		k = int(n)
	except:
		return None
	if k == 0:
		return None
	if u == 'D':
		return system.date.addDays(d, k)
	if u == 'M':
		return system.date.addMonths(d, k)
	if u == 'W':
		return system.date.addDays(d, k * 7)
	return None


def freqOf(task):
	"""D5: CAST(CD_Freq AS float) + CAST(CM_Freq AS float), then .NET rounding.
	Returns (freqInt, rawSum, reason). reason is None when usable."""
	cd = _f(task.get('CD_Freq'))
	cm = _f(task.get('CM_Freq'))
	if cd is None and cm is None:
		return None, None, 'CD_Freq and CM_Freq are both empty'
	raw = (cd or 0.0) + (cm or 0.0)
	n = _netRound(raw)
	if n is None or n <= 0:
		return None, raw, 'frequency resolves to %r - not a positive number' % raw
	return n, raw, None


def occurrencesFor(firstDate, freq, unit, horizonTo, cap=None):
	"""PURE. Dates from firstDate stepping by (freq, unit) while <= horizonTo.
	Returns {'dates', 'capped', 'reason'}. A freq that cannot advance the date
	returns a reason rather than looping - the mechanism that lets .NET pile
	occurrences onto one date forever."""
	if cap is None:
		cap = _RAILS['perTask']
	out = {'dates': [], 'capped': False, 'reason': None}
	d = _mid(_toDate(firstDate))
	h = _mid(_toDate(horizonTo))
	if d is None:
		out['reason'] = 'no first date'
		return out
	if h is None:
		out['reason'] = 'no horizon'
		return out
	try:
		if int(freq) <= 0:
			out['reason'] = 'frequency %r does not advance the date' % freq
			return out
	except:
		out['reason'] = 'frequency %r is not a number' % freq
		return out
	n = 0
	while d is not None and not system.date.isAfter(d, h):
		if n >= cap:
			out['capped'] = True
			out['reason'] = ('per-task cap %d reached - refusing to generate '
				'more' % cap)
			break
		out['dates'].append(d)
		n += 1
		nxt = advance(d, freq, unit)
		if nxt is None or not system.date.isAfter(nxt, d):
			out['reason'] = ('step did not advance past %s - stopping'
				% _dayKey(d))
			break
		d = nxt
	return out


def releaseDecision(occ, matched, frozenStatuses=None):
	"""PURE. F-1 / D-PM5-2. The whole release rule.

	occ      {'subId','strippedId','dayKey'}
	matched  work orders carrying that id in EITHER form, from WO_N_Header or
	         WO_C_header, with NO date filter. Each:
	         {'src','woId','dayKey','status','poLinked'}

	Returns (action, reason) where action is one of:
	  'RELEASE'  no work order exists for this occurrence - create one
	  'UPDATE'   one exists on a different date - re-date it, do NOT duplicate
	  'SKIP'     one exists on this date - nothing to do
	  'FROZEN'   exists but must not be touched (started/finished/cancelled,
	             PO- or meter-linked, planner-pinned, or ambiguous)
	2.5.0: a matched row with pinned=True (WO_N_Plan.Pinned='Y') is FROZEN -
	the planner owns its date. Checked after status, before ambiguity.
	"""
	if frozenStatuses is None:
		frozenStatuses = _FROZEN_STATUSES
	if not matched:
		return 'RELEASE', 'no work order carries %s' % occ.get('strippedId')

	linked = [m for m in matched if m.get('poLinked')]
	if linked:
		m = linked[0]
		return 'FROZEN', ('%s WO %s is PO/meter linked - never re-dated or '
			're-released' % (m.get('src'), m.get('woId')))

	frozen = [m for m in matched if _s(m.get('status')).upper()
		in frozenStatuses]
	if frozen:
		m = frozen[0]
		return 'FROZEN', ('%s WO %s is status %s - work started, finished or '
			'cancelled' % (m.get('src'), m.get('woId'), m.get('status')))

	pinned = [m for m in matched if m.get('pinned')]
	if pinned:
		m = pinned[0]
		return 'FROZEN', ('%s WO %s is planner-pinned (WO_N_Plan) - the '
			'planner owns its date; unpin to hand it back'
			% (m.get('src'), m.get('woId')))

	if len(matched) > 1:
		return 'FROZEN', ('%d work orders carry this id (%s) - ambiguous, a '
			'human must resolve it' % (len(matched),
			', '.join([str(m.get('woId')) for m in matched])))

	m = matched[0]
	if _s(m.get('dayKey')) == _s(occ.get('dayKey')):
		return 'SKIP', ('already released as %s WO %s on %s'
			% (m.get('src'), m.get('woId'), m.get('dayKey')))

	return 'UPDATE', ('re-date %s WO %s from %s to %s (F-1: one work order '
		'per occurrence, dates move)' % (m.get('src'), m.get('woId'),
		m.get('dayKey'), occ.get('dayKey')))


def rebaseAnchor(restartOn, sparedMax, freq, unit):
	"""PURE. D-PM5-7 catch-up rule for rebase(): the new anchor is restartOn,
	unless a spared (protected) work order sits ON or AFTER it, in which
	case the anchor steps one full frequency past the newest spared date -
	so the regenerated window can never collide with protected work.
	freq is the CD_Freq+CM_Freq sum with .NET half-to-even rounding (S1 -
	deliberately fixing .NET's Block rebuild, which used CD_Freq alone,
	extraction D10). Returns (anchorDate, why) or (None, why)."""
	r = _mid(_toDate(restartOn))
	if r is None:
		return None, 'restartOn unreadable: %r' % (restartOn,)
	s = _mid(_toDate(sparedMax)) if sparedMax is not None else None
	if s is not None and not system.date.isBefore(s, r):
		return advance(s, freq, unit), ('catch-up: spared WO on %s is on/'
			'after restartOn %s - anchor = spared + 1 frequency'
			% (_dayKey(s), _dayKey(r)))
	return r, 'restartOn'


def repeat12Lifecycle(rec, months, state, shortWoId):
	"""Spec 1.1: one lifecycle pair per RELEASE/UPDATE of a Repeat12 window
	occurrence - consume rec's WO_M_Subtasks row, append a replacement at
	occurrence date + months. Pure except for the seq state it advances.

	rec    the decision record ({'subId','date','end','dayKey',...}).
	Returns (record, None) on success or (None, 'SKIP-...') to refuse.
	The record is rec plus: lifecycle=True, months, appendSubId (fresh
	sequence, NEVER '-S' - N-A), appendDate/appendDayKey/appendEnd,
	appendWeekNo/appendWeekNoStr."""
	m = _i(months)
	if m is None or m < 1:
		return None, ("SKIP-REPEAT12-HORIZON: 'PM WM Horizon' is %r - "
			'cannot place the append' % (months,))
	sid = freshSubtaskId(shortWoId, state)
	if sid is None:
		return None, ('SKIP-REPEAT12-SEQ: no fresh sequence id inside a '
			'%d-step walk - master id space needs a human look'
			% _FRESH_SEQ_WALK)
	aStart = _mid(system.date.addMonths(rec['date'], m))
	endBase = _mid(_toDate(rec.get('end'))) if rec.get('end') is not None \
		else None
	aEnd = _mid(system.date.addMonths(
		endBase if endBase is not None else rec['date'], m))
	out = dict(rec)
	out.update({'lifecycle': True, 'months': m,
		'appendSubId': sid, 'appendDate': aStart,
		'appendDayKey': _dayKey(aStart), 'appendEnd': aEnd,
		'appendWeekNo': weekNo(aStart),
		'appendWeekNoStr': weekNoAndYear(aStart)})
	if _dayKey(aStart) <= _dayKey(rec['date']):
		return None, ('SKIP-REPEAT12-DATE: append %s is not strictly after '
			'the occurrence %s' % (_dayKey(aStart), _dayKey(rec['date'])))
	return out, None


def checkRails(plan, rails=None, history=None):
	"""PURE. F-4. Returns a list of breach dicts:
	{'rail','severity','detail'} - severity 'ABORT' kills the whole run,
	'MASTER' skips one master, 'SKIPPED' means the rail could not be evaluated.
	Never mutates the plan."""
	if rails is None:
		rails = _RAILS
	out = []
	releases = []
	updates = []
	perMaster = {}
	dayKeys = {}
	for mp in plan.get('masters') or []:
		m = mp.get('shortWoId')
		for r in mp.get('release') or []:
			releases.append(r)
			perMaster[m] = perMaster.get(m, 0) + 1
			k = '%s|%s' % (m, r.get('dayKey'))
			dayKeys.setdefault(k, []).append(r.get('subId'))
		# lifecycle pairs are 1:1 with a release write (5d-2), so they are
		# bounded and de-duplicated exactly like releases (spec 1.3)
		for r in mp.get('repeat12') or []:
			releases.append(r)
			perMaster[m] = perMaster.get(m, 0) + 1
			k = '%s|%s' % (m, r.get('dayKey'))
			dayKeys.setdefault(k, []).append(r.get('subId'))
		for r in mp.get('update') or []:
			updates.append(r)

	n = len(releases)
	if n > rails.get('perRun', 0):
		out.append({'rail': 'perRun', 'severity': 'ABORT',
			'detail': '%d releases planned, cap is %d - refusing the whole '
			'run' % (n, rails['perRun'])})

	for m in sorted(perMaster.keys()):
		if perMaster[m] > rails.get('perMaster', 0):
			out.append({'rail': 'perMaster', 'severity': 'MASTER',
				'detail': '%s plans %d releases, cap is %d'
				% (m, perMaster[m], rails['perMaster'])})

	seen = {}
	for r in releases:
		sid = r.get('strippedId')
		seen.setdefault(sid, 0)
		seen[sid] += 1
	dupes = [s for s in seen if seen[s] > 1]
	if dupes:
		out.append({'rail': 'duplicateId', 'severity': 'ABORT',
			'detail': 'the plan contains the same occurrence twice: %s'
			% ', '.join(sorted(dupes)[:6])})

	# repeat12 appends: fresh ids that collide with nothing else planned,
	# and strictly after the occurrence they replace (spec 1.3)
	apSeen = {}
	for mp in plan.get('masters') or []:
		for r in mp.get('repeat12') or []:
			a = _s(r.get('appendSubId'))
			apSeen.setdefault(a, 0)
			apSeen[a] += 1
			if stripS(a) in seen:
				out.append({'rail': 'repeat12Append', 'severity': 'ABORT',
					'detail': 'append id %s collides with a planned '
					'occurrence' % a})
			ad, od = r.get('appendDayKey'), r.get('dayKey')
			if ad is not None and od is not None and _s(ad) <= _s(od):
				out.append({'rail': 'repeat12Append', 'severity': 'ABORT',
					'detail': '%s appends at %s, not strictly after %s'
					% (r.get('subId'), ad, od)})
	apDup = [a for a in apSeen if apSeen[a] > 1]
	if apDup:
		out.append({'rail': 'repeat12Append', 'severity': 'ABORT',
			'detail': 'duplicate append id(s): %s'
			% ', '.join(sorted(apDup)[:6])})

	multi = [k for k in dayKeys if len(dayKeys[k]) > 1]
	if multi:
		out.append({'rail': 'sameMasterSameDate', 'severity': 'ABORT',
			'detail': 'more than one release for one master on one date: %s'
			% ', '.join(sorted(multi)[:6])})

	for mp in plan.get('masters') or []:
		for tp in mp.get('tasks') or []:
			if tp.get('capped'):
				out.append({'rail': 'perTask', 'severity': 'MASTER',
					'detail': '%s/%s hit the per-task cap %d'
					% (mp.get('shortWoId'), tp.get('taskId'),
					   rails.get('perTask'))})

	med = None
	usable = []
	try:
		if history:
			# only runs that released something - see 2.1.0
			usable = sorted([int(x) for x in history if int(x) > 0])
			if len(usable) >= _MEDIAN_MIN_SAMPLES:
				med = usable[len(usable) // 2] if len(usable) % 2 else \
					(usable[len(usable) // 2 - 1]
					 + usable[len(usable) // 2]) / 2.0
	except:
		med = None
		usable = []
	if med is None:
		out.append({'rail': 'medianMultiple', 'severity': 'SKIPPED',
			'detail': 'only %d usable history point(s), need %d - this rail is '
			'NOT evaluated and is NOT passing'
			% (len(usable), _MEDIAN_MIN_SAMPLES)})
	elif med > 0 and n > med * rails.get('medianMultiple', 5.0):
		out.append({'rail': 'medianMultiple', 'severity': 'ABORT',
			'detail': '%d releases is more than %.1fx the recent median of %s '
			'- stopping. Re-run with force=True to override.'
			% (n, rails['medianMultiple'], med)})
	return out


# ---------------------------------------------------------------------------
# DB adapters
# ---------------------------------------------------------------------------

def activeMasters(woId=None, woIds=None):
	sql = ("SELECT h.WO_ID AS WO_ID, "
		"RTRIM(ISNULL(h.Short_WO_Id, '')) AS Short_WO_Id, "
		"RTRIM(ISNULL(h.WO_Title, '')) AS WO_Title, "
		"RTRIM(ISNULL(h.Status, '')) AS Status, "
		"h.Request_Start_Date, h.Request_End_Date, "
		"RTRIM(ISNULL(h.Repeat_Type_Flag, '')) AS Repeat_Type_Flag, "
		"RTRIM(ISNULL(h.Editing_user, '')) AS Editing_user, "
		"RTRIM(ISNULL(d.Freq_Unit, 'W')) AS Freq_Unit, "
		"d.Meter_Id AS Meter_Id "
		"FROM dbo.WO_M_header h "
		"LEFT JOIN dbo.WO_M_details d ON d.WO_ID = h.WO_ID "
		"WHERE RTRIM(ISNULL(h.Status, '')) = 'A'")
	params = []
	if woId is not None:
		sql += " AND h.WO_ID = ?"
		params.append(int(woId))
	if woIds is not None:
		# spec 3 / BX-5: generated placeholders only, never concatenation.
		# plan() has already validated the list (non-empty, all ints).
		sql += " AND h.WO_ID IN (%s)" % ','.join(['?'] * len(woIds))
		params.extend([int(v) for v in woIds])
	sql += " ORDER BY h.Short_WO_Id"
	rows = _rows(_query(sql, params), ['WO_ID', 'Short_WO_Id', 'WO_Title',
		'Status', 'Request_Start_Date', 'Request_End_Date',
		'Repeat_Type_Flag', 'Editing_user', 'Freq_Unit', 'Meter_Id'])
	for r in rows:
		r['WO_ID'] = _i(r['WO_ID'])
		r['Meter_Id'] = _i(r['Meter_Id'])
		r['Freq_Unit'] = (_s(r['Freq_Unit']) or 'W').upper()[:1]
	return rows


def mastersFor(woIds):
	"""5d-4a: ANY-status display read for the Block console - the console
	must show non-'A' selections (rendered "not Active"), which
	activeMasters rightly filters out. Parameterised IN only (BX-5).
	Returns [] for an empty/None list rather than guessing a scope."""
	if not woIds:
		return []
	ids = [int(v) for v in woIds]
	sql = ("SELECT h.WO_ID AS WO_ID, "
		"RTRIM(ISNULL(h.Short_WO_Id, '')) AS Short_WO_Id, "
		"RTRIM(ISNULL(h.WO_Title, '')) AS WO_Title, "
		"RTRIM(ISNULL(h.Status, '')) AS Status, "
		"RTRIM(ISNULL(h.Repeat_Type_Flag, '')) AS Repeat_Type_Flag, "
		"RTRIM(ISNULL(d.Freq_Unit, 'W')) AS Freq_Unit "
		"FROM dbo.WO_M_header h "
		"LEFT JOIN dbo.WO_M_details d ON d.WO_ID = h.WO_ID "
		"WHERE h.WO_ID IN (%s) "
		"ORDER BY h.Short_WO_Id" % ','.join(['?'] * len(ids)))
	rows = _rows(_query(sql, ids), ['WO_ID', 'Short_WO_Id', 'WO_Title',
		'Status', 'Repeat_Type_Flag', 'Freq_Unit'])
	for r in rows:
		r['WO_ID'] = _i(r['WO_ID'])
	return rows


def tasksFor(woId):
	"""D4: Task_Id normalised with CHAR(160) stripped, not just RTRIM."""
	ds = _query(
		"SELECT REPLACE(RTRIM(Task_Id), CHAR(160), '') AS Task_Id, "
		"RTRIM(ISNULL(Short_Task_Id, '')) AS Short_Task_Id, "
		"RTRIM(ISNULL(Task_Title, '')) AS Task_Title, "
		"RTRIM(ISNULL(Repeat_Type_flag, '')) AS Repeat_Type_flag, "
		"RTRIM(ISNULL(CD_Freq, '')) AS CD_Freq, "
		"RTRIM(ISNULL(CM_Freq, '')) AS CM_Freq, "
		"Start_Date, Next_Service_Value, "
		"RTRIM(ISNULL(Repeat_for_Following_12_Months, 'N')) AS Repeat12 "
		"FROM dbo.WO_M_Task WHERE WO_Id = ? ORDER BY Task_Id",
		[int(woId)])
	rows = _rows(ds, ['Task_Id', 'Short_Task_Id', 'Task_Title',
		'Repeat_Type_flag', 'CD_Freq', 'CM_Freq', 'Start_Date',
		'Next_Service_Value', 'Repeat12'])
	for r in rows:
		r['Task_Id'] = _tid(r['Task_Id'])
		for c in ['Short_Task_Id', 'Task_Title', 'Repeat_Type_flag',
		          'CD_Freq', 'CM_Freq', 'Repeat12']:
			r[c] = _s(r[c])
		r['Repeat12'] = (r['Repeat12'] or 'N').upper()
	return rows


def subtasksFor(woId):
	ds = _query(
		"SELECT RTRIM(ISNULL(Short_SubTask_Id, '')) AS SubId, "
		"REPLACE(RTRIM(Task_Id), CHAR(160), '') AS Task_Id, "
		"Req_Start_Date, Req_End_Date, Week_No, "
		"RTRIM(ISNULL(Status, '')) AS Status, "
		"Meter_ID AS Meter_ID, Meter_Reading "
		"FROM dbo.WO_M_Subtasks WHERE WO_Id = ? ORDER BY Req_Start_Date",
		[int(woId)])
	rows = _rows(ds, ['SubId', 'Task_Id', 'Req_Start_Date', 'Req_End_Date',
		'Week_No', 'Status', 'Meter_ID', 'Meter_Reading'])
	for r in rows:
		r['SubId'] = _s(r['SubId'])
		r['Task_Id'] = _tid(r['Task_Id'])
		r['Status'] = _s(r['Status'])
	return rows


def xRowCount(woId):
	"""WO_X_Subtasks rows for a master. Non-zero (or unreadable -> None)
	refuses the Repeat12 lifecycle and, in 5d-2, rebase: the X interplay
	(extraction 14.5) is read but its creators are not - refuse before
	guessing (design principle 5)."""
	try:
		v = _scalar('SELECT COUNT(*) FROM dbo.WO_X_Subtasks '
			'WHERE WO_ID = ?', [int(woId)])
		return int(v or 0)
	except:
		return None


def xDatesFor(woId):
	"""Q2 (spec 3): X-held (taskId, dayKey) pairs for a master, from
	WO_X_Subtasks - Task_Id CHAR(160)-normalised (D4), date by
	CAST(... AS DATE). X rows are excluded occurrences parked by the PM
	calendar; the planner treats their dates as occupied (cadence
	ghosts). Returns a set, or None when unreadable - the caller must
	then NOT skip on a guess (2.2.0 behaviour + a stub)."""
	try:
		ds = _query(
			"SELECT REPLACE(RTRIM(Task_Id), CHAR(160), '') AS Task_Id, "
			"CONVERT(varchar(10), CAST(Req_Start_Date AS DATE), 120) "
			"AS DayKey "
			"FROM dbo.WO_X_Subtasks WHERE WO_ID = ?", [int(woId)])
		out = set()
		for r in _rows(ds, ['Task_Id', 'DayKey']):
			t, k = _tid(r['Task_Id']), _s(r['DayKey'])
			if t and k:
				out.add((t, k))
		return out
	except:
		return None


def meterDueIds(woId):
	"""D2 / S2.3:  *** UNTESTED PATH ***  There are no meter-based masters on
	dev, so this has never once executed. It is implemented per source and
	covered by no test. Deliberately on hold (2026-07-26) - staging a meter
	master is the way to close it. subtask ids that are due on METER, regardless of date -
	Meter_Reading below the meter's current Last_Reading_Value. 1.x had no
	equivalent and would under-release every meter PM."""
	try:
		ds = _query(
			"SELECT RTRIM(ISNULL(s.Short_SubTask_Id, '')) AS SubId "
			"FROM dbo.WO_M_Subtasks s "
			"INNER JOIN dbo.Meter m ON m.Meter_ID = s.Meter_ID "
			"WHERE s.WO_Id = ? "
			"AND ISNULL(s.Meter_Reading, 0) < ISNULL(m.Last_Reading_Value, 0)",
			[int(woId)])
		return set([_s(r['SubId']) for r in _rows(ds, ['SubId'])])
	except:
		return set()


def pinTableExists():
	"""P-PLN1 S3: True once dbo.WO_N_Plan exists (INFORMATION_SCHEMA).
	Only True is cached, so the DDL landing later is seen on the next call."""
	global _pinTableKnown
	if _pinTableKnown:
		return True
	try:
		n = _scalar("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
			"WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = ?", [_PIN_TABLE])
		if int(n or 0) > 0:
			_pinTableKnown = True
	except:
		_pinTableKnown = False
	return _pinTableKnown


def matchedWOs(subId):
	"""F-1: every work order carrying this occurrence's id in EITHER form,
	live or archive, with NO DATE CONDITION. PO linkage is the UNION of
	PO_Header and PO_Details (D6) plus any Meter_Reading back-reference.
	2.5.0: 'pinned' = the planner pin (WO_N_Plan.Pinned = 'Y'), read only
	when the table exists; archive rows are never pinned."""
	stripped = stripS(subId)
	raw = _s(subId)
	if pinTableExists():
		pinCol = ("ISNULL((SELECT TOP 1 CASE WHEN RTRIM(ISNULL(x.Pinned, 'N')) = 'Y' "
			"THEN 1 ELSE 0 END FROM dbo.WO_N_Plan x WHERE x.WO_ID = h.WO_ID), 0) AS Pinned ")
	else:
		pinCol = "0 AS Pinned "
	ds = _query(
		"SELECT 'N' AS Src, h.WO_ID, h.Request_Start_Date, "
		"RTRIM(ISNULL(h.Status, '')) AS Status, "
		"RTRIM(ISNULL(h.Purchase_Order_Flag, '')) AS PO_Flag, "
		"(SELECT COUNT(*) FROM dbo.PO_Details p WHERE p.WO_Id = h.WO_ID) AS PO_Lines, "
		"(SELECT COUNT(*) FROM dbo.PO_Header q WHERE q.WO_Id = h.WO_ID) AS PO_Hdrs, "
		"(SELECT COUNT(*) FROM dbo.Meter_Reading m WHERE m.From_WO_ID = h.WO_ID) AS Mtr_Refs, "
		+ pinCol +
		"FROM dbo.WO_N_Header h "
		"WHERE REPLACE(RTRIM(ISNULL(h.Short_WO_Id, '')), CHAR(160), '') IN (?, ?) "
		"UNION ALL "
		"SELECT 'C' AS Src, c.WO_ID, c.Request_Start_Date, "
		"RTRIM(ISNULL(c.Status, '')) AS Status, "
		"RTRIM(ISNULL(c.Purchase_Order_Flag, '')) AS PO_Flag, "
		"(SELECT COUNT(*) FROM dbo.PO_Details p WHERE p.WO_Id = c.WO_ID) AS PO_Lines, "
		"(SELECT COUNT(*) FROM dbo.PO_Header q WHERE q.WO_Id = c.WO_ID) AS PO_Hdrs, "
		"(SELECT COUNT(*) FROM dbo.Meter_Reading m WHERE m.From_WO_ID = c.WO_ID) AS Mtr_Refs, "
		"0 AS Pinned "
		"FROM dbo.WO_C_header c "
		"WHERE REPLACE(RTRIM(ISNULL(c.Short_WO_Id, '')), CHAR(160), '') IN (?, ?)",
		[stripped, raw, stripped, raw])
	rows = _rows(ds, ['Src', 'WO_ID', 'Request_Start_Date', 'Status',
		'PO_Flag', 'PO_Lines', 'PO_Hdrs', 'Mtr_Refs', 'Pinned'])
	out = []
	for r in rows:
		poLinked = (_s(r['PO_Flag']) == '1' or (_i(r['PO_Lines']) or 0) > 0
			or (_i(r['PO_Hdrs']) or 0) > 0 or (_i(r['Mtr_Refs']) or 0) > 0)
		out.append({'src': _s(r['Src']), 'woId': _i(r['WO_ID']),
			'date': r['Request_Start_Date'],
			'dayKey': _dayKey(_mid(r['Request_Start_Date'])),
			'status': _s(r['Status']), 'poLinked': poLinked,
			'pinned': (_i(r['Pinned']) or 0) == 1,
			'poFlag': _s(r['PO_Flag']),
			'poLines': _i(r['PO_Lines']) or 0,
			'poHdrs': _i(r['PO_Hdrs']) or 0,
			'mtrRefs': _i(r['Mtr_Refs']) or 0})
	return out


def meterInfo(meterId):
	if meterId is None:
		return None
	try:
		ds = _query(
			"SELECT Meter_ID, RTRIM(ISNULL(Short_Meter_Id, '')) AS Short_Meter_Id, "
			"ISNULL(Weekly_RateOf_Change, 1.0) AS Weekly_RateOf_Change, "
			"Last_Reading_Value, Last_Reading_Date, Limit_Value "
			"FROM dbo.Meter WHERE Meter_ID = ?", [int(meterId)])
		if ds.getRowCount() == 0:
			return None
		r = _rows(ds, ['Meter_ID', 'Short_Meter_Id', 'Weekly_RateOf_Change',
			'Last_Reading_Value', 'Last_Reading_Date', 'Limit_Value'])[0]
		r['Weekly_RateOf_Change'] = _f(r['Weekly_RateOf_Change'])
		return r
	except:
		return None


def cmProjectedDate(anchor, freq, rate):
	"""S2.2 verbatim: weeks = freq / ISNULL(rate, 1.0); next = anchor + weeks*7
	days. A zero rate yields no date (the .NET guard). PURE."""
	d = _mid(_toDate(anchor))
	if d is None:
		return None
	r = 1.0 if rate is None else float(rate)
	if r == 0.0:
		return None
	try:
		weeks = float(freq) / r
	except:
		return None
	return system.date.addDays(d, int(round(weeks * 7.0)))


# ---------------------------------------------------------------------------
# orchestration - DRY RUN ONLY. No INSERT/UPDATE/DELETE in this module.
# ---------------------------------------------------------------------------

def _planTask(master, task, existing, horizonTo, state, sink, xRows=0,
		session=None, xSet=None):
	tid = task['Task_Id']
	tp = {'taskId': tid, 'title': task['Task_Title'], 'kind': None,
	      'freq': None, 'freqRaw': None, 'unit': master['Freq_Unit'],
	      'anchor': None, 'extend': [], 'skip': None, 'note': '',
	      'capped': False, 'repeat12': False, 'xHeld': []}

	mine = [s for s in existing if s['Task_Id'] == tid]
	tp['materialised'] = len(mine)

	rtf = (task['Repeat_Type_flag'] or master['Repeat_Type_Flag']
		or 'CD').upper()
	cm = _f(task['CM_Freq'])
	tp['kind'] = 'CM' if (rtf.startswith('CM') or (cm is not None and cm > 0)) \
		else 'CD'

	if task['Repeat12'] == 'Y':
		# D-PM5-6a ADOPTED: window-driven task. Anchor reported for the
		# human; NO frequency extends - the window is the source of truth
		# and the lifecycle (consume+append) is planned in planMaster per
		# released occurrence.
		tp['repeat12'] = True
		for s in mine:
			d = _mid(s['Req_Start_Date'])
			if d is not None and (tp['anchor'] is None
					or system.date.isAfter(d, tp['anchor'])):
				tp['anchor'] = d
		if tp['kind'] == 'CM':
			tp['skip'] = ('SKIP-REPEAT12-CM: Repeat12 on a CM task is '
				'unspecified in source (the append copies no meter '
				'fields) - refused, occurrences excluded (spec 1.1)')
			_log(sink, '%s/%s %s' % (master['Short_WO_Id'], tid,
				tp['skip']), level='warn', session=session)
			return tp
		if xRows is None or xRows > 0:
			tp['skip'] = ('SKIP-REPEAT12-X: WO_X_Subtasks %s - X interplay '
				'unread, refused (spec 1.1)'
				% ('unreadable' if xRows is None
				   else 'has %d row(s)' % xRows))
			_log(sink, '%s/%s %s' % (master['Short_WO_Id'], tid,
				tp['skip']), level='warn', session=session)
			return tp
		tp['note'] = ('repeat12: window-driven - lifecycle planned per '
			'released occurrence, no frequency extends')
		return tp

	freq, raw, why = freqOf(task)
	tp['freq'], tp['freqRaw'] = freq, raw
	if why:
		tp['skip'] = 'SKIP-NO-FREQ: %s' % why
		_log(sink, '%s/%s %s' % (master['Short_WO_Id'], tid, tp['skip']),
			level='warn', session=session)
		return tp

	# anchor: last materialised occurrence, else the task's Start_Date (which
	# IS its first occurrence)
	anchor = None
	for s in mine:
		d = _mid(s['Req_Start_Date'])
		if d is not None and (anchor is None or system.date.isAfter(d, anchor)):
			anchor = d
	if anchor is None:
		anchor = _mid(_toDate(task['Start_Date']))
		if anchor is None:
			tp['skip'] = 'SKIP-NO-ANCHOR: no subtasks and Start_Date is null'
			_log(sink, '%s/%s %s' % (master['Short_WO_Id'], tid, tp['skip']),
				level='warn', session=session)
			return tp
		first = anchor
	elif tp['kind'] == 'CM':
		mi = meterInfo(master['Meter_Id'])
		tp['meter'] = mi
		first = cmProjectedDate(anchor, freq,
			mi.get('Weekly_RateOf_Change') if mi else None)
		if first is None:
			tp['skip'] = ('SKIP-CM-RATE: meter rate is zero or unreadable - '
				'no projection possible (S2.2 guard)')
			_log(sink, '%s/%s %s' % (master['Short_WO_Id'], tid, tp['skip']),
				level='warn', session=session)
			return tp
	else:
		first = advance(anchor, freq, master['Freq_Unit'])
	tp['anchor'] = anchor

	occ = occurrencesFor(first, freq, master['Freq_Unit'], horizonTo,
		_RAILS['perTask'])
	tp['capped'] = occ['capped']
	if occ['reason'] and not occ['dates']:
		tp['skip'] = 'SKIP-NO-OCCURRENCES: %s' % occ['reason']
		_log(sink, '%s/%s %s' % (master['Short_WO_Id'], tid, tp['skip']),
			level='warn', session=session)
		return tp
	if occ['reason']:
		tp['note'] = occ['reason']

	for d in occ['dates']:
		k = _dayKey(d)
		if xSet and (tid, k) in xSet:
			# Q2 (spec 3): the date is X-excluded. Withhold the
			# occurrence, consume the cadence step (occurrencesFor has
			# already stepped past it), burn no id.
			tp['xHeld'].append(k)
			_log(sink, '%s/%s skip-x: %s is X-excluded - occurrence '
				'withheld, step consumed (spec 3 Q2)'
				% (master['Short_WO_Id'], tid, k), level='warn',
				session=session)
			continue
		state['seq'] += 1
		sid, suffixed = nextSubtaskId(master['Short_WO_Id'], state['seq'],
			state['width'], state['taken'])
		state['taken'].add(sid)
		tp['extend'].append({'subId': sid, 'suffixedS': suffixed, 'date': d,
			'dayKey': _dayKey(d), 'weekNo': weekNo(d),
			'weekNoStr': weekNoAndYear(d)})
	return tp


def planMaster(master, cfg, asOf=None, horizonDays=None, sink=None,
		session=None):
	"""One master, DRY RUN. D-PM5-1: one work order per task - no Week_No
	merge. Writes nothing."""
	if sink is None:
		sink = []
	asOf = _mid(_toDate(asOf) or system.date.now())
	days = int(horizonDays if horizonDays is not None else cfg['woWindowDays'])
	horizonTo = system.date.addDays(asOf, days)

	mp = {'woId': master['WO_ID'], 'shortWoId': master['Short_WO_Id'],
	      'title': master['WO_Title'], 'freqUnit': master['Freq_Unit'],
	      'meterId': master['Meter_Id'],
	      'headerNextDue': _mid(master['Request_Start_Date']),
	      'tasks': [], 'release': [], 'update': [], 'frozen': [], 'skip': [],
	      'repeat12': [],
	      'advanceHeader': None, 'error': None,
	      'masterSkip': None, 'windowXDrift': [], 'xUnreadable': False}
	# Q3 (spec 3): a base id past the .NET rebuild boundary risks released
	# id overflow (base + '-NNNN'/'-S' vs char(25)). Named whole-master
	# skip, zero occurrences considered - visible on the first dry plan.
	if len(master['Short_WO_Id'] or '') > _MAX_BASE_ID_LEN:
		mp['masterSkip'] = ('SKIP-IDLEN: base id is %d chars (> %d) - '
			'released ids risk overflow, master skipped by name (spec 3 '
			'Q3, BX-3)' % (len(master['Short_WO_Id'] or ''),
			_MAX_BASE_ID_LEN))
		_log(sink, '%s %s' % (master['Short_WO_Id'], mp['masterSkip']),
			level='warn', session=session)
		return mp
	try:
		existing = subtasksFor(master['WO_ID'])
		tasks = tasksFor(master['WO_ID'])
		xRows = xRowCount(master['WO_ID'])
		xSet = xDatesFor(master['WO_ID'])
		if xSet is None:
			# spec 3: unreadable X must not skip on a guess - extension
			# behaves as 2.2.0 and the plan says so out loud.
			mp['xUnreadable'] = True
			_log(sink, '%s WO_X_Subtasks unreadable - extension X-skip '
				'disabled for this master (spec 3)'
				% master['Short_WO_Id'], level='warn', session=session)
		drift = [s['SubId'] for s in existing
			if (s['SubId'] or '').endswith('-X')]
		if drift:
			# rail only: X occurrences never enter the window by
			# construction, so any '-X' id here is legacy drift.
			mp['windowXDrift'] = drift
			_log(sink, '%s windowXDrift: %d window row(s) carry a -X id '
				'(legacy drift, behaviour unchanged): %s'
				% (master['Short_WO_Id'], len(drift), drift),
				level='warn', session=session)
		if not tasks:
			mp['error'] = 'NO TASKS - master skipped (see D-4b-4)'
			_log(sink, '%s %s' % (master['Short_WO_Id'], mp['error']),
				level='warn', session=session)
			return mp

		width = _seqWidth([s['SubId'] for s in existing])
		mp['seqWidth'] = width
		# ONE seq counter per MASTER - the -NNNN law is master-wide. A
		# per-task counter makes task 002 reuse task 001's numbers and
		# nextSubtaskId then hides the collision behind a bogus '-S'.
		seq0 = 0
		for s in existing:
			base = stripS(s['SubId'])
			if '-' in base:
				tail = base.rsplit('-', 1)[1]
				if tail.isdigit():
					seq0 = max(seq0, int(tail))
		state = {'seq': seq0, 'width': width,
			'taken': set([s['SubId'] for s in existing]).union(
				set([stripS(s['SubId']) for s in existing]))}

		for t in tasks:
			mp['tasks'].append(_planTask(master, t, existing, horizonTo,
				state, sink, xRows, session, xSet))

		# spec S0: a task the engine refuses to maintain is a task it
		# refuses to act on - its materialised occurrences never become
		# candidates (2.1.0 released them while refusing the task, which
		# for Repeat12 shrank the window every run until the task died).
		refused = set([tp['taskId'] for tp in mp['tasks'] if tp['skip']])
		r12ok = set([tp['taskId'] for tp in mp['tasks']
			if tp.get('repeat12') and not tp['skip']])

		# --- candidates: materialised (by date OR by meter) + planned -------
		mtrDue = meterDueIds(master['WO_ID'])
		cands = []
		for s in existing:
			if s['Task_Id'] in refused:
				continue
			d = _mid(s['Req_Start_Date'])
			if d is None:
				continue
			byDate = not system.date.isAfter(d, horizonTo)
			byMeter = s['SubId'] in mtrDue
			if not (byDate or byMeter):
				continue
			cands.append({'subId': s['SubId'], 'taskId': s['Task_Id'],
				'date': d, 'end': s['Req_End_Date'],
				'source': 'meter-due' if (byMeter and not byDate)
				else 'materialised'})
		for tp in mp['tasks']:
			for o in tp['extend']:
				cands.append({'subId': o['subId'], 'taskId': tp['taskId'],
					'date': o['date'], 'end': None, 'source': 'planned'})
		cands.sort(key=lambda c: (_dayKey(c['date']), c['subId']))

		for c in cands:
			occ = {'subId': c['subId'], 'strippedId': stripS(c['subId']),
			       'dayKey': _dayKey(c['date'])}
			matched = matchedWOs(c['subId'])
			action, reason = releaseDecision(occ, matched)
			rec = {'subId': c['subId'], 'strippedId': occ['strippedId'],
			       'taskId': c['taskId'], 'date': c['date'],
			       'end': c.get('end'),
			       'dayKey': occ['dayKey'], 'source': c['source'],
			       'weekNo': weekNo(c['date']),
			       'weekNoStr': weekNoAndYear(c['date']),
			       'action': action, 'reason': reason, 'matched': matched}
			if c['taskId'] in r12ok and action in ('RELEASE', 'UPDATE'):
				# spec 1.1: lifecycle pair. Routed to mp['repeat12'] ONLY -
				# db 1.2.1 never reads that bucket, so the pair cannot be
				# half-applied before the 1.3.0 writer exists (5d-2).
				lc, why = repeat12Lifecycle(rec, cfg.get('pmHorizonMonths'),
					state, master['Short_WO_Id'])
				if lc is None:
					rec['action'] = 'SKIP'
					rec['reason'] = why
					mp['skip'].append(rec)
					_log(sink, '%s/%s %s' % (master['Short_WO_Id'],
						c['taskId'], why), level='warn', session=session)
				else:
					mp['repeat12'].append(lc)
				continue
			if action == 'RELEASE':
				mp['release'].append(rec)
			elif action == 'UPDATE':
				mp['update'].append(rec)
			elif action == 'FROZEN':
				mp['frozen'].append(rec)
			else:
				mp['skip'].append(rec)

		# --- Next Due: earliest occurrence not already satisfied ------------
		pool = [r['date'] for r in mp['release']] + \
			[r['date'] for r in mp['update']] + \
			[r['date'] for r in mp['repeat12']] + \
			[r['appendDate'] for r in mp['repeat12']]
		for s in existing:
			d = _mid(s['Req_Start_Date'])
			if d is not None and system.date.isAfter(d, horizonTo):
				pool.append(d)
		for tp in mp['tasks']:
			for o in tp['extend']:
				pool.append(o['date'])
		if pool:
			nxt = pool[0]
			for d in pool:
				if system.date.isBefore(d, nxt):
					nxt = d
			cur = mp['headerNextDue']
			if cur is None or _dayKey(cur) != _dayKey(nxt):
				mp['advanceHeader'] = {'from': cur, 'to': nxt,
					'fromKey': _dayKey(cur), 'toKey': _dayKey(nxt)}

		_log(sink, '%s: %d task(s) extend=%d release=%d update=%d frozen=%d '
			'skip=%d repeat12=%d' % (master['Short_WO_Id'], len(mp['tasks']),
			sum([len(t['extend']) for t in mp['tasks']]), len(mp['release']),
			len(mp['update']), len(mp['frozen']), len(mp['skip']),
			len(mp['repeat12'])),
			session=session)
	except:
		mp['error'] = _err()
		_log(sink, '%s planMaster FAILED: %s'
			% (master['Short_WO_Id'], mp['error']), level='error',
			session=session)
	return mp


def plan(woId=None, asOf=None, horizonDays=None, session=None, actor=None,
		history=None, force=False, upTo=None, woIds=None):
	"""THE dry run. Computes what the engine WOULD do and writes nothing.

	  session   Perspective session - the only thing that fills the
	            Diagnostics Viewer User column. Omit in gateway scope.
	  actor     label for runs with no session (timer, console).
	  history   recent per-run release counts, for the median rail.
	  force     record an override of ABORT rails (2.0.0 has no write path, so
	            this only affects the reported verdict).
	  upTo      spec 3: .NET's RELEASE_UPTO_DATE - horizon becomes
	            dayKey <= dayKey(upTo). Must not precede asOf.
	  woIds     spec 3: Block-console master scope (list of WO_IDs).
	            Mutually exclusive with woId; [] is a named error.
	"""
	sink = []
	who = str(actor or ('session' if session is not None else 'gateway'))
	out = {'ok': False, 'version': _VERSION, 'dryRun': True, 'actor': who,
	       'attributed': session is not None, 'forced': bool(force),
	       'log': sink, 'masters': [], 'stubs': [], 'counts': {},
	       'breaches': [], 'verdict': None}
	try:
		# --- spec 3 named errors: refuse loudly, attempt nothing --------
		if woId is not None and woIds is not None:
			out['error'] = ('scope-ambiguous: pass woId or woIds, '
				'not both')
			_log(sink, 'plan REFUSED: %s' % out['error'], level='error',
				session=session)
			return out
		scopeIds = None
		if woIds is not None:
			scopeIds = []
			for v in woIds:
				iv = _i(v)
				if iv is None:
					out['error'] = 'scope-bad-id: %r is not a WO_ID' % (v,)
					_log(sink, 'plan REFUSED: %s' % out['error'],
						level='error', session=session)
					return out
				scopeIds.append(iv)
			if not scopeIds:
				out['error'] = ('scope-empty: an empty woIds never means '
					'"everything"')
				_log(sink, 'plan REFUSED: %s' % out['error'],
					level='error', session=session)
				return out
		cfg = config()
		out['config'] = cfg
		asOfD = _mid(_toDate(asOf) or system.date.now())
		days = int(horizonDays if horizonDays is not None
			else cfg['woWindowDays'])
		if upTo is not None:
			upToD = _mid(_toDate(upTo))
			if upToD is None:
				out['error'] = 'upto-unparseable: %r' % (upTo,)
				_log(sink, 'plan REFUSED: %s' % out['error'],
					level='error', session=session)
				return out
			if system.date.isBefore(upToD, asOfD):
				out['error'] = ('upto-before-asof: %s < %s'
					% (_dayKey(upToD), _dayKey(asOfD)))
				_log(sink, 'plan REFUSED: %s' % out['error'],
					level='error', session=session)
				return out
			# the RELEASE_UPTO_DATE slot: same machinery, exact end date
			days = int(system.date.daysBetween(asOfD, upToD))
			out['upTo'] = upToD
			out['upToKey'] = _dayKey(upToD)
		out['asOf'] = asOfD
		out['asOfKey'] = _dayKey(asOfD)
		out['horizonDays'] = days
		out['horizonTo'] = system.date.addDays(asOfD, days)
		out['horizonToKey'] = _dayKey(out['horizonTo'])

		if cfg['horizonSource'].startswith('FALLBACK'):
			out['stubs'].append('WO_WINDOW unreadable - using fallback %d '
				'days. Verify the key before trusting any number here.' % days)
		if weekNo(asOfD) is None:
			out['stubs'].append('Week_No could not be computed - the S9.2 '
				'port is not evaluating. Treat every stamp as unsafe.')

		_log(sink, 'plan by=%s asOf=%s horizon=%dd -> %s (WO_WINDOW=%r)%s'
			% (who, out['asOfKey'], days, out['horizonToKey'],
			   cfg['woWindowRaw'],
			   (' upTo=%s' % out['upToKey']) if upTo is not None else ''),
			session=session)

		masters = activeMasters(woId, scopeIds)
		_log(sink, '%d Active master(s) in scope' % len(masters),
			session=session)
		if scopeIds is not None and len(masters) < len(scopeIds):
			# the console may select any status; the engine plans 'A' only
			got = set([m['WO_ID'] for m in masters])
			missing = [i for i in scopeIds if i not in got]
			out['scopeNotActive'] = missing
			_log(sink, 'scope: %d of %d requested master(s) are Active - '
				'not planned: %s' % (len(masters), len(scopeIds),
				missing), level='warn', session=session)
		for m in masters:
			out['masters'].append(planMaster(m, cfg, asOfD, days, sink,
				session))

		c = {'masters': len(out['masters']), 'extend': 0, 'release': 0,
		     'update': 0, 'frozen': 0, 'skip': 0, 'advanceHeader': 0,
		     'skippedTasks': 0, 'errors': 0, 'suffixedS': 0, 'meterDue': 0,
		     'repeat12': 0, 'skipX': 0, 'skipIdlen': 0}
		for mp in out['masters']:
			if mp['error']:
				c['errors'] += 1
			if mp.get('masterSkip'):
				c['skipIdlen'] += 1
			for k in ['release', 'update', 'frozen', 'skip', 'repeat12']:
				c[k] += len(mp[k])
			c['meterDue'] += len([r for r in mp['release'] + mp['update']
				+ mp['repeat12'] if r['source'] == 'meter-due'])
			if mp['advanceHeader']:
				c['advanceHeader'] += 1
			for tp in mp['tasks']:
				c['extend'] += len(tp['extend'])
				c['skipX'] += len(tp.get('xHeld') or [])
				if tp['skip']:
					c['skippedTasks'] += 1
				for o in tp['extend']:
					if o['suffixedS']:
						c['suffixedS'] += 1
		out['counts'] = c

		out['breaches'] = checkRails(out, _RAILS, history)
		aborts = [b for b in out['breaches'] if b['severity'] == 'ABORT']
		if aborts and not force:
			out['verdict'] = 'ABORT'
		elif aborts:
			out['verdict'] = 'ABORT-OVERRIDDEN'
		else:
			out['verdict'] = 'OK'
		out['ok'] = True
		_log(sink, 'plan done: %s verdict=%s breaches=%d'
			% (c, out['verdict'], len(out['breaches'])), session=session,
			level=('info' if out['verdict'] == 'OK' else 'warn'))
	except:
		out['error'] = _err()
		_log(sink, 'plan FAILED: %s' % out['error'], level='error',
			session=session)
	return out


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def report(p, verbose=True):
	L = []
	A = L.append
	A('=' * 78)
	A('workmate.pm_engine %s - DRY RUN - NOTHING WAS WRITTEN'
		% p.get('version'))
	A('run by: %s   diagnostics User attributed: %s'
		% (p.get('actor'), p.get('attributed')))
	A('=' * 78)
	cfg = p.get('config') or {}
	A('db              : %s' % cfg.get('db'))
	A('WO_WINDOW       : %r -> horizon %s days (%s)'
		% (cfg.get('woWindowRaw'), p.get('horizonDays'),
		   cfg.get('horizonSource')))
	A('as of           : %s   horizon to: %s'
		% (p.get('asOfKey'), p.get('horizonToKey')))
	A('PM WM Horizon   : %r months' % cfg.get('pmHorizonRaw'))
	A('REBUILD_DELETE  : %r%s' % (cfg.get('rebuildDeleteReleased'),
		'   <- rebuild DELETES released instances'
		if str(cfg.get('rebuildDeleteReleased') or '').upper() == 'Y' else ''))
	A('.NET interval   : %r days (0 = login-run disabled - the cutover lever)'
		% cfg.get('netUpdateIntervalDays'))
	A('rails           : %s' % cfg.get('rails'))
	A('frozen statuses : %s' % cfg.get('frozenStatuses'))
	A('Week_No today   : %s (stored as a double)' % cfg.get('weekNoSample'))
	if not p.get('ok'):
		A('')
		A('PLAN FAILED: %s' % p.get('error'))
		return '\n'.join(L)
	c = p.get('counts') or {}
	A('')
	A('COUNTS  masters=%d extend=%d RELEASE=%d UPDATE=%d FROZEN=%d skip=%d '
		'REPEAT12=%d (meter-due=%d)  advanceHeader=%d skippedTasks=%d '
		'-S=%d errors=%d'
		% (c.get('masters', 0), c.get('extend', 0), c.get('release', 0),
		   c.get('update', 0), c.get('frozen', 0), c.get('skip', 0),
		   c.get('repeat12', 0),
		   c.get('meterDue', 0), c.get('advanceHeader', 0),
		   c.get('skippedTasks', 0), c.get('suffixedS', 0),
		   c.get('errors', 0)))
	for s in p.get('stubs') or []:
		A('STUB    %s' % s)
	A('')
	A('VERDICT %s' % p.get('verdict'))
	for b in p.get('breaches') or []:
		A('  %-8s %-20s %s' % (b['severity'], b['rail'], b['detail']))
	if not verbose:
		return '\n'.join(L)
	for mp in p.get('masters') or []:
		A('')
		A('-' * 78)
		A('%-22s WO_ID=%s unit=%s nextDue(db)=%s'
			% (mp['shortWoId'], mp['woId'], mp['freqUnit'],
			   _dayKey(mp['headerNextDue'])))
		A('  %s' % (mp['title'] or ''))
		if mp['error']:
			A('  ERROR  %s' % mp['error'])
			continue
		for tp in mp['tasks']:
			A('  task %-4s %-34s kind=%s freq=%r(raw %r) materialised=%d'
				% (tp['taskId'], (tp['title'] or '')[:34], tp['kind'],
				   tp['freq'], tp['freqRaw'], tp.get('materialised', 0)))
			if tp['skip']:
				A('           %s' % tp['skip'])
			if tp['note']:
				A('           NOTE %s' % tp['note'])
			for o in tp['extend']:
				A('           + %-26s %s  wk %s%s'
					% (o['subId'], o['dayKey'], o['weekNoStr'],
					   '  [-S]' if o['suffixedS'] else ''))
		for r in mp.get('repeat12') or []:
			A('  %-8s %-26s %s -> +%dmo %s %s  wk %s  (%s)'
				% ('R12', r['subId'], r['dayKey'], r.get('months', 0),
				   r.get('appendSubId'), r.get('appendDayKey'),
				   r.get('appendWeekNoStr'), r.get('action')))
		for key, tag in [('release', 'RELEASE'), ('update', 'UPDATE'),
		                 ('frozen', 'FROZEN'), ('skip', 'skip')]:
			for r in mp[key]:
				A('  %-8s %-26s %s  %s' % (tag, r['subId'], r['dayKey'],
					r['reason']))
		if mp['advanceHeader']:
			A('  ADVANCE  Request_Start_Date %s -> %s'
				% (mp['advanceHeader']['fromKey'],
				   mp['advanceHeader']['toKey']))
	return '\n'.join(L)