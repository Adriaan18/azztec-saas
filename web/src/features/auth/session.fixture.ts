/**
 * Azztec_SaaS_web_auth_session_fixture_v1_0_0.ts  ->  web/src/features/auth/session.fixture.ts
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6
 *
 * Test data only. One /auth/me body shaped as DP2a's smoke returned it for the administrator (user 21,
 * RWD on both pages), and the three flat error bodies the sign-in page shows - their messages copied
 * from that smoke's output (2026-11-07), so a wording change on the server shows up here.
 *
 * Changelog:
 *   1.0.0  Initial DP2b.
 */
import type { SessionInfo } from '../../api/client';

export const VERSION = '1.0.0';

export function sessionFixture(over: Partial<SessionInfo> = {}): SessionInfo {
  return {
    ok: true,
    user: { userId: 21, shortId: 'AZZ', name: 'Azzmax logon' },
    rights: { planner: 'RWD', womaint: 'RWD' },
    isAdmin: true,
    expiresAt: '2026-11-07T15:18:34Z',
    ...over,
  };
}

export const SIGNIN_FAILED_BODY = {
  ok: false,
  code: 'SIGNIN_FAILED',
  message: 'Sign-in failed. Check your user name and password.',
  rid: 'rid-401',
};

export const NO_GROUP_BODY = {
  ok: false,
  code: 'NO_GROUP',
  message: "Your Workmate account isn't in a security group yet. Ask your Workmate administrator to add you.",
  rid: 'rid-403',
};

export const LOCKED_BODY = {
  ok: false,
  code: 'LOCKED',
  message: 'Too many failed sign-ins. Wait 15 minutes, then try again.',
  rid: 'rid-423',
};
