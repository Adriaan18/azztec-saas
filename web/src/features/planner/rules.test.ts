/**
 * Azztec_SaaS_web_planner_rules_test_v1_3_0.ts  ->  web/src/features/planner/rules.test.ts
 * Version:  1.3.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §6 (rules.test.ts row) · pair rule;
 *           Azztec_SaaS_S1i_Priority_Paint_Chunk_Spec_v1_0_0.md §5.1 · pair of rules.ts 1.2.0;
 *           Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (rules.test.ts row) · pair of rules.ts 1.3.0
 *
 * Zero network, zero DOM, plain objects from range.fixture.ts. The string cases are byte-for-byte the
 * oracle's output - a planner reads these tooltips every day, so they are the parity surface.
 *
 * Changelog:
 *   1.3.0  DP3b: every 1.2.0 case kept; VERSION is 1.3.0. HINT_RW byte for byte; chipTitle on an
 *          engine-owned PM that is not movable (the RO mapping, OD-107) carries no drag line, and the
 *          payload's own engine-owned movable PM still does.
 *   1.2.0  S1i: every 1.1.0 case kept; VERSION is 1.2.0. New block for the badge paint - isHexColour
 *          edges, luminance anchors, textOn on the seven RST colours (the S1i spec §5.1 table, computed
 *          by hand there and VERIFIED by this run - #0080FF is the narrow one, 3.73 vs 3.80), and
 *          priBadgeMap on the fixture, a KT-shaped literal, case folding, a mixed payload, the
 *          one-usable-colour consequence, all-junk and empty. Priority literals are test-local so the
 *          shared fixture stays RST-shaped.
 *   1.1.0  S1g: every 1.0.1 case kept. Two strings updated on purpose - rowTitle now ends with the
 *          OD-34 click line, VERSION is 1.1.0. New: full visibleWos precedence, capacityWorkers
 *          selected > team > internal, railRows team filter, teamOptions/priorityOptions/workerMenu/
 *          workerLabel, dowIso against known days, priRank/priClass/priRankMap, dialogTitle/dialogRows,
 *          cardRows, HINT/actorLabel.
 *   1.0.1  Four assertions corrected against the oracle: fmtLong is the ABBREVIATED day name
 *          ('Mon 14 Sep 2026', src 514), not the full one. Caught by the run, not by reading -
 *          1.0.0 asserted 'Monday' from memory and rules.ts was right all along.
 *   1.0.0  Initial S1f.
 */
import { describe, expect, it } from 'vitest';

import {
  DEFAULT_CATS,
  DEFAULT_FILTERS,
  DEFAULT_RAIL,
  HINT,
  HINT_RW,
  VERSION,
  actorLabel,
  anySelectedWorker,
  barClass,
  barWidth,
  byDay,
  capacityPerWeek,
  capacityWorkers,
  cardRows,
  chipTitle,
  countLine,
  countText,
  dialogRows,
  dialogTitle,
  dowIso,
  flagCounts,
  fmtH,
  fmtLong,
  fmtLongAny,
  fmtNum,
  fmtRange,
  indexWorkers,
  isCat,
  isHexColour,
  labourFor,
  loadOf,
  luminance,
  monthKey,
  monthLabel,
  pctOf,
  peopleFor,
  priBadgeMap,
  priClass,
  priRank,
  priRankMap,
  priorityOptions,
  railRows,
  rowLoad,
  rowTitle,
  stripTitle,
  teamOptions,
  textOn,
  visibleWos,
  weekBarTitle,
  weekStats,
  weeksIn,
  whoFor,
  workerLabel,
  workerMenu,
  ymd,
} from './rules';
import type { Filters, PriBadge } from './rules';
import type { Priority } from '../../api/client/types.gen';
import { DONE_104, FROM, PIN_105, PM_102, RANGE, REQ_103, TO, WO_101, WORKERS, WOS, WW_692, W_2, W_3, W_692, mkWo } from './range.fixture';

export const TEST_VERSION = '1.3.0';

const byId = indexWorkers(WORKERS);
const f = (over: Partial<Filters>): Filters => ({ ...DEFAULT_FILTERS, ...over });

