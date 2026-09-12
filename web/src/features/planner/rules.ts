/**
 * Azztec_SaaS_web_planner_rules_v1_0_0.ts  ->  web/src/features/planner/rules.ts
 * Version:  1.0.1   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.2 · OD-25, OD-26 · Landmines §D (index once)
 * Oracle:   Planner_v1_8_1.html - constants 482-485, state defaults 492, fmtRange/fmtLong/fmtH/fmtNum
 *           510-516, visible/byDay 541-558, capacity 561-578, chipEl who/title 590-606, month header
 *           label 623, countText 662-667, strip 668-676, rail 774-790.
 * Consumes: src/api/client/types.gen.ts (Wo, Worker, WorkerWeek - read 2026-09-12, ^export type lines).
 *
 * Pure. No Date (dates.ts owns it), no DOM, no fetch. Everything here is a function over the RangeData
 * dicts, so it tests with plain objects and the components stay thin. Strings are byte-for-byte the
 * oracle's - the tooltip texts are the parity surface a planner reads every day.
 *
 * Two deliberate departures from the oracle, both recorded in the spec:
 *   - weeksIn() takes civil days (window.days), never (to - from) / 864e5 - the DST landmine (§C).
 *   - railRows() is OD-24/OD-26: internal by default, contractors and loaded-only as client toggles,
 *     and the count line so hidden rows are counted, never silent. The oracle listed all 363.
 * capacityWorkers() carries only the "all internal" branch: the selected-worker and team branches
 * arrive with the S1g filters, and the precedence order is kept in the comment so nobody reorders it.
 *
 * Changelog:
 *   1.0.1  Comment fix only, no behaviour change: fmtLong's doc line claimed 'Monday 14 Sep 2026'.
 *          The oracle (src 514) builds it from the ABBREVIATED DOW, so the real output is
 *          'Mon 14 Sep 2026'. The code was already right; the comment was not.
 *   1.0.0  Initial S1f.
 */
import type { Wo, Worker, WorkerWeek } from '../../api/client/types.gen';

export const VERSION = '1.0.1';

/* ------------------------------------------------------------------ constants (oracle 482-485) */

export const CAT_ORDER = ['WO', 'PM', 'REQ', 'DONE'] as const;
export type Cat = (typeof CAT_ORDER)[number];
export type Cats = Record<Cat, boolean>;
/** The oracle's S.cats default: DONE off (src 492). */
export const DEFAULT_CATS: Cats = { WO: true, PM: true, REQ: true, DONE: false };

export const DOW = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'] as const;
export const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] as const;
export const MONL = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const;

export function isCat(v: string): v is Cat {
  return CAT_ORDER.some((c) => c === v);
}

/* ------------------------------------------------------------------ ISO string parts (no Date) */

/** y / m (1-12) / d from yyyy-MM-dd by slicing. Callers pass contract strings, already validated. */
export function ymd(s: string): { y: number; m: number; d: number } {
  return { y: Number(s.slice(0, 4)), m: Number(s.slice(5, 7)), d: Number(s.slice(8, 10)) };
}

/** The 'yyyy-MM' key the month view uses for its `out` cells. */
export function monthKey(s: string): string {
  return s.slice(0, 7);
}

/** Oracle fmtRange (510-513): `14 Sep - 20 Sep 2026`, the from-year shown only when it differs. */
export function fmtRange(from: string, to: string): string {
  const a = ymd(from);
  const b = ymd(to);
  const sa = `${a.d} ${MON[a.m - 1]}${a.y !== b.y ? ` ${a.y}` : ''}`;
  return `${sa} \u2013 ${b.d} ${MON[b.m - 1]} ${b.y}`;
}

/** Oracle fmtLong (514): `Mon 14 Sep 2026` - the ABBREVIATED day, title-cased. dow is Monday = 0; strips pass 0. */
export function fmtLong(s: string, dow: number): string {
  const p = ymd(s);
  const name = dow >= 0 && dow < 7 ? DOW[dow] : 'MON';
  return `${name.charAt(0)}${name.slice(1).toLowerCase()} ${p.d} ${MON[p.m - 1]} ${p.y}`;
}

/** Oracle 623: the month view's range label. */
export function monthLabel(anchor: string, from: string, to: string): string {
  const p = ymd(anchor);
  return `${MONL[p.m - 1]} ${p.y}  \u00b7  ${fmtRange(from, to)}`;
}

/* ------------------------------------------------------------------ numbers (oracle 515-516) */

export function fmtNum(h: number): string {
  return (Math.round(h * 10) / 10).toString().replace(/\.0$/, '');
}

export function fmtH(h: number): string {
  if (!h || h <= 0) return '?';
  return `${fmtNum(h)}h`;
}

