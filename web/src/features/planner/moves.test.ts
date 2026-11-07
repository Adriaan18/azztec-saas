/**
 * Azztec_SaaS_web_planner_moves_test_v1_0_1.ts  ->  web/src/features/planner/moves.test.ts
 * Version:  1.0.1   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (moves.test.ts row) · pair of moves.ts 1.0.1
 *
 * Two halves. Pure: outcomeOf over every code the 0.7.0 contract can return, the oracle's strings
 * (whyNotMovable, the moved / undone toasts with the pin note and OD-116's end note), applyMove's
 * immutability and pushUndo's cap. The wire: postMove / postUndo against a fetch stub that records the
 * Request the generated client built - the method, the URL and the JSON body are asserted, so the keys
 * the oracle sends ({woId, toIso, expectStartIso, confirm}) are pinned at the network, and a fetch
 * that rejects comes back as an outcome, never a throw.
 *
 * Changelog:
 *   1.0.1  Pair of moves.ts 1.0.1 (the lint fix): the version case expects 1.0.1. Every case unchanged.
 *   1.0.0  Initial DP3b.
 */
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

import { client } from '../../api/client/client.gen';
import {
  NETWORK_MESSAGE,
  TOAST_MS,
  UNDO_MAX,
  UNDO_TOAST_MS,
  VERSION,
  applyMove,
  endNote,
  fmtDelta,
  movedToast,
  outcomeOf,
  pinNote,
  postMove,
  postUndo,
  pushUndo,
  undoneToast,
  whyNotMovable,
} from './moves';
import { SPAN_REASON, mkConfirm, mkError, mkResult } from './moves.fixture';
import { DONE_104, PM_102, RANGE, mkWo } from './range.fixture';
import type { UndoRef } from '../../api/client/types.gen';

export const TEST_VERSION = '1.0.1';

const BASE = 'http://test.local';

describe('moves - constants', () => {
  it('carries its version and the oracle numbers', () => {
    expect(VERSION).toBe('1.0.1');
    expect(UNDO_MAX).toBe(10);
    expect(TOAST_MS).toBe(4000);
    expect(UNDO_TOAST_MS).toBe(6500);
  });
});

describe('moves - outcomeOf (the oracle handleWriteError, as data)', () => {
  it('a 200 with ok:true is the move', () => {
    const r = mkResult();
    const o = outcomeOf(200, r);
    expect(o.kind).toBe('ok');
    if (o.kind === 'ok') expect(o.result).toBe(r);
  });

  it('CONFIRM is a 200 with ok:false and a preview (OD-112)', () => {
    const o = outcomeOf(200, mkConfirm());
    expect(o.kind).toBe('confirm');
    if (o.kind === 'confirm') {
      expect(o.preview.sid).toBe('WO-101');
      expect(o.message).toBe('WO-101: The target date is in the past');
    }
  });

  it('a 200 that is neither a move nor a confirm with a preview is a failure, never a move', () => {
    expect(outcomeOf(200, { ok: false, code: 'CONFIRM', message: 'no preview' }).kind).toBe('failed');
    expect(outcomeOf(200, 'nonsense').kind).toBe('failed');
  });

  it('STALE carries the message and currentStart', () => {
    const body = mkError('STALE', 'WO-101 moved since you loaded the planner (now 2026-09-18) - refreshing', {
      currentStart: '2026-09-18',
    });
    expect(outcomeOf(409, body)).toEqual({
      kind: 'stale',
      code: 'STALE',
      message: 'WO-101 moved since you loaded the planner (now 2026-09-18) - refreshing',
      currentStart: '2026-09-18',
    });
  });

  it('NO_IDENTITY, NO_RIGHT and a lost session are identity problems (the banner)', () => {
    expect(outcomeOf(403, mkError('NO_IDENTITY', 'your login has no Workmate identity')).kind).toBe('identity');
    expect(outcomeOf(403, mkError('NO_RIGHT', 'Planner needs RW')).kind).toBe('identity');
    const lost = outcomeOf(401, { ok: false, code: 'NO_SESSION', message: 'sign in', rid: 'r' });
    expect(lost).toEqual({ kind: 'identity', code: 'NO_SESSION', message: 'sign in' });
  });

  it('400, 404 and 422 are refusals with the server message', () => {
    expect(outcomeOf(404, mkError('NOT_FOUND', 'WO 9 not found'))).toEqual({
      kind: 'refused',
      code: 'NOT_FOUND',
      message: 'WO 9 not found',
    });
    expect(outcomeOf(422, mkError('LOCKED_STATUS', 'WO-104 is Closed')).kind).toBe('refused');
    expect(outcomeOf(400, mkError('BAD_REQUEST', 'woId missing')).kind).toBe('refused');
  });

  it('500, CSRF, an unknown status and no response at all are failures', () => {
    expect(outcomeOf(500, mkError('WRITE_FAILED', 'the move did not save'))).toEqual({
      kind: 'failed',
      code: 'WRITE_FAILED',
      message: 'the move did not save',
    });
    expect(outcomeOf(403, mkError('CSRF', 'X-Azztec-Request header missing')).kind).toBe('failed');
    expect(outcomeOf(502, 'Bad Gateway')).toEqual({ kind: 'failed', code: 'HTTP_502', message: 'HTTP 502' });
    expect(outcomeOf(0, null)).toEqual({ kind: 'failed', code: 'NETWORK', message: NETWORK_MESSAGE });
  });
});