describe('rules.ts - constants and ISO parts', () => {
  it('carries its version and the oracle cats default (DONE off)', () => {
    expect(VERSION).toBe('1.3.0');
    expect(DEFAULT_CATS).toEqual({ WO: true, PM: true, REQ: true, DONE: false });
    expect(DEFAULT_RAIL).toEqual({ contractors: false, loadedOnly: true });
    expect(DEFAULT_FILTERS).toEqual({ teamId: 0, workers: {}, pri: 0, unassigned: false, q: '' });
  });

  it('isCat accepts the four cats only', () => {
    for (const c of ['WO', 'PM', 'REQ', 'DONE']) expect(isCat(c)).toBe(true);
    expect(isCat('')).toBe(false);
    expect(isCat('done')).toBe(false);
  });

  it('ymd and monthKey slice, never parse', () => {
    expect(ymd('2026-09-14')).toEqual({ y: 2026, m: 9, d: 14 });
    expect(ymd('2026-01-01')).toEqual({ y: 2026, m: 1, d: 1 });
    expect(monthKey('2026-09-14')).toBe('2026-09');
  });

  it('dowIso is Monday = 0 on known days, including the DST day and a leap February', () => {
    expect(dowIso('2026-09-14')).toBe(0); // the standing Monday
    expect(dowIso('2026-09-20')).toBe(6);
    expect(dowIso('2026-09-27')).toBe(6); // NZ DST starts, still a Sunday
    expect(dowIso('2026-01-01')).toBe(3); // Thursday
    expect(dowIso('2026-02-01')).toBe(6);
    expect(dowIso('2024-02-29')).toBe(3); // leap day, Thursday
    expect(dowIso('2030-12-31')).toBe(1);
  });

  it('fmtRange shows the from-year only when it differs (oracle 510-513)', () => {
    expect(fmtRange('2026-09-14', '2026-09-20')).toBe('14 Sep \u2013 20 Sep 2026');
    expect(fmtRange('2026-12-28', '2027-01-03')).toBe('28 Dec 2026 \u2013 3 Jan 2027');
  });

  it('fmtLong, fmtLongAny and monthLabel match the oracle strings', () => {
    expect(fmtLong('2026-09-14', 0)).toBe('Mon 14 Sep 2026');
    expect(fmtLong('2026-09-20', 6)).toBe('Sun 20 Sep 2026');
    expect(fmtLong('2026-09-16', 2)).toBe('Wed 16 Sep 2026');
    expect(fmtLongAny('2026-09-16')).toBe('Wed 16 Sep 2026');
    expect(fmtLongAny('2026-09-15')).toBe('Tue 15 Sep 2026');
    expect(monthLabel('2026-09-16', '2026-08-31', '2026-10-04')).toBe('September 2026  \u00b7  31 Aug \u2013 4 Oct 2026');
  });
});

describe('rules.ts - numbers (oracle 515-516, 578, 669)', () => {
  it('fmtNum / fmtH', () => {
    expect(fmtNum(3.5)).toBe('3.5');
    expect(fmtNum(12)).toBe('12');
    expect(fmtNum(2.04)).toBe('2');
    expect(fmtNum(10.5)).toBe('10.5');
    expect(fmtH(3.5)).toBe('3.5h');
    expect(fmtH(12)).toBe('12h');
    expect(fmtH(0)).toBe('?');
    expect(fmtH(-1)).toBe('?');
  });

  it('pctOf never divides by zero and never clamps (OD-25)', () => {
    expect(pctOf(74, 0)).toBe(0);
    expect(pctOf(10, 1)).toBe(1000);
    expect(pctOf(24, 1)).toBe(2400);
    expect(pctOf(10.5, 41)).toBe(26);
    expect(pctOf(0, 40)).toBe(0);
  });

  it('barClass thresholds at 79 / 80 / 100 / 101', () => {
    expect(barClass(79)).toBe('');
    expect(barClass(80)).toBe('ok');
    expect(barClass(100)).toBe('ok');
    expect(barClass(101)).toBe('over');
    expect(barClass(1000)).toBe('over');
    expect(barClass(0)).toBe('');
  });

  it('barWidth caps the bar at 100% but the number is not touched', () => {
    expect(barWidth(1000)).toBe('100%');
    expect(barWidth(100)).toBe('100%');
    expect(barWidth(26)).toBe('26%');
    expect(barWidth(0)).toBe('0%');
  });
});

describe('rules.ts - visibility and indexes (oracle 541-558)', () => {
  it('visibleWos with the default cats hides DONE', () => {
    const v = visibleWos(WOS, DEFAULT_CATS);
    expect(v.map((w) => w.id)).toEqual([101, 102, 103, 105]);
    expect(visibleWos(WOS, { ...DEFAULT_CATS, DONE: true })).toHaveLength(5);
    expect(visibleWos(WOS, { WO: false, PM: false, REQ: false, DONE: false })).toHaveLength(0);
    expect(visibleWos([mkWo({ id: 9, cat: 'XX' })], { ...DEFAULT_CATS, DONE: true })).toHaveLength(0);
  });

  it('byDay groups by start and keeps order', () => {
    const m = byDay([...WOS, mkWo({ id: 106, start: '2026-09-14' })]);
    expect(m.get('2026-09-14')?.map((w) => w.id)).toEqual([101, 106]);
    expect(m.get('2026-09-15')?.map((w) => w.id)).toEqual([102]);
    expect(m.get('2026-09-19')).toBeUndefined();
    expect(m.size).toBe(5);
  });

  it('indexWorkers keys by id', () => {
    expect(byId.get(692)?.initials).toBe('JB');
    expect(byId.get(999)).toBeUndefined();
  });
});

