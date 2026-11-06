/**
 * Azztec_SaaS_web_auth_session_v1_0_0.ts  ->  web/src/features/auth/session.ts
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-97, OD-98
 * Consumes: src/api/client (generated 2026-11-07 from docs/api/openapi_0_6_0.json, openapi-ts 0.99):
 *           meApiV1AuthMeGet, signInApiV1AuthSigninPost, signOutApiV1AuthSignoutPost, SessionInfo.
 *
 * The session lives in the query cache under one key: SessionInfo when signed in, null when not.
 * Everything that changes it goes through four functions, so the cache and the cookie never disagree
 * for long:
 *   - rememberSession  after a sign-in: every cached page goes, the new session goes in
 *   - forgetSession    after a 401 from anything but the sign-in flow: the session becomes null
 *   - signOut          the API call, then null, then every cached page goes
 *   - the gate (SessionGate.tsx) turns null into /signin?next=<where the person was>
 * Clearing the pages matters at a shared PC: the next person must not see the last one's data.
 *
 * The calls go through the generated SDK with throwOnError false, so a refusal comes back as a body and
 * a status, not an exception. The password goes out exactly as typed - never trimmed (trap 1).
 *
 * A fetch that fails outright (server down, network gone) reaches here one of two ways, depending on the
 * openapi-ts client: thrown, or returned with response undefined. statusOf reads the second as status 0
 * and the try / catch takes the first, so both give the same answer.
 *
 * installAuthInterceptors is the client half of OD-97: X-Azztec-Request on every method that can change
 * something, and the 401 watch. main.tsx installs it once on the app's client; the test installs it on
 * a client of its own.
 *
 * Changelog:
 *   1.0.0  Initial DP2b.
 */
import { queryOptions, useQuery } from '@tanstack/react-query';
import type { QueryClient } from '@tanstack/react-query';

import { meApiV1AuthMeGet, signInApiV1AuthSigninPost, signOutApiV1AuthSignoutPost } from '../../api/client/sdk.gen';
import type { SessionInfo } from '../../api/client';
import type { Client } from '../../api/client/client';
import { CSRF_HEADER, MESSAGES, isAuthCall, needsCsrf, signInFailure } from './rules';

export const VERSION = '1.0.0';

export const SESSION_KEY = ['auth', 'session'] as const;
/** the backend re-reads rights every 60 s (rights_cache_seconds); the page asks no more often */
export const SESSION_STALE_MS = 60_000;

/** the HTTP status, or 0 when fetch failed and the client returned no response at all */
function statusOf(response: Response | undefined): number {
  return response ? response.status : 0;
}

/** GET /auth/me: the session, or null on a 401. Any other failure throws - the gate says so. */
export async function fetchSession(): Promise<SessionInfo | null> {
  const r = await meApiV1AuthMeGet();
  if (r.data) return r.data;
  const status = statusOf(r.response);
  if (status === 401) return null;
  throw new Error(status === 0 ? 'session check failed: no response' : `session check failed: HTTP ${status}`);
}

export function sessionQueryOptions() {
  return queryOptions({
    queryKey: SESSION_KEY,
    queryFn: fetchSession,
    staleTime: SESSION_STALE_MS,
    retry: false,
  });
}

export function useSession() {
  return useQuery(sessionQueryOptions());
}

function isSessionQuery(queryKey: ReadonlyArray<unknown>): boolean {
  return queryKey[0] === SESSION_KEY[0] && queryKey[1] === SESSION_KEY[1];
}

/** A new session replaces every page cached under the old one - a different person may be signing in. */
export async function rememberSession(queryClient: QueryClient, session: SessionInfo): Promise<void> {
  await queryClient.cancelQueries({ queryKey: SESSION_KEY });
  queryClient.removeQueries({ predicate: (q) => !isSessionQuery(q.queryKey) });
  queryClient.setQueryData(sessionQueryOptions().queryKey, session);
}

/** The 401 path. The gate sees null and sends the person to /signin?next=<where they were>. */
export function forgetSession(queryClient: QueryClient): void {
  queryClient.setQueryData(sessionQueryOptions().queryKey, null);
}

/**
 * POST /auth/signout, then forget. A failed call still forgets - the cookie may already have expired,
 * or the server may be down, and the person asked to leave either way. Null goes in first, so the gate
 * unmounts the page before the page's queries are removed underneath it.
 */
export async function signOut(queryClient: QueryClient): Promise<void> {
  try {
    await signOutApiV1AuthSignoutPost();
  } catch {
    // unreachable server: the page still forgets the person
  }
  forgetSession(queryClient);
  queryClient.removeQueries({ predicate: (q) => !isSessionQuery(q.queryKey) });
}

export type SignInResult =
  | { ok: true; session: SessionInfo }
  | { ok: false; status: number; code: string; message: string };

function networkFailure(): SignInResult {
  return { ok: false, status: 0, code: 'NETWORK', message: MESSAGES.NETWORK };
}

/** POST /auth/signin. A session, or the one line the page shows - never an exception. */
export async function signIn(login: string, password: string): Promise<SignInResult> {
  try {
    const r = await signInApiV1AuthSigninPost({ body: { login, password } });
    if (r.data) return { ok: true, session: r.data };
    const status = statusOf(r.response);
    if (status === 0) return networkFailure();
    return { ok: false, status, ...signInFailure(status, r.error) };
  } catch {
    return networkFailure();
  }
}

export function installAuthInterceptors(client: Client, onUnauthorized: () => void): void {
  client.interceptors.request.use((request) => {
    if (needsCsrf(request.method)) request.headers.set(CSRF_HEADER, '1');
    return request;
  });
  client.interceptors.response.use((response, request) => {
    if (response.status === 401 && !isAuthCall(new URL(request.url).pathname)) onUnauthorized();
    return response;
  });
}
