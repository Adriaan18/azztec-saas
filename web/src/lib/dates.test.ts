/**
 * Azztec_SaaS_web_lib_dates_test_v1_1_0.ts  ->  web/src/lib/dates.test.ts
 * Version:  1.1.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §6 (dates.test.ts row) · pair rule (Ways of Working §4)
 *
 * Zero network, zero DOM, plain string values. The DST pair (17<->29 Sep 2026 = +/-12) is the same
 * assertion the backend carries for civil_days (Landmines §A) - both halves of the contract must agree.
 * NZ DST starts 27 Sep 2026; on a UTC CI box these pass trivially, on the NZ dev box they are the test.
 *
 * 1.1.0 adds the window cases. The OD-23 proof is a loop, not an assertion: every month window from
 * 2025-01 to 2030-12 is <= 42 days and checkWindow() accepts it, so the cap and the oracle's month
 * geometry agree by construction, not by the one example someone picked.
 *
 * Changelog:
 *   1.1.0  S1f: windowFor week / twoweek / month (Sep 2026 across the DST day, Aug 2026 = 42), the
 *          2025-2030 loop, navAnchor, dowOf, isMode, isIso, todayIso shape.
 *   1.0.0  Initial S1e.
 */
import { describe, expect, it } from 'vitest';

import { checkWindow } from '../features/planner/usePlannerRange';
import {
  MODES,
  VERSION,
  addDays,
  civilDays,
  dowOf,
  isIso,
  isMode,
  iso,
  navAnchor,
  parseIso,
  todayIso,
  weekStart,
  windowFor,
} from './dates';

export const TEST_VERSION = '1.1.0';

describe('dates.ts - the civil-date twin', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.1.0');
  });

  // 1. the Ignition daysBetween bug, must not be reproduced
  it('civilDays 17 -> 29 Sep 2026 is 12 and the reverse is -12', () => {
    expect(civilDays('2026-09-17', '2026-09-29')).toBe(12);
    expect(civilDays('2026-09-29', '2026-09-17')).toBe(-12);
  });

  // 2. symmetric across the 27 Sep 2026 transition itself
  it('civilDays is symmetric across the DST change', () => {
    expect(civilDays('2026-09-26', '2026-09-28')).toBe(2);
    expect(civilDays('2026-09-28', '2026-09-26')).toBe(-2);
    expect(civilDays('2026-09-27', '2026-09-27')).toBe(0);
  });

  // 3. Monday-start weeks, Monday included
  it('weekStart returns the Monday for every day of the week', () => {
    const days = ['2026-09-14', '2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18', '2026-09-19', '2026-09-20'];
    for (const d of days) expect(weekStart(d)).toBe('2026-09-14');
    expect(weekStart('2026-09-21')).toBe('2026-09-21');
  });

  // 4. round-trip with no timezone shift
  it('iso(parseIso(s)) round-trips without a day shift', () => {
    for (const s of ['2026-09-18', '2026-01-01', '2026-12-31', '2026-09-27', '2024-02-29']) {
      expect(iso(parseIso(s))).toBe(s);
    }
  });

  // 5. calendar addition across the boundary
  it('addDays across the DST boundary keeps the civil day count', () => {
    expect(addDays('2026-09-26', 2)).toBe('2026-09-28');
    expect(addDays('2026-09-28', -2)).toBe('2026-09-26');
    expect(civilDays('2026-09-26', addDays('2026-09-26', 2))).toBe(2);
    expect(addDays('2026-09-14', 41)).toBe('2026-10-25'); // the month view's widest window, OD-23
  });

  // 6. calendar-strict, matching the backend
  it('rejects 2026-02-31 and malformed input, like date.fromisoformat', () => {
    expect(() => parseIso('2026-02-31')).toThrow(RangeError);
    expect(() => parseIso('2026-13-01')).toThrow(RangeError);
    expect(() => parseIso('2026-9-1')).toThrow(RangeError);
    expect(() => parseIso('2026-09-18T00:00:00')).toThrow(RangeError);
    expect(() => parseIso('')).toThrow(RangeError);
    expect(() => civilDays('2026-02-31', '2026-03-01')).toThrow(RangeError);
  });
});

