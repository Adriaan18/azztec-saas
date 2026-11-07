/**
 * Azztec_SaaS_web_planner_PlannerView_test_v1_3_0.tsx  ->  web/src/features/planner/PlannerView.test.tsx
 * Version:  1.3.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §6 (planner.route.test.tsx row) · OD-29;
 *           Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §6 (PlannerView.test.tsx row) · OD-30;
 *           Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (PlannerView.test.tsx row) · OD-107, OD-113
 *
 * Three jobs. First, validateSearch as a pure function: a bogus mode or a calendar-invalid anchor must
 * fall back rather than reach the network. Second, the wire: mode+anchor in the URL must produce a
 * request for the window windowFor derives - `from=2026-09-14&to=2026-09-20` for week/2026-09-16 -
 * with `from=`, never `from_=`. Third (1.1.0), OD-30: when the window changes while a request is in
 * flight, that request's AbortSignal fires - TanStack drops a query's fetch when it loses its last
 * observer, provided the queryFn consumed the signal, and the generated queryFn does.
 *
 * The fetch stub is the instrument, as in the S1e hook test: it now answers with the S1f fixture so
 * the chips, the rail and the card render, and the keyboard / Escape / day-dialog cases have something
 * to act on. This is still the only file in the tree that stubs fetch.
 *
 * No router here: PlannerView takes mode and anchor as props (spec 6 contingency, taken up front).
 * The module imports planner.css; Vite serves that in the jsdom environment without a plugin.
 * The Zustand store is module-global, so beforeEach resets the fields these cases touch.
 *
 * 1.3.0 (DP3b): the stub is now a small server. GET /range answers with `server`, a RangeData that a
 * scripted POST /move or /undo moves when its reply is ok (applyMove - tested on its own in
 * moves.test.ts), so the refetch after a move draws what the server would; every POST is recorded with
 * its path and JSON body. The drags are the useWoDrag test's: MouseEvents with a pointerId, inside
 * act(), with elementFromPoint stubbed to the cell the case drops on.
 *
 * Changelog:
 *   1.3.0  DP3b: the moves block - the drag's post, the ok flow (apply, toast, Undo, refetch), CONFIRM ->
 *          the dialog -> Move it / Cancel / Escape, STALE, the write banner, Ctrl+Z (and inert in the
 *          search box), a refused chip, Escape mid-drag, the click after a drop, and RO (no .mv, the
 *          read-only hint, a drag posts nothing). The read-only cases are unchanged; the store reset
 *          also empties the undo stack.
 *   1.2.1  Smoke fix, before the tag. `importOriginal<typeof import('...')>()` is an inline import()
 *          type, which the repo forbids (consistent-type-imports). The module is imported as a
 *          type-only namespace at the top instead, and the generic points at that. Same mock.
 *   1.2.0  W1b: SelectedWOCard's Open button became a Link (OD-5 closed), so this file's two card
 *          cases started throwing on useLinkProps - a real regression from that change, not a flake.
 *          Link is mocked below. No case's meaning moved; the card still renders and Escape, the
 *          selection and the day dialog are asserted exactly as they were.
 *   1.1.0  S1g: fixture-backed stub, store reset, the OD-30 abort case, keyboard nav, Escape, day head.
 *   1.0.0  Initial S1f.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import type * as ReactRouter from '@tanstack/react-router';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { client } from '../../api/client/client.gen';
import { PlannerView, validateSearch } from './PlannerView';
import { applyMove } from './moves';
import { mkConfirm, mkError, mkResult } from './moves.fixture';
import { RANGE } from './range.fixture';
import { DEFAULT_CATS, DEFAULT_FILTERS, HINT, HINT_RW } from './rules';
import { usePlannerStore } from './store';
import { navAnchor, todayIso, windowFor } from '../../lib/dates';
import type { MoveResult, RangeData } from '../../api/client/types.gen';

/**
 * W1b: PlannerView renders SelectedWOCard, whose Open control is now a <Link> to /workorders/$id -
 * and a Link needs a RouterProvider this file deliberately does not stand up. importOriginal keeps
 * every other export real; only Link is swapped, for the same plain <a> SelectedWOCard.test uses.
 * The alternative was a memory router here, which would make a wire test depend on the route tree.
 */
vi.mock('@tanstack/react-router', async (importOriginal) => ({
  ...(await importOriginal<typeof ReactRouter>()),
  Link: ({
    children,
    to,
    params,
    className,
    ...rest
  }: {
    children: ReactNode;
    to: string;
    params: Record<string, string>;
    className?: string;
  }) => (
    <a className={className} data-params={JSON.stringify(params)} data-to={to} href="#" {...rest}>
      {children}
    </a>
  ),
}));

