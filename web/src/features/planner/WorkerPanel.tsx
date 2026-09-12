/**
 * Azztec_SaaS_web_planner_WorkerPanel_v1_0_0.tsx  ->  web/src/features/planner/WorkerPanel.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.10 · OD-24, OD-25, OD-26
 * Oracle:   Planner_v1_8_1.html renderRail (771-799)
 *
 * The workers rail. OD-26, measured not guessed: RST has 363 workers = 179 internal + 184 contractors,
 * and only 46 internal have hours on the standing week (72 on the June variety window). So the default
 * is loaded internal, with contractors and loaded-only as toggles and the count line always visible -
 * hidden rows are counted, never silent.
 *
 * The week bars are the API's workerWeeks, already flagged server-side. The load bar is OD-25: full and
 * red at 1000%, with the real number in the tooltip. RST's capacity column is a 1 h/week placeholder on
 * most people (Landmines §E), so those rows are honest noise, not a defect.
 *
 * Read-only: the oracle's click-to-filter and click-the-capacity-to-edit are S1g / S4, so the rows are
 * divs with no handlers and the `.cap` span carries no edit affordance.
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { CapacityBar } from './CapacityBar';
import { countLine, flagCounts, fmtNum, railRows, rowLoad, rowTitle, weekBarTitle, weeksIn } from './rules';
import type { RailOpts } from './rules';
import type { Worker, WorkerWeek } from '../../api/client/types.gen';

export const VERSION = '1.0.0';

export type WorkerPanelProps = {
  workers: ReadonlyArray<Worker>;
  load: Readonly<Record<string, number>>;
  workerWeeks: Readonly<Record<string, Array<WorkerWeek>>>;
  /** civil days in the window - weeksIn() turns it into the capacity multiplier */
  days: number;
  opts: RailOpts;
  onToggleContractors: () => void;
  onToggleLoadedOnly: () => void;
};

export function WorkerPanel({
  workers,
  load,
  workerWeeks,
  days,
  opts,
  onToggleContractors,
  onToggleLoadedOnly,
}: WorkerPanelProps) {
  const weeks = weeksIn(days);
  const r = railRows(workers, load, opts);
  return (
    <div className="card">
      <h3>
        WORKERS <span>({r.rows.length})</span>
      </h3>
      <div className="tog">
        <label>
          <input type="checkbox" checked={opts.loadedOnly} onChange={onToggleLoadedOnly} /> loaded only
        </label>
        <label>
          <input type="checkbox" checked={opts.contractors} onChange={onToggleContractors} /> contractors
        </label>
      </div>
      <div className="tog" data-count>
        {countLine(r, opts)}
      </div>
      <div className="workers">
        {r.rows.length === 0 ? <div className="empty">nobody matches these toggles</div> : null}
        {r.rows.map((w) => (
          <WorkerRow key={w.id} w={w} load={load} weeks={weeks} wks={workerWeeks[String(w.id)] ?? []} />
        ))}
      </div>
    </div>
  );
}

type WorkerRowProps = {
  w: Worker;
  load: Readonly<Record<string, number>>;
  weeks: number;
  wks: ReadonlyArray<WorkerWeek>;
};

/** Oracle 777-790, minus the click handlers. */
function WorkerRow({ w, load, weeks, wks }: WorkerRowProps) {
  const { ld, cap, pct } = rowLoad(w, load, weeks);
  const f = flagCounts(wks);
  return (
    <div className={w.internal ? 'wk' : 'wk contr'} data-worker={w.id} title={rowTitle(w, ld, cap, pct)}>
      <div className="av">{w.initials}</div>
      <div className="nm">
        {w.name}
        <small>
          {w.team}
          {w.skills.length > 0 ? ` \u00b7 ${w.skills[0].title}` : ''}
        </small>
        {wks.length > 0 ? (
          <div className="wkb">
            {wks.map((wk) => (
              <i key={wk.weekStart} className={wk.flag} title={weekBarTitle(wk)} />
            ))}
          </div>
        ) : null}
      </div>
      <div className="ld">
        <b>{fmtNum(ld)} h</b> {'\u00b7'} <span className="cap">{fmtNum(w.hrsPerWeek || 0)}/wk</span>
        <CapacityBar pct={pct} />
        {f.over > 0 || f.under > 0 ? (
          <span className="flags">
            {f.over > 0 ? <b className="over">{f.over} over</b> : null}
            {f.over > 0 && f.under > 0 ? ' \u00b7 ' : ''}
            {f.under > 0 ? <b className="under">{f.under} under</b> : null}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export default WorkerPanel;