describe('dates.ts 1.1.0 - the planner window (oracle windowFor / nav)', () => {
  // 7. week and twoweek from a mid-week anchor
  it('week and twoweek windows start on the Monday of the anchor', () => {
    expect(windowFor('week', '2026-09-16')).toEqual({ from: '2026-09-14', to: '2026-09-20', days: 7 });
    expect(windowFor('twoweek', '2026-09-16')).toEqual({ from: '2026-09-14', to: '2026-09-27', days: 14 });
    expect(windowFor('week', '2026-09-14')).toEqual({ from: '2026-09-14', to: '2026-09-20', days: 7 });
    expect(windowFor('week', '2026-09-20')).toEqual({ from: '2026-09-14', to: '2026-09-20', days: 7 });
  });

  // 8. Sep 2026: 1 Sep is a Tuesday, 30 days -> 5 rows; the window crosses the 27 Sep DST day
  it('month Sep 2026 is 31 Aug .. 4 Oct, 35 days, across the DST change', () => {
    expect(windowFor('month', '2026-09-16')).toEqual({ from: '2026-08-31', to: '2026-10-04', days: 35 });
    expect(windowFor('month', '2026-09-01')).toEqual({ from: '2026-08-31', to: '2026-10-04', days: 35 });
    expect(windowFor('month', '2026-09-30')).toEqual({ from: '2026-08-31', to: '2026-10-04', days: 35 });
  });

  // 9. Aug 2026: 1 Aug is a Saturday, 31 days -> 6 rows = 42, the OD-23 worst case
  it('month Aug 2026 is 27 Jul .. 6 Sep, exactly 42 days', () => {
    expect(windowFor('month', '2026-08-15')).toEqual({ from: '2026-07-27', to: '2026-09-06', days: 42 });
    expect(checkWindow('2026-07-27', '2026-09-06')).toEqual({ ok: true, days: 42 });
  });

  // 10. June 2026: 1 Jun is a Monday -> the variety window's month starts on its own Monday
  it('month Jun 2026 is 1 Jun .. 5 Jul, 35 days', () => {
    expect(windowFor('month', '2026-06-15')).toEqual({ from: '2026-06-01', to: '2026-07-05', days: 35 });
  });

  // 11. the OD-23 proof, by construction
  it('every month window 2025-01 .. 2030-12 is <= 42 days and checkWindow accepts it', () => {
    for (let y = 2025; y <= 2030; y++) {
      for (let m = 1; m <= 12; m++) {
        const anchor = `${y}-${String(m).padStart(2, '0')}-15`;
        const w = windowFor('month', anchor);
        expect(w.days).toBeLessThanOrEqual(42);
        expect(w.days % 7).toBe(0);
        expect(dowOf(w.from)).toBe(0);
        expect(dowOf(w.to)).toBe(6);
        expect(checkWindow(w.from, w.to)).toEqual({ ok: true, days: w.days });
      }
    }
  });

  // 12. nav: month lands on the 1st, week keeps the weekday, twoweek moves 14
  it('navAnchor moves the anchor like the oracle nav()', () => {
    expect(navAnchor('month', '2026-09-16', 1)).toBe('2026-10-01');
    expect(navAnchor('month', '2026-09-16', -1)).toBe('2026-08-01');
    expect(navAnchor('month', '2026-12-16', 1)).toBe('2027-01-01');
    expect(navAnchor('week', '2026-09-16', 1)).toBe('2026-09-23');
    expect(navAnchor('week', '2026-09-16', -1)).toBe('2026-09-09');
    expect(navAnchor('twoweek', '2026-09-16', 1)).toBe('2026-09-30');
    expect(dowOf(navAnchor('week', '2026-09-16', 3))).toBe(dowOf('2026-09-16'));
  });

  // 13. Monday = 0
  it('dowOf is Monday-based', () => {
    expect(dowOf('2026-09-14')).toBe(0);
    expect(dowOf('2026-09-20')).toBe(6);
    expect(dowOf('2026-08-01')).toBe(5);
  });

  // 14. the URL-param guards (OD-29)
  it('isMode and isIso guard the search params', () => {
    expect(MODES).toEqual(['week', 'twoweek', 'month']);
    expect(isMode('week')).toBe(true);
    expect(isMode('sixm')).toBe(false);
    expect(isMode(undefined)).toBe(false);
    expect(isIso('2026-09-16')).toBe(true);
    expect(isIso('2026-02-31')).toBe(false);
    expect(isIso(42)).toBe(false);
  });

  // 15. todayIso is a real civil date - shape and round-trip only, never the value
  it('todayIso returns a parseable yyyy-MM-dd', () => {
    const t = todayIso();
    expect(isIso(t)).toBe(true);
    expect(weekStart(t) <= t).toBe(true);
  });
});
