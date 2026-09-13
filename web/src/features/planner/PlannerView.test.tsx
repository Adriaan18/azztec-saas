/**
 * Azztec_SaaS_web_planner_PlannerView_test_v1_1_0.tsx  ->  web/src/features/planner/PlannerView.test.tsx
 * Version:  1.1.0   Date: 2026-09-13   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §6 (planner.route.test.tsx row) · OD-29;
 *           Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §6 (PlannerView.test.tsx row) · OD-30
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
 * Changelog:
 *   1.1.0  S1g: fixture-backed stub, store reset, the OD-30 abort case, keyboard nav, Escape, day head.
 *   1.0.0  Initial S1f.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { client } from '../../api/client/client.gen';
import { PlannerView, validateSearch } from './PlannerView';
import { RANGE } from './range.fixture';
import { DEFAULT_CATS, DEFAULT_FILTERS } from './rules';
import { usePlannerStore } from './store';
import { navAnchor, todayIso, windowFor } from '../../lib/dates';

export const TEST_VERSION = '1.1.0';

const BASE = 'http://test.local';

function urlOf(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

const fetchStub = vi.fn((input: RequestInfo | URL) => {
  const u = new URL(urlOf(input));
  const from = u.searchParams.get('from') ?? '';
  const to = u.searchParams.get('to') ?? '';
  const body = { ...RANGE, from, to, today: from };
  return Promise.resolve(
    new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } }),
  );
});

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
    usePlannerStore.setState({ selected: 0, dayOpen: '', filters: { ...DEFAULT_FILTERS }, cats: { ...DEFAULT_CATS } });
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
