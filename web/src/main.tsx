/**
 * Azztec_SaaS_web_main_v1_1_0.tsx  ->  web/src/main.tsx
 * Version:  1.1.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.12;
 *           Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s6 . OD-97
 * Base:     the file @tanstack/cli 0.71.0 wrote (read on the box 2026-09-12), unchanged except the
 *           QueryClientProvider and the Query devtools panel.
 *
 * S1e's tests brought their own QueryClientProvider, so the app never needed one until now. The
 * planner route is the first consumer, hence the provider lands here rather than in the route.
 *
 * The CLI also wrote src/router.tsx with a getRouter() factory; main.tsx does not import it and never
 * has. It is left in place, unused, rather than deleted mid-slice - noted in the raw log.
 *
 * 1.1.0: the generated client gets the two sign-in interceptors before the first render - the
 * X-Azztec-Request header on every POST, and a 401 from anything but the sign-in flow forgetting the
 * session, which the gate in routes/__root.tsx turns into /signin?next=<where the person was>. The
 * client is the one the SDK functions default to, so every page call is covered without touching a page.
 *
 * Changelog:
 *   1.1.0  DP2b: installAuthInterceptors(client, ...). Nothing else moved.
 *   1.0.0  Initial S1f. The CLI base is not versioned; this is version 1 of the file as we own it.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'
import { client } from './api/client/client.gen'
import { forgetSession, installAuthInterceptors } from './features/auth/session'

const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
  scrollRestoration: true,
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

/** One client for the app. The planner's own cap, staleTime and 60 s poll live in usePlannerRange. */
const queryClient = new QueryClient()

/** DP2b: the CSRF header on writes; a 401 anywhere but sign-in forgets the session - the gate does the rest. */
installAuthInterceptors(client, () => forgetSession(queryClient))

const rootElement = document.getElementById('app')!

if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  root.render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>,
  )
}