export const TEST_VERSION = '1.3.0';

const BASE = 'http://test.local';

function urlOf(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

/** 1.3.0: what GET /range answers with - moved by every ok reply to a POST, reset before each case. */
let server: RangeData = RANGE;
/** the scripted replies to POST /move and /undo, taken in order */
const replies: Array<{ status: number; body: unknown }> = [];
/** every POST the view made: path and JSON body */
const posts: Array<{ path: string; body: unknown }> = [];

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

function isMove(body: unknown): body is MoveResult {
  return typeof body === 'object' && body !== null && (body as { ok?: unknown }).ok === true;
}

const fetchStub = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
  const u = new URL(urlOf(input));
  if (input instanceof Request && input.method === 'POST') {
    const body: unknown = await input.json();
    posts.push({ path: u.pathname, body });
    const reply = replies.shift() ?? { status: 500, body: mkError('INTERNAL', 'no scripted reply') };
    if (reply.status === 200 && isMove(reply.body)) server = applyMove(server, reply.body);
    return json(reply.status, reply.body);
  }
  const from = u.searchParams.get('from') ?? '';
  const to = u.searchParams.get('to') ?? '';
  return json(200, { ...server, from, to, today: from });
});

/** the GETs so far - a refetch after a write shows up here */
function gets(): number {
  return fetchStub.mock.calls.filter(([i]) => !(i instanceof Request && i.method === 'POST')).length;
}

