/**
 * Azztec_SaaS_web_routes_root_v1_1_0.tsx  ->  web/src/routes/__root.tsx
 * Version:  1.1.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s3.7 . OD-50, OD-51;
 *           Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-97, OD-100
 *
 * Written against the CLI's file as pasted on 2026-09-16 (Block 2) - the first version of the root route
 * we own. Everything the CLI put here stays as it was: the router import, both devtools imports, the
 * global stylesheet import and its place, the devtools panel, the formatting (no semicolons). The one
 * change: the page renders inside the shell. ShellLayout reads the router's pathname (the shell lights
 * Plannex from it) and hands the shell the one navigation this build has - Plannex -> /planner with the
 * planner's own defaults (validateSearch({}) = month / today), which is what KT's BtnPlannex opens.
 *
 * A route file exports Route only (Landmines s.C), so the version lives in this header and nowhere else
 * (Ways of Working s2). validateSearch comes from PlannerView, which the route tree already pulls into
 * the main chunk through routes/planner.tsx; the smoke checks the planner chunk is still split (spec s4
 * trap 6). The global stylesheet is imported before the two feature modules so it enters the cascade
 * first - Tailwind v4's preflight is layered anyway; the CLI's three unlayered rules are not.
 *
 * 1.1.0 - the sign-in gate (DP2b):
 *   - /signin renders bare: no shell, no gate.
 *   - Every other path renders inside SessionGate. No session -> /signin?next=<path + search>; a
 *     session -> the shell, with the person's name, Sign out, and the page.
 *   - The page's right comes from the session (OD-100). NA -> NoAccess in the main cell instead of the
 *     page, so the page never mounts and never asks the API for what it would refuse. RO -> "view only"
 *     under the name. The pages themselves are unchanged: the Planner and WO Maint are read-only until
 *     DP3, which checks the right before it draws a move control.
 *   - Sign out goes through session.signOut; the gate then sees null and does the navigating.
 *   - onSignedOut is a useCallback: it is an effect dependency inside the gate.
 *
 * Changelog:
 *   1.1.0  DP2b: SessionGate around the shell, /signin outside it, name / view only / Sign out into
 *          AppShell, NoAccess for an NA page.
 *   1.0.0  S1k: ShellLayout wraps <Outlet /> in AppShell. Before this: CLI-generated, unversioned.
 */
import {
  Outlet,
  createRootRoute,
  useNavigate,
  useRouterState,
} from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'

import '../styles.css'

import { validateSearch } from '../features/planner/PlannerView'
import { AppShell } from '../features/shell/AppShell'
import { activeKeyFor } from '../features/shell/rules'
import { NoAccess } from '../features/auth/NoAccess'
import { SessionGate } from '../features/auth/SessionGate'
import { SIGNIN_PATH, pageAccess, pageForKey } from '../features/auth/rules'
import { signOut } from '../features/auth/session'
import type { SessionInfo } from '../api/client'

export const Route = createRootRoute({
  component: RootComponent,
})

/** The shell around every signed-in route: the pathname and the session in, Plannex and Sign out out. */
function ShellLayout({ session }: { session: SessionInfo }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const onPlannex = () => {
    void navigate({ to: '/planner', search: validateSearch({}) })
  }
  const activeKey = activeKeyFor(pathname)
  const access = pageAccess(session.rights, activeKey)
  const page = pageForKey(activeKey)
  return (
    <AppShell
      pathname={pathname}
      onPlannex={onPlannex}
      userName={session.user.name}
      viewOnly={access === 'RO'}
      onSignOut={() => void signOut(queryClient)}
    >
      {access === 'NA' && page !== null ? <NoAccess page={page} /> : <Outlet />}
    </AppShell>
  )
}

/** /signin bare; everything else behind the gate. */
function Body() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const href = useRouterState({ select: (s) => s.location.href })
  const navigate = useNavigate()
  const onSignedOut = useCallback(
    (next: string) => {
      void navigate({ to: '/signin', search: { next }, replace: true })
    },
    [navigate],
  )
  if (pathname === SIGNIN_PATH) return <Outlet />
  return (
    <SessionGate href={href} onSignedOut={onSignedOut}>
      {(session) => <ShellLayout session={session} />}
    </SessionGate>
  )
}

function RootComponent() {
  return (
    <>
      <Body />
      <TanStackDevtools
        config={{
          position: 'bottom-right',
        }}
        plugins={[
          {
            name: 'TanStack Router',
            render: <TanStackRouterDevtoolsPanel />,
          },
        ]}
      />
    </>
  )
}
