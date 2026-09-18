/**
 * Azztec_SaaS_web_lib_dates_v1_2_0.ts  ->  web/src/lib/dates.ts
 * Version:  1.2.0   Date: 2026-09-16   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.1 · OD-23, OD-29 · Landmines §C, §D;
 *           Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md §3.9 (the header clock)
 * Oracle:   Planner_v1_8_1.html windowFor (src 519-532, six-month branch not ported), nav (871-876)
 * Twins:    backend/app/planner/rules.py civil_days / week_start / iso / parse_iso (Python date objects)
 *
 * THE ONLY MODULE IN web/ THAT TOUCHES Date (Landmines §C, .claude/rules/frontend.md). Everything
 * else passes yyyy-MM-dd strings. Rules:
 *   - never `new Date("2026-09-18")` - that is UTC midnight, the wrong civil day in NZ; parseISO() only
 *   - day arithmetic is CALENDAR arithmetic (differenceInCalendarDays), never ms/86400000 - the
 *     27 Sep 2026 DST change is where that breaks, and the Ignition daysBetween bug is exactly that
 *   - calendar-strict: '2026-02-31' is rejected, matching the backend's date.fromisoformat (Landmines §D).
 *     Java's SimpleDateFormat rolled it to 3 March; nobody "fixes" this back on either side.
 *
 * 1.1.0 adds the planner window: windowFor(mode, anchor) returns ISO strings, never Dates, and every
 * window it can produce is <= 42 days (OD-23) - the month view is at most 6 rows x 7. The six-month
 * mode is deliberately absent (needs an API summary shape; raw log 2026-09-12 §8.5). todayIso() is
 * the browser's civil day and is used ONLY for the default URL anchor (OD-29); the cells highlight
 * the API's `today` (OD-6, server tz).
 *
 * 1.2.0 adds the shell's clock: HEADER_DATE / HEADER_TIME are the HeaderToolbar view's own dateFormat()
 * patterns ("MMM d", "HH:mm:ss" - the same tokens in date-fns and Java), headerDate / headerTime format
 * a Date, and headerClock() takes ONE new Date() read for both strings so the pair can never straddle
 * midnight. The live KT page read "Sep 16" on 2026-09-16 (screenshot), so the en-US month abbreviation
 * is the oracle's. The clock is the only time the shell reads the browser's Date, and it does it here.
 *
 * Changelog:
 *   1.2.0  S1k: HEADER_DATE, HEADER_TIME, headerDate, headerTime, headerClock. 1.1.0 exports unchanged.
 *   1.1.0  S1f: Mode/MODES/isMode, Window/windowFor, navAnchor, todayIso, dowOf, daysInMonthOf,
 *          monthStart, isIso. 1.0.0 exports unchanged.
 *   1.0.0  Initial S1e.
 */
import {
  addDays as dfAddDays,
  addMonths,
  differenceInCalendarDays,
  format,
  getDay,
  getDaysInMonth,
  isValid,
  parseISO,
  startOfMonth,
  startOfWeek,
} from 'date-fns';

export const VERSION = '1.2.0';

/** The contract's date format. */
export const ISO = 'yyyy-MM-dd';

const ISO_RE = /^\d{4}-\d{2}-\d{2}$/;

/** yyyy-MM-dd -> Date (local civil day). Strict: shape, validity, and round-trip must all hold. */
export function parseIso(s: string): Date {
  if (!ISO_RE.test(s)) throw new RangeError(`not yyyy-MM-dd: ${s}`);
  const d = parseISO(s);
  if (!isValid(d) || format(d, ISO) !== s) throw new RangeError(`not a calendar date: ${s}`);
  return d;
}

/** True when v is a string parseIso() accepts. The URL-param guard (OD-29). */
export function isIso(v: unknown): v is string {
  if (typeof v !== 'string') return false;
  try {
    parseIso(v);
    return true;
  } catch {
    return false;
  }
}

/** Date -> yyyy-MM-dd. The twin of rules.iso(). */
export function iso(d: Date): string {
  return format(d, ISO);
}

function asDate(v: string | Date): Date {
  return typeof v === 'string' ? parseIso(v) : v;
}

