/**
 * Azztec_SaaS_web_main_v1_0_0.tsx  ->  web/src/main.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.12
 * Base:     the file @tanstack/cli 0.71.0 wrote (read on the box 2026-09-12), unchanged except the
 *           QueryClientProvider and the Query devtools panel.
 *
 * S1e's tests brought their own QueryClientProvider, so the app never needed one until now. The
 * planner route is the first consumer, hence the provider lands here rather than in the route.
 *
 * The CLI also wrote src/router.tsx with a getRouter() factory; main.tsx does not import it and never
 * has. It is left in place, unused, rather than deleted mid-slice - noted in the raw log.
 *
 * Changelog:
 *   1.0.0  Initial S1f. The CLI base is not versioned; this is version 1 of the file as we own it.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'

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
