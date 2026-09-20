/**
 * Azztec_SaaS_web_workorders_rules_v1_0_1.ts  ->  web/src/features/workorders/rules.ts
 * Version:  1.0.1   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.2 · OD-72..OD-79 · Landmines §C
 * Oracle:   WOMaint_2026-09-19_view.json v16.28.3, WOStatus / WOProgress / WONumBadge / CompleteWithinSeg
 *           (docs/reference/, byte copies), stylesheet v2.69 (docs/reference/Workmate_Stylesheet_2026-09-20_v2_69.css
 *           lines 444-463 - the token values below are copied from it, not invented).
 *
 * Pure. No Date, no DOM, no fetch - lib/dates.ts stays the only module touching Date, and every
 * date this page shows arrives as a string from the API (iso()/stamp() server-side), so this module
 * only re-arranges characters.
 *
 * One deliberate rendering departure, same pixels: the oracle writes `rgba(var(--wo-rgb-x),0.16)`
 * into inline styles and lets CSS custom properties resolve at paint. jsdom's style parser rejects
 * var() inside a colour function, so the badge helpers here emit the RESOLVED rgba values from the
 * same v2.69 table. The computed colour is identical; the tokens still live in wo.css for the
 * selectors that use them there (the Closed mode chip).
 *
 * Changelog:
 *   1.0.1  Smoke fix, before the tag. Two things, both the same mistake in different clothes.
 *          (a) StatusCard.icon was `string`, so symbols.tsx needed a cast to index the glyph record
 *          and the cast hid a glyph that did not exist. It is WoGlyphName now - a type-only import,
 *          so this module stays pure and free of runtime dependencies.
 *          (b) The four index maps were typed Record<K, V>, which tells TS a miss is impossible, so
 *          every `key ?` and `?? fallback` guarding them read as dead code to lint (5 errors). They
 *          return `V | undefined` now, which is what they always did at runtime. No behaviour moved.
 *   1.0.0  Initial W1b.
 */
import type { ProgressRow, RespUser, WoRecord } from '../../api/client';
import type { WoGlyphName } from './icons';

export const VERSION = '1.0.1';

/* ------------------------------------------------------------------ palettes (stylesheet v2.69, verbatim) */

export const WO_RGB = {
  request: '255, 193, 7',
  planned: '23, 162, 184',
  pending: '93, 173, 226',
  acknowledged: '111, 66, 193',
  approved: '11, 94, 215',
  active: '40, 167, 69',
  closed: '220, 53, 69',
  cancelled: '108, 117, 125',
  deferred: '255, 152, 0',
} as const;

export type WoStatusKey = keyof typeof WO_RGB;

/** WO status letter -> palette key. `F` paints in the badge although the status row has no card (OD-74). */
export const STATUS_KEY: Readonly<Record<string, WoStatusKey | undefined>> = {
  R: 'request',
  H: 'planned',
  P: 'pending',
  K: 'acknowledged',
  A: 'approved',
  V: 'active',
  C: 'closed',
  D: 'cancelled',
  F: 'deferred',
};

export const PO_RGB = {
  pending: '93, 173, 226',
  waiting: '255, 128, 192',
  approved: '111, 66, 193',
  issued: '40, 167, 69',
  received: '0, 0, 128',
  partRecv: '0, 128, 255',
  completed: '220, 53, 69',
  exported: '0, 204, 204',
  rfq: '255, 193, 7',
  cancelled: '108, 117, 125',
} as const;

export const PO_STATUS_KEY: Readonly<Record<string, keyof typeof PO_RGB | undefined>> = {
  P: 'pending',
  W: 'waiting',
  A: 'approved',
  I: 'issued',
  R: 'received',
  T: 'partRecv',
  C: 'completed',
  X: 'exported',
  Q: 'rfq',
  D: 'cancelled',
};

/* ------------------------------------------------------------------ WONumBadge v1.3.0 */

export interface BadgeParts {
  status: string;
  text: string;
  prog: number;
  hasPO: boolean;
}

/**
 * The oracle's transform, exactly: parts = value.split('|'); status = first char of parts[0];
 * text = parts[1] when present else parts[0]; prog = int(float(parts[2])) else 0; hasPO from parts[3].
 * A status-less composite therefore shows parts[1] - the oracle's behaviour, not "fixed" here.
 */
export function parseBadge(value: string | null | undefined): BadgeParts {
  const v = value ?? '';
  const parts = v.split('|');
  const status = parts[0] ? parts[0].charAt(0) : '';
  const text = parts.length >= 2 ? parts[1] : (parts[0] ?? '');
  let prog = 0;
  if (parts.length >= 3) {
    const n = Number.parseFloat(parts[2]);
    prog = Number.isFinite(n) ? Math.trunc(n) : 0;
  }
  let hasPO = false;
  if (parts.length >= 4) {
    const n = Number.parseFloat(parts[3]);
    hasPO = Number.isFinite(n) && n > 0;
  }
  return { status, text, prog, hasPO };
}

