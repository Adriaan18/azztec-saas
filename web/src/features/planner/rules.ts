/**
 * Azztec_SaaS_web_planner_rules_v1_3_0.ts  ->  web/src/features/planner/rules.ts
 * Version:  1.3.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §5.1 · OD-30…OD-34 · Landmines §D (index once);
 *           Azztec_SaaS_S1i_Priority_Paint_Chunk_Spec_v1_0_0.md §3.2 · OD-39, OD-40, OD-41;
 *           Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (rules.ts row) · OD-107
 * Oracle:   Planner_v1_8_1.html - constants 482-485, state defaults 492, fmtRange/fmtLong/fmtH/fmtNum
 *           510-516, teamMembers/anySelectedWorker/visible/byDay 536-558, capacity 561-578, chipEl
 *           who/title 590-606, month header label 623, countText 662-667, strip 668-676, showDay rows
 *           717-727, rail 774-790, renderSelected 804-819, renderFilters 841-852, Clear 1537.
 * Consumes: src/api/client/types.gen.ts (Wo, Worker, WorkerWeek, Team, Priority, LabourRow - the
 *           ^export type lines pasted 2026-09-13).
 *
 * Pure. No Date (dates.ts owns it), no DOM, no fetch. Everything here is a function over the RangeData
 * dicts, so it tests with plain objects and the components stay thin. Strings are byte-for-byte the
 * oracle's - the tooltip texts are the parity surface a planner reads every day.
 *
 * Deliberate departures from the oracle, all recorded in the S1f/S1g specs:
 *   - weeksIn() takes civil days (window.days), never (to - from) / 864e5 - the DST landmine (§C).
 *   - railRows() is OD-24/OD-26: internal by default, contractors and loaded-only as client toggles,
 *     and the count line so hidden rows are counted, never silent. The oracle listed all 363.
 *   - priRank()/priClass() are OD-32: badge colour by rank in priorities[] (RST has no A-D letters).
 *   - isHexColour()/luminance()/textOn()/priBadgeMap() are OD-39/40/41 (S1i): the badge paints from the
 *     payload's `colour` only when the payload's colours carry information, with the higher-contrast of
 *     the base badge's own text colour and white. Not the oracle's - it never painted from data.
 *   - HINT, actorLabel() and rowTitle()'s last line are OD-34: chrome says only what is true here.
 *   - dowIso() is pure calendar arithmetic (Sakamoto) so fmtLong can name any day without Date. The
 *     spec (§5.1) said fmtLong "already takes ISO"; it takes ISO + dow, and the strips passed 0 because
 *     a week start is always Monday. The card and the dialog name arbitrary days, hence this.
 *
 * Changelog:
 *   1.3.0  DP3b. HINT_RW, the hint when the person can move (OD-107). chipTitle's engine-owned line
 *          needs `wo.movable` too: identical on every payload the server sends (an engine-owned PM
 *          that is not locked is movable, and locked is the branch before), and at RO - where
 *          PlannerView maps movable to false - no chip promises a drag it cannot do.
 *   1.2.0  S1i. isHexColour (the OD-36 free-text guard), luminance / textOn (OD-40: WCAG contrast picks
 *          #2b2b2b or #ffffff, ties dark), PriBadge + priBadgeMap (OD-39: paint only at >= 2 distinct
 *          usable colours, case-folded; OD-41: one map for both badge sites, rank from priRankMap so the
 *          rank contract keeps one implementation). Nothing else moved; priRank/priRankMap/priClass stand.
 *   1.1.0  S1g. Filters type + DEFAULT_FILTERS; visibleWos/capacityWorkers/capacityPerWeek gain the
 *          oracle's full precedence behind an optional trailing parameter (1.0.1 call sites stand);
 *          railRows gains the team filter; rowTitle gains the click line; teamOptions/priorityOptions/
 *          workerMenu/workerLabel for the filters row; priRank/priClass/priRankMap (OD-32); dowIso;
 *          dialogTitle/dialogRows for the day dialog; cardRows for the selected card; HINT/actorLabel.
 *   1.0.1  Comment fix only, no behaviour change: fmtLong's doc line claimed 'Monday 14 Sep 2026'.
 *          The oracle (src 514) builds it from the ABBREVIATED DOW, so the real output is
 *          'Mon 14 Sep 2026'. The code was already right; the comment was not.
 *   1.0.0  Initial S1f.
 */
import type { LabourRow, Priority, Team, Wo, Worker, WorkerWeek } from '../../api/client/types.gen';

