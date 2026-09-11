/**
 * Azztec_SaaS_web_lib_dates_test_v1_0_0.ts  ->  web/src/lib/dates.test.ts
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1e_Web_Chunk_Spec_v1_0_0.md §6.1 tests 1-6 · pair rule (Ways of Working §4)
 *
 * Zero network, zero DOM, plain string values. The DST pair (17<->29 Sep 2026 = +/-12) is the same
 * assertion the backend carries for civil_days (Landmines §A) - both halves of the contract must agree.
 * NZ DST starts 27 Sep 2026; on a UTC CI box these pass trivially, on the NZ dev box they are the test.
 *
 * Changelog:
 *   1.0.0  Initial S1e.
 */
import { describe, expect, it } from 'vitest';

import { VERSION, addDays, civilDays, iso, parseIso, weekStart } from './dates';

export const TEST_VERSION = '1.0.0';

describe('dates.ts - the civil-date twin', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.0');
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
