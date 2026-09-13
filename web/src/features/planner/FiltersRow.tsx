/**
 * Azztec_SaaS_web_planner_FiltersRow_v1_0_0.tsx  ->  web/src/features/planner/FiltersRow.tsx
 * Version:  1.0.0   Date: 2026-09-13   Author: Adriaan
 * Spec:     Azztec_SaaS_S1g_Readonly_Chunk_Spec_v1_0_0.md §5.5 · OD-31, OD-34
 * Oracle:   Planner_v1_8_1.html markup 399-412, renderFilters 839-858, wiring 1533-1538
 *
 * The filters row: Team select, the worker multi-select menu (.wsel), Priority select, Unassigned only,
 * the search box, Clear, the hint and the actor label. Markup and class names are the oracle's; the
 * option labels, groups and the hint come from rules.ts so they are pinned there.
 *
 * Local state, deliberately: the menu's open/closed (oracle 1538 toggles a class), and the search text
 * with its 150 ms settle (oracle 1536) - the store only ever sees the trimmed, settled value. A team
 * change clearing the worker selection is the store's job (setTeam), not this component's.
 *
 * Escape inside this row closes the menu and stops there, so the document-level handler in
 * PlannerView does not also clear the selection. Keys typed in the inputs never reach that handler
 * anyway - it checks the target tag, as the oracle does at 1590.
 *
 * No shadcn (OD-31): the menu is the oracle's div + labels + checkboxes with its own CSS.
 *
 * Changelog:
 *   1.0.0  Initial S1g.
 */
import { useEffect, useRef, useState } from 'react';

import { HINT, actorLabel, priorityOptions, teamOptions, workerLabel, workerMenu } from './rules';
import type { Filters } from './rules';
import type { Priority, Team, Worker } from '../../api/client/types.gen';

export const VERSION = '1.0.0';

/** Oracle 1536. */
export const SEARCH_SETTLE_MS = 150;

export type FiltersRowProps = {
  teams: ReadonlyArray<Team>;
  priorities: ReadonlyArray<Priority>;
  workers: ReadonlyArray<Worker>;
  byId: ReadonlyMap<number, Worker>;
  filters: Filters;
  /** the envelope's actor (an int until OD-2) */
  actor: number;
  onTeam: (teamId: number) => void;
  onToggleWorker: (id: number) => void;
  onPri: (pri: number) => void;
  onUnassigned: (on: boolean) => void;
  /** receives the trimmed, settled text */
  onQ: (q: string) => void;
  onClear: () => void;
};

export function FiltersRow({
  teams,
  priorities,
  workers,
  byId,
  filters,
  actor,
  onTeam,
  onToggleWorker,
  onPri,
  onUnassigned,
  onQ,
  onClear,
}: FiltersRowProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [q, setQ] = useState(filters.q);
  const wsel = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // A click outside .wsel closes the menu (the oracle's document click handler).
  useEffect(() => {
    if (!menuOpen) return;
    const onDoc = (ev: MouseEvent) => {
      if (wsel.current && ev.target instanceof Node && !wsel.current.contains(ev.target)) setMenuOpen(false);
    };
    document.addEventListener('click', onDoc);
    return () => document.removeEventListener('click', onDoc);
  }, [menuOpen]);

  // Clear (oracle 1537 sets el('q').value = '') - the only external write to the search text.
  useEffect(() => {
    if (filters.q === '') setQ('');
  }, [filters.q]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const onSearch = (v: string) => {
    setQ(v);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      timer.current = null;
      onQ(v.trim());
    }, SEARCH_SETTLE_MS);
  };

  const groups = workerMenu(workers, filters.teamId);

  return (
    <div
      className="filters"
      onKeyDown={(ev) => {
        if (ev.key === 'Escape' && menuOpen) {
          ev.stopPropagation();
          setMenuOpen(false);
        }
      }}
    >
      <label>
        Team{' '}
        <select value={filters.teamId} onChange={(ev) => onTeam(Number(ev.target.value) || 0)}>
          <option value={0}>All teams</option>
          {teamOptions(teams).map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <div className={menuOpen ? 'wsel open' : 'wsel'} ref={wsel}>
        <button
          type="button"
          onClick={(ev) => {
            ev.stopPropagation();
            setMenuOpen((o) => !o);
          }}
        >
          Worker: <span className="who">{workerLabel(filters, byId)}</span> {'\u25BE'}
        </button>
        <div className="menu">
          {groups.map((g) => (
            <div key={g.label}>
              <div className="grp">{g.label}</div>
              {g.rows.map((r) => (
                <label key={r.id}>
                  <input type="checkbox" checked={!!filters.workers[r.id]} onChange={() => onToggleWorker(r.id)} /> {r.name}{' '}
                  <span className="cap">{r.cap}</span>
                </label>
              ))}
            </div>
          ))}
        </div>
      </div>
      <label>
        Priority{' '}
        <select value={filters.pri} onChange={(ev) => onPri(Number(ev.target.value) || 0)}>
          <option value={0}>Any</option>
          {priorityOptions(priorities).map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        <input type="checkbox" checked={filters.unassigned} onChange={(ev) => onUnassigned(ev.target.checked)} /> Unassigned only
      </label>
      <input
        type="text"
        value={q}
        placeholder="Search WO / title / asset / location"
        onChange={(ev) => onSearch(ev.target.value)}
      />
      <button type="button" onClick={onClear}>
        Clear
      </button>
      <span className="hint">{HINT}</span>
      <span className="sp" />
      <span className="hint" data-actor>
        {actorLabel(actor)}
      </span>
    </div>
  );
}

export default FiltersRow;
