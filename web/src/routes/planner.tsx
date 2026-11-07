/**
 * Azztec_SaaS_web_routes_planner_v1_1_0.tsx  ->  web/src/routes/planner.tsx
 * Version:  1.1.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md 5.11 . OD-29;
 *           Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (routes/planner.tsx row) . OD-107
 *
 * The URL binding, and nothing else. Everything drawn lives in features/planner/PlannerView.tsx, which
 * is why this file has no test of its own - the view's test covers validateSearch and the wire, and
 * what is left here is three lines of router API.
 *
 * mode and anchor are the only search params (OD-29). The setter merges, so changing the mode keeps
 * the anchor and the link stays shareable.
 *
 * 1.1.0: the session decides whether the planner moves (OD-107) - canMove is the planner right at RW
 * or better, actorId the person whose undo stack it is. The SessionGate above every route has already
 * loaded the session, so both are settled by the time this renders. The API is the gate; this is the
 * courtesy that keeps a read-only person from being offered a drag the server would refuse.
 *
 * A route file exports Route and nothing else: the router plugin code-splits on that shape, and any
 * other export is pulled into the main bundle (it warned eleven times about the default export in
 * 1.0.0). PlannerRoute stays a local function.
 *
 * Changelog:
 *   1.1.0  DP3b: canMove = allows(rights.planner, 'RW') and actorId = user.userId from useSession().
 *   1.0.1  Dropped the default export and the VERSION const - both defeat code-splitting (smoke).
 *   1.0.0  Initial S1f.
 */
import { createFileRoute } from '@tanstack/react-router';

import { allows } from '../features/auth/rules';
import { useSession } from '../features/auth/session';
import { PlannerView, validateSearch } from '../features/planner/PlannerView';

export const Route = createFileRoute('/planner')({
  validateSearch,
  component: PlannerRoute,
});

function PlannerRoute() {
  const { mode, anchor } = Route.useSearch();
  const navigate = Route.useNavigate();
  const session = useSession().data;
  return (
    <PlannerView
      mode={mode}
      anchor={anchor}
      canMove={!!session && allows(session.rights.planner, 'RW')}
      actorId={session ? session.user.userId : 0}
      onSearch={(next) => void navigate({ search: (prev) => ({ ...prev, ...next }) })}
    />
  );
}
