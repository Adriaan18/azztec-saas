/**
 * Azztec_SaaS_web_auth_SessionGate_v1_0_0.tsx  ->  web/src/features/auth/SessionGate.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-97
 *
 * The guard. routes/__root.tsx wraps every path but /signin in this; nothing inside it mounts - no page,
 * no page query - until the session is known.
 *   - a session          -> children(session)
 *   - null (a 401)       -> onSignedOut(next), where next is where the person was (path + search)
 *   - still asking       -> one quiet line
 *   - the server failed  -> the line and a Try again; a session already in hand is kept through a
 *                           failed re-check, so a blip on the network does not throw anyone out
 *
 * Props-driven and router-free (the PlannerView precedent): the root passes navigate as onSignedOut,
 * the test passes a spy. onSignedOut must be stable (useCallback) - it is an effect dependency, and a
 * new function every render would navigate every render.
 *
 * Changelog:
 *   1.0.0  Initial DP2b.
 */
import { useEffect } from 'react';
import type { ReactNode } from 'react';

import { MESSAGES, safeNext } from './rules';
import { useSession } from './session';
import type { SessionInfo } from '../../api/client';

import './auth.css';

export const VERSION = '1.0.0';

export type SessionGateProps = {
  /** where the person is - the router location's href (path + search) */
  href: string;
  /** called once with the safe ?next= when there is no session */
  onSignedOut: (next: string) => void;
  children: (session: SessionInfo) => ReactNode;
};

export function SessionGate({ href, onSignedOut, children }: SessionGateProps) {
  const query = useSession();
  const signedOut = query.isSuccess && query.data === null;
  const next = safeNext(href);

  useEffect(() => {
    if (signedOut) onSignedOut(next);
  }, [signedOut, next, onSignedOut]);

  if (query.data) return <>{children(query.data)}</>;
  if (query.isError) {
    return (
      <div className="wm-auth-wait" data-name="SessionError">
        <p>{MESSAGES.NETWORK}</p>
        <button onClick={() => void query.refetch()} type="button">
          Try again
        </button>
      </div>
    );
  }
  return (
    <div className="wm-auth-wait" data-name="SessionWait">
      <p>{MESSAGES.CHECKING}</p>
    </div>
  );
}
