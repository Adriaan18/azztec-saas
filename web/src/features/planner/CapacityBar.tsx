/**
 * Azztec_SaaS_web_planner_CapacityBar_v1_0_0.tsx  ->  web/src/features/planner/CapacityBar.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.7 · OD-25
 * Oracle:   Planner_v1_8_1.html strip build (668-676), bar markup (294-296)
 *
 * OD-25, signed: the bar is min(100, pct) WIDE and the label carries the REAL pct. RST's capacity
 * column is a placeholder on most workers (1 h/week), so 1000% and 2400% are routine - a bar that
 * clamps the number instead of the width hides exactly the thing a planner needs to see. No
 * placeholder heuristic, no "capped" wording: the bar is full, the label says 1000%.
 *
 * WeekStrip lives here because it is the bar's only consumer in the grid and they share the OD-25
 * rule; the rail's per-row bar is the same component (WorkerPanel imports it).
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { barClass, barWidth, capacityWorkers, fmtNum, pctOf, stripTitle, weekStats } from './rules';
import type { Wo, Worker } from '../../api/client/types.gen';

export const VERSION = '1.0.0';

export type CapacityBarProps = { pct: number };

/** Oracle 294-296 + 675: `<div class="bar"><i class="over" style="width:100%"></i></div>`. */
export function CapacityBar({ pct }: CapacityBarProps) {
  const cls = barClass(pct);
  return (
    <div className="bar">
      <i className={cls} style={{ width: barWidth(pct) }} />
    </div>
  );
}

export type WeekStripProps = {
  weekStart: string;
  weekEnd: string;
  /** the already-visible WOs for the whole window; weekStats slices by date */
  wos: ReadonlyArray<Wo>;
  /** capacity per week for the internal workers, from rules.capacityPerWeek - computed once */
  cap: number;
  workers: ReadonlyArray<Worker>;
};

/** Oracle stripEl (668-676). The planned figure has three states: a number, `?` (count but no hours
 * anywhere) and `0` (nothing that week); the count line only carries a pct when capacity exists. */
export function WeekStrip({ weekStart, weekEnd, wos, cap, workers }: WeekStripProps) {
  const st = weekStats(weekStart, weekEnd, wos);
  const pct = pctOf(st.planned, cap);
  const nWorkers = capacityWorkers(workers).length;
  const planned = st.planned > 0 ? fmtNum(st.planned) : st.count > 0 ? '?' : '0';
  return (
    <div className="strip" title={stripTitle(weekStart, st, cap, nWorkers)}>
      <div className="n">
        {planned} <small>/ {cap > 0 ? fmtNum(cap) : '?'} h</small>
      </div>
      <CapacityBar pct={pct} />
      {st.unknown > 0 ? (
        <div className="u">+{st.unknown} WO no hrs</div>
      ) : (
        <div className="w">{cap > 0 ? `${st.count} WO \u00b7 ${pct}%` : `${st.count} WO`}</div>
      )}
    </div>
  );
}

export default CapacityBar;
