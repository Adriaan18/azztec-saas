/**
 * Azztec_SaaS_web_auth_rules_test_v1_0_0.ts  ->  web/src/features/auth/rules.test.ts
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . pair of rules.ts 1.0.0
 *
 * Pure: plain values in, plain values out - no DOM, no fetch. The refusal bodies are the ones DP2a's
 * smoke returned (session.fixture.ts), so the message line is tested against the server's real words.
 *
 * Changelog:
 *   1.0.0  Initial DP2b. 34 cases (17 of them the safeNext refusals, one per row).
 */
import { describe, expect, it } from 'vitest';

import {
  CSRF_HEADER,
  LANDING,
  MESSAGES,
  PAGE_LABEL,
  RANK,
  SIGNIN_PATH,
  VERSION,
  allows,
  isAuthCall,
  landingFor,
  needsCsrf,
  pageAccess,
  pageForKey,
  safeNext,
  signInFailure,
} from './rules';
import { LOCKED_BODY, NO_GROUP_BODY, SIGNIN_FAILED_BODY } from './session.fixture';
import type { PageRights } from '../../api/client';

export const TEST_VERSION = '1.0.0';

describe('version', () => {
  it('rules.ts is 1.0.0', () => {
    expect(VERSION).toBe('1.0.0');
  });
});

describe('page rights (OD-100)', () => {
  it('the ladder is NA < RO < RW < RWD, and allows reads it', () => {
    expect([RANK.NA, RANK.RO, RANK.RW, RANK.RWD]).toEqual([0, 1, 2, 3]);
    expect(allows('RWD', 'RW')).toBe(true);
    expect(allows('RW', 'RW')).toBe(true);
    expect(allows('RO', 'RW')).toBe(false);
    expect(allows('RO', 'RO')).toBe(true);
    expect(allows('NA', 'RO')).toBe(false);
  });

  it('pageForKey: the two shell keys that carry a right, and nothing else', () => {
    expect(pageForKey('plannex')).toBe('planner');
    expect(pageForKey('womaint')).toBe('womaint');
    expect(pageForKey('')).toBeNull();
    expect(pageForKey('pmx')).toBeNull();
  });

  it('pageAccess: the right on the page under the key; null where no right applies', () => {
    const rights: PageRights = { planner: 'RO', womaint: 'NA' };
    expect(pageAccess(rights, 'plannex')).toBe('RO');
    expect(pageAccess(rights, 'womaint')).toBe('NA');
    expect(pageAccess(rights, '')).toBeNull();
    expect(PAGE_LABEL).toEqual({ planner: 'the Planner', womaint: 'WO Maint' });
  });
});

describe('safeNext - ?next= stays a path on this site', () => {
  it('keeps a path with its search and hash, trimmed', () => {
    expect(safeNext('/planner')).toBe('/planner');
    expect(safeNext('/planner?mode=month&anchor=2026-11-07')).toBe('/planner?mode=month&anchor=2026-11-07');
    expect(safeNext('/workorders/662704?woType=M#top')).toBe('/workorders/662704?woType=M#top');
    expect(safeNext('  /planner  ')).toBe('/planner');
    expect(safeNext('/')).toBe('/');
  });

  it.each([
    ['undefined', undefined],
    ['null', null],
    ['a number', 42],
    ['an object', { next: '/planner' }],
    ['the empty string', ''],
    ['no leading slash', 'planner'],
    ['an absolute URL', 'https://evil.example/planner'],
    ['a protocol-relative URL', '//evil.example/planner'],
    ['a backslash', '/\\evil.example'],
    ['a tab', '/\t/evil.example'],
    ['a newline', '/\n/evil.example'],
    ['DEL', '/plan\u007fner'],
    ['the sign-in page', '/signin'],
    ['the sign-in page with its own next', '/signin?next=%2Fplanner'],
    ['the sign-in page with a hash', '/signin#x'],
    ['under the sign-in page', '/signin/again'],
    ['the sign-in page in capitals', '/SignIn'],
  ])('refuses %s', (_label, raw) => {
    expect(safeNext(raw)).toBe('');
  });

  it('a path that only starts like the sign-in page is a path', () => {
    expect(safeNext('/signing')).toBe('/signing');
  });
});

