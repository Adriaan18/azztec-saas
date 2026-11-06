/**
 * Azztec_SaaS_web_routes_signin_v1_0_0.tsx  ->  web/src/routes/signin.tsx
 * Version:  1.0.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6
 *
 * The URL binding for the sign-in page, and nothing else - SignInPage is props-driven and carries the
 * test. routes/__root.tsx renders this route bare, outside the shell and outside the gate.
 *
 * ?next= is where the gate found the person; safeNext keeps it a path on this site. One navigation
 * path: a session in the cache - already there when the page opens, or just put there by
 * rememberSession - sends the person to landingFor(next). history.replace takes the whole path + search
 * as one string and keeps /signin out of the Back button.
 *
 * Route exports only (Landmines s.C); version in this header alone (Ways of Working s2).
 *
 * Changelog:
 *   1.0.0  Initial DP2b.
 */
import { useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useRouter } from '@tanstack/react-router';
import { useEffect } from 'react';

import { SignInPage } from '../features/auth/SignInPage';
import { landingFor, safeNext } from '../features/auth/rules';
import { rememberSession, useSession } from '../features/auth/session';

export const Route = createFileRoute('/signin')({
  validateSearch: (search: Record<string, unknown>) => ({ next: safeNext(search.next) }),
  component: SignInRoute,
});

function SignInRoute() {
  const { next } = Route.useSearch();
  const router = useRouter();
  const queryClient = useQueryClient();
  const session = useSession();
  const signedIn = Boolean(session.data);
  const target = landingFor(next);

  useEffect(() => {
    if (signedIn) router.history.replace(target);
  }, [signedIn, target, router]);

  return <SignInPage onSignedIn={(s) => void rememberSession(queryClient, s)} />;
}
