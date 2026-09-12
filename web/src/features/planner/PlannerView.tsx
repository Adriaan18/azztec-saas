/**
 * Azztec_SaaS_web_planner_PlannerView_v1_0_0.tsx  ->  web/src/features/planner/PlannerView.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md 5.11 . OD-6, OD-23, OD-26, OD-29
 *
 * The whole read-only planner as a props-driven component: mode and anchor in, an onSearch callback
 * out. routes/planner.tsx is the thin wrapper that binds those two to the URL.
 *
 * Split this way on purpose (spec 6, the route-test contingency taken up front): the view can be
 * rendered and its wire asserted without a router, a route tree or a memory history, so the test
 * proves what it claims - that mode+anchor produce exactly one request for the derived window.
 *
 * validateSearch lives here too, next to the types it guards. OD-29: a bad anchor falls back to today
 * rather than fetching something silly, and from/to never appear in the URL - windowFor derives them,
 * which is what keeps every request inside the 42-day cap.
 *
 * The banner reports the client-side window verdict first and the query error second: a refused window
 * never fetched, so a network message there would be a lie.
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { useMemo } from 'react';

import { PlannerGrid } from './PlannerGrid';
import { PlannerHeader } from './PlannerHeader';
import { WorkerPanel } from './WorkerPanel';
import { indexWorkers, monthKey, visibleWos } from './rules';
import { usePlannerStore } from './store';
import { usePlannerRange } from './usePlannerRange';
import { MODES, isIso, isMode, navAnchor, todayIso, windowFor } from '../../lib/dates';
import type { Mode } from '../../lib/dates';

import './planner.css';

export const VERSION = '1.0.0';

export type PlannerSearch = { mode: Mode; anchor: string };

/** OD-29. Plain guards, no zod adapter: two params, two shapes, both already tested in dates.test.ts. */
export function validateSearch(search: Record<string, unknown>): PlannerSearch {
  return {
    mode: isMode(search.mode) ? search.mode : 'month',
    anchor: isIso(search.anchor) ? search.anchor : todayIso(),
  };
}

export type PlannerViewProps = PlannerSearch & {
  /** the URL writer; the route passes navigate(), the test passes a spy */
  onSearch: (next: Partial<PlannerSearch>) => void;
};

export function PlannerView({ mode, anchor, onSearch }: PlannerViewProps) {
  const store = usePlannerStore();

  const window = useMemo(() => windowFor(mode, anchor), [mode, anchor]);
  const { query, window: check } = usePlannerRange(window.from, window.to);
  const data = query.data;

  const byId = useMemo(() => indexWorkers(data?.workers ?? []), [data]);
  const wos = useMemo(() => visibleWos(data?.wos ?? [], store.cats), [data, store.cats]);

  const today = data?.today ?? todayIso();
  const message = !check.ok ? check.message : query.error ? String(query.error) : '';

  return (
    <div className="wm-planner">
      <PlannerHeader
        mode={mode}
        anchor={anchor}
        window={window}
        counts={data?.counts ?? null}
        cats={store.cats}
        railOpen={store.railOpen}
        onMode={(m) => onSearch({ mode: m })}
        onNav={(n) => onSearch({ anchor: navAnchor(mode, anchor, n) })}
        onToday={() => onSearch({ anchor: todayIso() })}
        onCat={store.toggleCat}
        onAllCats={() => {
          store.setAllCats(!(store.cats.WO && store.cats.PM && store.cats.REQ && store.cats.DONE));
        }}
        onRail={store.toggleRail}
      />

      <div className={message ? 'banner on' : 'banner'}>
        <b>{check.ok ? 'request failed' : 'window refused'}</b>
        <span>{message}</span>
      </div>

      <div className="body">
        <div className="grid-wrap">
          <PlannerGrid
            mode={mode}
            window={window}
            wos={wos}
            today={today}
            anchorMonth={monthKey(anchor)}
            workers={data?.workers ?? []}
            byId={byId}
            selected={store.selected}
            onSelect={store.select}
          />
          <div className={!data && query.isFetching ? 'loading on' : 'loading'}>LOADING</div>
        </div>
        <div className={store.railOpen ? 'rail' : 'rail hide'}>
          <WorkerPanel
            workers={data?.workers ?? []}
            load={data?.load ?? {}}
            workerWeeks={data?.workerWeeks ?? {}}
            days={window.days}
            opts={{ contractors: store.contractors, loadedOnly: store.loadedOnly }}
            onToggleContractors={store.toggleContractors}
            onToggleLoadedOnly={store.toggleLoadedOnly}
          />
        </div>
      </div>

      <div className="foot">
        <span>
          Planner UI {VERSION} {'\u00b7'} {MODES.length} modes {'\u00b7'} window {window.days} d
        </span>
        <span className="sp" />
        <span>
          {data ? `lib ${data.libVersion} \u00b7 api ${data.apiVersion} \u00b7 range ${data.ms} ms` : ''}
          {data && query.isFetching ? ' \u00b7 refreshing...' : ''}
        </span>
      </div>
    </div>
  );
}

export default PlannerView;
