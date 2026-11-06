/**
 * Azztec_SaaS_web_auth_SessionGate_test_v1_0_0.tsx  ->  web/src/features/auth/SessionGate.test.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-97 . pair of SessionGate.tsx 1.0.0
 *
 * Router-free, like the gate: the page is a child function, onSignedOut a spy, href a string. fetch is
 * stubbed for the whole file and answers /auth/me with whatever meReply holds (401 unless a case says
 * otherwise); every case gets its own QueryClient, so nothing is cached between cases. A case that
 * leaves a fetch hanging waits until the stub has actually been called, so its one-off reply can never
 * leak into the next case.
 *
 * Changelog:
 *   1.0.0  Initial DP2b. 7 cases.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { client } from '../../api/client/client.gen';
import { SessionGate, VERSION } from './SessionGate';
import { MESSAGES } from './rules';
import { SESSION_KEY, forgetSession } from './session';
import { sessionFixture } from './session.fixture';

export const TEST_VERSION = '1.0.0';

const BASE = 'http://test.local';
const NO_IDENTITY = { ok: false, code: 'NO_IDENTITY', message: 'Sign in first.', rid: 'rid-401' };

let meReply: { status: number; body: unknown } = { status: 401, body: NO_IDENTITY };

const fetchStub = vi.fn<(input: RequestInfo | URL) => Promise<Response>>(() =>
  Promise.resolve(
    new Response(JSON.stringify(meReply.body), {
      status: meReply.status,
      headers: { 'content-type': 'application/json' },
    }),
  ),
);

vi.stubGlobal('fetch', fetchStub);
client.setConfig({ baseUrl: BASE });

function must(root: HTMLElement, sel: string): HTMLElement {
  const el = root.querySelector(sel);
  if (!el) throw new Error(`no element matched ${sel}`);
  return el as HTMLElement;
}

function newQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function draw(href: string, qc: QueryClient) {
  const onSignedOut = vi.fn();
  const r = render(
    <QueryClientProvider client={qc}>
      <SessionGate href={href} onSignedOut={onSignedOut}>
        {(session) => <p data-name="page">{session.user.name}</p>}
      </SessionGate>
    </QueryClientProvider>,
  );
  return { ...r, onSignedOut };
}

beforeEach(() => {
  meReply = { status: 401, body: NO_IDENTITY };
  fetchStub.mockClear();
});

afterEach(() => {
  cleanup();
});

afterAll(() => {
  vi.unstubAllGlobals();
});

describe('SessionGate - nothing mounts until the session is known', () => {
  it('carries its version', () => {
    expect(VERSION).toBe('1.0.0');
  });

  it('a session already in the cache renders the page at once and asks nothing', () => {
    const qc = newQueryClient();
    qc.setQueryData(SESSION_KEY, sessionFixture());
    const { container, onSignedOut } = draw('/planner', qc);
    expect(must(container, '[data-name="page"]').textContent).toBe('Azzmax logon');
    expect(fetchStub).not.toHaveBeenCalled();
    expect(onSignedOut).not.toHaveBeenCalled();
  });

  it('while it asks: one quiet line and no page', async () => {
    fetchStub.mockImplementationOnce(() => new Promise<Response>(() => undefined));
    const { container, onSignedOut } = draw('/planner', newQueryClient());
    expect(must(container, '[data-name="SessionWait"]').textContent).toBe(MESSAGES.CHECKING);
    await waitFor(() => expect(fetchStub).toHaveBeenCalledTimes(1));
    expect(must(container, '[data-name="SessionWait"]').textContent).toBe(MESSAGES.CHECKING);
    expect(container.querySelector('[data-name="page"]')).toBeNull();
    expect(onSignedOut).not.toHaveBeenCalled();
  });

  it('a 401 calls onSignedOut once, with where the person was - path and search', async () => {
    const { container, onSignedOut } = draw('/planner?mode=month&anchor=2026-11-07', newQueryClient());
    await waitFor(() => expect(onSignedOut).toHaveBeenCalledTimes(1));
    expect(onSignedOut).toHaveBeenCalledWith('/planner?mode=month&anchor=2026-11-07');
    const req = fetchStub.mock.calls.at(0)?.[0];
    expect(req instanceof Request ? new URL(req.url).pathname : '').toBe('/api/v1/auth/me');
    expect(container.querySelector('[data-name="page"]')).toBeNull();
  });

  it('the sign-in page is never a next: it goes out as empty', async () => {
    const { onSignedOut } = draw('/signin?next=%2Fplanner', newQueryClient());
    await waitFor(() => expect(onSignedOut).toHaveBeenCalledTimes(1));
    expect(onSignedOut).toHaveBeenCalledWith('');
  });

  it('the check failed: the line and Try again, which asks again and lets the page in', async () => {
    meReply = { status: 500, body: { ok: false, code: 'INTERNAL', message: 'boom', rid: 'rid-500' } };
    const { container, onSignedOut } = draw('/planner', newQueryClient());
    await waitFor(() => expect(container.querySelector('[data-name="SessionError"]')).not.toBeNull());
    expect(must(container, '[data-name="SessionError"] p').textContent).toBe(MESSAGES.NETWORK);
    meReply = { status: 200, body: sessionFixture() };
    fireEvent.click(must(container, '[data-name="SessionError"] button'));
    await waitFor(() => expect(container.querySelector('[data-name="page"]')).not.toBeNull());
    expect(must(container, '[data-name="page"]').textContent).toBe('Azzmax logon');
    expect(fetchStub).toHaveBeenCalledTimes(2);
    expect(onSignedOut).not.toHaveBeenCalled();
  });

  it('a session forgotten while the page is up (a 401 elsewhere) takes the page down and signs out once', async () => {
    const qc = newQueryClient();
    qc.setQueryData(SESSION_KEY, sessionFixture());
    const { container, onSignedOut } = draw('/workorders/662704', qc);
    expect(container.querySelector('[data-name="page"]')).not.toBeNull();
    act(() => {
      forgetSession(qc);
    });
    await waitFor(() => expect(onSignedOut).toHaveBeenCalledTimes(1));
    expect(onSignedOut).toHaveBeenCalledWith('/workorders/662704');
    expect(container.querySelector('[data-name="page"]')).toBeNull();
    expect(fetchStub).not.toHaveBeenCalled();
  });
});