describe('rules.ts - the S1g filters (oracle 540-556)', () => {
  const ALL = { ...DEFAULT_CATS, DONE: true };

  it('anySelectedWorker', () => {
    expect(anySelectedWorker(DEFAULT_FILTERS)).toBe(false);
    expect(anySelectedWorker(f({ workers: { 692: false } }))).toBe(false);
    expect(anySelectedWorker(f({ workers: { 692: true } }))).toBe(true);
  });

  it('priority keeps only that priId', () => {
    expect(visibleWos(WOS, ALL, f({ pri: 1 })).map((w) => w.id)).toEqual([101]);
    expect(visibleWos(WOS, ALL, f({ pri: 7 })).map((w) => w.id)).toEqual([103]);
    expect(visibleWos(WOS, ALL, f({ pri: 42 }))).toHaveLength(0);
  });

  it('unassigned hides anything with assigned people', () => {
    expect(visibleWos(WOS, ALL, f({ unassigned: true })).map((w) => w.id)).toEqual([102, 103, 104]);
  });

  it('a selected worker keeps only WOs assigned to them; two selected is a union', () => {
    expect(visibleWos(WOS, ALL, f({ workers: { 692: true } })).map((w) => w.id)).toEqual([101, 105]);
    expect(visibleWos(WOS, ALL, f({ workers: { 4: true } })).map((w) => w.id)).toEqual([105]);
    expect(visibleWos(WOS, ALL, f({ workers: { 4: true, 2: true } })).map((w) => w.id)).toEqual([101, 105]);
    expect(visibleWos(WOS, ALL, f({ workers: { 692: false } }))).toHaveLength(5); // false = not selected
  });

  it('search is case-insensitive over sid / title / asset / assetTitle / loc / locTitle', () => {
    expect(visibleWos(WOS, ALL, f({ q: 'infeed' })).map((w) => w.id)).toEqual([101]);
    expect(visibleWos(WOS, ALL, f({ q: 'SAWMILL' })).map((w) => w.id)).toEqual([101]);
    expect(visibleWos(WOS, ALL, f({ q: 'pm-10' })).map((w) => w.id)).toEqual([102, 105]);
    expect(visibleWos(WOS, ALL, f({ q: 'zzz' }))).toHaveLength(0);
  });

  it('precedence: cats off beats everything; filters stack', () => {
    expect(visibleWos(WOS, { WO: false, PM: false, REQ: false, DONE: false }, f({ q: 'infeed' }))).toHaveLength(0);
    expect(visibleWos(WOS, ALL, f({ workers: { 692: true }, q: 'filter' })).map((w) => w.id)).toEqual([105]);
    expect(visibleWos(WOS, ALL, f({ workers: { 692: true }, unassigned: true }))).toHaveLength(0);
  });
});

describe('rules.ts - capacity (oracle 561-577)', () => {
  it('capacityWorkers: internal by default (the 1.0.1 case, unchanged)', () => {
    expect(capacityWorkers(WORKERS).map((w) => w.id)).toEqual([692, 2]);
  });

  it('capacityWorkers precedence: selected workers > team > internal', () => {
    expect(capacityWorkers(WORKERS, f({ workers: { 3: true } })).map((w) => w.id)).toEqual([3]);
    expect(capacityWorkers(WORKERS, f({ workers: { 3: true }, teamId: 1 })).map((w) => w.id)).toEqual([3]);
    expect(capacityWorkers(WORKERS, f({ teamId: 9 })).map((w) => w.id)).toEqual([3]);
    expect(capacityWorkers(WORKERS, f({ teamId: 1 })).map((w) => w.id)).toEqual([692, 2]);
    expect(capacityWorkers(WORKERS, f({ teamId: 77 }))).toHaveLength(0);
  });

  it('capacityPerWeek sums the precedence result', () => {
    expect(capacityPerWeek(WORKERS)).toBe(41);
    expect(capacityPerWeek([])).toBe(0);
    expect(capacityPerWeek(WORKERS, f({ workers: { 692: true } }))).toBe(1);
    expect(capacityPerWeek(WORKERS, f({ teamId: 9 }))).toBe(0);
  });

  it('weekStats on the fixture, all cats vs default cats', () => {
    expect(weekStats(FROM, TO, WOS)).toEqual({ planned: 10.5, unknown: 1, count: 5 });
    expect(weekStats(FROM, TO, visibleWos(WOS, DEFAULT_CATS))).toEqual({ planned: 6.5, unknown: 1, count: 4 });
    expect(weekStats('2026-09-21', '2026-09-27', WOS)).toEqual({ planned: 0, unknown: 0, count: 0 });
  });

  it('client weekStats with all cats on equals the API weeks[] entry', () => {
    const st = weekStats(FROM, TO, WOS);
    const api = RANGE.weeks[0];
    expect(st.planned).toBe(api.planned);
    expect(st.unknown).toBe(api.unknown);
    expect(st.count).toBe(api.count);
    expect(capacityPerWeek(WORKERS)).toBe(api.capacity);
    expect(pctOf(st.planned, capacityPerWeek(WORKERS))).toBe(api.pct);
  });
});