function qc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function must(root: ParentNode, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

describe('PlannerView - validateSearch (OD-29)', () => {
  it('keeps a good mode and anchor', () => {
    expect(validateSearch({ mode: 'week', anchor: '2026-09-16' })).toEqual({ mode: 'week', anchor: '2026-09-16' });
    expect(validateSearch({ mode: 'twoweek', anchor: '2026-06-01' })).toEqual({
      mode: 'twoweek',
      anchor: '2026-06-01',
    });
  });

  it('falls back to month + today on a bogus mode or a calendar-invalid anchor', () => {
    expect(validateSearch({ mode: 'sixm', anchor: '2026-02-31' })).toEqual({ mode: 'month', anchor: todayIso() });
    expect(validateSearch({})).toEqual({ mode: 'month', anchor: todayIso() });
    expect(validateSearch({ mode: 42, anchor: ['x'] })).toEqual({ mode: 'month', anchor: todayIso() });
  });

  it('every fallback anchor produces a window inside the cap', () => {
    const s = validateSearch({});
    expect(windowFor(s.mode, s.anchor).days).toBeLessThanOrEqual(42);
  });
});

describe('PlannerView - the wire, the keys, the dialog', () => {
  beforeAll(() => {
    vi.stubGlobal('fetch', fetchStub);
    client.setConfig({ baseUrl: BASE });
  });
  afterAll(() => {
    vi.unstubAllGlobals();
  });
  beforeEach(() => {
    fetchStub.mockClear();
    server = RANGE;
    replies.length = 0;
    posts.length = 0;
    usePlannerStore.setState({
      selected: 0,
      dayOpen: '',
      filters: { ...DEFAULT_FILTERS },
      cats: { ...DEFAULT_CATS },
      undo: [],
      undoBy: 0,
    });
  });
  afterEach(() => {
    cleanup();
  });

  it('week + 2026-09-16 requests from=2026-09-14&to=2026-09-20, once, with from= not from_=', async () => {
    render(
      <QueryClientProvider client={qc()}>
        <PlannerView mode="week" anchor="2026-09-16" onSearch={vi.fn()} />
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(fetchStub).toHaveBeenCalledTimes(1);
    });
    const url = urlOf(fetchStub.mock.calls[0][0]);
    expect(url).toContain('/api/v1/planner/range');
    expect(url).toContain('from=2026-09-14');
    expect(url).toContain('to=2026-09-20');
    expect(url).not.toContain('from_');
  });

  it('month + 2026-08-15 requests the 42-day window, still one request', async () => {
    render(
      <QueryClientProvider client={qc()}>
        <PlannerView mode="month" anchor="2026-08-15" onSearch={vi.fn()} />
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(fetchStub).toHaveBeenCalledTimes(1);
    });
    const url = urlOf(fetchStub.mock.calls[0][0]);
    expect(url).toContain('from=2026-07-27');
    expect(url).toContain('to=2026-09-06');
  });

  it('a nav while a request is in flight aborts it in the browser and issues the new window (OD-30)', async () => {
    const seen: { signal: AbortSignal | null } = { signal: null };
    fetchStub.mockImplementationOnce((input) => {
      seen.signal = input instanceof Request ? input.signal : null;
      return new Promise<Response>(() => {
        /* never resolves - the request stays in flight until it is aborted */
      });
    });
    const client1 = qc();
    const { rerender } = render(
      <QueryClientProvider client={client1}>
        <PlannerView mode="week" anchor="2026-09-16" onSearch={vi.fn()} />
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(fetchStub).toHaveBeenCalledTimes(1);
    });
    expect(seen.signal).not.toBeNull();
    expect(seen.signal?.aborted).toBe(false);
    rerender(
      <QueryClientProvider client={client1}>
        <PlannerView mode="week" anchor="2026-09-23" onSearch={vi.fn()} />
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(fetchStub).toHaveBeenCalledTimes(2);
    });
    expect(urlOf(fetchStub.mock.calls[1][0])).toContain('from=2026-09-21');
    await waitFor(() => {
      expect(seen.signal?.aborted).toBe(true);
    });
  });

  it('Left / Right / T move the anchor through onSearch; the same keys in a text input do nothing', async () => {
    const onSearch = vi.fn();
    const { container } = render(
      <QueryClientProvider client={qc()}>
        <PlannerView mode="week" anchor="2026-09-16" onSearch={onSearch} />
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(container.querySelectorAll('.chip')).toHaveLength(4); // DONE off by default
    });
    fireEvent.keyDown(document, { key: 'ArrowRight' });
    expect(onSearch).toHaveBeenLastCalledWith({ anchor: navAnchor('week', '2026-09-16', 1) });
    fireEvent.keyDown(document, { key: 'ArrowLeft' });
    expect(onSearch).toHaveBeenLastCalledWith({ anchor: navAnchor('week', '2026-09-16', -1) });
    fireEvent.keyDown(document, { key: 't' });
    expect(onSearch).toHaveBeenLastCalledWith({ anchor: todayIso() });
    expect(onSearch).toHaveBeenCalledTimes(3);
    fireEvent.keyDown(must(container, 'input[type="text"]'), { key: 'ArrowRight' });
    fireEvent.keyDown(must(container, 'select'), { key: 'T' });
    expect(onSearch).toHaveBeenCalledTimes(3);
  });

  it('a chip click selects and the card follows; Escape clears; Escape with the dialog open closes it and keeps the selection', async () => {
    const { container } = render(
      <QueryClientProvider client={qc()}>
        <PlannerView mode="week" anchor="2026-09-16" onSearch={vi.fn()} />
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(container.querySelectorAll('.chip')).toHaveLength(4);
    });
    expect(must(container, '.selc').getAttribute('data-wo')).toBe('0');
    fireEvent.click(must(container, '[data-wo="101"].chip'));
    expect(must(container, '.selc').getAttribute('data-wo')).toBe('101');
    expect(must(container, '[data-wo="101"].chip').className).toContain('sel');
    fireEvent.click(must(container, '[data-day="2026-09-14"]'));
    expect(must(container, '.ovl').className).toBe('ovl on');
    expect(must(container, '.ovl h2').textContent).toContain('MON 14 SEP 2026');
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(container.querySelector('.ovl')).toBeNull();
    expect(must(container, '.selc').getAttribute('data-wo')).toBe('101');
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(must(container, '.selc').getAttribute('data-wo')).toBe('0');
  });

  it('the day dialog lists the visible WOs of that day and its Select assigns the selection', async () => {
    const { container } = render(
      <QueryClientProvider client={qc()}>
        <PlannerView mode="week" anchor="2026-09-16" onSearch={vi.fn()} />
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(container.querySelectorAll('.chip')).toHaveLength(4);
    });
    fireEvent.click(must(container, '[data-day="2026-09-14"]'));
    expect(container.querySelectorAll('.ovl .job')).toHaveLength(1);
    fireEvent.click(must(container, '.ovl .job .acts button'));
    expect(container.querySelector('.ovl')).toBeNull();
    expect(must(container, '.selc').getAttribute('data-wo')).toBe('101');
    // a second Select on the same WO must not toggle it off (oracle 736 assigns)
    fireEvent.click(must(container, '[data-day="2026-09-14"]'));
    fireEvent.click(must(container, '.ovl .job .acts button'));
    expect(must(container, '.selc').getAttribute('data-wo')).toBe('101');
  });

  it('the filters row and the rail click narrow the grid (S1g, end to end on the fixture)', async () => {
    const { container } = render(
      <QueryClientProvider client={qc()}>
        <PlannerView mode="week" anchor="2026-09-16" onSearch={vi.fn()} />
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(container.querySelectorAll('.chip')).toHaveLength(4);
    });
    fireEvent.click(must(container, '.wsel button'));
    fireEvent.click(must(container, '.wsel .menu input')); // Ann Kowhai (2): 101 and 105
    expect(container.querySelectorAll('.chip')).toHaveLength(2);
    expect(must(container, '.wsel .who').textContent).toBe('Ann Kowhai');
    fireEvent.click(Array.from(container.querySelectorAll('.filters button')).find((b) => b.textContent === 'Clear') as HTMLElement);
    expect(container.querySelectorAll('.chip')).toHaveLength(4);
    fireEvent.click(must(container, '.wk[data-worker="692"]')); // rail click-to-filter: 101 and 105
    expect(must(container, '.wk[data-worker="692"]').className).toBe('wk on');
    expect(container.querySelectorAll('.chip')).toHaveLength(2);
  });
});