/** progress id -> the badge underline percentage. 2 (Wait) is handled apart; anything else is 0. */
export const BADGE_PCT: Readonly<Record<number, number | undefined>> = { 1: 0, 3: 25, 4: 50, 5: 75, 6: 100 };

export interface BadgeStyle {
  backgroundColor: string;
  color: string;
  backgroundImage: string;
}

/**
 * WONumBadge's three dynamic longhands. Both background layers are ALWAYS emitted (the PO dot is
 * transparent when absent) so the static two-entry backgroundSize/Position/Repeat lists in wo.css
 * stay aligned per CSS layer rules - drop one layer and the underline renders as a 7 px square.
 * Wait (prog 2) is a muted 8 % nub in its own grey, deliberately unlike real progress.
 */
export function badgeStyle(value: string | null | undefined): BadgeStyle {
  const { status, prog, hasPO } = parseBadge(value);
  const key = STATUS_KEY[status];
  const backgroundColor = key ? `rgba(${WO_RGB[key]}, 0.16)` : `rgba(${WO_RGB.cancelled}, 0.08)`;
  const color = key ? `rgba(${WO_RGB[key]}, 0.8)` : `rgba(${WO_RGB.cancelled}, 0.5)`;
  let fill: string;
  let pct: number;
  if (prog === 2) {
    fill = 'rgba(100, 116, 139, 0.55)';
    pct = 8;
  } else {
    fill = key ? `rgba(${WO_RGB[key]}, 0.95)` : '#196690';
    pct = BADGE_PCT[prog] ?? 0;
  }
  const dot = hasPO ? '#0B5ED7' : 'transparent';
  const backgroundImage =
    `radial-gradient(circle, ${dot} 55%, transparent 60%), ` +
    `linear-gradient(to right, ${fill} ${pct}%, transparent ${pct}%)`;
  return { backgroundColor, color, backgroundImage };
}

/* ------------------------------------------------------------------ PONumBadge v1.2.0 (W1c renders it) */

export interface PoBadgeStyle {
  backgroundColor: string;
  color: string;
  text: string;
}

/**
 * The PO badge's colour pair and text. The oracle's text rule is right(value, len-2) - equivalent
 * to stripping "<status><separator>". The second character is a FLAG channel (`!`/`w`/`W`/`c`/`C`
 * add a dot and an orange ring) - not implemented here; W1a's repo always ships a plain `|`,
 * and the flags belong to the PO module.
 */
export function poBadgeStyle(value: string | null | undefined): PoBadgeStyle {
  const v = value ?? '';
  const key = PO_STATUS_KEY[v.charAt(0)];
  const backgroundColor = key ? `rgba(${PO_RGB[key]}, 0.16)` : `rgba(${PO_RGB.cancelled}, 0.08)`;
  const color = key ? `rgba(${PO_RGB[key]}, 0.8)` : `rgba(${PO_RGB.cancelled}, 0.5)`;
  const text = v.length > 2 ? v.slice(2) : v;
  return { backgroundColor, color, text };
}

/* ------------------------------------------------------------------ WOStatus - EIGHT cards (OD-74) */

export interface StatusCard {
  code: string;
  label: string;
  /** a key of GLYPHS in features/workorders/icons.tsx - a name with no paths is a compile error */
  icon: WoGlyphName;
  /** lit background - the --wo-color-* value, v2.69 verbatim */
  hex: string;
  /** lit 2px border colour */
  accent: string;
  /** R is the one card whose lit icon and label are #000, not #FFF (its #FFC107 is too light for white) */
  darkText: boolean;
}

/** The export's eight, in card order. There is no Deferred card - the oracle's gap, kept (OD-74). */
export const WO_STATUS_CARDS: ReadonlyArray<StatusCard> = [
  { code: 'R', label: 'Request', icon: 'warning', hex: '#FFC107', accent: '#D4A006', darkText: true },
  { code: 'H', label: 'Planned', icon: 'assignment', hex: '#17A2B8', accent: '#11808F', darkText: false },
  { code: 'P', label: 'Pending', icon: 'schedule', hex: '#5DADE2', accent: '#3A8BBF', darkText: false },
  { code: 'K', label: "Ack'd", icon: 'thumb_up', hex: '#6F42C1', accent: '#5A349E', darkText: false },
  { code: 'A', label: 'Approved', icon: 'check_circle', hex: '#0B5ED7', accent: '#084AAB', darkText: false },
  { code: 'V', label: 'Active', icon: 'play_circle_filled', hex: '#28A745', accent: '#1E8236', darkText: false },
  { code: 'C', label: 'Closed', icon: 'cancel', hex: '#DC3545', accent: '#B02A37', darkText: false },
  { code: 'D', label: 'Cancel', icon: 'block', hex: '#6C757D', accent: '#565E64', darkText: false },
];

