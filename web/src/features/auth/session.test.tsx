/**
 * Azztec_SaaS_web_auth_session_test_v1_0_0.tsx  ->  web/src/features/auth/session.test.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-97, OD-98 . pair of session.ts 1.0.0
 *
 * The useWorkorders.test harness: fetch is stubbed for the whole file and the stub is the instrument -
 * the cases read the Request the generated client built (method, path, headers, body), not only what
 * came back. Replies are routed by path through one Map, emptied before each case. The generated client
 * needs an absolute baseUrl under Node; the browser build runs same-origin with it unset.
 *
 * The interceptors go on a client of their own (createClient), never on the app's shared one, so the
 * other cases see the client exactly as a page does without main.tsx. A failed fetch is a rejected
 * promise - session.ts must give the same answer whether the openapi-ts client rethrows it or returns
 * it with no response.
 *
 * Changelog:
 *   1.0.0  Initial DP2b. 19 cases.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createClient, createConfig } from '../../api/client/client';
import { client } from '../../api/client/client.gen';
import { CSRF_HEADER, MESSAGES } from './rules';
import {
  SESSION_KEY,
  SESSION_STALE_MS,
  VERSION,
  fetchSession,
  forgetSession,
  installAuthInterceptors,
  rememberSession,
  sessionQueryOptions,
  signIn,
  signOut,
  useSession,
} from './session';
import { LOCKED_BODY, NO_GROUP_BODY, SIGNIN_FAILED_BODY, sessionFixture } from './session.fixture';

export const TEST_VERSION = '1.0.0';

const BASE = 'http://test.local';
const ME = '/api/v1/auth/me';
const SIGNIN = '/api/v1/auth/signin';
const SIGNOUT = '/api/v1/auth/signout';
const NO_IDENTITY = { ok: false, code: 'NO_IDENTITY', message: 'Sign in first.', rid: 'rid-401' };

type Reply = { status: number; body: unknown };
const replies = new Map<string, Reply>();

function reply(path: string, status: number, body: unknown): void {
  replies.set(path, { status, body });
}

function urlOf(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

const fetchStub = vi.fn((input: RequestInfo | URL): Promise<Response> => {
  const path = new URL(urlOf(input)).pathname;
  const r = replies.get(path) ?? { status: 404, body: { ok: false, code: 'NOT_FOUND', message: path, rid: 'rid-404' } };
  return Promise.resolve(
    new Response(JSON.stringify(r.body), { status: r.status, headers: { 'content-type': 'application/json' } }),
  );
});

vi.stubGlobal('fetch', fetchStub);
client.setConfig({ baseUrl: BASE });

/** the Request the generated client handed to fetch on call i */
function requestAt(i: number): Request {
  const input = fetchStub.mock.calls.at(i)?.[0];
  if (!(input instanceof Request)) throw new Error(`fetch call ${i} was not a Request`);
  return input;
}

function pathAt(i: number): string {
  return new URL(requestAt(i).url).pathname;
}

function failNextFetch(): void {
  fetchStub.mockImplementationOnce(() => Promise.reject(new TypeError('fetch failed')));
}

function newQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

/** a cache holding one signed-in session and one page's data */
function seeded(): QueryClient {
  const qc = newQueryClient();
  qc.setQueryData(['planner', 'range'], { rows: [1] });
  qc.setQueryData(SESSION_KEY, sessionFixture());
  return qc;
}

beforeEach(() => {
  replies.clear();
  fetchStub.mockClear();
});

afterEach(() => {
  cleanup();
});

afterAll(() => {
  vi.unstubAllGlobals();
});

describe('version and the cache contract', () => {
  it('session.ts is 1.0.0; one key, 60 s stale (the backend rights cache), no retry', () => {
    expect(VERSION).toBe('1.0.0');
    expect(SESSION_KEY).toEqual(['auth', 'session']);
    expect(SESSION_STALE_MS).toBe(60_000);
    const opts = sessionQueryOptions();
    expect(opts.queryKey).toEqual(['auth', 'session']);
    expect(opts.staleTime).toBe(60_000);
    expect(opts.retry).toBe(false);
  });
});

describe('fetchSession - GET /auth/me', () => {
  it('200: the session, from a GET on the right path', async () => {
    reply(ME, 200, sessionFixture());
    await expect(fetchSession()).resolves.toEqual(sessionFixture());
    expect(requestAt(0).method).toBe('GET');
    expect(pathAt(0)).toBe(ME);
  });

  it('401: null - "not signed in" is an answer, not an error', async () => {
    reply(ME, 401, NO_IDENTITY);
    await expect(fetchSession()).resolves.toBeNull();
  });

  it('500: throws, so the gate can say the check failed', async () => {
    reply(ME, 500, { ok: false, code: 'INTERNAL', message: 'boom', rid: 'rid-500' });
    await expect(fetchSession()).rejects.toThrow('HTTP 500');
  });

  it('no network: throws too', async () => {
    failNextFetch();
    await expect(fetchSession()).rejects.toThrow();
  });
});