describe('rules.ts - text (oracle 590-606, 662-676, 785, 790)', () => {
  it('countText lumps REQ into WO like counts.wo and appends hours', () => {
    expect(countText(WOS)).toBe('2 WO | 2 PM | 1 done | 10.5h');
    expect(countText([PM_102])).toBe('1 PM');
    expect(countText([])).toBe('');
  });

  it('whoFor: up to three initials, +n, #id for unknowns', () => {
    expect(whoFor(WO_101, byId)).toBe('JB AK');
    expect(whoFor(PIN_105, byId)).toBe('JB AK CS +1');
    expect(whoFor(PM_102, byId)).toBe('');
    expect(whoFor(mkWo({ assigned: [999] }), byId)).toBe('#999');
  });

  it('chipTitle carries the OD-1 locked line on an engine-owned PM without a pin table', () => {
    const t = chipTitle(PM_102);
    expect(t).toBe(
      'PM-102 \u00b7 Weekly greasing\nPlanned\nno hours yet\nPM - engine owned; run the S3 DDL (WO_N_Plan) to allow planner pins',
    );
  });

  it('chipTitle on a labour WO with asset and location (OD-33: unchanged by the S1g fixture fields)', () => {
    expect(chipTitle(WO_101)).toBe(
      'WO-101 \u00b7 Replace chain on infeed\nPlanned \u00b7 priority P1\nINF-01 - Infeed conveyor\nSAW - Sawmill\n3.5h (labour)\ndrag to move',
    );
  });

  it('chipTitle: pinned, engine-owned movable, and closed branches', () => {
    expect(chipTitle(PIN_105)).toContain(
      '\nPINNED by the planner (engine date 2026-09-25) - the release engine leaves it alone',
    );
    expect(chipTitle(mkWo({ engineOwned: true, movable: true }))).toContain('\nPM - drag to move; the first move pins it');
    // Oracle quirk kept for parity: locked = C/D too (Landmines §E), and the oracle's only locked text is the PM one.
    expect(chipTitle(DONE_104)).toBe(
      'WO-104 \u00b7 Bearing swap\nClosed\n4h (labour)\nPM - engine owned; run the S3 DDL (WO_N_Plan) to allow planner pins',
    );
    expect(chipTitle(REQ_103)).toContain('\u00b7 priority N/A');
  });

  it('stripTitle', () => {
    expect(stripTitle(FROM, weekStats(FROM, TO, WOS), 41, 2)).toBe(
      'Week of Mon 14 Sep 2026\nplanned 10.5 h of 41 h capacity (2 workers)\n1 WO have no hours yet',
    );
    expect(stripTitle(FROM, { planned: 8, unknown: 0, count: 2 }, 0, 0)).toBe(
      'Week of Mon 14 Sep 2026\nplanned 8 h of 0 h capacity (0 workers)',
    );
  });

  it('weekBarTitle carries the real pct and degrades to `h` at capacity 0 (OD-25)', () => {
    expect(weekBarTitle(WW_692)).toBe('wk of 2026-09-14: 10 / 1 h (1000%) over');
    expect(weekBarTitle({ weekStart: FROM, planned: 74, capacity: 0, pct: 0, flag: 'ok' })).toBe(
      'wk of 2026-09-14: 74 h ok',
    );
  });

  it('rowTitle ends with the OD-34 click line', () => {
    expect(rowTitle(W_692, 10, 1, 1000)).toBe(
      'Jo Bloggs (JB)\n10 h attributed in this window \u00b7 capacity 1 h/week \u00b7 1000% of 1 h\nclick = filter the work to this person',
    );
    expect(rowTitle(W_2, 0, 0, 0)).toBe(
      'Ann Kowhai (AK)\n0 h attributed in this window \u00b7 capacity 40 h/week\nclick = filter the work to this person',
    );
  });
});