/* ------------------------------------------------------------------ WOProgress + OD-75 */

/** The symbol's own six labels - not the database titles - for the ids it draws. */
export const PROGRESS_SYMBOL_LABELS: Readonly<Record<number, string | undefined>> = {
  1: 'None',
  2: 'Wait',
  3: '25%',
  4: '50%',
  5: '75%',
  6: '100%',
};

export interface ProgressCard {
  id: number;
  label: string;
  /** 1..6 -> the oracle's inline SVG symbol; null -> the plain card (7 Scheduled, 8 Assigned on RST) */
  symbol: number | null;
}

/** One card per active dbo.Progress row, by id (OD-75 / OD-67). prog 0 lights none - the FK rejects 0. */
export function progressCards(all: ReadonlyArray<ProgressRow>): ProgressCard[] {
  return [...all]
    .sort((a, b) => a.id - b.id)
    .map((r) => ({
      id: r.id,
      label: PROGRESS_SYMBOL_LABELS[r.id] ?? r.title,
      symbol: r.id >= 1 && r.id <= 6 ? r.id : null,
    }));
}

/* ------------------------------------------------------------------ the Work Order ID pill */

/**
 * txtWorkOrderId's own inline map - NOT the token palette: P and K share #6F42C1 and A is #007BFF
 * there, unlike --wo-color-pending/approved. Ported verbatim; do not "fix" it to the tokens.
 */
export const ID_PILL: Readonly<Record<string, string | undefined>> = {
  R: '#FFC107',
  H: '#17A2B8',
  P: '#6F42C1',
  K: '#6F42C1',
  A: '#007BFF',
  V: '#28A745',
  C: '#DC3545',
  D: '#6C757D',
};

/** The oracle's text rule is `'' -> #000 else #FFF` - an unknown non-empty status gets #FFF on #FFFFCC. */
export function idPillStyle(status: string): { backgroundColor: string; color: string } {
  return {
    backgroundColor: ID_PILL[status] ?? '#FFFFCC',
    color: status === '' ? '#000' : '#FFF',
  };
}

/* ------------------------------------------------------------------ CompleteWithinSeg (read-only, OD-79) */

export interface SegmentItem {
  value: WoRecord['completeWithin'];
  label: string;
}