describe('useSession', () => {
  it('a 401 settles as success with null, so the gate can tell signed out from still asking', async () => {
    reply(ME, 401, NO_IDENTITY);
    const qc = newQueryClient();
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useSession(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
    expect(fetchStub).toHaveBeenCalledTimes(1);
  });
});

describe('signIn - POST /auth/signin', () => {
  it('sends the user name and password exactly as typed - never trimmed (trap 1)', async () => {
    reply(SIGNIN, 200, sessionFixture());
    expect(await signIn(' AZZ ', ' s3cret ')).toEqual({ ok: true, session: sessionFixture() });
    const req = requestAt(0);
    expect(req.method).toBe('POST');
    expect(pathAt(0)).toBe(SIGNIN);
    expect(req.headers.get('content-type')).toContain('application/json');
    expect(JSON.parse(await req.text())).toEqual({ login: ' AZZ ', password: ' s3cret ' });
  });

  it.each([
    [401, SIGNIN_FAILED_BODY],
    [403, NO_GROUP_BODY],
    [423, LOCKED_BODY],
  ])('%i comes back in the server words, with its code', async (status, body) => {
    reply(SIGNIN, status, body);
    expect(await signIn('AZZ', 'wrong')).toEqual({ ok: false, status, code: body.code, message: body.message });
  });

  it('an unreachable server is one line, not an exception', async () => {
    failNextFetch();
    expect(await signIn('AZZ', 's3cret')).toEqual({
      ok: false,
      status: 0,
      code: 'NETWORK',
      message: MESSAGES.NETWORK,
    });
  });
});

describe('installAuthInterceptors - the client half of OD-97', () => {
  function freshClient() {
    const onUnauthorized = vi.fn();
    const fresh = createClient(createConfig({ baseUrl: BASE }));
    installAuthInterceptors(fresh, onUnauthorized);
    return { fresh, onUnauthorized };
  }

  it('a POST carries X-Azztec-Request: 1; a GET does not', async () => {
    reply(SIGNOUT, 200, { ok: true });
    reply(ME, 200, sessionFixture());
    const { fresh } = freshClient();
    await fresh.post({ url: SIGNOUT });
    await fresh.get({ url: ME });
    expect(requestAt(0).method).toBe('POST');
    expect(requestAt(0).headers.get(CSRF_HEADER)).toBe('1');
    expect(requestAt(1).method).toBe('GET');
    expect(requestAt(1).headers.get(CSRF_HEADER)).toBeNull();
  });

  it('a 401 from a page call means the session is gone: onUnauthorized, once', async () => {
    reply('/api/v1/workorders', 401, NO_IDENTITY);
    const { fresh, onUnauthorized } = freshClient();
    await fresh.get({ url: '/api/v1/workorders' });
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it('a 401 from sign-in or from the session probe is the sign-in flow talking: no call', async () => {
    reply(SIGNIN, 401, SIGNIN_FAILED_BODY);
    reply(ME, 401, NO_IDENTITY);
    const { fresh, onUnauthorized } = freshClient();
    await fresh.post({ url: SIGNIN, body: { login: 'AZZ', password: 'wrong' } });
    await fresh.get({ url: ME });
    expect(fetchStub).toHaveBeenCalledTimes(2);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it('a 200 and a 403 are not a lost session', async () => {
    reply('/api/v1/planner/range', 200, { ok: true });
    reply('/api/v1/workorders', 403, { ok: false, code: 'NO_RIGHT', message: 'no', rid: 'rid-403' });
    const { fresh, onUnauthorized } = freshClient();
    await fresh.get({ url: '/api/v1/planner/range' });
    await fresh.get({ url: '/api/v1/workorders' });
    expect(fetchStub).toHaveBeenCalledTimes(2);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});

describe('the cache: remember, forget, sign out', () => {
  it('rememberSession drops every cached page and stores the new session', async () => {
    const qc = newQueryClient();
    qc.setQueryData(['planner', 'range'], { rows: [1] });
    qc.setQueryData(['workorders', 662704], { sid: '3CL-260826-010' });
    qc.setQueryData(SESSION_KEY, null);
    await rememberSession(qc, sessionFixture());
    expect(qc.getQueryData(['planner', 'range'])).toBeUndefined();
    expect(qc.getQueryData(['workorders', 662704])).toBeUndefined();
    expect(qc.getQueryData(SESSION_KEY)).toEqual(sessionFixture());
    expect(fetchStub).not.toHaveBeenCalled();
  });

  it('forgetSession sets the session to null and touches nothing else', () => {
    const qc = seeded();
    forgetSession(qc);
    expect(qc.getQueryData(SESSION_KEY)).toBeNull();
    expect(qc.getQueryData(['planner', 'range'])).toEqual({ rows: [1] });
    expect(fetchStub).not.toHaveBeenCalled();
  });

  it('signOut posts /auth/signout, then forgets the person and drops their pages', async () => {
    reply(SIGNOUT, 200, { ok: true });
    const qc = seeded();
    await signOut(qc);
    expect(requestAt(0).method).toBe('POST');
    expect(pathAt(0)).toBe(SIGNOUT);
    expect(qc.getQueryData(SESSION_KEY)).toBeNull();
    expect(qc.getQueryData(['planner', 'range'])).toBeUndefined();
  });

  it('signOut still forgets when the server cannot be reached', async () => {
    failNextFetch();
    const qc = seeded();
    await signOut(qc);
    expect(fetchStub).toHaveBeenCalledTimes(1);
    expect(qc.getQueryData(SESSION_KEY)).toBeNull();
    expect(qc.getQueryData(['planner', 'range'])).toBeUndefined();
  });
});