/**
 * Civil days from a to b, signed: civilDays('2026-09-17', '2026-09-29') === 12 and the reverse is -12.
 * The twin of rules.civil_days() = (date_b - date_a).days. Inclusive windows are civilDays + 1.
 */
export function civilDays(a: string | Date, b: string | Date): number {
  return differenceInCalendarDays(asDate(b), asDate(a));
}

/** Shift by n calendar days, returned as yyyy-MM-dd. DST-safe because it is calendar, not ms. */
export function addDays(d: string | Date, n: number): string {
  return iso(dfAddDays(asDate(d), n));
}

/** Monday of the week containing d, as yyyy-MM-dd. Weeks start Monday (Port Spec §7, OD-6). */
export function weekStart(d: string | Date): string {
  return iso(startOfWeek(asDate(d), { weekStartsOn: 1 }));
}

/* ------------------------------------------------------------------ 1.1.0: the planner window */

/** The three modes S1f draws. 'sixm' is the oracle's fourth and is not ported (spec §1). */
export type Mode = 'week' | 'twoweek' | 'month';
export const MODES: ReadonlyArray<Mode> = ['week', 'twoweek', 'month'];

export function isMode(v: unknown): v is Mode {
  return typeof v === 'string' && MODES.some((m) => m === v);
}

/** Inclusive window as ISO strings. `days` is civilDays(from, to) + 1 and is always <= 42 (OD-23). */
export type Window = { from: string; to: string; days: number };

/** Day of week, Monday = 0 ... Sunday = 6. The oracle's (getDay() + 6) % 7. */
export function dowOf(d: string | Date): number {
  return (getDay(asDate(d)) + 6) % 7;
}

export function daysInMonthOf(d: string | Date): number {
  return getDaysInMonth(asDate(d));
}

/** First of the month containing d, as yyyy-MM-dd. */
export function monthStart(d: string | Date): string {
  return iso(startOfMonth(asDate(d)));
}

/**
 * Port of the oracle's windowFor(). week = Monday..Sunday of the anchor's week; twoweek = 14 days from
 * that Monday; month = from the Monday on or before the 1st, rows = ceil((dow(1st) + daysInMonth) / 7),
 * to = from + rows*7 - 1. A 31-day month starting Saturday or Sunday needs 6 rows = 42 days, the cap.
 */
export function windowFor(mode: Mode, anchor: string): Window {
  let from: string;
  let to: string;
  if (mode === 'week') {
    from = weekStart(anchor);
    to = addDays(from, 6);
  } else if (mode === 'twoweek') {
    from = weekStart(anchor);
    to = addDays(from, 13);
  } else {
    const first = monthStart(anchor);
    from = weekStart(first);
    const rows = Math.ceil((dowOf(first) + daysInMonthOf(first)) / 7);
    to = addDays(from, rows * 7 - 1);
  }
  return { from, to, days: civilDays(from, to) + 1 };
}

/**
 * Port of the oracle's nav(n): week moves the anchor 7n days (weekday kept), twoweek 14n, month lands on
 * the 1st of the month n months away (the oracle's addMonths(d, n) is new Date(y, m + n, 1)).
 */
export function navAnchor(mode: Mode, anchor: string, n: number): string {
  if (mode === 'week') return addDays(anchor, 7 * n);
  if (mode === 'twoweek') return addDays(anchor, 14 * n);
  return iso(addMonths(startOfMonth(asDate(anchor)), n));
}

/** The browser's civil day. Default URL anchor only (OD-29); never the source of the `today` cell. */
export function todayIso(): string {
  return iso(new Date());
}

/** HeaderToolbar dateLabel: dateFormat(now(), "MMM d") */
export const HEADER_DATE = 'MMM d';
/** HeaderToolbar timeLabel: dateFormat(now(), "HH:mm:ss") */
export const HEADER_TIME = 'HH:mm:ss';

export function headerDate(d: Date): string {
  return format(d, HEADER_DATE);
}

export function headerTime(d: Date): string {
  return format(d, HEADER_TIME);
}

export type HeaderClock = { date: string; time: string };

/** Both header strings from ONE read of the browser clock. */
export function headerClock(): HeaderClock {
  const now = new Date();
  return { date: headerDate(now), time: headerTime(now) };
}
