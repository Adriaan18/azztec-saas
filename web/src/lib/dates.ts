/**
 * Azztec_SaaS_web_lib_dates_v1_0_0.ts  ->  web/src/lib/dates.ts
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1e_Web_Chunk_Spec_v1_0_0.md §6.1 · Planner Port Spec §7 · Landmines §C, §D
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
 * Changelog:
 *   1.0.0  Initial S1e.
 */
import {
  addDays as dfAddDays,
  differenceInCalendarDays,
  format,
  isValid,
  parseISO,
  startOfWeek,
} from 'date-fns';

export const VERSION = '1.0.0';

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
