/**
 * Azztec_SaaS_web_workorders_useWorkorders_test_v1_0_1.tsx  ->  web/src/features/workorders/useWorkorders.test.tsx
 * Version:  1.0.1   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §5 · pair of useWorkorders.ts 1.0.0
 *
 * The usePlannerRange.test harness, exactly: `fetch` is stubbed for the whole file and the stub is
 * the instrument - the disabled-query case asserts the stub was NOT called, not merely that no data
 * came back (the Ways of Working §4 lesson). The generated client builds a Request object and Node's
 * Request rejects relative URLs, so the client gets an absolute baseUrl here; the browser build runs
 * same-origin with baseUrl unset.
 *
 * Changelog:
 *   1.0.1  Smoke fix, before the tag. Advancing a fake timer fires the setTimeout, but the setState
 *          it calls is outside React's work loop, so result.current still held the old value and both
 *          debounce cases failed. The advance is wrapped in act() now, which flushes the update. The
 *          hook was never wrong - the test was measuring before React had run.
 *   1.0.0  Initial W1b. 13 cases.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { client } from '../../api/client/client.gen';
import { recordFixture } from './record.fixture';
import {
  PAGE_SIZE,
  SEARCH_DEBOUNCE_MS,
  SEARCH_MIN_CHARS,
  STALE_MS,
  VERSION,
  settleSearch,
  useDebouncedValue,
  useWoList,
  useWoRecord,
  woListQueryOptions,
  woRecordQueryOptions,
} from './useWorkorders';
import type { WoListFilters } from './useWorkorders';

export const TEST_VERSION = '1.0.1';

const BASE = 'http://test.local';

/** A truthful-enough /workorders body: the hook does not validate, the backend contract test does. */
function listBody(): string {
  return JSON.stringify({
    rows: [],
    count: 0,
    more: false,
    filters: { woType: 'N', includeClosed: 0, includeArchive: 0, search: '', limit: PAGE_SIZE, offset: 0 },
    ok: true,
    apiVersion: 'test',
    actor: 21,
    ms: 1,
  });
}

function urlOf(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

function signalOf(input: RequestInfo | URL): AbortSignal | null {
  if (typeof input === 'string' || input instanceof URL) return null;
  return input.signal;
}

const fetchStub = vi.fn((input: RequestInfo | URL) => {
  const u = new URL(urlOf(input));
  const body = /\/workorders\/\d+$/.test(u.pathname) ? JSON.stringify(recordFixture()) : listBody();
  return Promise.resolve(
    new Response(body, { status: 200, headers: { 'content-type': 'application/json' } }),
  );
});

vi.stubGlobal('fetch', fetchStub);
client.setConfig({ baseUrl: BASE });

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const FILTERS: WoListFilters = {
  woType: 'N',
  includeClosed: 0,
  includeArchive: 0,
  search: '',
  limit: PAGE_SIZE,
  offset: 0,
};

beforeEach(() => {
  fetchStub.mockClear();
});

afterEach(() => {
  vi.useRealTimers();
});

afterAll(() => {
  vi.unstubAllGlobals();
});

describe('settleSearch - the two-character gate (OD-78)', () => {
  it('passes a real term trimmed and swallows a one-character one', () => {
    expect(settleSearch('  bin 16 ')).toBe('bin 16');
    expect(settleSearch('b')).toBe('');
    expect(settleSearch(' ')).toBe('');
    expect(SEARCH_MIN_CHARS).toBe(2);
  });
});

describe('useDebouncedValue', () => {
  it('is immediate on first render', () => {
    const { result } = renderHook(() => useDebouncedValue('a', SEARCH_DEBOUNCE_MS));
    expect(result.current).toBe('a');
  });
  it('holds the old value until the delay passes, then settles', async () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, SEARCH_DEBOUNCE_MS), {
      initialProps: { v: 'a' },
    });
    rerender({ v: 'ab' });
    expect(result.current).toBe('a');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(SEARCH_DEBOUNCE_MS - 1);
    });
    expect(result.current).toBe('a');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(result.current).toBe('ab');
  });
  it('a keystroke inside the window restarts it', async () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, SEARCH_DEBOUNCE_MS), {
      initialProps: { v: 'a' },
    });
    rerender({ v: 'ab' });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    rerender({ v: 'abc' });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    expect(result.current).toBe('a');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(result.current).toBe('abc');
  });
});

