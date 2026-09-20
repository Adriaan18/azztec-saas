/**
 * Azztec_SaaS_web_workorders_WoMaintView_test_v1_0_1.tsx  ->  web/src/features/workorders/WoMaintView.test.tsx
 * Version:  1.0.1   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §5 · pair of WoMaintView.tsx 1.0.0
 *
 * The one file in the slice that stubs fetch end to end - the view is props-driven, so it renders
 * with NO router, no route tree and no memory history, and the wire assertions are about the
 * request the filters produced, not about the router.
 *
 * Changelog:
 *   1.0.1  Smoke fix, before the tag. Two things. getByText('Check bin 16 level PE') went ambiguous
 *          the moment the record actually rendered - the title is in the list row AND the header
 *          card, which is correct and is now ASSERTED (two matches, one of them .wo-titlefield)
 *          rather than tripped over. And the version pin follows WoMaintView 1.0.1. 21 cases.
 *   1.0.0  Initial W1b. 21 cases.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactElement } from 'react';
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { client } from '../../api/client/client.gen';
import { VERSION, WoMaintView, validateSearch } from './WoMaintView';
import type { WoMaintViewProps } from './WoMaintView';
import { recordFixture } from './record.fixture';

export const TEST_VERSION = '1.0.1';

const BASE = 'http://test.local';

const ROW = {
  id: 662704,
  sid: '3CL-260826-010',
  title: 'Check bin 16 level PE',
  asset: '3CL-090.170.PE1',
  loc: '3CL-090.170',
  status: 'V',
  prog: 6,
  hasPO: true,
  entry: '2026-08-26 19:17:09',
  badge: 'V|3CL-260826-010|6|1',
};

function urlOf(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

const fetchStub = vi.fn((input: RequestInfo | URL) => {
  const u = new URL(urlOf(input));
  const body = /\/workorders\/\d+$/.test(u.pathname)
    ? JSON.stringify(recordFixture())
    : JSON.stringify({
        rows: [ROW],
        count: 1,
        more: false,
        filters: {
          woType: 'N',
          includeClosed: 0,
          includeArchive: 0,
          search: '',
          limit: 200,
          offset: 0,
        },
        ok: true,
        apiVersion: 'test',
        actor: 21,
        ms: 1,
      });
  return Promise.resolve(
    new Response(body, { status: 200, headers: { 'content-type': 'application/json' } }),
  );
});

vi.stubGlobal('fetch', fetchStub);
client.setConfig({ baseUrl: BASE });

function wrap(el: ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{el}</QueryClientProvider>);
}

function props(over: Partial<WoMaintViewProps> = {}): WoMaintViewProps {
  return {
    type: 'N',
    closed: 0,
    archive: 0,
    q: '',
    woId: 0,
    onSearch: vi.fn(),
    onSelect: vi.fn(),
    ...over,
  };
}

function listCalls(): URL[] {
  return fetchStub.mock.calls
    .map((c) => new URL(urlOf(c[0])))
    .filter((u) => u.pathname === '/api/v1/workorders');
}

beforeEach(() => {
  fetchStub.mockClear();
});

afterEach(() => {
  cleanup();
});

afterAll(() => {
  vi.unstubAllGlobals();
});

describe('validateSearch (OD-29 / OD-73)', () => {
  it('seeds N / 0 / 0 / empty from an empty URL, like the view custom props', () => {
    expect(validateSearch({})).toEqual({ type: 'N', closed: 0, archive: 0, q: '' });
  });
  it('accepts the four valid types including the empty All', () => {
    for (const t of ['', 'N', 'CP', 'M']) {
      expect(validateSearch({ type: t }).type).toBe(t);
    }
  });
  it('falls back to N on a junk type rather than fetching something silly', () => {
    expect(validateSearch({ type: 'ZZ' }).type).toBe('N');
  });
  it('reads the tri-state flags from strings, as a URL supplies them', () => {
    expect(validateSearch({ closed: '2', archive: '1' })).toMatchObject({ closed: 2, archive: 1 });
  });
  it('falls back to 0 on an out-of-range or junk flag', () => {
    expect(validateSearch({ closed: '7', archive: 'x' })).toMatchObject({ closed: 0, archive: 0 });
  });
  it('keeps a search term and ignores a non-string one', () => {
    expect(validateSearch({ q: 'bin 16' }).q).toBe('bin 16');
    expect(validateSearch({ q: 42 }).q).toBe('');
  });
});

describe('the wire', () => {
  it('asks for the list once with the seeded filters', async () => {
    wrap(<WoMaintView {...props()} />);
    await waitFor(() => expect(listCalls()).toHaveLength(1));
    const u = listCalls()[0];
    expect(u.searchParams.get('woType')).toBe('N');
    expect(u.searchParams.get('limit')).toBe('200');
    expect(u.searchParams.get('offset')).toBe('0');
  });
  it('does not ask for a record when nothing is selected', async () => {
    wrap(<WoMaintView {...props()} />);
    await waitFor(() => expect(listCalls()).toHaveLength(1));
    expect(fetchStub.mock.calls.map((c) => urlOf(c[0])).some((u) => /workorders\/\d+$/.test(u))).toBe(
      false,
    );
  });
  it('asks for the record when one is selected, and the title lands in both panes', async () => {
    const { container } = wrap(<WoMaintView {...props({ woId: 662704 })} />);
    await waitFor(() => expect(container.querySelector('.wo-titlefield')).toBeTruthy());
    // once in the list row, once in the header card - the oracle shows it in both
    expect(screen.getAllByText('Check bin 16 level PE')).toHaveLength(2);
    expect(
      fetchStub.mock.calls.map((c) => urlOf(c[0])).some((u) => u.endsWith('/workorders/662704')),
    ).toBe(true);
  });
  it('carries the archive flag through to the request', async () => {
    wrap(<WoMaintView {...props({ archive: 2 })} />);
    await waitFor(() => expect(listCalls()).toHaveLength(1));
    expect(listCalls()[0].searchParams.get('includeArchive')).toBe('2');
  });
});

describe('the layout', () => {
  it('draws the list panel and the five main tabs', async () => {
    const { container } = wrap(<WoMaintView {...props()} />);
    await waitFor(() => expect(container.querySelector('.wo-list')).toBeTruthy());
    expect(container.querySelectorAll('[data-tab]')).toHaveLength(5);
  });
  it('makes only the Work Order tab selectable; the other four are inert with a title', async () => {
    const { container } = wrap(<WoMaintView {...props()} />);
    await waitFor(() => expect(container.querySelector('[data-tab="workorder"]')).toBeTruthy());
    expect(container.querySelectorAll('button[data-tab]')).toHaveLength(1);
    const inert = container.querySelectorAll<HTMLSpanElement>('span[data-tab]');
    expect(inert).toHaveLength(4);
    for (const el of inert) {
      expect(el.getAttribute('aria-disabled')).toBe('true');
      expect(el.getAttribute('title') ?? '').toContain('OD-51');
    }
  });
  it('prompts for a selection when none is made', async () => {
    wrap(<WoMaintView {...props()} />);
    await waitFor(() => expect(screen.getByText('Select a work order from the list.')).toBeTruthy());
  });
  it('draws the six sub-tabs once a record is loaded, Details live and five inert', async () => {
    const { container } = wrap(<WoMaintView {...props({ woId: 662704 })} />);
    await waitFor(() => expect(container.querySelectorAll('[data-subtab]')).toHaveLength(6));
    expect(container.querySelectorAll('button[data-subtab]')).toHaveLength(1);
    expect(container.querySelector('[data-subtab="details"]')?.className).toContain('on');
  });
  it('renders the Details sub-tab content with the record', async () => {
    wrap(<WoMaintView {...props({ woId: 662704 })} />);
    await waitFor(() => expect(screen.getByText('652 KPP Plant')).toBeTruthy());
  });
  it('scopes everything under .wm-wo so the planner inherits no tokens', () => {
    const { container } = wrap(<WoMaintView {...props()} />);
    expect(container.querySelector('.wm-wo')).toBeTruthy();
  });
});

describe('the handlers', () => {
  it('a type chip writes the URL rather than holding local state', async () => {
    const p = props();
    wrap(<WoMaintView {...p} />);
    await waitFor(() => expect(screen.getByText('PM')).toBeTruthy());
    fireEvent.click(screen.getByText('PM'));
    expect(p.onSearch).toHaveBeenCalledWith({ type: 'M' });
  });
  it('a row click asks the route to navigate', async () => {
    const p = props();
    wrap(<WoMaintView {...p} />);
    await waitFor(() => expect(screen.getByText('Check bin 16 level PE')).toBeTruthy());
    fireEvent.click(screen.getByText('Check bin 16 level PE'));
    expect(p.onSelect).toHaveBeenCalledWith(662704);
  });
  it('the search box writes q to the URL', async () => {
    const p = props();
    wrap(<WoMaintView {...p} />);
    await waitFor(() => expect(screen.getByLabelText('Search work orders')).toBeTruthy());
    fireEvent.change(screen.getByLabelText('Search work orders'), { target: { value: 'bin' } });
    expect(p.onSearch).toHaveBeenCalledWith({ q: 'bin' });
  });
});

describe('the error state', () => {
  it('says the record failed without blaming the list', async () => {
    fetchStub.mockImplementation((input: RequestInfo | URL) => {
      const u = new URL(urlOf(input));
      if (/\/workorders\/\d+$/.test(u.pathname)) {
        return Promise.resolve(new Response('{}', { status: 500 }));
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            rows: [ROW],
            count: 1,
            more: false,
            filters: {
              woType: 'N',
              includeClosed: 0,
              includeArchive: 0,
              search: '',
              limit: 200,
              offset: 0,
            },
            ok: true,
            apiVersion: 'test',
            actor: 21,
            ms: 1,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        ),
      );
    });
    wrap(<WoMaintView {...props({ woId: 662704 })} />);
    await waitFor(() => expect(screen.getByText('That work order could not be loaded.')).toBeTruthy());
    expect(screen.getByText('Check bin 16 level PE')).toBeTruthy();
  });
});

describe('version', () => {
  it('WoMaintView.tsx is 1.0.1', () => {
    expect(VERSION).toBe('1.0.1');
  });
});
