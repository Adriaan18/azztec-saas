/**
 * Azztec_SaaS_web_planner_PlannerView_v1_2_0.tsx  ->  web/src/features/planner/PlannerView.tsx
 * Version:  1.2.0   Date: 2026-11-07   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md 5.11 . OD-6, OD-23, OD-26, OD-29;
 *           Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md 5.12 . OD-30, OD-33, OD-34;
 *           Azztec_SaaS_DP3_Planner_Moves_Chunk_Spec_v1_0_1.md §6 (PlannerView.tsx row) . OD-107, OD-113
 * Oracle:   Planner_v1_8_1.html render 860-866, select 869, nav 871-876, keyboard 1582-1596; the write
 *           side: doMove, undoLast, handleWriteError, showConfirm, the poll and focus guards in wire
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
 * 1.2.0 makes it move (DP3b), as the oracle's flow (OD-113): a chip dropped on another day posts
 * {woId, toIso, expectStartIso, confirm:false}; ok applies the result to every cached window, pushes
 * the undo, toasts with Undo and refetches every window; CONFIRM opens the dialog and Move it posts
 * again with confirm:true; STALE toasts and refetches; NO_IDENTITY / NO_RIGHT / a lost session raise
 * the write banner; anything else toasts. Undo (the toast's button or Ctrl+Z) posts the newest undo
 * dict; a refused undo leaves the stack, a failed one goes back on top (OD-113). The range poll and
 * the focus refetch pause while a drag, a write or the confirm is live. Escape ends a drag first, then
 * the confirm, then the day dialog, then the selection; Enter in the confirm is Move it; Ctrl+Z is
 * inert in an input or a select (OD-113). The click that follows a drop is swallowed (the oracle's
 * 50 ms suppressClick) so a drop never also selects.
 *
 * canMove (OD-107) defaults to false - the read-only planner, unchanged: at RO every chip's movable is
 * mapped false before the grid sees it (no .mv, no grab cursor, no drag line in the tooltip), the drag
 * is inert, Ctrl+Z does nothing and the hint is the read-only one. The API is the gate; this is
 * courtesy. actorId keys the undo stack to the person (store.undoBy).
 *
 * Changelog:
 *   1.2.0  DP3b: moves - the drag (useWoDrag), doMove / undoLast over moves.ts, ConfirmMoveDialog,
 *          Toast, the write banner, Ctrl+Z, the poll pause, the click guard; canMove / actorId props;
 *          the keyboard handler reads its state through a ref, bound once.
 *   1.1.0  S1g: FiltersRow, SelectedWOCard, DayDialog, keyboard, filters into visibleWos and the grid,
 *          rail click-to-filter, clearSelect.
 *   1.0.0  Initial S1f.
 */
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';

import { ConfirmMoveDialog } from './ConfirmMoveDialog';
import { DayDialog } from './DayDialog';
import { FiltersRow } from './FiltersRow';
import { PlannerGrid } from './PlannerGrid';
import { PlannerHeader } from './PlannerHeader';
import { SelectedWOCard } from './SelectedWOCard';
import { Toast, useToast } from './Toast';
import { WorkerPanel } from './WorkerPanel';
import { applyMove, movedToast, postMove, postUndo, undoneToast, whyNotMovable } from './moves';
import type { Outcome } from './moves';
import { HINT, HINT_RW, byDay, indexWorkers, monthKey, visibleWos } from './rules';
import { usePlannerStore } from './store';
import { isPlannerRangeKey, usePlannerRange } from './usePlannerRange';
import { useWoDrag } from './useWoDrag';
import { MODES, isIso, isMode, navAnchor, todayIso, windowFor } from '../../lib/dates';
import type { Mode } from '../../lib/dates';
import type { MovePreview, MoveResult, RangeData, Wo } from '../../api/client/types.gen';

import './planner.css';

export const VERSION = '1.2.0';

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
  /** OD-107: allows(rights.planner, 'RW'). False - the default - is the read-only planner. */
  canMove?: boolean;
  /** the signed-in person's user id; the undo stack belongs to them (store.undoBy) */
  actorId?: number;
};

/** Oracle 1590: keys typed into a control belong to the control. */
function inControl(target: EventTarget | null): boolean {
  const tag = target instanceof HTMLElement ? target.tagName : '';
  return tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA';
}

