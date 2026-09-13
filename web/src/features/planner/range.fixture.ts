/**
 * Azztec_SaaS_web_planner_range_fixture_v1_1_0.ts  ->  web/src/features/planner/range.fixture.ts
 * Version:  1.1.0   Date: 2026-09-13   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §5.4 · test helper, not a test (vitest include is *.test.*)
 *
 * One RangeData for the standing window 2026-09-14..2026-09-20, hand-built and contract-shaped: the
 * backend's test_openapi_contract guards the real shape, this only has to type-check against the
 * generated client. Worker 692 is RST's real 1000% row (10 h against 1 h/week, verified 2026-09-12);
 * the rest is invented to give every branch a case: WO / PM / REQ / DONE, labour vs estimate vs no
 * hours, locked vs pinned vs movable, internal vs contractor, loaded vs idle.
 *
 * Changelog:
 *   1.1.0  S1g. priorities[] in the RST shape (P1..P4, N/A) so priRank has ranks 1..5 (OD-32);
 *          REQ_103 points at N/A; WO_101 gains hasPO, a two-day span (end, days 1) and a second labour
 *          row - Jo 2.5h + Ann 1h = the WO's 3.5h, so nothing summed elsewhere moves; PM_102 gains a
 *          responsible person. Every S1f sum (weeks[], counts, load, chip strings) is unchanged.
 *   1.0.0  Initial S1f.
 */
import type { RangeData, Wo, Worker, WorkerWeek } from '../../api/client/types.gen';

export const FIXTURE_VERSION = '1.1.0';

export const FROM = '2026-09-14';
export const TO = '2026-09-20';
export const TODAY = '2026-09-16';

const WO_DEFAULTS: Wo = {
  id: 0,
  sid: '',
  title: '',
  status: 'H',
  statusTitle: 'Planned',
  type: 'W',
  cat: 'WO',
  start: FROM,
  startTime: '',
  end: '',
  days: 0,
  weekNo: 2026.38,
  prog: 1,
  priId: 0,
  pri: '',
  estimate: 0,
  resp: 0,
  asset: '',
  assetTitle: '',
  loc: '',
  locTitle: '',
  hasPO: false,
  engineOwned: false,
  pinned: false,
  pinnedOn: '',
  engineDate: '',
  locked: false,
  movable: true,
  hrs: 0,
  hrsSrc: '',
  assigned: [],
};

/** A WO with every field present; override what the case needs. */
export function mkWo(over: Partial<Wo>): Wo {
  return { ...WO_DEFAULTS, ...over };
}

const WORKER_DEFAULTS: Worker = {
  id: 0,
  sid: '',
  name: '',
  initials: '',
  skills: [],
  hrsPerWeek: 0,
  teamId: 1,
  team: 'MAINT',
  internal: true,
};

export function mkWorker(over: Partial<Worker>): Worker {
  return { ...WORKER_DEFAULTS, ...over };
}

/** 101 - a corrective WO, labour hours, two people, priority P1, Monday, spans into Tuesday, PO linked. */
export const WO_101 = mkWo({
  id: 101,
  sid: 'WO-101',
  title: 'Replace chain on infeed',
  cat: 'WO',
  start: '2026-09-14',
  end: '2026-09-15',
  days: 1,
  priId: 1,
  pri: 'P1',
  asset: 'INF-01',
  assetTitle: 'Infeed conveyor',
  loc: 'SAW',
  locTitle: 'Sawmill',
  hasPO: true,
  hrs: 3.5,
  hrsSrc: 'labour',
  assigned: [692, 2],
});

/** 102 - an engine-owned PM, no pin table: locked, immovable, no hours; Ann is responsible. OD-1 on RST, 2,364 times. */
export const PM_102 = mkWo({
  id: 102,
  sid: 'PM-102',
  title: 'Weekly greasing',
  type: 'M',
  cat: 'PM',
  start: '2026-09-15',
  resp: 2,
  engineOwned: true,
  locked: true,
  movable: false,
  hrs: 0,
  hrsSrc: '',
});

/** 103 - a request with an estimate, priority N/A (RST's fifth priority row). */
export const REQ_103 = mkWo({
  id: 103,
  sid: 'REQ-103',
  title: 'Check hydraulic leak',
  status: 'R',
  statusTitle: 'Request',
  cat: 'REQ',
  start: '2026-09-16',
  priId: 7,
  pri: 'N/A',
  hrs: 2,
  hrsSrc: 'estimate',
});

