/**
 * Azztec_SaaS_web_routes_workorders_index_v1_0_0.tsx  ->  web/src/routes/workorders.index.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.12 · OD-5, OD-29, OD-73
 * Replaces: web/src/routes/workorders.tsx (deleted in the same drop - see below)
 *
 * WHY THE RENAME. As `workorders.tsx`, this file was not a sibling of `workorders.$id.tsx` - it was
 * its PARENT. TanStack's file-based routing reads `workorders.tsx` + `workorders.$id.tsx` as a layout
 * with a child, so navigating to /workorders/662396 matched the child, mounted this component as the
 * layout, and rendered nothing else because a layout without <Outlet/> shows no child. The screen
 * therefore sat on "Select a work order from the list." with the id right there in the URL, and no
 * record request ever went out - which is exactly what the 2026-09-20 smoke saw.
 *
 * `workorders.index.tsx` is a LEAF at /workorders. With no `workorders.route.tsx` beside it, the
 * router generates a pathless parent that renders an Outlet, and /workorders and /workorders/$id
 * become siblings - two leaves, each rendering the whole page, which is what §3.12 described.
 * An index route's id carries the trailing slash: createFileRoute('/workorders/').
 *
 * Route exports only (Landmines §C); version in this header alone (Ways of Working §2).
 *
 * Changelog:
 *   1.0.0  Initial W1b (renamed from routes/workorders.tsx 1.0.0 before the tag).
 */
import { createFileRoute } from '@tanstack/react-router';

import { WoMaintView, validateSearch } from '../features/workorders/WoMaintView';

export const Route = createFileRoute('/workorders/')({
  validateSearch,
  component: WorkordersIndexRoute,
});

function WorkordersIndexRoute() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <WoMaintView
      {...search}
      onSearch={(next) => void navigate({ search: (prev) => ({ ...prev, ...next }) })}
      onSelect={(woId) =>
        void navigate({ to: '/workorders/$id', params: { id: String(woId) }, search })
      }
      woId={0}
    />
  );
}