/** A CONFIRM waiting on the dialog: what Move it posts again, with confirm:true. */
type Pending = { wo: Wo; toIso: string; preview: MovePreview };

export function PlannerView({ mode, anchor, onSearch, canMove = false, actorId = 0 }: PlannerViewProps) {
  const store = usePlannerStore();
  const queryClient = useQueryClient();
  const window = useMemo(() => windowFor(mode, anchor), [mode, anchor]);

  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [writeProblem, setWriteProblem] = useState('');
  const { toast, show: showToast, hide: hideToast } = useToast();
  /** the WOs on screen by id, for the drag - written after each render, read at drag time */
  const woIndex = useRef<ReadonlyMap<number, Wo>>(new Map());

  const setBusyBoth = (on: boolean) => {
    busyRef.current = on;
    setBusy(on);
  };

  /** OD-113: the server's result goes into every cached window at once ... */
  const applyEverywhere = (r: MoveResult) => {
    queryClient.setQueriesData<RangeData>({ predicate: (q) => isPlannerRangeKey(q.queryKey) }, (old) =>
      old ? applyMove(old, r) : old,
    );
  };
  /** ... and then every window is fetched again, so what shows is the server's. */
  const refetchAll = () => {
    void queryClient.invalidateQueries({ predicate: (q) => isPlannerRangeKey(q.queryKey) });
  };

  /** Oracle handleWriteError, for every outcome that is not a success or a confirm. */
  const report = (out: Outcome) => {
    if (out.kind === 'ok') return;
    if (out.kind === 'identity') {
      setWriteProblem(out.message);
      return;
    }
    showToast(out.message);
    if (out.kind === 'stale' || out.kind === 'failed') refetchAll();
  };

  /** Oracle doMove. expectStartIso is the start this planner drew the chip on - the server's STALE check. */
  const doMove = async (wo: Wo, toIso: string, confirm: boolean) => {
    if (busyRef.current) return;
    if (!wo.movable) {
      showToast(whyNotMovable(wo));
      return;
    }
    setBusyBoth(true);
    const out = await postMove({ woId: wo.id, toIso, expectStartIso: wo.start, confirm });
    setBusyBoth(false);
    if (out.kind === 'ok') {
      store.pushUndo(out.result.undo, actorId);
      applyEverywhere(out.result);
      showToast(movedToast(out.result), true);
      refetchAll();
      return;
    }
    if (out.kind === 'confirm') {
      setPending({ wo, toIso, preview: out.preview });
      return;
    }
    report(out);
  };

  /** Oracle undoLast (the move branch). OD-113: refused stays off the stack, failed goes back on. */
  const undoLast = async () => {
    if (busyRef.current) return;
    const u = store.popUndo();
    if (!u) {
      showToast('Nothing to undo');
      return;
    }
    setBusyBoth(true);
    const out = await postUndo(u);
    setBusyBoth(false);
    if (out.kind === 'ok') {
      applyEverywhere(out.result);
      showToast(undoneToast(out.result));
      refetchAll();
      return;
    }
    if (out.kind === 'failed' || out.kind === 'identity') store.pushUndo(u, actorId);
    report(out);
  };

  const confirmYes = () => {
    const p = pending;
    if (!p) return;
    setPending(null);
    void doMove(p.wo, p.toIso, true);
  };

  const drag = useWoDrag({
    enabled: canMove,
    woById: (id) => woIndex.current.get(id),
    onRefuse: (wo) => {
      showToast(whyNotMovable(wo));
    },
    onDrop: (wo, toIso) => {
      void doMove(wo, toIso, false);
    },
  });

  const paused = drag.dragging || busy || pending !== null;
  const { query, window: check } = usePlannerRange(window.from, window.to, { paused });
  const data = query.data;

  // OD-107: at RO no chip is movable, whatever the server says - no .mv, no grab cursor, no drag line.
  const rawWos = data?.wos;
  const allWos = useMemo(() => {
    const list = rawWos ?? [];
    return canMove ? list : list.map((w) => (w.movable ? { ...w, movable: false } : w));
  }, [rawWos, canMove]);
  useEffect(() => {
    woIndex.current = new Map(allWos.map((w) => [w.id, w]));
  }, [allWos]);

  const byId = useMemo(() => indexWorkers(data?.workers ?? []), [data]);
  const wos = useMemo(() => visibleWos(allWos, store.cats, store.filters), [allWos, store.cats, store.filters]);
  const selectedWo = useMemo(
    () => (data && store.selected ? (allWos.find((w) => w.id === store.selected) ?? null) : null),
    [data, allWos, store.selected],
  );
  const dayList = useMemo(() => (store.dayOpen ? (byDay(wos).get(store.dayOpen) ?? []) : []), [wos, store.dayOpen]);

  const today = data?.today ?? todayIso();
  const message = !check.ok ? check.message : query.error ? String(query.error) : '';

  // The undo stack is the signed-in person's: a different person never inherits it.
  const { undoBy, clearUndo } = store;
  useEffect(() => {
    if (undoBy !== 0 && undoBy !== actorId) clearUndo();
  }, [undoBy, actorId, clearUndo]);

  // Oracle 1582-1596 minus R / D / S / A. One listener, bound once; it reads this render's state
  // through the ref, so it never acts on a stale dialog or a stale undo stack.
  const onKey = (ev: KeyboardEvent) => {
    if (ev.key === 'Escape') {
      if (drag.isActive()) {
        drag.cancel();
        return;
      }
      if (pending) {
        setPending(null);
        return;
      }
      if (store.dayOpen) {
        store.closeDay();
        return;
      }
    }
    if (pending) {
      // the confirm is open: Enter is Move it (oracle 1587), everything else waits
      if (ev.key === 'Enter' && !(ev.target instanceof HTMLSelectElement)) {
        ev.preventDefault();
        confirmYes();
      }
      return;
    }
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === 'z' || ev.key === 'Z')) {
      if (!canMove || inControl(ev.target)) return; // OD-113: a text box keeps its own undo
      ev.preventDefault();
      void undoLast();
      return;
    }
    if (inControl(ev.target)) return;
    if (ev.key === 'ArrowLeft') onSearch({ anchor: navAnchor(mode, anchor, -1) });
    else if (ev.key === 'ArrowRight') onSearch({ anchor: navAnchor(mode, anchor, 1) });
    else if (ev.key === 't' || ev.key === 'T') onSearch({ anchor: todayIso() });
    else if (ev.key === 'Escape') store.clearSelect();
  };
  const keyRef = useRef(onKey);
  useEffect(() => {
    keyRef.current = onKey;
  });
  useEffect(() => {
    const listener = (ev: KeyboardEvent) => {
      keyRef.current(ev);
    };
    document.addEventListener('keydown', listener);
    return () => document.removeEventListener('keydown', listener);
  }, []);

  return (
    <div className={drag.dragging ? 'wm-planner dragging' : 'wm-planner'}>
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
        hint={canMove ? HINT_RW : HINT}
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
      {writeProblem ? (
        <div className="banner on" data-write>
          <b>Problem</b>
          <span>{writeProblem}</span>
          <span className="x" title="Dismiss" onClick={() => setWriteProblem('')}>
            {'×'}
          </span>
        </div>
      ) : null}
      <div className="body">
        <div className="grid-wrap" onPointerDown={drag.onPointerDown}>
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
            onSelect={(id) => {
              if (!drag.clickSuppressed()) store.select(id);
            }}
            onOpenDay={(key) => {
              if (!drag.clickSuppressed()) store.openDay(key);
            }}
            onClearSelect={() => {
              if (!drag.clickSuppressed()) store.clearSelect();
            }}
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
          Planner UI {VERSION} {'·'} {MODES.length} modes {'·'} window {window.days} d
        </span>
        <span className="sp" />
        <span>
          {data ? `lib ${data.libVersion} · api ${data.apiVersion} · range ${data.ms} ms` : ''}
          {data && query.isFetching ? ' · refreshing...' : ''}
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
      <ConfirmMoveDialog preview={pending ? pending.preview : null} onYes={confirmYes} onNo={() => setPending(null)} />
      <Toast
        toast={toast}
        onUndo={() => {
          hideToast();
          void undoLast();
        }}
      />
      <div className="drag-layer" ref={drag.layerRef} />
    </div>
  );
}

export default PlannerView;
