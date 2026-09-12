/**
 * Azztec_SaaS_web_planner_PlannerView_test_v1_0_0.tsx  ->  web/src/features/planner/PlannerView.test.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §6 (planner.route.test.tsx row) · OD-29
 *
 * Two jobs. First, validateSearch as a pure function: a bogus mode or a calendar-invalid anchor must
 * fall back rather than reach the network. Second, the wire: mode+anchor in the URL must produce a
 * request for the window windowFor derives - `from=2026-09-14&to=2026-09-20` for week/2026-09-16 -
 * with `from=`, never `from_=` (the fourth occurrence of that alias being closed at the wire).
 *
 * The fetch stub is the instrument, as in the S1e hook test: asserting the rendered output alone would
 * pass even if the request had gone out with the wrong window.
 *
 * No router here: PlannerView takes mode and anchor as props (spec 6 contingency, taken up front), so
 * this proves the derivation and the request without a route tree or a memory history in the way.
 * The module imports planner.css; Vite serves that in the jsdom environment without a plugin.
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, waitFor, cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { client } from '../../api/client/client.gen';
import { PlannerView, validateSearch } from './PlannerView';
import { todayIso, windowFor } from '../../lib/dates';

export const TEST_VERSION = '1.0.0';

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
  const body = {
    from,
    to,
    today: from,
    wos: [],
    labour: [],
    workers: [],
    teams: [],
    priorities: [],
    colours: {},
    weeks: [],
    load: {},
    counts: { wo: 0, pm: 0, done: 0, total: 0 },
    pinTable: false,
    workerWeeks: {},
    uomHours: 12,
    libVersion: 'test',
    ok: true,
    apiVersion: 'test',
    actor: 1,
    ms: 0,
  };
  return Promise.resolve(
    new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } }),
  );
});

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

describe('PlannerView - the wire', () => {
  beforeAll(() => {
    vi.stubGlobal('fetch', fetchStub);
    client.setConfig({ baseUrl: BASE });
  });
  afterAll(() => {
    vi.unstubAllGlobals();
  });
  beforeEach(() => {
    fetchStub.mockClear();
  });
  afterEach(() => {
    cleanup();
  });

  it('week + 2026-09-16 requests from=2026-09-14&to=2026-09-20, once, with from= not from_=', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
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
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
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
});