describe('rules.ts - the rail (OD-24 / OD-26)', () => {
  it('weeksIn is civil days / 7, at least 1', () => {
    expect(weeksIn(7)).toBe(1);
    expect(weeksIn(14)).toBe(2);
    expect(weeksIn(35)).toBe(5);
    expect(weeksIn(42)).toBe(6);
    expect(weeksIn(1)).toBe(1);
  });

  it('loadOf reads the string-keyed contract and defaults to 0', () => {
    expect(loadOf(RANGE.load, 692)).toBe(10);
    expect(loadOf(RANGE.load, 2)).toBe(0);
    expect(loadOf(RANGE.load, 424242)).toBe(0);
  });

  it('railRows default: loaded internal only, counts carried', () => {
    const r = railRows(WORKERS, RANGE.load, DEFAULT_RAIL);
    expect(r.rows.map((w) => w.id)).toEqual([692]);
    expect(r).toMatchObject({ internal: 2, contractors: 1, loaded: 1 });
    expect(countLine(r, DEFAULT_RAIL)).toBe('1 of 2 internal \u00b7 1 contractors hidden');
  });

  it('railRows: loadedOnly off shows every internal, API order kept', () => {
    const opts = { contractors: false, loadedOnly: false };
    const r = railRows(WORKERS, RANGE.load, opts);
    expect(r.rows.map((w) => w.id)).toEqual([692, 2]);
    expect(countLine(r, opts)).toBe('2 of 2 internal \u00b7 1 contractors hidden');
  });

  it('railRows: contractors on, loadedOnly on - the loaded contractor appears', () => {
    const opts = { contractors: true, loadedOnly: true };
    const r = railRows(WORKERS, RANGE.load, opts);
    expect(r.rows.map((w) => w.id)).toEqual([692, 3]);
    expect(countLine(r, opts)).toBe('1 of 2 internal \u00b7 1 contractors');
  });

  it('railRows: everything on', () => {
    const r = railRows(WORKERS, RANGE.load, { contractors: true, loadedOnly: false });
    expect(r.rows.map((w) => w.id)).toEqual([692, 2, 3]);
  });

  it('railRows: the team filter runs first and the counts follow it (S1g)', () => {
    const opts = { contractors: true, loadedOnly: false };
    const r1 = railRows(WORKERS, RANGE.load, opts, 1);
    expect(r1.rows.map((w) => w.id)).toEqual([692, 2]);
    expect(r1).toMatchObject({ internal: 2, contractors: 0, loaded: 1 });
    expect(countLine(r1, opts)).toBe('2 of 2 internal \u00b7 0 contractors');
    const r9 = railRows(WORKERS, RANGE.load, DEFAULT_RAIL, 9);
    expect(r9.rows).toHaveLength(0);
    expect(countLine(r9, DEFAULT_RAIL)).toBe('0 of 0 internal \u00b7 1 contractors hidden');
  });

  it('rowLoad is the oracle line 779 - 692 is exactly 1000% on a one-week window', () => {
    expect(rowLoad(W_692, RANGE.load, 1)).toEqual({ ld: 10, cap: 1, pct: 1000 });
    expect(rowLoad(W_692, RANGE.load, 5)).toEqual({ ld: 10, cap: 5, pct: 200 });
    expect(rowLoad(W_2, RANGE.load, 1)).toEqual({ ld: 0, cap: 40, pct: 0 });
  });

  it('flagCounts tallies over / under only', () => {
    expect(flagCounts([WW_692])).toEqual({ over: 1, under: 0 });
    expect(
      flagCounts([
        WW_692,
        { weekStart: FROM, planned: 1, capacity: 40, pct: 3, flag: 'under' },
        { weekStart: FROM, planned: 0, capacity: 40, pct: 0, flag: 'empty' },
      ]),
    ).toEqual({ over: 1, under: 1 });
  });
});