describe('moves - the oracle strings', () => {
  it('whyNotMovable: closed, cancelled, the engine-owned PM, anything else', () => {
    expect(whyNotMovable(DONE_104)).toBe('WO-104 is closed - it does not move');
    expect(whyNotMovable(mkWo({ sid: 'WO-9', status: 'D', statusTitle: 'Cancelled' }))).toBe(
      'WO-9 is cancelled - it does not move',
    );
    expect(whyNotMovable(PM_102)).toBe(
      'PM-102 is a PM the release engine owns - run the S3 DDL (WO_N_Plan) to allow planner pins',
    );
    expect(whyNotMovable(mkWo({ sid: 'WO-8', movable: false }))).toBe('WO-8 cannot be moved');
  });

  it('fmtDelta signs the days', () => {
    expect(fmtDelta(7)).toBe('+7 d');
    expect(fmtDelta(-1)).toBe('-1 d');
    expect(fmtDelta(0)).toBe('0 d');
  });

  it('movedToast: the plain move, a move back', () => {
    expect(movedToast(mkResult())).toBe('Moved WO-101 → Wed 16 Sep 2026 (+2 d)');
    expect(movedToast(mkResult({ newStart: '2026-09-11', newEnd: '2026-09-12', delta: -3 }))).toBe(
      'Moved WO-101 → Fri 11 Sep 2026 (-3 d)',
    );
  });

  it('movedToast: OD-116 - a SPAN move says where the end landed', () => {
    expect(movedToast(mkResult({ reasons: [SPAN_REASON] }))).toBe(
      'Moved WO-101 → Wed 16 Sep 2026 (+2 d) · ends Thu 17 Sep 2026',
    );
    expect(endNote(mkResult({ reasons: [SPAN_REASON], newEnd: '' }))).toBe('');
    expect(endNote(mkResult({ reasons: [] }))).toBe('');
  });

  it('pinNote: pins, unpins, still pinned, nothing', () => {
    expect(pinNote(mkResult({ willPin: true, pinned: true }))).toBe(' · pinned (engine leaves it)');
    expect(pinNote(mkResult({ willUnpin: true }))).toBe(' · back on the engine date, pin cleared');
    expect(pinNote(mkResult({ pinned: true }))).toBe(' · still pinned');
    expect(pinNote(mkResult())).toBe('');
    expect(movedToast(mkResult({ willPin: true, pinned: true, reasons: [SPAN_REASON] }))).toBe(
      'Moved WO-101 → Wed 16 Sep 2026 (+2 d) · ends Thu 17 Sep 2026 · pinned (engine leaves it)',
    );
  });

  it('undoneToast', () => {
    expect(undoneToast(mkResult({ newStart: '2026-09-14', delta: -2 }))).toBe('Undone: WO-101 back on Mon 14 Sep 2026');
  });
});