describe('woListQueryOptions - the wire shape as data', () => {
  it('carries the six params under their exact names and staleTime 30s', () => {
    const opts = woListQueryOptions({ ...FILTERS, search: 'bin 16', includeClosed: 2, offset: 200 });
    expect(opts.staleTime).toBe(STALE_MS);
    const key = JSON.stringify(opts.queryKey);
    for (const part of ['woType', 'includeClosed', 'includeArchive', 'search', 'limit', 'offset']) {
      expect(key).toContain(part);
    }
  });
});

describe('useWoList on the wire', () => {
  it('builds /api/v1/workorders with every filter and never from_', async () => {
    const { result } = renderHook(() => useWoList({ ...FILTERS, woType: 'M', includeArchive: 1 }), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchStub).toHaveBeenCalledTimes(1);
    const u = new URL(urlOf(fetchStub.mock.calls[0][0]));
    expect(u.pathname).toBe('/api/v1/workorders');
    expect(u.searchParams.get('woType')).toBe('M');
    expect(u.searchParams.get('includeClosed')).toBe('0');
    expect(u.searchParams.get('includeArchive')).toBe('1');
    expect(u.searchParams.get('search')).toBe('');
    expect(u.searchParams.get('limit')).toBe(String(PAGE_SIZE));
    expect(u.searchParams.get('offset')).toBe('0');
    expect(u.searchParams.has('from_')).toBe(false);
  });
  it('a one-character search goes to the wire as the empty search', async () => {
    const { result } = renderHook(() => useWoList({ ...FILTERS, search: 'b' }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const u = new URL(urlOf(fetchStub.mock.calls[0][0]));
    expect(u.searchParams.get('search')).toBe('');
  });
  it('forwards an AbortSignal on the Request (OD-30)', async () => {
    const { result } = renderHook(() => useWoList(FILTERS), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(signalOf(fetchStub.mock.calls[0][0])).toBeInstanceOf(AbortSignal);
  });
});

describe('useWoRecord', () => {
  it('is disabled at 0: no request went out, not merely no data', async () => {
    const { result } = renderHook(() => useWoRecord(0), { wrapper });
    expect(result.current.fetchStatus).toBe('idle');
    expect(fetchStub).not.toHaveBeenCalled();
  });
  it('fetches /api/v1/workorders/662704 and returns the record', async () => {
    const { result } = renderHook(() => useWoRecord(662704), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const u = new URL(urlOf(fetchStub.mock.calls[0][0]));
    expect(u.pathname).toBe('/api/v1/workorders/662704');
    expect(result.current.data?.sid).toBe('3CL-260826-010');
  });
  it('woRecordQueryOptions carries enabled and staleTime', () => {
    expect(woRecordQueryOptions(0).enabled).toBe(false);
    expect(woRecordQueryOptions(7).enabled).toBe(true);
    expect(woRecordQueryOptions(7).staleTime).toBe(STALE_MS);
  });
  it('a non-2xx body surfaces as an error, not as data', async () => {
    fetchStub.mockImplementationOnce(() =>
      Promise.resolve(
        new Response(JSON.stringify({ ok: false, error: 'WO_NOT_FOUND' }), {
          status: 404,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );
    const { result } = renderHook(() => useWoRecord(1), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});

describe('version', () => {
  it('useWorkorders.ts is 1.0.0', () => {
    expect(VERSION).toBe('1.0.0');
  });
});