/** Oracle 669 / 779: capacity 0 -> 0, never NaN. Real pct otherwise, however large (OD-25). */
export function pctOf(planned: number, capacity: number): number {
  return capacity > 0 ? Math.round((100 * planned) / capacity) : 0;
}

export type BarClass = 'over' | 'ok' | '';

/** Oracle 578: over > 100, ok >= 80, neutral below. */
export function barClass(pct: number): BarClass {
  return pct > 100 ? 'over' : pct >= 80 ? 'ok' : '';
}

/** OD-25: the bar never exceeds 100% wide; the label carries the real pct. */
export function barWidth(pct: number): string {
  return `${Math.min(100, pct)}%`;
}

/* ------------------------------------------------------------------ visibility (oracle 541-558) */

/** Cats only in S1f. Priority / unassigned / worker / search arrive with the S1g filters row. */
export function visibleWos(wos: ReadonlyArray<Wo>, cats: Cats): Wo[] {
  return wos.filter((w) => isCat(w.cat) && cats[w.cat]);
}

/** Keyed by `start`. Built once per render (Landmines §D), never per cell. */
export function byDay(wos: ReadonlyArray<Wo>): Map<string, Wo[]> {
  const m = new Map<string, Wo[]>();
  for (const w of wos) {
    const list = m.get(w.start);
    if (list) list.push(w);
    else m.set(w.start, [w]);
  }
  return m;
}

/** Workers by id, built once per data load. */
export function indexWorkers(workers: ReadonlyArray<Worker>): Map<number, Worker> {
  return new Map(workers.map((w) => [w.id, w]));
}

/* ------------------------------------------------------------------ capacity (oracle 561-577) */

/**
 * Oracle precedence: selected workers > team > all internal. S1f has no worker or team filter, so only
 * the third branch exists here; S1g adds the first two IN THIS ORDER.
 */
export function capacityWorkers(workers: ReadonlyArray<Worker>): Worker[] {
  return workers.filter((w) => w.internal);
}

export function capacityPerWeek(workers: ReadonlyArray<Worker>): number {
  let c = 0;
  for (const w of capacityWorkers(workers)) c += w.hrsPerWeek || 0;
  return Math.round(c * 100) / 100;
}

export type WeekStats = { planned: number; unknown: number; count: number };

/** Oracle weekStats: WOs whose `start` lies in weekStart..weekEnd (ISO strings compare lexically). */
export function weekStats(weekStart: string, weekEnd: string, wos: ReadonlyArray<Wo>): WeekStats {
  let planned = 0;
  let unknown = 0;
  let count = 0;
  for (const w of wos) {
    if (w.start < weekStart || w.start > weekEnd) continue;
    count++;
    if (w.hrs > 0) planned += w.hrs;
    else unknown++;
  }
  return { planned: Math.round(planned * 100) / 100, unknown, count };
}

/* ------------------------------------------------------------------ text (oracle 590-606, 662-676) */

/** Oracle countText: `9 WO | 42 PM | 604 done | 123h` - REQ counts as WO, matching counts.wo. */
export function countText(list: ReadonlyArray<Wo>): string {
  let wo = 0;
  let pm = 0;
  let done = 0;
  let hrs = 0;
  for (const w of list) {
    if (w.cat === 'DONE') done++;
    else if (w.cat === 'PM') pm++;
    else wo++;
    hrs += w.hrs || 0;
  }
  const p: string[] = [];
  if (wo) p.push(`${wo} WO`);
  if (pm) p.push(`${pm} PM`);
  if (done) p.push(`${done} done`);
  if (hrs) p.push(`${fmtNum(hrs)}h`);
  return p.join(' | ');
}

/** Oracle 590-594: up to three initials, `+n` beyond, `#id` when the worker is not in the list. */
export function whoFor(wo: Wo, byId: ReadonlyMap<number, Worker>): string {
  if (!wo.assigned.length) return '';
  const inits: string[] = [];
  for (let i = 0; i < wo.assigned.length && i < 3; i++) {
    const id = wo.assigned[i];
    const w = byId.get(id);
    inits.push(w ? w.initials : `#${id}`);
  }
  return inits.join(' ') + (wo.assigned.length > 3 ? ` +${wo.assigned.length - 3}` : '');
}