export const VERSION = '1.3.0';

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

/**
 * Day of week for a yyyy-MM-dd, 0 = Monday ... 6 = Sunday, by Sakamoto's congruence - pure integer
 * arithmetic on the proleptic Gregorian calendar, no Date, no zone, no DST. Pinned against dates.ts's
 * dowOf in dates.test (the two must agree; this one exists so rules.ts stays Date-free).
 */
export function dowIso(s: string): number {
  const p = ymd(s);
  const t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4];
  const y = p.m < 3 ? p.y - 1 : p.y;
  const sunday0 = (y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) + t[p.m - 1] + p.d) % 7;
  return (sunday0 + 6) % 7;
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

/** fmtLong for any day - the card and the dialog (oracle 717, 812-813 call fmtLong(parseIso(x))). */
export function fmtLongAny(s: string): string {
  return fmtLong(s, dowIso(s));
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

/* ------------------------------------------------------------------ filters (oracle 536-557, 1533-1537) */

/** The oracle's S.teamId / S.workers / S.pri / S.unassigned / S.q. */
export type Filters = {
  teamId: number;
  workers: Readonly<Record<number, boolean>>;
  pri: number;
  unassigned: boolean;
  /** already trimmed (oracle 1536) */
  q: string;
};

export const DEFAULT_FILTERS: Filters = { teamId: 0, workers: {}, pri: 0, unassigned: false, q: '' };

/** Oracle 540. */
export function anySelectedWorker(f: Filters): boolean {
  return Object.values(f.workers).some((v) => v);
}

/**
 * Oracle visible() 541-556, in its order: cats, priority, unassigned, selected workers, search.
 * `filters` defaults to none so every S1f call site and test stands unchanged.
 */
export function visibleWos(wos: ReadonlyArray<Wo>, cats: Cats, filters: Filters = DEFAULT_FILTERS): Wo[] {
  const anyW = anySelectedWorker(filters);
  const q = filters.q.toLowerCase();
  return wos.filter((w) => {
    if (!isCat(w.cat) || !cats[w.cat]) return false;
    if (filters.pri && w.priId !== filters.pri) return false;
    if (filters.unassigned && w.assigned.length) return false;
    if (anyW && !w.assigned.some((id) => filters.workers[id])) return false;
    if (q) {
      const hay = `${w.sid} ${w.title} ${w.asset} ${w.assetTitle} ${w.loc} ${w.locTitle}`.toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });
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

/** Oracle 561-567, its precedence: selected workers > team > all internal. */
export function capacityWorkers(workers: ReadonlyArray<Worker>, filters: Filters = DEFAULT_FILTERS): Worker[] {
  if (anySelectedWorker(filters)) return workers.filter((w) => !!filters.workers[w.id]);
  if (filters.teamId) return workers.filter((w) => w.teamId === filters.teamId);
  return workers.filter((w) => w.internal);
}

export function capacityPerWeek(workers: ReadonlyArray<Worker>, filters: Filters = DEFAULT_FILTERS): number {
  let c = 0;
  for (const w of capacityWorkers(workers, filters)) c += w.hrsPerWeek || 0;
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

/** Oracle 600-606: the chip tooltip. The locked line is OD-1 on RST, 2,364 times. OD-33; 1.3.0 gates the PM drag line on movable (OD-107). */
export function chipTitle(wo: Wo): string {
  let t = `${wo.sid} \u00b7 ${wo.title}\n${wo.statusTitle}${wo.pri ? ` \u00b7 priority ${wo.pri}` : ''}`;
  if (wo.asset) t += `\n${wo.asset}${wo.assetTitle ? ` - ${wo.assetTitle}` : ''}`;
  if (wo.loc) t += `\n${wo.loc}${wo.locTitle ? ` - ${wo.locTitle}` : ''}`;
  t += wo.hrs > 0 ? `\n${fmtH(wo.hrs)} (${wo.hrsSrc})` : '\nno hours yet';
  if (wo.pinned) {
    t += `\nPINNED by the planner${wo.engineDate ? ` (engine date ${wo.engineDate})` : ''} - the release engine leaves it alone`;
  } else if (wo.locked) {
    t += '\nPM - engine owned; run the S3 DDL (WO_N_Plan) to allow planner pins';
  } else if (wo.engineOwned && wo.movable) {
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

/** Oracle 790 with the click half of its last line (OD-34: the click exists, the drag does not). */
export function rowTitle(w: Worker, ld: number, cap: number, pct: number): string {
  return (
    `${w.name} (${w.sid})\n${fmtNum(ld)} h attributed in this window \u00b7 capacity ${fmtNum(w.hrsPerWeek || 0)} h/week` +
    (cap > 0 ? ` \u00b7 ${pct}% of ${fmtNum(cap)} h` : '') +
    '\nclick = filter the work to this person'
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

/**
 * OD-26. API order kept (internal first, then name - the service sorts, the UI does not). The team
 * filter (oracle 778) runs first and the counts describe the team-filtered population, so
 * `12 of 12 internal` reads right under a team.
 */
export function railRows(
  workers: ReadonlyArray<Worker>,
  load: Readonly<Record<string, number>>,
  opts: RailOpts,
  teamId = 0,
): RailRows {
  let internal = 0;
  let contractors = 0;
  let loaded = 0;
  const rows: Worker[] = [];
  for (const w of workers) {
    if (teamId && w.teamId !== teamId) continue;
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

/* ------------------------------------------------------------------ the filters row (oracle 841-852) */

export type Option = { value: number; label: string };

/** Oracle 842: `MAINT \u00b7 12`, `ACME (contractor) \u00b7 3`. The `All teams` row is the component's. */
export function teamOptions(teams: ReadonlyArray<Team>): Option[] {
  return teams.map((t) => ({
    value: t.id,
    label: `${t.short || t.name}${t.internal ? '' : ' (contractor)'} \u00b7 ${t.users}`,
  }));
}

/** Oracle 845: `P1 \u00b7 Urgent`. The `Any` row is the component's. */
export function priorityOptions(priorities: ReadonlyArray<Priority>): Option[] {
  return priorities.map((p) => ({ value: p.id, label: `${p.short} \u00b7 ${p.title}` }));
}

export type MenuRow = { id: number; name: string; cap: string };
export type MenuGroup = { label: string; rows: MenuRow[] };

/**
 * Oracle 847-852: a copy of workers sorted internal first then `team + name`, filtered by team, grouped
 * by team with `other` for an empty team and ` \u00b7 contractor` on a contractor group.
 */
export function workerMenu(workers: ReadonlyArray<Worker>, teamId = 0): MenuGroup[] {
  const ws = workers
    .slice()
    .sort((a, b) =>
      a.internal === b.internal
        ? `${a.team || ''}${a.name}`.localeCompare(`${b.team || ''}${b.name}`)
        : a.internal
          ? -1
          : 1,
    );
  const groups: MenuGroup[] = [];
  let last: string | null = null;
  for (const w of ws) {
    if (teamId && w.teamId !== teamId) continue;
    const team = w.team || '';
    if (team !== last) {
      groups.push({ label: `${team || 'other'}${w.internal ? '' : ' \u00b7 contractor'}`, rows: [] });
      last = team;
    }
    groups[groups.length - 1].rows.push({ id: w.id, name: w.name, cap: `${fmtNum(w.hrsPerWeek || 0)}/wk` });
  }
  return groups;
}

/** Oracle 402's `#wlbl`: `any`, one name, or `n selected`. (Ours: the oracle's setter was not read.) */
export function workerLabel(f: Filters, byId: ReadonlyMap<number, Worker>): string {
  const ids = Object.keys(f.workers)
    .map(Number)
    .filter((id) => f.workers[id]);
  if (!ids.length) return 'any';
  if (ids.length === 1) return byId.get(ids[0])?.name ?? `#${ids[0]}`;
  return `${ids.length} selected`;
}

/* ------------------------------------------------------------------ priority rank (OD-32) */

/** 1-based position of `priId` in priorities[] (Sort_Sequence order); 0 when absent or unset. */
export function priRank(wo: Wo, priorities: ReadonlyArray<Priority>): number {
  if (!wo.priId) return 0;
  const i = priorities.findIndex((p) => p.id === wo.priId);
  return i < 0 ? 0 : i + 1;
}

/** Built once per data load; the grid never runs findIndex per chip (Landmines §D). */
export function priRankMap(priorities: ReadonlyArray<Priority>): Map<number, number> {
  return new Map(priorities.map((p, i) => [p.id, i + 1]));
}

/** `r1`..`r4` reuse the oracle's A/B/C/D colours in rank order; beyond 4 the base .pri style. */
export function priClass(rank: number): string {
  return rank >= 1 && rank <= 4 ? `r${rank}` : '';
}

/* ------------------------------------------------------------------ priority badge paint (S1i: OD-39 / OD-40 / OD-41) */

/** planner.css 118 / oracle 282: the base badge's own text colour, and the only alternative to it. */
const PRI_FG_DARK = '#2b2b2b';
const PRI_FG_LIGHT = '#ffffff';
const HEX6 = /^#[0-9A-Fa-f]{6}$/;

/** OD-36 ships Priority.colour as varchar(255) free text. Nothing reaches a style attribute without passing this. */
export function isHexColour(s: string): boolean {
  return HEX6.test(s);
}

/** WCAG relative luminance of a validated #RRGGBB: 0 = black, 1 = white. Pure arithmetic - no DOM, no Date. */
export function luminance(hex: string): number {
  const lin = (i: number): number => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(1) + 0.7152 * lin(3) + 0.0722 * lin(5);
}

const L_DARK = luminance(PRI_FG_DARK);
const L_LIGHT = luminance(PRI_FG_LIGHT);

function contrastRatio(a: number, b: number): number {
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

/**
 * OD-40: whichever of the base badge's dark text and white has the higher WCAG contrast against `hex`;
 * ties go dark. A contrast floor, not the oracle's aesthetic - on `.pri.A` (#EF6C57) it would pick
 * dark where the oracle hand-picked white - and it never runs there: A-D are CSS classes and KT never
 * reaches the paint path (OD-39). On RST's seven: #FF0000 and #0080FF take white, the rest dark.
 */
export function textOn(hex: string): string {
  const l = luminance(hex);
  return contrastRatio(l, L_DARK) >= contrastRatio(l, L_LIGHT) ? PRI_FG_DARK : PRI_FG_LIGHT;
}

/** One badge's look: the OD-32 rank always; `bg`/`fg` empty when the payload does not paint. */
export type PriBadge = { rank: number; bg: string; fg: string };

/**
 * OD-39 / OD-41: one entry per priority, built once per data load (Landmines §D) and read by both badge
 * sites. Per row the colour must pass isHexColour; per payload it paints only when there are >= 2
 * distinct usable colours (case-folded) - RST's seven paint, KT's four identical #FF8000 rows fall to
 * the `.pri.A-D` classes and keep their letters, and a payload with exactly one usable colour paints
 * nothing (the documented consequence). Rank comes from priRankMap so the rank contract has one
 * implementation and the OD-32 tests keep passing on it.
 */
export function priBadgeMap(priorities: ReadonlyArray<Priority>): Map<number, PriBadge> {
  const rank = priRankMap(priorities);
  const distinct = new Set(priorities.filter((p) => isHexColour(p.colour)).map((p) => p.colour.toUpperCase()));
  const paint = distinct.size >= 2;
  return new Map(
    priorities.map((p): [number, PriBadge] => [
      p.id,
      paint && isHexColour(p.colour)
        ? { rank: rank.get(p.id) ?? 0, bg: p.colour, fg: textOn(p.colour) }
        : { rank: rank.get(p.id) ?? 0, bg: '', fg: '' },
    ]),
  );
}

/* ------------------------------------------------------------------ labour helpers (oracle 720-721, 804-806) */

export function labourFor(woId: number, labour: ReadonlyArray<LabourRow>): LabourRow[] {
  return labour.filter((r) => r.woId === woId);
}

function nameOf(id: number, byId: ReadonlyMap<number, Worker>): string {
  return byId.get(id)?.name ?? `#${id}`;
}

/** Oracle 721: `Jo Bloggs 3.5h` per labour row. */
export function peopleFor(rows: ReadonlyArray<LabourRow>, byId: ReadonlyMap<number, Worker>): string[] {
  return rows.map((r) => `${nameOf(r.userId, byId)} ${fmtH(r.hours)}`);
}

/* ------------------------------------------------------------------ the day dialog (oracle 717-727) */

/** Oracle 717: `MON 14 SEP 2026`. */
export function dialogTitle(key: string): string {
  return fmtLongAny(key).toUpperCase();
}

export type DialogRow = {
  id: number;
  sid: string;
  cat: string;
  pri: string;
  priId: number;
  /** status · time → end · pinned / engine owned */
  meta1: string;
  title: string;
  /** asset · asset title · loc, or `no asset` */
  meta2: string;
  /** `3.5h (labour)` or `no hours yet` */
  hours: string;
  noHours: boolean;
  /** `Jo Bloggs 3.5h, Ann Kowhai 1h` | `owner <name>` | `nobody planned` */
  who: string;
};

/** Oracle 719-727, the strings of one `.job` row; the component only places them. */
export function dialogRows(
  list: ReadonlyArray<Wo>,
  labour: ReadonlyArray<LabourRow>,
  byId: ReadonlyMap<number, Worker>,
): DialogRow[] {
  return list.map((wo) => {
    const people = peopleFor(labourFor(wo.id, labour), byId);
    const resp = wo.resp ? nameOf(wo.resp, byId) : '';
    const meta1 =
      wo.statusTitle +
      (wo.startTime ? ` \u00b7 ${wo.startTime}` : '') +
      (wo.end && wo.end !== wo.start ? ` \u2192 ${wo.end}` : '') +
      (wo.pinned ? ' \u00b7 pinned' : wo.locked ? ' \u00b7 engine owned' : '');
    const meta2 =
      (wo.asset ? `${wo.asset}${wo.assetTitle ? ` \u00b7 ${wo.assetTitle}` : ''}` : 'no asset') +
      (wo.loc ? ` \u00b7 ${wo.loc}` : '');
    const noHours = !(wo.hrs > 0);
    const hours = noHours ? 'no hours yet' : `${fmtH(wo.hrs)} (${wo.hrsSrc})`;
    const who = people.length ? people.join(', ') : resp ? `owner ${resp}` : 'nobody planned';
    return { id: wo.id, sid: wo.sid, cat: wo.cat, pri: wo.pri, priId: wo.priId, meta1, title: wo.title, meta2, hours, noHours, who };
  });
}

/* ------------------------------------------------------------------ the selected card (oracle 804-819, 823) */

export type CardLabour = { name: string; skillTitle: string; hours: string; date: string };

export type CardRows = {
  /** statusTitle · pinned / engine owned · PO linked */
  status: string;
  /** `since <pinnedOn> · engine date <d>` when pinned, else '' */
  pin: string;
  start: string;
  /** '' when the WO has no end */
  end: string;
  priority: string;
  /** `code · title` or '' ; assetTitle is the hover title */
  asset: string;
  assetTitle: string;
  loc: string;
  locTitle: string;
  /** `3.5h` or '' (= `no estimate yet`) */
  hours: string;
  hoursSrc: string;
  /** '' = nobody */
  responsible: string;
  labour: CardLabour[];
};

export function cardRows(wo: Wo, labour: ReadonlyArray<LabourRow>, byId: ReadonlyMap<number, Worker>): CardRows {
  const status =
    wo.statusTitle +
    (wo.pinned ? ' \u00b7 pinned' : wo.engineOwned ? ' \u00b7 engine owned' : '') +
    (wo.hasPO ? ' \u00b7 PO linked' : '');
  const pin = wo.pinned ? `since ${wo.pinnedOn || '?'}${wo.engineDate ? ` \u00b7 engine date ${wo.engineDate}` : ''}` : '';
  const start = fmtLongAny(wo.start) + (wo.startTime ? ` ${wo.startTime}` : '');
  const end = wo.end ? fmtLongAny(wo.end) + (wo.days > 0 ? ` (${wo.days + 1} days)` : '') : '';
  const asset = wo.asset ? `${wo.asset}${wo.assetTitle ? ` \u00b7 ${wo.assetTitle}` : ''}` : '';
  const loc = wo.loc ? `${wo.loc}${wo.locTitle ? ` \u00b7 ${wo.locTitle}` : ''}` : '';
  const rows = labourFor(wo.id, labour).map((r) => ({
    name: nameOf(r.userId, byId),
    skillTitle: r.skillTitle || '',
    hours: fmtH(r.hours),
    date: r.date || '',
  }));
  return {
    status,
    pin,
    start,
    end,
    priority: wo.pri || '\u2014',
    asset,
    assetTitle: wo.assetTitle || '',
    loc,
    locTitle: wo.locTitle || '',
    hours: wo.hrs > 0 ? fmtH(wo.hrs) : '',
    hoursSrc: wo.hrsSrc || '',
    responsible: wo.resp ? nameOf(wo.resp, byId) : '',
    labour: rows,
  };
}

/* ------------------------------------------------------------------ chrome strings (OD-34) */

/** The filters-row hint: only what is true in the read-only planner. */
export const HINT = 'click = select \u00b7 \u2190 \u2192 = navigate \u00b7 T = today \u00b7 Esc = clear';

/** DP3b, OD-107: the hint when the person can move - the drag and Ctrl+Z are true now. */
export const HINT_RW = `drag = move \u00b7 Ctrl+Z = undo \u00b7 ${HINT}`;

/** The envelope's actor is an int until identity (OD-2). */
export function actorLabel(actor: number): string {
  return `actor #${actor}`;
}
