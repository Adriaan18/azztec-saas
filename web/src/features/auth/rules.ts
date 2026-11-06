/**
 * Azztec_SaaS_web_auth_rules_v1_0_0.ts  ->  web/src/features/auth/rules.ts
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-97, OD-98, OD-100
 *
 * Pure: no React, no fetch, no Date. The sign-in page's message line, the page rights the shell reads,
 * where a sign-in lands, and which requests carry the CSRF header - each a function the test calls with
 * plain values.
 *
 * The server owns the wording of every refusal (OD-98): a 401, 403 or 423 body's message goes on the
 * page exactly as it came, so "no such login" and "wrong password" stay one sentence (trap 6). The page
 * words only what the server cannot say: an empty form, a server it cannot reach, a stale page (CSRF),
 * and anything unexpected - which carries the request id, so a person has something to read out to
 * support (D1 audit gap 6).
 *
 * Changelog:
 *   1.0.0  Initial DP2b.
 */
import type { PageRights } from '../../api/client';

export const VERSION = '1.0.0';

export type Right = PageRights['planner'];
export type Page = keyof PageRights;

/** NA < RO < RW < RWD - the ladder the backend's deps.RANK uses (OD-100) */
export const RANK: Readonly<Record<Right, number>> = { NA: 0, RO: 1, RW: 2, RWD: 3 };

export function allows(have: Right, need: Right): boolean {
  return RANK[have] >= RANK[need];
}

/** the shell's active key (shell/rules.activeKeyFor) -> the page whose right governs it */
export function pageForKey(activeKey: string): Page | null {
  if (activeKey === 'plannex') return 'planner';
  if (activeKey === 'womaint') return 'womaint';
  return null;
}

/** the person's right on the page under that key, or null where no page right applies */
export function pageAccess(rights: PageRights, activeKey: string): Right | null {
  const page = pageForKey(activeKey);
  return page === null ? null : rights[page];
}

export const PAGE_LABEL: Readonly<Record<Page, string>> = { planner: 'the Planner', womaint: 'WO Maint' };

export const SIGNIN_PATH = '/signin';
/** where a sign-in with nowhere to go back to lands - '/' is still the CLI's placeholder page */
export const LANDING = '/planner';

/**
 * The ?next= a sign-in returns to: a path on this site, or ''. One leading slash, never two (a
 * protocol-relative URL names another host), no backslash (browsers read it as a slash), no control
 * character (the URL parser drops tabs and newlines, which could join two slashes), and never the
 * sign-in page itself, in any letter case (the router matches paths case-insensitively).
 */
export function safeNext(raw: unknown): string {
  if (typeof raw !== 'string') return '';
  const next = raw.trim();
  if (!next.startsWith('/') || next.startsWith('//') || next.includes('\\')) return '';
  for (let i = 0; i < next.length; i += 1) {
    const c = next.charCodeAt(i);
    if (c < 0x20 || c === 0x7f) return '';
  }
  const path = next.replace(/[?#].*$/, '').toLowerCase();
  if (path === SIGNIN_PATH || path.startsWith(`${SIGNIN_PATH}/`)) return '';
  return next;
}

/** '' and '/' land on the Planner; anything safeNext let through is used as it is */
export function landingFor(next: string): string {
  return next === '' || next === '/' ? LANDING : next;
}

export const MESSAGES = {
  MISSING: 'Enter your user name and password.',
  NETWORK: "Can't reach the Azztec server. Check the connection, then try again.",
  CSRF: 'This page is out of date. Reload it, then sign in again.',
  CHECKING: 'Checking your sign-in...',
} as const;

export type Failure = { code: string; message: string };

function field(body: unknown, key: string): string {
  if (typeof body !== 'object' || body === null) return '';
  const value = (body as Record<string, unknown>)[key];
  return typeof value === 'string' ? value : '';
}

/**
 * The message line for a sign-in that did not return a session. 401 / 403 / 423 carry the server's own
 * words (the generic failure, an OD-98 reason, the lock); a 403 CSRF is the page's fault, not the
 * person's; 422 is an empty field; anything else names its status and, when there is one, the rid.
 */
export function signInFailure(status: number, body: unknown): Failure {
  const code = field(body, 'code');
  const message = field(body, 'message');
  if (status === 403 && code === 'CSRF') return { code, message: MESSAGES.CSRF };
  if ((status === 401 || status === 403 || status === 423) && message !== '') {
    return { code: code === '' ? `HTTP_${status}` : code, message };
  }
  if (status === 422) return { code: 'MISSING', message: MESSAGES.MISSING };
  const rid = field(body, 'rid');
  const ref = rid === '' ? '' : ` If it keeps happening, give your administrator this ref: ${rid}.`;
  return {
    code: code === '' ? `HTTP_${status}` : code,
    message: `Sign-in didn't work (HTTP ${status}). Try again.${ref}`,
  };
}

/** OD-97. Sent on every request that can change something; reads do not need it. */
export const CSRF_HEADER = 'X-Azztec-Request';

export function needsCsrf(method: string): boolean {
  const m = method.toUpperCase();
  return m !== 'GET' && m !== 'HEAD' && m !== 'OPTIONS';
}

/**
 * A 401 from these is the sign-in flow talking, not a session that ended: a wrong password on
 * /auth/signin, and the gate's own probe on /auth/me. Any other 401 means the session is gone.
 */
export function isAuthCall(pathname: string): boolean {
  return pathname === '/api/v1/auth/signin' || pathname === '/api/v1/auth/me';
}