/** Oracle 600-606: the chip tooltip. The locked line is OD-1 on RST, 2,364 times. */
export function chipTitle(wo: Wo): string {
  let t = `${wo.sid} \u00b7 ${wo.title}\n${wo.statusTitle}${wo.pri ? ` \u00b7 priority ${wo.pri}` : ''}`;
  if (wo.asset) t += `\n${wo.asset}${wo.assetTitle ? ` - ${wo.assetTitle}` : ''}`;
  if (wo.loc) t += `\n${wo.loc}${wo.locTitle ? ` - ${wo.locTitle}` : ''}`;
  t += wo.hrs > 0 ? `\n${fmtH(wo.hrs)} (${wo.hrsSrc})` : '\nno hours yet';
  if (wo.pinned) {
    t += `\nPINNED by the planner${wo.engineDate ? ` (engine date ${wo.engineDate})` : ''} - the release engine leaves it alone`;
  } else if (wo.locked) {
    t += '\nPM - engine owned; run the S3 DDL (WO_N_Plan) to allow planner pins';
  } else if (wo.engineOwned) {
    t += '\nPM - drag to move; the first move pins it';
  } else if (wo.movable) {
    t += '\ndrag to move';
  }
  return t;
}

/** Oracle 674: the strip tooltip. weekStart is always a Monday, so fmtLong gets dow 0. */
export function stripTitle(weekStart: string, st: WeekStats, cap: number, nWorkers: number): string {
  return (
    `Week of ${fmtLong(weekStart, 0)}\nplanned ${fmtNum(st.planned)} h of ${fmtNum(cap)} h capacity (${nWorkers} workers)` +
    (st.unknown ? `\n${st.unknown} WO have no hours yet` : '')
  );
}

/** Oracle 785: one rail week bar's tooltip. Capacity 0 degrades to `planned h` (OD-25). */
export function weekBarTitle(wk: WorkerWeek): string {
  const cap = wk.capacity > 0 ? ` / ${fmtNum(wk.capacity)} h (${wk.pct}%)` : ' h';
  return `wk of ${wk.weekStart}: ${fmtNum(wk.planned)}${cap} ${wk.flag}`;
}

/** Oracle 790 minus its last line (click = filter, drag = plan hours are S1g / S4). */
export function rowTitle(w: Worker, ld: number, cap: number, pct: number): string {
  return (
    `${w.name} (${w.sid})\n${fmtNum(ld)} h attributed in this window \u00b7 capacity ${fmtNum(w.hrsPerWeek || 0)} h/week` +
    (cap > 0 ? ` \u00b7 ${pct}% of ${fmtNum(cap)} h` : '')
  );
}

/* ------------------------------------------------------------------ the rail (oracle 774-790, OD-26) */

/** Oracle 775 computed this from ms / 864e5; window.days is civil days, so this is exact and DST-safe. */
export function weeksIn(days: number): number {
  return Math.max(1, days / 7);
}

/** Hours attributed to a worker in the window; `load` is keyed by user id as a string (contract). */
export function loadOf(load: Readonly<Record<string, number>>, id: number): number {
  return load[String(id)] || 0;
}

export type RailOpts = { contractors: boolean; loadedOnly: boolean };
export const DEFAULT_RAIL: RailOpts = { contractors: false, loadedOnly: true };

export type RailRows = {
  rows: Worker[];
  internal: number;
  contractors: number;
  /** internal workers with hours in the window */
  loaded: number;
};

/** OD-26. API order kept (internal first, then name - the service sorts, the UI does not). */
export function railRows(
  workers: ReadonlyArray<Worker>,
  load: Readonly<Record<string, number>>,
  opts: RailOpts,
): RailRows {
  let internal = 0;
  let contractors = 0;
  let loaded = 0;
  const rows: Worker[] = [];
  for (const w of workers) {
    if (w.internal) {
      internal++;
      if (loadOf(load, w.id) > 0) loaded++;
    } else {
      contractors++;
    }
    if (!w.internal && !opts.contractors) continue;
    if (opts.loadedOnly && loadOf(load, w.id) <= 0) continue;
    rows.push(w);
  }
  return { rows, internal, contractors, loaded };
}

/** OD-26: `46 of 179 internal \u00b7 184 contractors hidden` - hidden rows are counted, never silent. */
export function countLine(r: RailRows, opts: RailOpts): string {
  const shownInternal = opts.loadedOnly ? r.loaded : r.internal;
  const left = `${shownInternal} of ${r.internal} internal`;
  const right = opts.contractors ? `${r.contractors} contractors` : `${r.contractors} contractors hidden`;
  return `${left} \u00b7 ${right}`;
}

/** The per-row numbers the oracle computes inline at 779. */
export function rowLoad(
  w: Worker,
  load: Readonly<Record<string, number>>,
  weeks: number,
): { ld: number; cap: number; pct: number } {
  const ld = loadOf(load, w.id);
  const cap = (w.hrsPerWeek || 0) * weeks;
  return { ld, cap, pct: pctOf(ld, cap) };
}

/** The oracle's over / under tally for a row's `flags` span (783-787). */
export function flagCounts(wks: ReadonlyArray<WorkerWeek>): { over: number; under: number } {
  let over = 0;
  let under = 0;
  for (const wk of wks) {
    if (wk.flag === 'over') over++;
    else if (wk.flag === 'under') under++;
  }
  return { over, under };
}
