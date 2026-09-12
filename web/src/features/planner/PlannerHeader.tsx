/**
 * Azztec_SaaS_web_planner_PlannerHeader_v1_0_0.tsx  ->  web/src/features/planner/PlannerHeader.tsx
 * Version:  1.0.0   Date: 2026-09-12   Author: Adriaan
 * Spec:     Azztec_SaaS_S1f_Grid_Chunk_Spec_v1_0_0.md §5.9 · OD-29
 * Oracle:   Planner_v1_8_1.html header markup (381-398), renderHeader (619-631)
 *
 * The header bar. Mode buttons and the prev/today/next arrows write the URL (OD-29); the cat chips and
 * the rail button write the store. Totals come from the API's counts, not from a client count, so the
 * number matches what the range query actually returned.
 *
 * 6M is rendered DISABLED rather than hidden: the oracle has it, it needs an API summary shape that is
 * not designed yet (raw log 2026-09-12 §8.5), and a greyed button with a tooltip is an honest gap
 * where a missing button is a silent one.
 *
 * Not here: Suggest, the AI orb, the filters row, keyboard shortcuts - S1g and later (spec §1).
 *
 * Changelog:
 *   1.0.0  Initial S1f.
 */
import { CAT_ORDER, fmtRange, monthLabel } from './rules';
import type { Cat, Cats } from './rules';
import type { Counts } from '../../api/client/types.gen';
import type { Mode, Window } from '../../lib/dates';

export const VERSION = '1.0.0';

const MODE_LABEL: Record<Mode, string> = { week: 'Week', twoweek: '2W', month: 'Month' };
const SIXM_WHY = 'six-month needs an API summary shape - not built yet';

export type PlannerHeaderProps = {
  mode: Mode;
  anchor: string;
  window: Window;
  counts: Counts | null;
  cats: Cats;
  railOpen: boolean;
  onMode: (mode: Mode) => void;
  onNav: (n: number) => void;
  onToday: () => void;
  onCat: (cat: Cat) => void;
  onAllCats: () => void;
  onRail: () => void;
};

export function PlannerHeader({
  mode,
  anchor,
  window,
  counts,
  cats,
  railOpen,
  onMode,
  onNav,
  onToday,
  onCat,
  onAllCats,
  onRail,
}: PlannerHeaderProps) {
  const label = mode === 'month' ? monthLabel(anchor, window.from, window.to) : fmtRange(window.from, window.to);
  return (
    <div className="hdr">
      <span className="title">PLANNER</span>
      <span className="range">{label}</span>
      <div className="seg" id="modes">
        {(Object.keys(MODE_LABEL) as Array<Mode>).map((m) => (
          <button key={m} data-mode={m} className={m === mode ? 'on' : ''} onClick={() => onMode(m)}>
            {MODE_LABEL[m]}
          </button>
        ))}
        <button data-mode="sixm" disabled title={SIXM_WHY}>
          6M
        </button>
      </div>
      <button onClick={() => onNav(-1)} title="previous">
        {'\u2039'}
      </button>
      <button className="gold" onClick={onToday}>
        Today
      </button>
      <button onClick={() => onNav(1)} title="next">
        {'\u203a'}
      </button>
      <div className="cats" id="cats">
        <button data-cat="ALL" onClick={onAllCats}>
          All
        </button>
        {CAT_ORDER.map((c) => (
          <button key={c} data-cat={c} className={cats[c] ? 'on' : ''} onClick={() => onCat(c)}>
            {c === 'DONE' ? 'Done' : c}
          </button>
        ))}
      </div>
      <span className="sp" />
      <span className="totals">
        {counts ? `${counts.wo} WO  |  ${counts.pm} PM  |  ${counts.done} done` : ''}
      </span>
      <button className={railOpen ? 'on' : ''} onClick={onRail} title="workers">
        {'\u2630'}
      </button>
    </div>
  );
}

export default PlannerHeader;
