/**
 * Azztec_SaaS_web_planner_PlannerView_v1_1_0.tsx  ->  web/src/features/planner/PlannerView.tsx
 * Version:  1.1.0   Date: 2026-09-13   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md 5.11 . OD-6, OD-23, OD-26, OD-29;
 *           Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md 5.12 . OD-30, OD-33, OD-34
 * Oracle:   Planner_v1_8_1.html render 860-866, select 869, nav 871-876, keyboard 1582-1596
 *
 * The whole read-only planner as a props-driven component: mode and anchor in, an onSearch callback
 * out. routes/planner.tsx is the thin wrapper that binds those two to the URL.
 *
 * Split this way on purpose (spec 6, the route-test contingency taken up front): the view can be
 * rendered and its wire asserted without a router, a route tree or a memory history, so the test
 * proves what it claims - that mode+anchor produce exactly one request for the derived window, and
 * (1.1.0) that a superseded request is aborted in the browser when the window changes (OD-30).
 *
 * validateSearch lives here too, next to the types it guards. OD-29: a bad anchor falls back to today
 * rather than fetching something silly, and from/to never appear in the URL - windowFor derives them,
 * which is what keeps every request inside the 42-day cap.
 *
 * The banner reports the client-side window verdict first and the query error second: a refused window
 * never fetched, so a network message there would be a lie.
 *
 * 1.1.0 composes the rest of read-only: the filters row under the header (oracle 399), the visible set
 * through the full filter precedence, the selected card under the rail (oracle #selc), the day dialog
 * off the day head, and the keyboard - Left / Right / T / Escape - as one document listener that
 * ignores keys typed in inputs and selects (oracle 1590). Escape closes an open dialog before anything
 * else (oracle 1583-1586), then clears the selection. The dialog's Select assigns the selection like
 * the oracle (736) rather than toggling it.
 *
 * Changelog:
 *   1.1.0  S1g: FiltersRow, SelectedWOCard, DayDialog, keyboard, filters into visibleWos and the grid,
 *          rail click-to-filter, clearSelect.
 *   1.0.0  Initial S1f.
 */
import { useEffect, useMemo } from 'react';

import { DayDialog } from './DayDialog';
import { FiltersRow } from './FiltersRow';
import { PlannerGrid } from './PlannerGrid';
import { PlannerHeader } from './PlannerHeader';
import { SelectedWOCard } from './SelectedWOCard';
import { WorkerPanel } from './WorkerPanel';
import { byDay, indexWorkers, monthKey, visibleWos } from './rules';
import { usePlannerStore } from './store';
import { usePlannerRange } from './usePlannerRange';
import { MODES, isIso, isMode, navAnchor, todayIso, windowFor } from '../../lib/dates';
import type { Mode } from '../../lib/dates';

import './planner.css';

export const VERSION = '1.1.0';

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

/** Oracle 1590: keys typed into a control belong to the control. */
function inControl(target: EventTarget | null): boolean {
  const tag = target instanceof HTMLElement ? target.tagName : '';
  return tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA';
}

export function PlannerView({ mode, anchor, onSearch }: PlannerViewProps) {
  const store = usePlannerStore();
  const window = useMemo(() => windowFor(mode, anchor), [mode, anchor]);
  const { query, window: check } = usePlannerRange(window.from, window.to);
  const data = query.data;

  const byId = useMemo(() => indexWorkers(data?.workers ?? []), [data]);
  const wos = useMemo(() => visibleWos(data?.wos ?? [], store.cats, store.filters), [data, store.cats, store.filters]);
  const selectedWo = useMemo(() => (data && store.selected ? (data.wos.find((w) => w.id === store.selected) ?? null) : null), [data, store.selected]);
  const dayList = useMemo(() => (store.dayOpen ? (byDay(wos).get(store.dayOpen) ?? []) : []), [wos, store.dayOpen]);

  const today = data?.today ?? todayIso();
  const message = !check.ok ? check.message : query.error ? String(query.error) : '';

  // Oracle 1582-1596 minus drag / undo / R / D / S / A. One listener; re-bound when its inputs change.
  const { dayOpen, closeDay, clearSelect } = store;
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape' && dayOpen) {
        closeDay();
        return;
      }
      if (inControl(ev.target)) return;
      if (ev.key === 'ArrowLeft') onSearch({ anchor: navAnchor(mode, anchor, -1) });
      else if (ev.key === 'ArrowRight') onSearch({ anchor: navAnchor(mode, anchor, 1) });
      else if (ev.key === 't' || ev.key === 'T') onSearch({ anchor: todayIso() });
      else if (ev.key === 'Escape') clearSelect();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [mode, anchor, dayOpen, closeDay, clearSelect, onSearch]);

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
      <FiltersRow
        teams={data?.teams ?? []}
        priorities={data?.priorities ?? []}
        workers={data?.workers ?? []}
        byId={byId}
        filters={store.filters}
        actor={data?.actor ?? 0}
        onTeam={store.setTeam}
        onToggleWorker={store.toggleWorker}
        onPri={store.setPri}
        onUnassigned={store.setUnassigned}
        onQ={store.setQ}
        onClear={store.clearFilters}
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
            filters={store.filters}
            priorities={data?.priorities ?? []}
            selected={store.selected}
            onSelect={store.select}
            onOpenDay={store.openDay}
            onClearSelect={store.clearSelect}
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
            teamId={store.filters.teamId}
            selected={store.filters.workers}
            onToggleWorker={store.toggleWorker}
          />
          <SelectedWOCard wo={selectedWo} labour={data?.labour ?? []} byId={byId} onClear={store.clearSelect} />
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
      <DayDialog
        dateIso={store.dayOpen}
        list={dayList}
        labour={data?.labour ?? []}
        byId={byId}
        priorities={data?.priorities ?? []}
        onSelect={(id) => {
          if (store.selected !== id) store.select(id);
        }}
        onClose={store.closeDay}
      />
    </div>
  );
}

export default PlannerView;