/** Same order and spelling as backend rules.SEGMENTS; the type pins it to the contract. */
export const SEGMENT_ITEMS: ReadonlyArray<SegmentItem> = [
  { value: 'day', label: 'Day' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
  { value: '3month', label: '3-Month' },
  { value: 'nextshut', label: 'Next shut' },
  { value: 'range', label: 'Range' },
];

/* ------------------------------------------------------------------ list panel */

export function listTitle(woType: string): string {
  if (woType === 'M') return 'Planned Maintenance';
  if (woType === '') return 'Work Orders + PM';
  return 'Work Orders';
}

export interface TypeChip {
  label: string;
  value: '' | 'N' | 'CP' | 'M';
}

/** WO -> N · CP -> CP · PM -> M · All -> '' - the view's own mapping and seed order. */
export const TYPE_CHIPS: ReadonlyArray<TypeChip> = [
  { label: 'WO', value: 'N' },
  { label: 'CP', value: 'CP' },
  { label: 'PM', value: 'M' },
  { label: 'All', value: '' },
];

/** OD-77: no total, ever - `200+` while `more` is true. */
export function recordCount(count: number, more: boolean): string {
  return `No of Records: ${count}${more ? '+' : ''}`;
}

/* ------------------------------------------------------------------ tabs */

export interface TabItem {
  key: string;
  label: string;
  /** live in W1b; the rest draw inert with the OD-51 title */
  live: boolean;
}

export function linkedTabLabel(count: number): string {
  return count > 1 ? 'Linked WO (+)' : 'Linked WO';
}

/** Tab_0..Tab_4. Only Work Order is live in W1b (OD-72); Activity is not W1c either - its own audit. */
export function mainTabs(linkedCount: number): TabItem[] {
  return [
    { key: 'workorder', label: 'Work Order', live: true },
    { key: 'activity', label: 'Activity', live: false },
    { key: 'querynotes', label: 'Query/Notes', live: false },
    { key: 'linked', label: linkedTabLabel(linkedCount), live: false },
    { key: 'events', label: 'WO Event History', live: false },
  ];
}

/** SubTab_0 · 5 · 1 · 2 · 3 · 4 - the VIEW order, which is not the index order. Details only is live. */
export const SUB_TABS: ReadonlyArray<TabItem> = [
  { key: 'details', label: 'Details', live: true },
  { key: 'pos', label: 'Purchase Orders', live: false },
  { key: 'attachments', label: 'Attachments', live: false },
  { key: 'procedures', label: 'Procedures', live: false },
  { key: 'parts', label: 'Parts', live: false },
  { key: 'labour', label: 'Labour', live: false },
];

/* ------------------------------------------------------------------ display strings (pure - no Date) */

/** 'yyyy-MM-dd HH:mm:ss' -> 'dd/MM/yyyy HH:mm' (the oracle's dateFormat on every stamp field). */
export function displayStamp(s: string | null | undefined): string {
  const v = s ?? '';
  if (v.length < 16) return '';
  return `${v.slice(8, 10)}/${v.slice(5, 7)}/${v.slice(0, 4)} ${v.slice(11, 16)}`;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * The date-time input's display: 'Sep 17, 2026 10:11 AM'. Built by slicing the API's `start` +
 * `startTime` strings - string arithmetic only, calendar-safe across the 27 Sep DST change.
 */
export function displayDateTime(dateIso: string | null | undefined, hhmm: string | null | undefined): string {
  const d = dateIso ?? '';
  if (d.length < 10) return '';
  const month = MONTHS[Number(d.slice(5, 7)) - 1] ?? '?';
  let out = `${month} ${Number(d.slice(8, 10))}, ${d.slice(0, 4)}`;
  const t = hhmm ?? '';
  if (t.length >= 5) {
    const h = Number(t.slice(0, 2));
    const h12 = h % 12 === 0 ? 12 : h % 12;
    out += ` ${h12}:${t.slice(3, 5)} ${h >= 12 ? 'PM' : 'AM'}`;
  }
  return out;
}

/**
 * The oracle's toString on a numeric column prints '0.0', not '0' - these are floats on the wire
 * (durationHrs, estCost, downTime, weekNo), so an integer value gains one decimal.
 */
export function numText(n: number | null | undefined): string {
  if (n === null || n === undefined) return '';
  return Number.isInteger(n) ? n.toFixed(1) : String(n);
}

/** The view's respUsersSummary: ', '-joined short ids, or '(none)'. */
export function respUsersLine(users: ReadonlyArray<RespUser>): string {
  const line = users.map((u) => u.shortId).join(', ');
  return line === '' ? '(none)' : line;
}

/* ------------------------------------------------------------------ Details sub-tab rows */

export interface FieldRow {
  label: string;
  value: string;
  /** the small id label beside the value (TM-MAINT beside Maintenance Team) */
  desc?: string;
}

export interface StampRow {
  label: string;
  user: string;
  date: string;
}

/** The WOC dropdowns prepend '-- No Selection --' at 0; the read-only page shows the same for ''. */
export function wocText(title: string): string {
  return title === '' ? '-- No Selection --' : title;
}

/** LeftCol, view order. lblDeptDesc/lblClassDesc carry no binding in the export - not rendered. */
export function detailLeft(r: WoRecord): FieldRow[] {
  return [
    { label: 'WO Group :', value: r.groupTitle },
    { label: 'Reason :', value: r.reasonTitle },
    { label: 'Fault :', value: r.faultTitle },
    { label: 'Dept. :', value: r.costCenterTitle },
    { label: 'Class :', value: r.accountTitle },
    { label: 'Charge To :', value: r.chargeToName, desc: r.chargeToShort },
    { label: 'Responsibility :', value: r.respSupplierName, desc: r.respSupplierShort },
  ];
}

/** MiddleCol, view order. */
export function detailMiddle(r: WoRecord): FieldRow[] {
  return [
    { label: 'WOC 1 :', value: wocText(r.woc1Title) },
    { label: 'WOC 2 :', value: wocText(r.woc2Title) },
    { label: 'WOC 3 :', value: wocText(r.woc3Title) },
    { label: 'Company :', value: r.companyTitle },
    { label: 'Ref. 1 :', value: r.ref1 },
    { label: 'Ref. 2 :', value: r.ref2 },
  ];
}

/** RightCol, view order. Created's date is the LOGGED date - the oracle binds Logged_Date there. */
export function detailStamps(r: WoRecord): StampRow[] {
  return [
    { label: 'Created By :', user: r.createdBy, date: displayStamp(r.logged) },
    { label: 'Ack. By :', user: r.ackBy, date: displayStamp(r.ackDate) },
    { label: 'Approved By :', user: r.approvedBy, date: displayStamp(r.approvedDate) },
    { label: 'Closed By :', user: r.closedBy, date: displayStamp(r.closedDate) },
    { label: 'Cancelled By :', user: r.cancelledBy, date: displayStamp(r.cancelledDate) },
    { label: 'Last Save :', user: r.lastSaveBy, date: displayStamp(r.lastSaveDate) },
  ];
}