describe('landingFor', () => {
  it("'' and '/' land on the Planner; anything safeNext let through is used as it is", () => {
    expect(SIGNIN_PATH).toBe('/signin');
    expect(LANDING).toBe('/planner');
    expect(landingFor('')).toBe('/planner');
    expect(landingFor('/')).toBe('/planner');
    expect(landingFor('/workorders/662704')).toBe('/workorders/662704');
  });
});

describe('signInFailure - the one message line (OD-98)', () => {
  it('401: the server words - one sentence for an unknown login and a wrong password (trap 6)', () => {
    expect(signInFailure(401, SIGNIN_FAILED_BODY)).toEqual({
      code: 'SIGNIN_FAILED',
      message: 'Sign-in failed. Check your user name and password.',
    });
  });

  it('403: a refusal reason in the server words, with its code', () => {
    expect(signInFailure(403, NO_GROUP_BODY)).toEqual({ code: 'NO_GROUP', message: NO_GROUP_BODY.message });
  });

  it('423: the lock, in the server words', () => {
    expect(signInFailure(423, LOCKED_BODY)).toEqual({ code: 'LOCKED', message: LOCKED_BODY.message });
  });

  it('403 CSRF is the page, not the person: reload', () => {
    const body = { ok: false, code: 'CSRF', message: 'X-Azztec-Request header missing', rid: 'rid-csrf' };
    expect(signInFailure(403, body)).toEqual({ code: 'CSRF', message: MESSAGES.CSRF });
  });

  it('422 is an empty field', () => {
    expect(signInFailure(422, { detail: [] })).toEqual({ code: 'MISSING', message: MESSAGES.MISSING });
  });

  it('a 401 with no body: a code from the status and the plain line', () => {
    expect(signInFailure(401, null)).toEqual({
      code: 'HTTP_401',
      message: "Sign-in didn't work (HTTP 401). Try again.",
    });
  });

  it('anything else names the status, and the rid when there is one', () => {
    expect(signInFailure(500, { ok: false, code: 'INTERNAL', message: 'boom', rid: 'abc123' })).toEqual({
      code: 'INTERNAL',
      message:
        "Sign-in didn't work (HTTP 500). Try again. If it keeps happening, give your administrator this ref: abc123.",
    });
    expect(signInFailure(502, undefined)).toEqual({
      code: 'HTTP_502',
      message: "Sign-in didn't work (HTTP 502). Try again.",
    });
    expect(signInFailure(502, 'Bad Gateway')).toEqual({
      code: 'HTTP_502',
      message: "Sign-in didn't work (HTTP 502). Try again.",
    });
  });
});

describe('the CSRF header and the 401 watch (OD-97)', () => {
  it('every method that can change something carries the header; reads do not', () => {
    expect(CSRF_HEADER).toBe('X-Azztec-Request');
    for (const m of ['POST', 'PUT', 'PATCH', 'DELETE', 'post']) expect(needsCsrf(m), m).toBe(true);
    for (const m of ['GET', 'HEAD', 'OPTIONS', 'get']) expect(needsCsrf(m), m).toBe(false);
  });

  it('a 401 from sign-in or the session probe is the sign-in flow talking; any other path is a lost session', () => {
    expect(isAuthCall('/api/v1/auth/signin')).toBe(true);
    expect(isAuthCall('/api/v1/auth/me')).toBe(true);
    expect(isAuthCall('/api/v1/auth/signout')).toBe(false);
    expect(isAuthCall('/api/v1/planner/range')).toBe(false);
    expect(isAuthCall('/api/v1/workorders/662704')).toBe(false);
  });

  it('the four lines the page words itself', () => {
    expect(MESSAGES).toEqual({
      MISSING: 'Enter your user name and password.',
      NETWORK: "Can't reach the Azztec server. Check the connection, then try again.",
      CSRF: 'This page is out of date. Reload it, then sign in again.',
      CHECKING: 'Checking your sign-in...',
    });
  });
});