/* ------------------------------------------------------------------ 1.3.0: moves (DP3b) */

/** Where elementFromPoint says the pointer is - the cell a case drops on. */
let over: Element | null = null;

/** A pointer event every jsdom can build: a MouseEvent with the pointerId the drag matches on. */
function pointer(type: string, target: EventTarget, x: number, y: number) {
  const ev = new MouseEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0 });
  Object.defineProperty(ev, 'pointerId', { value: 1 });
  act(() => {
    target.dispatchEvent(ev);
  });
}

/** Press on the chip, move 60 px over the day's cell, let go. */
function dragTo(root: ParentNode, woId: number, iso: string) {
  const chip = must(root, `.chip[data-wo="${woId}"]`);
  over = must(root, `.cell[data-date="${iso}"]`);
  pointer('pointerdown', chip, 100, 100);
  pointer('pointermove', document, 160, 100);
  pointer('pointerup', document, 160, 100);
}

function button(root: ParentNode, text: string): HTMLElement {
  const b = Array.from(root.querySelectorAll('button')).find((x) => x.textContent === text);
  if (!b) throw new Error(`no button ${text}`);
  return b;
}

describe('PlannerView - moves (DP3b)', () => {
  const realElementFromPoint = Object.getOwnPropertyDescriptor(document, 'elementFromPoint');

  beforeAll(() => {
    vi.stubGlobal('fetch', fetchStub);
    client.setConfig({ baseUrl: BASE });
  });
  afterAll(() => {
    vi.unstubAllGlobals();
  });
  beforeEach(() => {
    fetchStub.mockClear();
    server = RANGE;
    replies.length = 0;
    posts.length = 0;
    over = null;
    Object.defineProperty(document, 'elementFromPoint', { configurable: true, value: () => over });
    usePlannerStore.setState({
      selected: 0,
      dayOpen: '',
      filters: { ...DEFAULT_FILTERS },
      cats: { ...DEFAULT_CATS },
      undo: [],
      undoBy: 0,
    });
  });
  afterEach(() => {
    cleanup();
    if (realElementFromPoint) Object.defineProperty(document, 'elementFromPoint', realElementFromPoint);
    else Reflect.deleteProperty(document, 'elementFromPoint');
  });

  async function mount(canMove = true) {
    const r = render(
      <QueryClientProvider client={qc()}>
        <PlannerView mode="week" anchor="2026-09-16" onSearch={vi.fn()} canMove={canMove} actorId={21} />
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(r.container.querySelectorAll('.chip')).toHaveLength(4);
    });
    return r;
  }

  const MOVE_101 = { woId: 101, toIso: '2026-09-16', expectStartIso: '2026-09-14' };

  it('a drop posts the oracle body; ok draws the chip on its new day, toasts with Undo and refetches', async () => {
    replies.push({ status: 200, body: mkResult() });
    const { container } = await mount();
    expect(must(container, '.filters .hint').textContent).toBe(HINT_RW);
    expect(container.querySelectorAll('.chip.mv')).toHaveLength(3); // 101, 103, 105 - 102 is locked
    const before = gets();
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(posts).toHaveLength(1);
    });
    expect(posts[0]).toEqual({ path: '/api/v1/planner/move', body: { ...MOVE_101, confirm: false } });
    await waitFor(() => {
      expect(must(container, '.toast').className).toBe('toast on');
    });
    expect(must(container, '.toast .msg').textContent).toBe('Moved WO-101 → Wed 16 Sep 2026 (+2 d)');
    expect(button(container, 'Undo')).toBeTruthy();
    await waitFor(() => {
      expect(gets()).toBeGreaterThan(before);
    });
    await waitFor(() => {
      expect(container.querySelector('.cell[data-date="2026-09-16"] .chip[data-wo="101"]')).not.toBeNull();
    });
    expect(container.querySelector('.cell[data-date="2026-09-14"] .chip[data-wo="101"]')).toBeNull();
    expect(usePlannerStore.getState().undo).toEqual([mkResult().undo]);
    expect(usePlannerStore.getState().undoBy).toBe(21);
  });

  it('CONFIRM opens the dialog; Move it posts again with confirm:true', async () => {
    replies.push({ status: 200, body: mkConfirm() }, { status: 200, body: mkResult() });
    const { container } = await mount();
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(container.querySelector('[data-confirm]')).not.toBeNull();
    });
    expect(must(container, '[data-confirm] h2').textContent).toBe('MOVE WO-101?');
    expect(posts).toHaveLength(1);
    fireEvent.click(button(container, 'Move it'));
    await waitFor(() => {
      expect(posts).toHaveLength(2);
    });
    expect(posts[1]).toEqual({ path: '/api/v1/planner/move', body: { ...MOVE_101, confirm: true } });
    expect(container.querySelector('[data-confirm]')).toBeNull();
    await waitFor(() => {
      expect(must(container, '.toast .msg').textContent).toContain('Moved WO-101');
    });
  });

  it('Cancel and Escape close the dialog and post nothing more; Enter is Move it', async () => {
    replies.push(
      { status: 200, body: mkConfirm() },
      { status: 200, body: mkConfirm() },
      { status: 200, body: mkConfirm() },
    );
    const { container } = await mount();
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(container.querySelector('[data-confirm]')).not.toBeNull();
    });
    fireEvent.click(button(container, 'Cancel'));
    expect(container.querySelector('[data-confirm]')).toBeNull();
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(container.querySelector('[data-confirm]')).not.toBeNull();
    });
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(container.querySelector('[data-confirm]')).toBeNull();
    expect(posts).toHaveLength(2);
    expect(posts.every((p) => (p.body as { confirm: boolean }).confirm === false)).toBe(true);
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(container.querySelector('[data-confirm]')).not.toBeNull();
    });
    replies.push({ status: 200, body: mkResult() });
    fireEvent.keyDown(document, { key: 'Enter' });
    await waitFor(() => {
      expect(posts).toHaveLength(4);
    });
    expect((posts[3].body as { confirm: boolean }).confirm).toBe(true);
  });

  it("the toast's Undo posts /undo with the undo dict and says Undone", async () => {
    replies.push(
      { status: 200, body: mkResult() },
      { status: 200, body: mkResult({ newStart: '2026-09-14', newEnd: '2026-09-15', delta: -2 }) },
    );
    const { container } = await mount();
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(must(container, '.toast').className).toBe('toast on');
    });
    fireEvent.click(button(container, 'Undo'));
    await waitFor(() => {
      expect(posts).toHaveLength(2);
    });
    expect(posts[1]).toEqual({
      path: '/api/v1/planner/undo',
      body: { woId: 101, toIso: '2026-09-14', expectStartIso: '2026-09-16' },
    });
    await waitFor(() => {
      expect(must(container, '.toast .msg').textContent).toBe('Undone: WO-101 back on Mon 14 Sep 2026');
    });
    expect(usePlannerStore.getState().undo).toEqual([]);
  });

  it('Ctrl+Z undoes the last move; in the search box it is the box own undo', async () => {
    replies.push(
      { status: 200, body: mkResult() },
      { status: 200, body: mkResult({ newStart: '2026-09-14', delta: -2 }) },
    );
    const { container } = await mount();
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(posts).toHaveLength(1);
    });
    await waitFor(() => {
      expect(usePlannerStore.getState().undo).toHaveLength(1);
    });
    fireEvent.keyDown(must(container, 'input[type="text"]'), { key: 'z', ctrlKey: true });
    expect(posts).toHaveLength(1);
    fireEvent.keyDown(document, { key: 'z', ctrlKey: true });
    await waitFor(() => {
      expect(posts).toHaveLength(2);
    });
    expect(posts[1].path).toBe('/api/v1/planner/undo');
  });

  it('a refused undo leaves the stack; a failed one goes back on top (OD-113)', async () => {
    replies.push(
      { status: 200, body: mkResult() },
      { status: 500, body: mkError('WRITE_FAILED', 'the undo did not save') },
      {
        status: 409,
        body: mkError('STALE', 'WO-101 moved since you loaded the planner', { currentStart: '2026-09-18' }),
      },
    );
    const { container } = await mount();
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(usePlannerStore.getState().undo).toHaveLength(1);
    });
    fireEvent.keyDown(document, { key: 'z', ctrlKey: true });
    await waitFor(() => {
      expect(must(container, '.toast .msg').textContent).toBe('the undo did not save');
    });
    expect(usePlannerStore.getState().undo).toHaveLength(1);
    fireEvent.keyDown(document, { key: 'z', ctrlKey: true });
    await waitFor(() => {
      expect(must(container, '.toast .msg').textContent).toBe('WO-101 moved since you loaded the planner');
    });
    expect(usePlannerStore.getState().undo).toHaveLength(0);
    expect(posts.map((p) => p.path)).toEqual(['/api/v1/planner/move', '/api/v1/planner/undo', '/api/v1/planner/undo']);
  });

  it('STALE toasts the server line and refetches', async () => {
    replies.push({
      status: 409,
      body: mkError('STALE', 'WO-101 moved since you loaded the planner (now 2026-09-18) - refreshing', {
        currentStart: '2026-09-18',
      }),
    });
    const { container } = await mount();
    const before = gets();
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(must(container, '.toast .msg').textContent).toBe(
        'WO-101 moved since you loaded the planner (now 2026-09-18) - refreshing',
      );
    });
    await waitFor(() => {
      expect(gets()).toBeGreaterThan(before);
    });
    expect(usePlannerStore.getState().undo).toEqual([]);
  });

  it('NO_RIGHT raises the write banner, and its x dismisses it', async () => {
    replies.push({ status: 403, body: mkError('NO_RIGHT', 'no right planner need=RW have=RO') });
    const { container } = await mount();
    dragTo(container, 101, '2026-09-16');
    await waitFor(() => {
      expect(container.querySelector('[data-write]')).not.toBeNull();
    });
    expect(must(container, '[data-write]').textContent).toContain('no right planner need=RW have=RO');
    fireEvent.click(must(container, '[data-write] .x'));
    expect(container.querySelector('[data-write]')).toBeNull();
  });

  it('a chip that cannot move toasts why, and nothing is posted', async () => {
    const { container } = await mount();
    dragTo(container, 102, '2026-09-16');
    expect(must(container, '.toast .msg').textContent).toBe(
      'PM-102 is a PM the release engine owns - run the S3 DDL (WO_N_Plan) to allow planner pins',
    );
    expect(posts).toHaveLength(0);
  });

  it('Escape mid-drag ends it with nothing posted; the click after a drop does not select', async () => {
    replies.push({ status: 200, body: mkResult() });
    const { container } = await mount();
    const chip = must(container, '.chip[data-wo="101"]');
    over = must(container, '.cell[data-date="2026-09-16"]');
    pointer('pointerdown', chip, 100, 100);
    pointer('pointermove', document, 160, 100);
    expect(container.querySelector('.ghost')).not.toBeNull();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(container.querySelector('.ghost')).toBeNull();
    pointer('pointerup', document, 160, 100);
    expect(posts).toHaveLength(0);

    dragTo(container, 101, '2026-09-16');
    fireEvent.click(must(container, '.chip[data-wo="101"]'));
    expect(must(container, '.selc').getAttribute('data-wo')).toBe('0');
    await waitFor(() => {
      expect(posts).toHaveLength(1);
    });
  });

  it('read-only (OD-107): no .mv, the read-only hint, a drag posts nothing and Ctrl+Z does nothing', async () => {
    const { container } = await mount(false);
    expect(container.querySelectorAll('.chip.mv')).toHaveLength(0);
    expect(must(container, '.filters .hint').textContent).toBe(HINT);
    dragTo(container, 101, '2026-09-16');
    expect(container.querySelector('.ghost')).toBeNull();
    fireEvent.keyDown(document, { key: 'z', ctrlKey: true });
    expect(posts).toHaveLength(0);
    expect(must(container, '.toast').className).toBe('toast');
  });
});
