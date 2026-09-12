/**
 * Azztec_SaaS_web_planner_PlannerGrid_v1_0_0.tsx  ->  web/src/features/planner/PlannerGrid.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.8 · OD-6, OD-23 · Landmines §D
 * Oracle:   Planner_v1_8_1.html renderMonth (633-660), renderWeek (678-693), renderTwoWeek (695-713)
 *
 * Three layouts off one window:
 *   week     - `grid week`, 7 columns, no dow row, no strip (the cells carry the hh line)
 *   twoweek  - `grid twoweek`, 7 + strip column, dow row, two rows each ending in a WeekStrip
 *   month    - `grid`, 7 + strip column, dow row, ceil rows, out-of-month cells dashed
 *
 * byDay() and capacityPerWeek() are computed ONCE here and passed down (Landmines §D: the Ignition
 * version rebuilt the index inside the cell loop and took 40 s on a month of RST). Cells get their
 * list, not the map.
 *
 * `today` is the API's, never the browser's (OD-6). Past / today / out are ISO string comparisons.
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { useMemo } from 'react';
import type { ReactElement } from 'react';

import { DayCell } from './DayCell';
import { WeekStrip } from './CapacityBar';
import { DOW, byDay, capacityPerWeek, monthKey } from './rules';
import { addDays } from '../../lib/dates';
import type { Mode, Window } from '../../lib/dates';
import type { Wo, Worker } from '../../api/client/types.gen';

export const VERSION = '1.0.0';

export type PlannerGridProps = {
  mode: Mode;
  window: Window;
  /** already filtered by cats - the header owns that toggle */
  wos: ReadonlyArray<Wo>;
  /** the API's today (OD-6), not the browser's */
  today: string;
  /** 'yyyy-MM' of the anchor; month mode dashes the cells outside it */
  anchorMonth: string;
  workers: ReadonlyArray<Worker>;
  byId: ReadonlyMap<number, Worker>;
  selected: number;
  onSelect: (id: number) => void;
};

export function PlannerGrid({
  mode,
  window,
  wos,
  today,
  anchorMonth,
  workers,
  byId,
  selected,
  onSelect,
}: PlannerGridProps) {
  const days = useMemo(() => byDay(wos), [wos]);
  const cap = useMemo(() => capacityPerWeek(workers), [workers]);

  /** every date in the window, in order - one pass, no Date arithmetic below this line */
  const dates = useMemo(() => {
    const out: string[] = [];
    for (let i = 0; i < window.days; i++) out.push(addDays(window.from, i));
    return out;
  }, [window.from, window.days]);

  const isMonth = mode === 'month';
  const rows: string[][] = [];
  for (let i = 0; i < dates.length; i += 7) rows.push(dates.slice(i, i + 7));

  const cell = (dateIso: string, col: number, idx: number) => (
    <DayCell
      key={dateIso}
      dateIso={dateIso}
      mode={mode}
      col={col}
      list={days.get(dateIso) ?? []}
      isPast={dateIso < today}
      isToday={dateIso === today}
      out={isMonth && monthKey(dateIso) !== anchorMonth}
      first={isMonth && idx === 0}
      byId={byId}
      selected={selected}
      onSelect={onSelect}
    />
  );

  return (
    <>
      {mode === 'week' ? null : (
        <div className="dow">
          {DOW.map((d) => (
            <div key={d}>{d}</div>
          ))}
          <div className="strip">HOURS / WEEK</div>
        </div>
      )}
      <div className={mode === 'week' ? 'grid week' : mode === 'twoweek' ? 'grid twoweek' : 'grid'}>
        {rows.map((row, r) => (
          <Row key={row[0]} row={row} r={r} mode={mode} cell={cell} wos={wos} cap={cap} workers={workers} />
        ))}
      </div>
    </>
  );
}

type RowProps = {
  row: string[];
  r: number;
  mode: Mode;
  cell: (dateIso: string, col: number, idx: number) => ReactElement;
  wos: ReadonlyArray<Wo>;
  cap: number;
  workers: ReadonlyArray<Worker>;
};

/** One week: seven cells, then the strip in the eighth column unless the mode is week. */
function Row({ row, r, mode, cell, wos, cap, workers }: RowProps) {
  return (
    <>
      {row.map((dateIso, col) => cell(dateIso, col, r * 7 + col))}
      {mode === 'week' ? null : (
        <WeekStrip weekStart={row[0]} weekEnd={row[row.length - 1]} wos={wos} cap={cap} workers={workers} />
      )}
    </>
  );
}

export default PlannerGrid;