describe('rules.ts - the filters row (oracle 841-852)', () => {
  it('teamOptions labels byte-for-byte', () => {
    expect(teamOptions(RANGE.teams)).toEqual([
      { value: 1, label: 'MAINT \u00b7 2' },
      { value: 9, label: 'ACME (contractor) \u00b7 1' },
    ]);
    expect(teamOptions([{ id: 5, short: '', name: 'Electrical', internal: true, users: 0 }])[0].label).toBe(
      'Electrical \u00b7 0',
    );
  });

  it('priorityOptions labels byte-for-byte', () => {
    expect(priorityOptions(RANGE.priorities).map((o) => o.label)).toEqual([
      'P1 \u00b7 Urgent',
      'P2 \u00b7 High',
      'P3 \u00b7 Normal',
      'P4 \u00b7 Low',
      'N/A \u00b7 Not Applicable',
    ]);
    expect(priorityOptions(RANGE.priorities)[4].value).toBe(7);
  });

  it('workerMenu groups internal first, by team, contractor group suffixed; team filter applies', () => {
    const m = workerMenu(WORKERS);
    expect(m.map((g) => g.label)).toEqual(['MAINT', 'ACME \u00b7 contractor']);
    expect(m[0].rows).toEqual([
      { id: 2, name: 'Ann Kowhai', cap: '40/wk' },
      { id: 692, name: 'Jo Bloggs', cap: '1/wk' },
    ]);
    expect(m[1].rows).toEqual([{ id: 3, name: 'Con Tractor', cap: '0/wk' }]);
    expect(workerMenu(WORKERS, 1).map((g) => g.label)).toEqual(['MAINT']);
    expect(workerMenu(WORKERS, 9)[0].rows.map((r) => r.id)).toEqual([3]);
    expect(workerMenu([W_2, { ...W_3, team: '' }]).map((g) => g.label)).toEqual(['MAINT', 'other \u00b7 contractor']);
  });

  it('workerLabel: any / one name / n selected / #id', () => {
    expect(workerLabel(DEFAULT_FILTERS, byId)).toBe('any');
    expect(workerLabel(f({ workers: { 692: true } }), byId)).toBe('Jo Bloggs');
    expect(workerLabel(f({ workers: { 692: true, 2: false } }), byId)).toBe('Jo Bloggs');
    expect(workerLabel(f({ workers: { 692: true, 2: true } }), byId)).toBe('2 selected');
    expect(workerLabel(f({ workers: { 999: true } }), byId)).toBe('#999');
  });
});

describe('rules.ts - priority rank (OD-32)', () => {
  it('priRank is the 1-based Sort_Sequence position; 0 when unset or unknown', () => {
    expect(priRank(WO_101, RANGE.priorities)).toBe(1);
    expect(priRank(REQ_103, RANGE.priorities)).toBe(5);
    expect(priRank(PM_102, RANGE.priorities)).toBe(0);
    expect(priRank(mkWo({ priId: 42, pri: 'P9' }), RANGE.priorities)).toBe(0);
  });

  it('priClass lights r1..r4 only', () => {
    expect(priClass(1)).toBe('r1');
    expect(priClass(4)).toBe('r4');
    expect(priClass(5)).toBe('');
    expect(priClass(0)).toBe('');
  });

  it('priRankMap agrees with priRank for every fixture priority', () => {
    const m = priRankMap(RANGE.priorities);
    expect(m.get(1)).toBe(1);
    expect(m.get(7)).toBe(5);
    expect(m.get(42)).toBeUndefined();
    for (const wo of WOS) expect(m.get(wo.priId) ?? 0).toBe(priRank(wo, RANGE.priorities));
  });
});