describe('moves - applyMove and pushUndo', () => {
  it('applyMove moves the one WO and leaves the range it was given alone', () => {
    const next = applyMove(RANGE, mkResult());
    const moved = next.wos.find((w) => w.id === 101);
    expect(moved?.start).toBe('2026-09-16');
    expect(moved?.end).toBe('2026-09-17');
    expect(RANGE.wos.find((w) => w.id === 101)?.start).toBe('2026-09-14');
    expect(next.wos.filter((w) => w.id !== 101)).toEqual(RANGE.wos.filter((w) => w.id !== 101));
    expect(next.wos[1]).toBe(RANGE.wos[1]);
  });

  it('applyMove carries the pin and keeps a week number or engine date the result leaves empty', () => {
    const pinned = applyMove(
      RANGE,
      mkResult({ woId: 105, sid: 'PM-105', pinned: false, willUnpin: true, weekNo: 0, engineDate: '' }),
    );
    const w = pinned.wos.find((x) => x.id === 105);
    const before = RANGE.wos.find((x) => x.id === 105);
    expect(w?.pinned).toBe(false);
    expect(w?.weekNo).toBe(before?.weekNo);
    expect(w?.engineDate).toBe(before?.engineDate);
    const pins = applyMove(RANGE, mkResult({ pinned: true, willPin: true, engineDate: '2026-09-14' }));
    expect(pins.wos.find((x) => x.id === 101)?.engineDate).toBe('2026-09-14');
  });

  it('applyMove returns the very same range when the WO is not in it', () => {
    expect(applyMove(RANGE, mkResult({ woId: 999 }))).toBe(RANGE);
  });

  it('pushUndo keeps the newest ten and never touches the stack it was given', () => {
    const u = (n: number): UndoRef => ({ woId: n, toIso: '2026-09-14', expectStartIso: '2026-09-16' });
    let stack: UndoRef[] = [];
    for (let i = 1; i <= 12; i++) stack = pushUndo(stack, u(i));
    expect(stack).toHaveLength(10);
    expect(stack[0].woId).toBe(3);
    expect(stack[9].woId).toBe(12);
    const before = [...stack];
    pushUndo(stack, u(13));
    expect(stack).toEqual(before);
  });
});

describe('moves - the wire', () => {
  const seen: Request[] = [];
  const answer: { status: number; body: unknown } = { status: 200, body: mkResult() };
  const fetchStub = vi.fn((input: RequestInfo | URL) => {
    if (input instanceof Request) seen.push(input);
    return Promise.resolve(
      new Response(JSON.stringify(answer.body), {
        status: answer.status,
        headers: { 'content-type': 'application/json' },
      }),
    );
  });

  beforeAll(() => {
    vi.stubGlobal('fetch', fetchStub);
    client.setConfig({ baseUrl: BASE });
  });
  afterAll(() => {
    vi.unstubAllGlobals();
  });
  afterEach(() => {
    seen.length = 0;
    fetchStub.mockClear();
  });

  it('postMove sends the oracle keys to /api/v1/planner/move and returns the move', async () => {
    answer.status = 200;
    answer.body = mkResult();
    const o = await postMove({ woId: 101, toIso: '2026-09-16', expectStartIso: '2026-09-14', confirm: false });
    expect(o.kind).toBe('ok');
    expect(seen).toHaveLength(1);
    expect(seen[0].method).toBe('POST');
    expect(seen[0].url).toBe(`${BASE}/api/v1/planner/move`);
    expect(await seen[0].json()).toEqual({
      woId: 101,
      toIso: '2026-09-16',
      expectStartIso: '2026-09-14',
      confirm: false,
    });
  });

  it('postMove turns a 409 into the stale outcome', async () => {
    answer.status = 409;
    answer.body = mkError('STALE', 'WO-101 moved', { currentStart: '2026-09-18' });
    const o = await postMove({ woId: 101, toIso: '2026-09-16', expectStartIso: '2026-09-14', confirm: true });
    expect(o).toEqual({ kind: 'stale', code: 'STALE', message: 'WO-101 moved', currentStart: '2026-09-18' });
  });

  it('postUndo sends the undo dict to /api/v1/planner/undo', async () => {
    answer.status = 200;
    answer.body = mkResult({ newStart: '2026-09-14', delta: -2 });
    const o = await postUndo({ woId: 101, toIso: '2026-09-14', expectStartIso: '2026-09-16' });
    expect(o.kind).toBe('ok');
    expect(seen[0].url).toBe(`${BASE}/api/v1/planner/undo`);
    expect(await seen[0].json()).toEqual({ woId: 101, toIso: '2026-09-14', expectStartIso: '2026-09-16' });
  });

  it('a fetch that rejects comes back as the network failure, not a throw', async () => {
    fetchStub.mockImplementationOnce(() => Promise.reject(new TypeError('Failed to fetch')));
    const o = await postMove({ woId: 101, toIso: '2026-09-16', expectStartIso: '2026-09-14', confirm: false });
    expect(o).toEqual({ kind: 'failed', code: 'NETWORK', message: NETWORK_MESSAGE });
  });
});