/** 104 - closed, locked by status. */
export const DONE_104 = mkWo({
  id: 104,
  sid: 'WO-104',
  title: 'Bearing swap',
  status: 'C',
  statusTitle: 'Closed',
  cat: 'DONE',
  start: '2026-09-17',
  locked: true,
  movable: false,
  hrs: 4,
  hrsSrc: 'labour',
});

/** 105 - a PM the planner pinned (the S3 world): pin glyph, movable. */
export const PIN_105 = mkWo({
  id: 105,
  sid: 'PM-105',
  title: 'Filter change',
  type: 'M',
  cat: 'PM',
  start: '2026-09-18',
  engineOwned: true,
  pinned: true,
  pinnedOn: '2026-09-10',
  engineDate: '2026-09-25',
  movable: true,
  hrs: 1,
  hrsSrc: 'estimate',
  assigned: [692, 2, 3, 4],
});

export const WOS: Wo[] = [WO_101, PM_102, REQ_103, DONE_104, PIN_105];

/** 692 - RST's real 1000% (10 h against 1 h/week placeholder capacity, Landmines §E). */
export const W_692 = mkWorker({
  id: 692,
  sid: 'JB',
  name: 'Jo Bloggs',
  initials: 'JB',
  hrsPerWeek: 1,
  skills: [{ id: 5, title: 'Fitter', sysId: 50, hrsPerWeek: 1, supplierId: 11 }],
});
/** 2 - internal, real 40 h/week, nothing attributed this window. */
export const W_2 = mkWorker({ id: 2, sid: 'AK', name: 'Ann Kowhai', initials: 'AK', hrsPerWeek: 40 });
/** 3 - a contractor with hours. */
export const W_3 = mkWorker({
  id: 3,
  sid: 'CS',
  name: 'Con Tractor',
  initials: 'CS',
  hrsPerWeek: 0,
  teamId: 9,
  team: 'ACME',
  internal: false,
});

export const WORKERS: Worker[] = [W_692, W_2, W_3];

export const WW_692: WorkerWeek = { weekStart: FROM, planned: 10, capacity: 1, pct: 1000, flag: 'over' };

/** Full contract body. Envelope per OD-14. */
export const RANGE: RangeData = {
  from: FROM,
  to: TO,
  today: TODAY,
  wos: WOS,
  /** two rows on 101 summing to its 3.5 h: Jo (skilled, dated) and Ann (no skill row, no date) */
  labour: [
    { resId: 1, woId: 101, userId: 692, hours: 2.5, rate: 0, note: '', date: '2026-09-14', skillId: 5, skillTitle: 'Fitter', uomId: 12 },
    { resId: 2, woId: 101, userId: 2, hours: 1, rate: 0, note: '', date: '', skillId: 0, skillTitle: '', uomId: 12 },
  ],
  workers: WORKERS,
  teams: [
    { id: 1, short: 'MAINT', name: 'Maintenance', internal: true, users: 2 },
    { id: 9, short: 'ACME', name: 'Acme Contracting', internal: false, users: 1 },
  ],
  /** RST's shape (Landmines §E): P1..P6 and N/A, ordered by Sort_Sequence - five rows here */
  priorities: [
    { id: 1, short: 'P1', title: 'Urgent' },
    { id: 2, short: 'P2', title: 'High' },
    { id: 3, short: 'P3', title: 'Normal' },
    { id: 4, short: 'P4', title: 'Low' },
    { id: 7, short: 'N/A', title: 'Not Applicable' },
  ],
  colours: { DONE: '#81C784', PM: '#4DD0E1', REQ: '#F48FB1', WO: '#FFC65C' },
  /** planned = 3.5 + 2 + 4 + 1 (all cats); unknown = the PM; capacity = 1 + 40 internal */
  weeks: [{ weekStart: FROM, planned: 10.5, unknown: 1, count: 5, capacity: 41, pct: 26 }],
  load: { '0': 0, '692': 10, '3': 2 },
  /** wo counts REQ (101 + 103), pm is 102 + the pinned 105 */
  counts: { wo: 2, pm: 2, done: 1, total: 5 },
  pinTable: false,
  workerWeeks: {
    '692': [WW_692],
    '2': [{ weekStart: FROM, planned: 0, capacity: 40, pct: 0, flag: 'empty' }],
    '3': [{ weekStart: FROM, planned: 2, capacity: 0, pct: 0, flag: 'ok' }],
  },
  uomHours: 12,
  libVersion: 'fixture',
  ok: true,
  apiVersion: 'fixture',
  actor: 1,
  ms: 0,
};