describe('rules.ts - priority badge paint (S1i: OD-39 / OD-40 / OD-41)', () => {
  /** test-local Priority rows; the shared fixture stays RST-shaped (five distinct real colours) */
  const pri = (id: number, colour: string): Priority => ({ id, short: `P${id}`, title: `Priority ${id}`, colour });
  const none = (rank: number): PriBadge => ({ rank, bg: '', fg: '' });

  it('isHexColour accepts #RRGGBB in either case and nothing else (OD-36 free text)', () => {
    for (const ok of ['#FF9F40', '#ff9f40', '#000000', '#FFFFFF']) expect(isHexColour(ok)).toBe(true);
    for (const bad of ['', '#FFF', '#GGGGGG', 'FF9F40', '#FF9F400', 'red', 'rgb(1,2,3)', ' #FF9F40', '#FF9F40 ']) {
      expect(isHexColour(bad)).toBe(false);
    }
  });

  it('luminance anchors: black 0, white 1', () => {
    expect(luminance('#000000')).toBe(0);
    expect(luminance('#FFFFFF')).toBeCloseTo(1, 10);
  });

  it('textOn on the seven RST colours - the S1i spec §5.1 table, verified here not by hand', () => {
    expect(textOn('#FF9F40')).toBe('#2b2b2b');
    expect(textOn('#74EE66')).toBe('#2b2b2b');
    expect(textOn('#C0C0C0')).toBe('#2b2b2b');
    expect(textOn('#C499C1')).toBe('#2b2b2b');
    expect(textOn('#FFFFFF')).toBe('#2b2b2b');
    expect(textOn('#FF0000')).toBe('#ffffff');
    expect(textOn('#0080FF')).toBe('#ffffff'); // 3.73 vs 3.80 - the narrow one, pinned on purpose
  });

  it('textOn: the base badge colour keeps its dark text, black takes white, and the rule is a contrast floor not the oracle', () => {
    expect(textOn('#9AA3AD')).toBe('#2b2b2b'); // --mut, the base .pri background
    expect(textOn('#000000')).toBe('#ffffff');
    expect(textOn('#EF6C57')).toBe('#2b2b2b'); // .pri.A: the oracle hand-picked white; OD-40 never runs there
    expect(textOn('#6f7c87')).toBe('#ffffff'); // .pri.D: agrees with the oracle
  });

  it('priBadgeMap on the RST-shaped fixture: every row painted, rank agrees with priRankMap', () => {
    const m = priBadgeMap(RANGE.priorities);
    const r = priRankMap(RANGE.priorities);
    expect(m.size).toBe(5);
    for (const p of RANGE.priorities) {
      expect(m.get(p.id)).toEqual({ rank: r.get(p.id), bg: p.colour, fg: textOn(p.colour) });
    }
    expect(m.get(1)).toEqual({ rank: 1, bg: '#FF0000', fg: '#ffffff' });
    expect(m.get(4)).toEqual({ rank: 4, bg: '#0080FF', fg: '#ffffff' });
    expect(m.get(7)).toEqual({ rank: 5, bg: '#FFFFFF', fg: '#2b2b2b' });
    expect(m.get(42)).toBeUndefined();
  });

  it('a KT-shaped payload (four rows, one colour) paints nothing and keeps its ranks (OD-39)', () => {
    const kt: Priority[] = [
      { id: 1, short: 'A', title: 'Action Today', colour: '#FF8000' },
      { id: 2, short: 'B', title: 'Action this week', colour: '#FF8000' },
      { id: 3, short: 'C', title: 'Action this month', colour: '#FF8000' },
      { id: 4, short: 'D', title: 'As sched. permits', colour: '#FF8000' },
    ];
    expect(Array.from(priBadgeMap(kt).values())).toEqual([none(1), none(2), none(3), none(4)]);
  });

  it('case does not defeat the gate: #ff8000 and #FF8000 are one colour', () => {
    const m = priBadgeMap([pri(1, '#ff8000'), pri(2, '#FF8000')]);
    expect(m.get(1)).toEqual(none(1));
    expect(m.get(2)).toEqual(none(2));
  });

  it('a mixed payload: hex rows paint, junk and empty rows fall to the class', () => {
    const m = priBadgeMap([pri(1, '#FF0000'), pri(2, ''), pri(3, 'not-a-colour'), pri(4, '#0080FF')]);
    expect(m.get(1)).toEqual({ rank: 1, bg: '#FF0000', fg: '#ffffff' });
    expect(m.get(2)).toEqual(none(2));
    expect(m.get(3)).toEqual(none(3));
    expect(m.get(4)).toEqual({ rank: 4, bg: '#0080FF', fg: '#ffffff' });
  });

  it('one usable colour among several paints nothing - the documented OD-39 consequence', () => {
    const m = priBadgeMap([pri(1, '#FF0000'), pri(2, ''), pri(3, 'red')]);
    expect(Array.from(m.values())).toEqual([none(1), none(2), none(3)]);
  });

  it('all junk paints nothing with ranks intact; an empty payload is an empty map', () => {
    expect(Array.from(priBadgeMap([pri(1, ''), pri(2, 'x')]).values())).toEqual([none(1), none(2)]);
    expect(priBadgeMap([]).size).toBe(0);
  });
});

describe('rules.ts - the day dialog (oracle 717-727)', () => {
  it('labourFor / peopleFor', () => {
    expect(labourFor(101, RANGE.labour)).toHaveLength(2);
    expect(labourFor(102, RANGE.labour)).toHaveLength(0);
    expect(peopleFor(labourFor(101, RANGE.labour), byId)).toEqual(['Jo Bloggs 2.5h', 'Ann Kowhai 1h']);
    expect(peopleFor([{ ...RANGE.labour[0], userId: 999 }], byId)).toEqual(['#999 2.5h']);
  });

  it('dialogTitle uppercases the long date', () => {
    expect(dialogTitle('2026-09-14')).toBe('MON 14 SEP 2026');
    expect(dialogTitle('2026-09-16')).toBe('WED 16 SEP 2026');
  });

  it('dialogRows strings on the fixture', () => {
    const rows = dialogRows([WO_101, PM_102, REQ_103, PIN_105], RANGE.labour, byId);
    expect(rows[0]).toEqual({
      id: 101,
      sid: 'WO-101',
      cat: 'WO',
      pri: 'P1',
      priId: 1,
      meta1: 'Planned \u2192 2026-09-15',
      title: 'Replace chain on infeed',
      meta2: 'INF-01 \u00b7 Infeed conveyor \u00b7 SAW',
      hours: '3.5h (labour)',
      noHours: false,
      who: 'Jo Bloggs 2.5h, Ann Kowhai 1h',
    });
    expect(rows[1]).toMatchObject({ meta1: 'Planned \u00b7 engine owned', meta2: 'no asset', hours: 'no hours yet', noHours: true, who: 'owner Ann Kowhai' });
    expect(rows[2]).toMatchObject({ meta1: 'Request', hours: '2h (estimate)', who: 'nobody planned' });
    expect(rows[3]).toMatchObject({ meta1: 'Planned \u00b7 pinned', hours: '1h (estimate)' });
    expect(dialogRows([mkWo({ startTime: '07:30' })], [], byId)[0].meta1).toBe('Planned \u00b7 07:30');
  });
});

