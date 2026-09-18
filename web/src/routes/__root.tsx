/**
 * Azztec_SaaS_web_routes_root_v1_0_0.tsx  ->  web/src/routes/__root.tsx
 * Version:  1.0.0   Date: 2026-09-16   Author: Adriaan
 * Spec:     Azztec_SaaS_S1k_Shell_Chunk_Spec_v1_0_1.md s3.7 . OD-50, OD-51
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
 * Changelog:
 *   1.0.0  S1k: ShellLayout wraps <Outlet /> in AppShell. Before this: CLI-generated, unversioned.
 */
import {
  Outlet,
  createRootRoute,
  useNavigate,
  useRouterState,
} from '@tanstack/react-router'

import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'

import '../styles.css'

import { validateSearch } from '../features/planner/PlannerView'
import { AppShell } from '../features/shell/AppShell'

export const Route = createRootRoute({
  component: RootComponent,
})

/** The shell around every route: the router's pathname in, the Plannex navigation out (OD-51). */
function ShellLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const navigate = useNavigate()
  const onPlannex = () => {
    void navigate({ to: '/planner', search: validateSearch({}) })
  }
  return (
    <AppShell pathname={pathname} onPlannex={onPlannex}>
      <Outlet />
    </AppShell>
  )
}

function RootComponent() {
  return (
    <>
      <ShellLayout />
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
