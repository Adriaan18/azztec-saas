/**
 * Azztec_SaaS_web_usePlannerRange_test_v1_0_0.tsx  ->  web/src/features/planner/usePlannerRange.test.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1e_Web_Chunk_Spec_v1_0_0.md §6.2 tests 1-7 · pair rule (Ways of Working §4)
 *
 * Zero network: `fetch` is stubbed for the whole file and the stub is the instrument. Test 5 asserts
 * the stub was NOT called for a refused window - asserting only the returned error would pass even if
 * the request had gone out (the Ways of Working §4 lesson, translated). Test 6 is the third occurrence
 * of the `from` alias, closed at the wire: the URL the generated client builds carries `from=`, never
 * `from_=`.
 *
 * The generated client builds a Request object, and Node's Request rejects relative URLs, so the
 * client gets an absolute baseUrl here. The browser build runs same-origin with baseUrl unset.
 *
 * Changelog:
 *   1.0.0  Initial S1e.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { client } from '../../api/client/client.gen';
import { MAX_WINDOW_DAYS, POLL_MS, STALE_MS, VERSION, checkWindow, plannerQueryOptions, usePlannerRange } from './usePlannerRange';

export const TEST_VERSION = '1.0.0';

const BASE = 'http://test.local';

/** A truthful-enough /range body: the hook does not validate, the contract test on the backend does. */
function rangeBody(from: string, to: string): string {
  return JSON.stringify({
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
  });
}

function urlOf(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

const fetchStub = vi.fn((input: RequestInfo | URL) => {
  const u = new URL(urlOf(input));
  const from = u.searchParams.get('from') ?? '';
  const to = u.searchParams.get('to') ?? '';
  return Promise.resolve(
    new Response(rangeBody(from, to), { status: 200, headers: { 'content-type': 'application/json' } }),
  );
});

function wrapperFor(qc: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe('usePlannerRange - the capped hook', () => {
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

  it('carries its version and the OD-23 constant', () => {
    expect(VERSION).toBe('1.0.0');
    expect(MAX_WINDOW_DAYS).toBe(42);
  });

  // 1-4. checkWindow, pure
  it('accepts a 7-day window', () => {
    expect(checkWindow('2026-09-14', '2026-09-20')).toEqual({ ok: true, days: 7 });
  });
  it('accepts a 42-day window (the month view worst case)', () => {
    expect(checkWindow('2026-09-14', '2026-10-25')).toEqual({ ok: true, days: 42 });
  });
  it('refuses a 43-day window as WINDOW_TOO_WIDE', () => {
    const r = checkWindow('2026-09-14', '2026-10-26');
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.code).toBe('WINDOW_TOO_WIDE');
  });
  it('refuses reversed and malformed windows as BAD_WINDOW, like the backend', () => {
    for (const [from, to] of [
      ['2026-09-20', '2026-09-14'],
      ['2026-02-31', '2026-03-01'],
      ['2026-9-14', '2026-09-20'],
    ]) {
      const r = checkWindow(from, to);
      expect(r.ok).toBe(false);
      if (!r.ok) expect(r.code).toBe('BAD_WINDOW');
    }
  });

  // 5. the zero-network proof
  it('does not fetch a refused window - the request never goes out', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => usePlannerRange('2026-09-14', '2026-10-26'), { wrapper: wrapperFor(qc) });
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchStub).not.toHaveBeenCalled();
    expect(result.current.window.ok).toBe(false);
    expect(result.current.query.fetchStatus).toBe('idle');
    expect(result.current.query.data).toBeUndefined();
    qc.clear();
  });

  // 6. the `from` pin, third occurrence
  it('fetches a valid window with from= on the wire and never from_=', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => usePlannerRange('2026-09-14', '2026-09-20'), { wrapper: wrapperFor(qc) });
    await waitFor(() => expect(result.current.query.isSuccess).toBe(true));
    expect(fetchStub).toHaveBeenCalledTimes(1);
    const url = urlOf(fetchStub.mock.calls[0][0]);
    expect(url.startsWith(`${BASE}/api/v1/planner/range?`)).toBe(true);
    expect(url).toContain('from=2026-09-14');
    expect(url).toContain('to=2026-09-20');
    expect(url).not.toContain('from_');
    expect(result.current.window).toEqual({ ok: true, days: 7 });
    expect(result.current.query.data?.from).toBe('2026-09-14');
    expect(result.current.query.data?.counts.total).toBe(0);
    qc.clear();
  });

  // 7. the poll settings, as data
  it('builds options with the poll paused in background and the cap wired to enabled', () => {
    const ok = plannerQueryOptions('2026-09-14', '2026-09-20');
    expect(ok.enabled).toBe(true);
    expect(ok.staleTime).toBe(STALE_MS);
    expect(ok.refetchInterval).toBe(POLL_MS);
    expect(ok.refetchIntervalInBackground).toBe(false);
    expect(JSON.stringify(ok.queryKey)).toContain('"from":"2026-09-14"');

    const wide = plannerQueryOptions('2026-09-14', '2026-10-26');
    expect(wide.enabled).toBe(false);
  });
});
