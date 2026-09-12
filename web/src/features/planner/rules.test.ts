/**
 * Azztec_SaaS_web_planner_rules_test_v1_0_1.ts  ->  web/src/features/planner/rules.test.ts
 * Version:  1.0.1   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §6 (rules.test.ts row) · pair rule
 *
 * Zero network, zero DOM, plain objects from range.fixture.ts. The string cases are byte-for-byte the
 * oracle's output - a planner reads these tooltips every day, so they are the parity surface.
 *
 * Changelog:
 *   1.0.1  Four assertions corrected against the oracle: fmtLong is the ABBREVIATED day name
 *          ('Mon 14 Sep 2026', src 514), not the full one. Caught by the run, not by reading -
 *          1.0.0 asserted 'Monday' from memory and rules.ts was right all along.
 *   1.0.0  Initial S1f.
 */
import { describe, expect, it } from 'vitest';

import {
  DEFAULT_CATS,
  DEFAULT_RAIL,
  VERSION,
  barClass,
  barWidth,
  byDay,
  capacityPerWeek,
  capacityWorkers,
  chipTitle,
  countLine,
  countText,
  flagCounts,
  fmtH,
  fmtLong,
  fmtNum,
  fmtRange,
  indexWorkers,
  isCat,
  loadOf,
  monthKey,
  monthLabel,
  pctOf,
  railRows,
  rowLoad,
  rowTitle,
  stripTitle,
  visibleWos,
  weekBarTitle,
  weekStats,
  weeksIn,
  whoFor,
  ymd,
} from './rules';
import { DONE_104, FROM, PIN_105, PM_102, RANGE, REQ_103, TO, WO_101, WORKERS, WOS, WW_692, W_2, W_692, mkWo } from './range.fixture';

export const TEST_VERSION = '1.0.1';

describe('rules.ts - constants and ISO parts', () => {
  it('carries its version and the oracle cats default (DONE off)', () => {
    expect(VERSION).toBe('1.0.1');
    expect(DEFAULT_CATS).toEqual({ WO: true, PM: true, REQ: true, DONE: false });
    expect(DEFAULT_RAIL).toEqual({ contractors: false, loadedOnly: true });
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

  it('fmtRange shows the from-year only when it differs (oracle 510-513)', () => {
    expect(fmtRange('2026-09-14', '2026-09-20')).toBe('14 Sep \u2013 20 Sep 2026');
    expect(fmtRange('2026-12-28', '2027-01-03')).toBe('28 Dec 2026 \u2013 3 Jan 2027');
  });

  it('fmtLong and monthLabel match the oracle strings', () => {
    expect(fmtLong('2026-09-14', 0)).toBe('Mon 14 Sep 2026');
    expect(fmtLong('2026-09-20', 6)).toBe('Sun 20 Sep 2026');
    expect(fmtLong('2026-09-16', 2)).toBe('Wed 16 Sep 2026');
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
    const byId = indexWorkers(WORKERS);
    expect(byId.get(692)?.initials).toBe('JB');
    expect(byId.get(999)).toBeUndefined();
  });
});

describe('rules.ts - capacity (oracle 561-577)', () => {
  it('capacityWorkers is internal only in S1f', () => {
    expect(capacityWorkers(WORKERS).map((w) => w.id)).toEqual([692, 2]);
  });

  it('capacityPerWeek sums internal hrsPerWeek', () => {
    expect(capacityPerWeek(WORKERS)).toBe(41);
    expect(capacityPerWeek([])).toBe(0);
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
    const byId = indexWorkers(WORKERS);
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

  it('chipTitle on a labour WO with asset and location', () => {
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

  it('rowTitle', () => {
    expect(rowTitle(W_692, 10, 1, 1000)).toBe(
      'Jo Bloggs (JB)\n10 h attributed in this window \u00b7 capacity 1 h/week \u00b7 1000% of 1 h',
    );
    expect(rowTitle(W_2, 0, 0, 0)).toBe('Ann Kowhai (AK)\n0 h attributed in this window \u00b7 capacity 40 h/week');
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
