/**
 * Azztec_SaaS_web_routes_workorders_id_v1_0_0.tsx  ->  web/src/routes/workorders.$id.tsx
 * Version:  1.0.0   Date: 2026-09-20   Author: Adriaan
 * Spec:     Azztec_SaaS_W1b_WOMaint_Page_Chunk_Spec_v1_0_0.md §3.12 · OD-5, OD-29, OD-73
 *
 * The named route OD-5 promised the planner: /workorders/$id. The same view as /workorders with the
 * selection supplied, so a link to one work order reproduces the list it came from as well as the
 * record - which is the whole point of OD-29.
 *
 * Route exports only (Landmines §C); version in this header alone (Ways of Working §2).
 *
 * $id is a string from the URL. A non-numeric one becomes 0, which renders the list and the
 * "Select a work order" prompt rather than firing a request that can only 404 (the hook is disabled
 * at 0). No validation redirect: a bad id in a pasted link should show the page, not an error screen.
 *
 * Changelog:
 *   1.0.0  Initial W1b.
 */
import { createFileRoute } from '@tanstack/react-router';

import { WoMaintView, validateSearch } from '../features/workorders/WoMaintView';

export const Route = createFileRoute('/workorders/$id')({
  validateSearch,
  component: WorkorderRoute,
});

function WorkorderRoute() {
  const { id } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const parsed = Number.parseInt(id, 10);
  const woId = Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  return (
    <WoMaintView
      {...search}
      onSearch={(next) => void navigate({ search: (prev) => ({ ...prev, ...next }) })}
      onSelect={(next) =>
        void navigate({ to: '/workorders/$id', params: { id: String(next) }, search })
      }
      woId={woId}
    />
  );
}