describe('rules.ts - the selected card (oracle 804-819)', () => {
  it('cardRows on the labour WO: PO linked, 2 days, labour source, two people', () => {
    const c = cardRows(WO_101, RANGE.labour, byId);
    expect(c.status).toBe('Planned \u00b7 PO linked');
    expect(c.pin).toBe('');
    expect(c.start).toBe('Mon 14 Sep 2026');
    expect(c.end).toBe('Tue 15 Sep 2026 (2 days)');
    expect(c.priority).toBe('P1');
    expect(c.asset).toBe('INF-01 \u00b7 Infeed conveyor');
    expect(c.assetTitle).toBe('Infeed conveyor');
    expect(c.loc).toBe('SAW \u00b7 Sawmill');
    expect(c.hours).toBe('3.5h');
    expect(c.hoursSrc).toBe('labour');
    expect(c.responsible).toBe('');
    expect(c.labour).toEqual([
      { name: 'Jo Bloggs', skillTitle: 'Fitter', hours: '2.5h', date: '2026-09-14' },
      { name: 'Ann Kowhai', skillTitle: '', hours: '1h', date: '' },
    ]);
  });

  it('cardRows on the locked PM: engine owned, no estimate, responsible named, no labour', () => {
    const c = cardRows(PM_102, RANGE.labour, byId);
    expect(c.status).toBe('Planned \u00b7 engine owned');
    expect(c.end).toBe('');
    expect(c.priority).toBe('\u2014');
    expect(c.asset).toBe('');
    expect(c.loc).toBe('');
    expect(c.hours).toBe('');
    expect(c.responsible).toBe('Ann Kowhai');
    expect(c.labour).toEqual([]);
  });

  it('cardRows on the pinned PM and a timed start', () => {
    const c = cardRows(PIN_105, RANGE.labour, byId);
    expect(c.status).toBe('Planned \u00b7 pinned');
    expect(c.pin).toBe('since 2026-09-10 \u00b7 engine date 2026-09-25');
    expect(cardRows(mkWo({ pinned: true }), [], byId).pin).toBe('since ?');
    expect(cardRows(mkWo({ start: '2026-09-16', startTime: '07:30', resp: 999 }), [], byId)).toMatchObject({
      start: 'Wed 16 Sep 2026 07:30',
      responsible: '#999',
    });
    expect(cardRows(mkWo({ end: '2026-09-16', days: 0 }), [], byId).end).toBe('Wed 16 Sep 2026');
  });
});

describe('rules.ts - chrome strings (OD-34)', () => {
  it('HINT and actorLabel byte-for-byte', () => {
    expect(HINT).toBe('click = select \u00b7 \u2190 \u2192 = navigate \u00b7 T = today \u00b7 Esc = clear');
    expect(actorLabel(1)).toBe('actor #1');
  });

  it('HINT_RW byte-for-byte: the drag and Ctrl+Z first, then the read-only hint (DP3b, OD-107)', () => {
    expect(HINT_RW).toBe(
      'drag = move \u00b7 Ctrl+Z = undo \u00b7 click = select \u00b7 \u2190 \u2192 = navigate \u00b7 T = today \u00b7 Esc = clear',
    );
  });

  it('chipTitle promises a drag only to a chip that can move (OD-107)', () => {
    const pm = mkWo({ sid: 'PM-9', title: 'Greasing', engineOwned: true, movable: true });
    expect(chipTitle(pm)).toContain('\nPM - drag to move; the first move pins it');
    const ro = chipTitle({ ...pm, movable: false });
    expect(ro).not.toContain('drag');
    expect(ro).toBe('PM-9 \u00b7 Greasing\nPlanned\nno hours yet');
    expect(chipTitle(mkWo({ sid: 'WO-9', title: 'X', movable: false }))).toBe('WO-9 \u00b7 X\nPlanned\nno hours yet');
  });
});
